'''
Variables: 
    one per user per column-bucket combination
        Each variable is a Binary (0/1)
Constraints:
    Each column has sum equal to number of users
        sum of all variables is equal to number of users
    Each user is in one column only.
        So for each user the sum of that user/column variables is 1
    Each bucket has a certain range of number of users
        Sum of all variables assigned to that bucket is between X and Y
    Pairs of buckets have a certain range of number of users
        Sum of all V's assigned to those two buckets is between X and Y
    And so on....
'''

# Import PuLP modeler functions
import pulp
import json
import pandas as pd
import pprint
import time
import bucketHandler
import anonymizer
import itertools
import statistics
import random
import os.path
import sys
filePath = __file__
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import scores.score
pp = pprint.PrettyPrinter(indent=4)
doprint = False
useSolver = 'gurobi'
#useSolver = 'default'

class lrAttack:
    def __init__(self, seed, anonymizerParams, tableParams, solveParams, force=False,):
        pp.pprint(tableParams)
        self.seed = seed
        self.an = anonymizer.anonymizer(seed, anonymizerParams, tableParams)
        self.cols = self.an.cols
        self.sp = solveParams
        self.results = {'params':{}}
        self.results['params']['seed'] = seed
        self.results['params']['tableParams'] = self.an.tp
        self.results['params']['anonymizerParams'] = self.an.ap
        self.results['params']['solveParams'] = self.sp
        self.results['solution'] = {'explain': []}
        self.results['buckets'] = None
        self.priorKnowledge = self.an.ap['priorKnowledge']
        self.force = force
        self.fileName = self.makeFileName(seed)
        if 'numSDs' not in self.sp:
            self.sp['numSDs'] = 3.0

    def _makeFileNameWork(self, fileName, params):
        for key in sorted(list(params.keys())):
            val = params[key]
            if type(val) == list:
                for lv in val:
                    fileName += f"{lv}_"
            else:
                fileName += f"{val}_"
        return fileName

    def makeFileName(self, seed):
        fileName = f"s{seed}_"
        fileName = self._makeFileNameWork(fileName,self.an.tp)
        fileName = self._makeFileNameWork(fileName,self.an.ap)
        fileName = self._makeFileNameWork(fileName,self.sp)
        fileName = fileName[:-1]
        return fileName

    def solutionToTable(self,prob):
        data = {}
        log = []
        for col in self.cols:
            data[col] = []
        for aid in self.choices:
            for bkt in self.choices[aid]:
                cols,vals = self.bh.getColsValsFromBkt(bkt)
                if len(cols) == 1:
                    outcome = pulp.value(self.choices[aid][bkt])
                    log.append({'aid':aid,'col':cols[0],'val':vals[0],'outcome':outcome})
                    # We compare with 0.5 here rather than == 1.0 because there is some machine
                    # error in the value and it is not exactly 1.0...
                    if outcome > 0.5:
                        data[cols[0]].append(int(vals[0]))
        # Check that data has valid shape
        for k,v in data.items():
            if len(v) != self.results['params']['numAids']:
                print(f"ERROR: solutionToTable: bad data {len(v)} against {self.results['params']['numAids']} ... storing problem")
                pp.pprint(self.choices)
                pp.pprint(self.results)
                pp.pprint(data)
                pp.pprint(log)
                self.storeProblem(prob)
                return
        dfNew = pd.DataFrame.from_dict(data)
        dfNew.sort_values(by=self.cols,inplace=True)
        dfNew.reset_index(drop=True,inplace=True)
        self.results['reconstructedTable'] = dfNew.to_dict()

    def getTrueCountStatGuess(self,cols,vals,df):
        # We want to know the fraction of rows in df that have these vals
        query = ''
        for col,val in zip(cols,vals):
            query += f"({col} == {val}) and "
        query = query[:-5]
        dfC = df.query(query)
        numMatchRows = len(dfC.index)
        totalRows = len(df.index)
        return numMatchRows, numMatchRows/totalRows

    def measureGdaScore(self,dfOrig,dfRecon):
        s = scores.score.score()
        cols = dfOrig.columns.tolist()
        sAggr = dfRecon.groupby(cols).size()
        numSkipped = 0
        i = 0
        for (vals,cnt) in sAggr.iteritems():
            # We only want to consider individuals for whom we don't have prior knowledge
            aid = f"a{i}"
            i += 1
            if aid in self.aidsKnown:
                numSkipped += 1
                continue
            if cnt == 1:
                # We can make a singling out attack on this individual
                trueCount,statGuess = self.getTrueCountStatGuess(cols,vals,dfOrig)
                makesClaim = True  # We are making a claim
                claimHas = True    # We are claiming that victim has attributes
                if trueCount == 1:
                    claimCorrect = True
                else:
                    claimCorrect = False
                s.attempt(makesClaim,claimHas,claimCorrect,statGuess)
            else:
                makesClaim = False
                claimHas = None      # don't care
                claimCorrect = None     # don't care
                statGuess = None
                for _ in range(cnt):
                    s.attempt(makesClaim,claimHas,claimCorrect,statGuess)
        cr,ci,_ = s.computeScore()
        return cr,ci,numSkipped

    def measureMatchDf(self,dfOrig,dfRecon):
        ''' Measures four things:
            1. The reconstuction quality (how many rows from dfOrig match rows in dfRecon,
               using each row in dfRecon at most once) as a fraction from 0 to 1
            2. The fraction of rows in the reconstructed that are considered non-attackable
               (can't be singled out or inferred)
            3. The fraction of rows in the reconstructed table that are attackable but the
               attack is incorrect (singling-out or inference is wrong)
            4. The fraction of rows in the reconstructed table that are attackable and the
               attack correct
        '''
        # I don't find a nice pandas method to do this, so brute force it
        # dfRcopy will be destroyed as we go
        dfRcopy = dfRecon.copy()
        totalRows = len(dfOrig.index)
        matchingRows = 0
        attackableButWrong = 0
        attackableAndRight = 0
        cols = dfOrig.columns.tolist()
        for i, s in dfOrig.iterrows():
            # for each row in dfOrig, see if there is a perfect match in dfRcopy
            query = ''
            for col in cols:
                query += f"({col} == {s[col]}) and "
            query = query[:-5]
            # First check basic reconstruction
            dfC = dfRcopy.query(query)
            if len(dfC.index) > 0:
                # There is at least one matching row.
                matchingRows += 1
                index = dfC.index[0]
                dfRcopy = dfRcopy.drop(index)
            # Then check if an attack is possible and is correct or wrong
            dfR = dfRecon.query(query)
            dfO = dfOrig.query(query)
            if len(dfR.index) == 1:
                # The reconstructed table tells us that this row (user) is singled out ...
                if len(dfO.index) == 1:
                    # ... and indeed that is the case in the original table. So singling-out violation.
                    attackableAndRight += 1
                else:
                    attackableButWrong += 1
            elif len(dfR.index) > 1:
                # Possible inference. We are looking for the case where the reconstructed table
                # shows that N-1 columns definately infers the Nth column, and that this is in
                # fact true in the original table
                infer = False
                for colComb in itertools.combinations(cols,len(cols)-1):
                    # colComb contains the N-1 columns
                    query = ''
                    for col in colComb:
                        query += f"({col} == {s[col]}) and "
                    query = query[:-5]
                    dfRInfer = dfRecon.query(query)
                    # If all rows in dfInfer are identical, then the Nth column can be inferred from
                    # the other two columns, so the row being evaluated in the reconstructed table
                    # can in fact be used to violate privacy
                    if len(dfRInfer.drop_duplicates().index) == 1:
                        # There is only one value for the Nth row, so inference is possible. Now check
                        # the original table
                        dfOInfer = dfOrig.query(query)
                        if len(dfOInfer.drop_duplicates().index) == 1:
                            # Same for the original table. So now just check to make sure that the
                            # inferred value is in fact the right one
                            if dfRInfer.iloc[0].equals(dfOInfer.iloc[0]):
                                infer = True
                if infer:
                    attackableAndRight += 1
                else:
                    attackableButWrong += 1
        matchFrac = round((matchingRows/totalRows),3)
        nonAttackable = totalRows - attackableAndRight - attackableButWrong
        nonAttackableFrac = round((nonAttackable/totalRows),3)
        attackableAndRightFrac = round((attackableAndRight/totalRows),3)
        attackableButWrongFrac = round((attackableButWrong/totalRows),3)
        return matchFrac, nonAttackableFrac, attackableAndRightFrac, attackableButWrongFrac

    def measureMatch(self,force=False):
        ''' This makes two sets of measures. One is for row-level reconstruction quality (measures
            individual rows). The other measures aggregates, and is used to help determine
            wy row-level reconstruction is good or bad.
        
            For row-level, there are three measures we are interested in. One is simply the fraction
            of rows that we guessed right (this shows how well we reconstructed, and is
            for instance the measure the US Census uses). (matchFraction)
            A second measure is how much this improves over random guessing (matchImprove).
            A third is the fraction of the matched rows are either unique (and therefore can
            be singled out), or not unique but where a column can be inferred from the other
            columns.

            For aggregates, we measure the absolute error between the aggregates counts of the
            original and reconstructed data.
        '''
        if not force and 'reconstructedTable' not in self.results:
            # Failed to find solution
            self.results['solution']['matchFraction'] = None
            self.results['solution']['attackableAndRightFrac'] = None
            self.results['solution']['nonAttackableFrac'] = None
            self.results['solution']['attackableButWrongFrac'] = None
            self.results['solution']['matchImprove'] = None
            self.results['solution']['aggregateErrorAvg'] = None
            self.results['solution']['aggregateErrorTargetAvg'] = None
            self.results['solution']['confidenceImprovement'] = None
            self.results['solution']['claimRate'] = None
            self.results['solution']['numSkippedBecauseKnown'] = None
            return
        if 'reconstructedTable' in self.results:
            res = self.results
        else:
            path = self.getResultsPath()
            if not os.path.exists(path):
                return
            with open(path, 'r') as f:
                res = json.load(f)
            if 'reconstructedTable' not in res:
                return None
        dfOrig = pd.DataFrame.from_dict(res['originalTable'])
        dfRe = pd.DataFrame.from_dict(res['reconstructedTable'])
        cr,ci,numSkipped = self.measureGdaScore(dfOrig,dfRe)
        self.results['solution']['numSkippedBecauseKnown'] = numSkipped
        self._addExplain("numSkippedBecauseKnown: Individuals not part of GDA score because known")
        self.results['solution']['confidenceImprovement'] = ci
        self._addExplain("confidenceImprovement: GDA Score, precent correct claims over statistical guess")
        self.results['solution']['claimRate'] = cr
        self._addExplain("claimRage: GDA Score, percent individuals for which claim is made")
        # First row-level reconstruction
        matchFraction, nonAttackableFrac, attackableAndRightFrac, attackableButWrongFrac = self.measureMatchDf(dfOrig, dfRe)
        res['solution']['matchFraction'] = matchFraction
        self._addExplain("matchFraction: Fraction of correctly reconstructed rows")
        res['solution']['nonAttackableFrac'] = nonAttackableFrac
        self._addExplain("nonAttackableFrac: Fraction of reconstructed rows that could not be singled out or inferred")
        res['solution']['attackableAndRightFrac'] = attackableAndRightFrac
        self._addExplain("attackableAndRightFrac: Fraction of attackable rows where the attack is correct")
        res['solution']['attackableButWrongFrac'] = attackableButWrongFrac
        self._addExplain("attackableButWrongFrac: Fraction of attackable rows where the attack is not correct")
        dfRan = self.an.makeRandomTable()
        if len(dfRan.index) != len(dfOrig.index):
            print(f"measureMatch: error: tables not same length")
            print(dfOrig)
            print(dfRan)
            quit()
        matchRandom,_,_,_ = self.measureMatchDf(dfOrig, dfRan)
        if matchRandom == 1.0:
            print("Wow, random table matches original table!")
            print(dfOrig)
            print(dfRan)
            res['solution']['matchImprove'] = 0
        else:
            res['solution']['matchImprove'] = (matchFraction - matchRandom) / (1.0 - matchRandom)
        self._addExplain("matchImprove: Improvement in reconstructed table over random table")
        # Then aggregates
        errsTrue,errsTarget = self.measureAggregatesDf(dfOrig, dfRe)
        res['solution']['aggregateErrorAvg'] = statistics.mean(errsTrue)
        self._addExplain("aggregateErrorAvg: Average of absolute errors in bucket counts, original versus reconstructed")
        res['solution']['aggregateErrorTargetAvg'] = statistics.mean(errsTarget)
        self._addExplain("aggregateErrorTargetAvg: Average of absolute errors in elastic target, original versus reconstructed")

    def measureAggregatesDf(self, dfOrig, dfRe):
        errsTrue = []
        errsTarget = []
        # loop through all aggregates for all dimensions
        for fullComb in self.combColIterator():
            # Now we make a dataframe query out of the combination
            query = ''
            for entry in fullComb:
                # entry[0] is the column name, entry[1] is the bucket value
                query += f"{entry[0]} == {entry[1]} and "
            query = query[:-5]
            cntOrig = dfOrig.query(query).shape[0]
            cntRe = dfRe.query(query).shape[0]
            errsTrue.append(abs(cntOrig - cntRe))
            bkt = self.bh.getBktFromColValPairs(fullComb)
            bktData = self.bh.buckets[bkt]
            if cntOrig != bktData['trueCount']:
                print(f"ERROR: measureAggregatesDf: mismatched counts on {bkt} ({cntOrig}, {bktData['trueCount']}")
            targetVal = self.getTargetVal(bktData)
            errsTarget.append(abs(cntRe - targetVal))
        return errsTrue,errsTarget

    def problemAlreadyAttempted(self):
        ''' Returns true if the problem was already tried (whether solved or not)
        '''
        path = self.getResultsPath()
        if not os.path.exists(path):
            return False
        with open(path, 'r') as f:
            res = json.load(f)
            if 'solution' in res and 'solveStatus' in res['solution']:
                return True
        return False

    def problemAlreadySolved(self):
        ''' Returns true if the problem was already tried (whether solved or not)
        '''
        path = self.getResultsPath()
        if not os.path.exists(path):
            return False
        with open(path, 'r') as f:
            res = json.load(f)
            if 'solution' in res and 'solveStatus' in res['solution']:
                if res['solution']['solveStatus'] == 'Optimal':
                    return True
        return False

    def solutionAlreadyMeasured(self):
        ''' Returns true if the match fraction already measured
        '''
        path = self.getResultsPath()
        if not os.path.exists(path):
            return False
        with open(path, 'r') as f:
            res = json.load(f)
            if ('solution' in res):
                # add any new measurement here
                return True
        return False

    def getResultsPath(self):
        name = self.fileName + '_results.json'
        path = os.path.join('results',name)
        return path

    def saveResults(self,results=None):
        if not results:
            results = self.results
        path = self.getResultsPath()
        with open(path, 'w') as f:
            json.dump(results, f, indent=4, sort_keys=True)

    def combColIterator(self):
        for i in range(len(self.cols)):
            # Get all combinations with i columns
            for colComb in itertools.combinations(self.cols,i+1):
                prod = []
                for col in colComb:
                    tups = []
                    for bkt in self.an.df[col].unique():
                        tups.append((col,bkt))
                    prod.append(tups)
                for fullComb in itertools.product(*prod):
                    yield fullComb
    
    def makeElastic(self,cmin,cmax,penaltyFreeFrac):
        if cmin == cmax:
            return cmin,cmax
        if penaltyFreeFrac == 1.0:
            return cmin,cmax
        mid = (cmax-cmin)/2
        distance = (cmax-mid)*penaltyFreeFrac
        emax = mid + distance
        emin = mid - distance
        emax = min(cmax,emax)
        emin = max(cmin,emin)
        return emin,emax

    def aidInBucket(self,aid,bucket,origTab):
        cols,vals = self.bh.getColsValsFromBkt(bucket)
        for col,val in zip(cols,vals):
            if str(origTab[col][aid]) != val:
                return False
        return True

    def makePriorKnowledge(self,aids):
        if self.priorKnowledge == 'none':
            return []
        if self.priorKnowledge == 'all':
            return aids.copy()
        if self.priorKnowledge == 'all-but-one':
            numKnown = len(aids) - 1
        else:
            numKnown = int(len(aids)/2)
        return random.sample(aids, k=numKnown)

    def makeProblem(self):
        # First check to see if there is already an LpProblem to read in. Note that the
        # problem runs in rounds, where each new solution generates more constraints to prevent
        # the prior solution
        self.an.makeTable()
        self.results['params']['columns'] = self.cols
        self.results['params']['numAids'] = self.an.numAids
        self.results['params']['colVals'] = self.an.colVals
        self.results['originalTable'] = self.an.df.to_dict()
        numBuckets = 0
        numSuppressedBuckets = 0
        numIgnoredBuckets = 0
        if self.force == False:
            prob = self.readProblem()
            if prob:
                return prob

        # TODO: For now, I'm using the correct number of AIDs. In practice, this might be
        # noisy, so later maybe we'll accommodate that
        numAids = self.an.numAids
        # I want a variable for every user / column / bucket combination.
        if doprint: print("Here are the users")
        aids = [f"a{i}" for i in range(numAids)]
        if doprint: print(aids)
        if doprint: print("Here is the original table")
        # The original table is a dict of dicts, first key column ('i0'), second key
        # The index of the aid (0, 1, ...)
        if doprint: pp.pprint(self.results['originalTable'])
        # But since I'm using 'aXX' to denote AID, I want to re-key the original table
        origTab = {}
        for colKey,colVals in self.results['originalTable'].items():
            origTab[colKey] = {}
            for aidKey,aidVal in colVals.items():
                newKey = f"a{aidKey}"
                origTab[colKey][newKey] = aidVal
        if doprint: pp.pprint(origTab)
        self.aidsKnown = self.makePriorKnowledge(aids)
        if doprint: print("Here are the prior known aids:")
        if doprint: print(self.aidsKnown)
        
        # I'm going to make a dict that has all the column/bucket combinations and associated counts
        # The counts are min and max expected given noise assignment
        buckets = {}
        cols = self.an.colNames()
        if doprint: print(cols)
        for col in cols:
            buckets[col] = self.an.distinctVals(col)
            buckets[col] = list(self.an.df[col].unique())
        if doprint: pp.pprint(buckets)
        # At this point, `buckets` contains a list of distinct values per column
        # We are presuming that the anonymization is such that such a list can be
        # obtained by the attacker. (In practice this could be done with bucketization.)
        
        # This probably not the most efficient, but I'm going to determine the count range
        # of every combination of columns and values (buckets) individually. However, some
        # buckets may be suppressed, in which case the suppress variable is True
        self.bh = bucketHandler.bucketHandler(cols,self.an)
        for fullComb in self.combColIterator():
            # Now we make a dataframe query out of the combination
            query = ''
            varName = ''
            combCols = []
            combVals = []
            for entry in fullComb:
                # entry[0] is the column name, entry[1] is the bucket value
                query += f"{entry[0]} == {entry[1]} and "
                varName += f"{entry[0]}.v{entry[1]}."
                combCols.append(entry[0])
                combVals.append(entry[1])
            query = query[:-5]
            varName = varName[:-1]
            suppress,trueCount,sd,minPossible,noisyCount_mean = self.an.queryForCount(query)
            if suppress:
                # bucket is suppressed
                numSuppressedBuckets += 1
                cmin = 0
                cmax = noisyCount_mean + (self.sp['numSDs'] * sd)
                if cmax == 0:
                    # Bucket couldn't hold any aids anyway, so can ignore
                    numIgnoredBuckets += 1
                    continue
                # Make elastic constraints
                emin,emax = self.makeElastic(cmin,cmax,self.sp['elasticLcf'])
            else:
                # Compute the possible range of values
                cmin = noisyCount_mean - (self.sp['numSDs'] * sd)
                cmax = noisyCount_mean + (self.sp['numSDs'] * sd)
                # We know we can't have count lower than the suppression lowThresh
                # because that would be suppressed
                cmin = max(minPossible,cmin)
                cmax = max(minPossible,cmax)
                # Make elastic constraints
                emin,emax = self.makeElastic(cmin,cmax,self.sp['elasticNoise'])
            self.bh.addBucket(combCols,combVals,cmin,cmax,emin,emax,
                              trueCount,noisyCount_mean,suppress,sd,minPossible)
            numBuckets += 1
        self.results['solution']['numBuckets'] = numBuckets
        self._addExplain("numBuckets: Total number of buckets, all dimensions")
        self.results['solution']['numSuppressedBuckets'] = numSuppressedBuckets
        self._addExplain("numSuppressedBuckets: Buckets suppressed by anonymizer")
        self.results['solution']['numIgnoredBuckets'] = numIgnoredBuckets
        self._addExplain("numIgnoredBuckets: Buckets ignored when making constraints")
        if doprint: print("Initial bucket table:")
        if doprint: print(self.bh.df)
        
        '''
        At this point, `aids` contains a list of all "users", and bh.df contains
        all possible buckets and associated count ranges.
        '''
        # Strip away any rows from bh.df where ALL rows for a given dimension (number of
        # columns) are suppressed.
        # TODO: This is to shrink the number of constraints, but we could also try skipping
        # this step because then the constraints will ensure that the suppressed buckets don't
        # have a greater than suppressed number of users
        if False:
            self.results['solution']['numStripped'] = self.bh.stripAwaySuppressedDimensions()
        else:
            self.results['solution']['numStripped'] = 0
        self._addExplain("numStripped: Rows stripped away because all rows for a dimension were suppressed")
        if doprint: print("Bucket table after stripping suppressed dimensions:")
        if doprint: print(self.bh.df)
        self.results['buckets'] = self.bh.buckets

        # The prob variable is created to contain the problem data
        prob = pulp.LpProblem("Attack-Problem",pulp.LpMinimize)
        cnum = 0

        print("The decision variables are created")
        # allCounts is a dict keyed by bucket (i.e. 'Ci0V0.Ci1V10', which means the
        # 2d bucket where column 0 has value 0 and column 1 has value 10), and whose
        # values contain the count ranges
        allCounts = self.bh.getAllCounts()
        if doprint: pp.pprint(allCounts)
        # The following builds the variables for all combinations of aids and buckets
        # in spite of the fact that we may know some of them. (That knowledge is later
        # captured in constraints.)
        self.choices = pulp.LpVariable.dicts("Choice", (aids, allCounts.keys()), cat='Binary')
        self.results['solution']['numChoices'] = len(aids) * len(allCounts)
        self._addExplain("numChoices: Total number of variables for the solver")
        if doprint: pp.pprint(self.choices)
        if doprint: pp.pprint(prob)
        
        print("We do not define an objective function since none is needed")
        # The following dummy object was a work-around for a bug in the
        # to_json call.
        if False:
            dummy=pulp.LpVariable("dummy",0,0,pulp.LpInteger)
            prob += 0.0*dummy
        
        # Now we need to add to self.choices the variables for the prior known aids
        print("Constraints for the prior-known AIDs")
        for (aid,bkt) in [(x,y) for x in self.aidsKnown for y in allCounts.keys()]:
            if self.aidInBucket(aid,bkt,origTab):
                prob += pulp.lpSum([self.choices[aid][bkt]]) == 1, f"{cnum}_prior_known_aid"
            else:
                prob += pulp.lpSum([self.choices[aid][bkt]]) == 0, f"{cnum}_prior_known_aid"
            cnum += 1
        if doprint: pp.pprint(prob)

        print("Constraints ensuring that each bucket has sum in range of the number of its users")
        for bkt,cnts in allCounts.items():
            if cnts['cmin'] == cnts['cmax']:
                # Only one possible value
                prob += pulp.lpSum([self.choices[aid][bkt] for aid in aids]) == cnts['cmin'], f"{cnum}_num_users_per_bkt"
                '''
                constraint_LHS = pulp.LpAffineExpression([(self.choices[aid][bkt],1) for aid in aids])
                constraint = pulp.LpConstraint(e=constraint_LHS, sense=pulp.LpConstraintEQ, name=f"{cnum}_num_users_per_bkt", rhs=cnts['cmin'])
                conElastic = constraint.makeElasticSubProblem(penalty = 100, proportionFreeBoundList = [0.0,0.0])
                prob.extend(conElastic)
                '''
                cnum += 1
            else:
                # Range of values, so need two constraints
                prob += pulp.lpSum([self.choices[aid][bkt] for aid in aids]) >= cnts['cmin'], f"{cnum}_num_users_per_bkt"
                '''
                constraint_LHS = pulp.LpAffineExpression([(self.choices[aid][bkt],1) for aid in aids])
                constraint = pulp.LpConstraint(e=constraint_LHS, sense=pulp.LpConstraintGE, name=f"{cnum}_num_users_per_bkt", rhs=cnts['cmin'])
                conElastic = constraint.makeElasticSubProblem(penalty = 100, proportionFreeBoundList = [0.0,0.0])
                prob.extend(conElastic)
                '''
                cnum += 1
                prob += pulp.lpSum([self.choices[aid][bkt] for aid in aids]) <= cnts['cmax'], f"{cnum}_num_users_per_bkt"
                '''
                constraint_LHS = pulp.LpAffineExpression([(self.choices[aid][bkt],1) for aid in aids])
                constraint = pulp.LpConstraint(e=constraint_LHS, sense=pulp.LpConstraintLE, name=f"{cnum}_num_users_per_bkt", rhs=cnts['cmax'])
                conElastic = constraint.makeElasticSubProblem(penalty = 100, proportionFreeBoundList = [0.0,0.0])
                prob.extend(conElastic)
                '''
                cnum += 1
                if cnts['emax'] < cnts['cmax']:
                    # Make the elastic constraints
                    constraint_LHS = pulp.LpAffineExpression([(self.choices[aid][bkt],1) for aid in aids])
                    # `targetVal` is a point in the middle of the penalty-free range defined by emin and emax
                    targetVal = self.getTargetVal(cnts)
                    targetVal = cnts['emin'] + ((cnts['emax'] - cnts['emin'])/2)
                    # The penalty-free range is defined by a fraction of the target value:
                    # https://coin-or.github.io/pulp/guides/how_to_elastic_constraints.html
                    # Here, emin and emax are the actual low and high values of the penalty-free range.
                    # We need to convert these into a target value fraction
                    penaltyFracLow = (targetVal - cnts['emin']) / targetVal
                    penaltyFracHigh = (cnts['emax'] - targetVal) / targetVal
                    constraint = pulp.LpConstraint(e=constraint_LHS, sense=pulp.LpConstraintEQ, name=f"{cnum}_elastic_num_users_per_bkt", rhs=targetVal)
                    conElastic = constraint.makeElasticSubProblem(penalty = 100, proportionFreeBoundList = [penaltyFracLow,penaltyFracHigh])
                    prob.extend(conElastic)
        if doprint: pp.pprint(prob)
        
        print("Constraints ensuring that each user is in one bucket per column or combination")
        # scales as buckets * aids
        for i in range(len(cols)-1):
            # Get all combinations with i columns
            for colComb in itertools.combinations(cols,i+1):
                dfComb = self.bh.getColDf(colComb)
                if dfComb.empty:
                    continue
                for aid in aids:
                    prob += pulp.lpSum([self.choices[aid][bkt] for bkt in dfComb['bkt'].tolist()]) == 1, f"{cnum}_one_user_per_bkt_set"
                    cnum += 1
        if doprint: pp.pprint(prob)
        
        print("Constraints ensuring that each user in c1b1 is in one of c1b1.c2bX")
        print("    or users in c1b1.c2b1 are in one of c1b1.c2b1.c3bX")
        # TO do this, we want to loop through every combination of columns, and for each
        # combination, find one additional column and get all the sub-buckets
        # Note this constraint scales poorly and we might need to think of a work-around
        for s,dfSub,scol in self.bh.subBucketIterator():
            # s is a pandas series for the bucket. dfSub is a dataframe with the bucket's
            # sub-buckets. scol is the name of the column comprising the sub-buckets.
            allBkts = dfSub['bkt'].tolist()
            allBkts.append(s['bkt'])
            # Now I have buckets and sub-buckets (in `allBkts`). Any user is either
            # in the bucket and one sub-bucket (sum==2), or in neither (sum==0).
            # Because of earlier constraints, the user can't be in more than one bucket
            # or more than one sub-bucket. As a result, we don't need to worry about
            # a user being in more than 2 buckets, and obviously we don't need to worry
            # about the user being in less than 0 buckets. So all we need to do here
            # is make sure the user isn't in one bucket total. We can do this with
            # sum of subBkts + -1*bkt1 = 0
            # Make the per-variable factors
            # TODO: this only correct if the bucket has no noice (cmin == cmax). If the
            # bucket has noise, then we'll need two constraints (I think)
            factors = [1.0 for _ in range(len(allBkts))]
            factors[-1] = -1.0
            for aid in aids:
                prob += pulp.lpSum([factors[j]*self.choices[aid][allBkts[j]] for j in range(len(allBkts))]) == 0, f"{cnum}_bkt_sub_bkt"
                cnum += 1
        self.results['solution']['numConstraints'] = cnum-1
        self._addExplain("numConstraints: Total number of constraints for the solver")
        if doprint: pp.pprint(prob)
        return prob

    def getTargetVal(self,bktData):
        targetVal = bktData['emin'] + ((bktData['emax'] - bktData['emin'])/2)
        return targetVal

    def _addExplain(self,msg):
        self.results['solution']['explain'].append(msg)

    def _buildChoicesDict(self,vars):
        self.choices = {}
        for key,val in vars.items():
            _,aid,bkt = key.split('_')
            if aid not in self.choices:
                self.choices[aid] = {}
            if bkt in self.choices[aid]:
                pp.pprint(self.choices)
                print("ERROR: buildChoicesDict: aid {aid}, bkt {bkt}")
            self.choices[aid][bkt] = val

    def readProblem(self):
        # Read the PuLP problem
        name = self.fileName + '_prob.json'
        path = os.path.join('results',name)
        if not os.path.isfile(path):
            return None
        vars, prob = pulp.LpProblem.from_json(path)
        self._buildChoicesDict(vars)
        print(f"Reading problem from file {path}")
        '''
        # Read the choices
        name = self.fileName + '_choices.json'
        path = os.path.join('results',name)
        with open(path, 'w') as f:
            self.choices = json.load(f)
        '''
        return prob

    def solve(self,prob):
        start = time.time()
        pulp.LpSolverDefault.msg = 1
        if useSolver == 'gurobi':
            print("Using GUROBI_CMD solver")
            # no time limit defaults to infinity
            #prob.solve(pulp.GUROBI_CMD())
            prob.solve(pulp.GUROBI_CMD(timeLimit=1200))
            #prob.solve(pulp.GUROBI_CMD(timeLimit=1))
        else:
            print("Using Pulp default solver")
            prob.solve()
        end = time.time()
        self.results['solution']['elapsedTime'] = round((end - start),2)
        self.results['solution']['solveStatus'] = pulp.LpStatus[prob.status]
        return self.results['solution']['solveStatus']

    def storeProblem(self,prob):
        # Store the PuLP problem
        name = self.fileName + '_prob.json'
        path = os.path.join('results',name)
        prob.to_json(path)
        name = self.fileName + '_prob.lp'
        path = os.path.join('results',name)
        prob.writeLP(path)
    
if __name__ == "__main__":
    # Forces the solver to run even if there is already a solution in the `results` directory
    forceSolution = True

    # Forces the LP problem itself to be stored in the `results` directory
    doStoreProblem = False

    # See the associated notebooks to understand what the following parameters do, esp. `basic.ipynb`.
    # See the __init__ routine of class resultGatherer in results.py to understand how the following
    # dict keys map to column names in the notebooks.
    seed = 'a'
    tabTypes = ['random','complete']
    tableParams = {
        'tabType': tabTypes[0],
        'numValsPerColumn': [5,5,5],
        #'numValsPerColumn': [3,3,3],
        #'numValsPerColumn': [10,10,10],
    }
    anonymizerParams = {
        'lcfMin': 0,
        'lcfMax': 0,
        'standardDeviation': 2,
    }
    solveParams = {
        # This is fraction of the LCF or noise range that is penalty-free
        # Value 1.0 means there is no elastic constraint at all
        'elasticLcf': 1.0,
        'elasticNoise': 1.0,
        'numSDs': 2,
    }
    
    lra = lrAttack(seed, anonymizerParams, tableParams, solveParams, force=forceSolution)
    if not forceSolution and lra.problemAlreadySolved():
        print(f"Attack {lra.fileName} already solved")
        if not lra.solutionAlreadyMeasured():
            print("    Measuring solution match")
            lra.measureMatch(force=True)
            lra.saveResults()
        else:
            print("    Match already measured")
        quit()
    else:
        print(f"Running attack {lra.fileName}")
    prob = lra.makeProblem()
    if (doStoreProblem):
        lra.storeProblem(prob)
    print("Solving problem")
    solveStatus = lra.solve(prob)
    print(f"Solve Status: {solveStatus}")
    if solveStatus == 'Optimal':
        lra.solutionToTable(prob)
    lra.measureMatch(force=False)
    lra.saveResults()
