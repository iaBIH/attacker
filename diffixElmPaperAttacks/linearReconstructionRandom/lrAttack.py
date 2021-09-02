'''
Setup:
    One column with AIDs (individual IDs)
        AID itself is a long random string
    One column with two values
        In one setup, each value at 50%
        In another setup, one value 10%, one value 90%
    Attacker knows all AID values, so knows which AIDs are
    in each bucket.
Variables: 
    one per user per dictinct value
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
import os
import itertools
import statistics
import random
import os.path
import sys
filePath = __file__
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import tools.score
import tools.bucketHandler
import tools.anonymizer
pp = pprint.PrettyPrinter(indent=4)
doprint = False
storeTableInResults = False
useSolver = 'gurobi'
#useSolver = 'default'

class lrAttack:
    def __init__(self, seed, anonymizerParams, tableParams, solveParams, force=False,):
        self.seed = seed
        self.an = tools.anonymizer.anonymizer(seed, anonymizerParams, tableParams)
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

    def solutionToTable(self):
        self.reconTab = {'aids':{},'i1':{}}
        for aid in self.aids:
            # Check the solver outcome for the '1' choice
            outcome = pulp.value(self.choices[aid][1])
            self.reconTab['aids'][aid] = self.origTab['aids'][aid]
            if outcome > 0.5:
                # '1' choice is true, so record as 1
                self.reconTab['i1'][aid] = 1
            else:
                # false, so record as 0
                self.reconTab['i1'][aid] = 0
        if storeTableInResults:
            self.results['reconstructedTable'] = self.reconTab

    def measureMatch(self,force=False):
        dfOrig = pd.DataFrame.from_dict(self.origTab)
        dfRe = pd.DataFrame.from_dict(self.reconTab)
        cr,ci,c = self.an.measureGdaScore(dfOrig,dfRe,self.aidsKnown,statGuess=self.an.tp['valueFreqs'])
        self.results['solution']['confidence'] = c
        self._addExplain("confidence: GDA Score, percent correct claims")
        self.results['solution']['confidenceImprovement'] = ci
        self._addExplain("confidenceImprovement: GDA Score, percent correct claims over statistical guess")
        self.results['solution']['claimRate'] = cr
        self._addExplain("claimRate: GDA Score, percent individuals for which claim is made")

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

    def substringIterator(self):
        if self.an.tp['attackerType'] == 'untrusted':
            offsets = [0]
            lens = []
            length = 1
            for _ in range(self.an.tp['aidLen']):
                lens.append(length)
                length += 1
        else:
            offsets = list(range(self.an.tp['aidLen']))
            lens = [1]

        for (offset,length) in [(x, y) for x in offsets for y in lens]:
            yield offset,length
    
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

    def offLenGroupsIter(self,offLenGroups):
        for offset in offLenGroups.keys():
            for length in offLenGroups[offset].keys():
                for substr in offLenGroups[offset][length].keys():
                    blob = offLenGroups[offset][length][substr]
                    # If both entries are suppressed, then we wouldn't anyway have
                    # known about the substring, so we can just ignore it
                    if blob[0]['suppress'] and blob[1]['suppress']:
                        continue
                    yield offset,length,substr,offLenGroups[offset][length][substr]

    def getBoundsFromEntry(self,entry):
        if entry['suppress']:
            cmin = 0
            cmax = entry['noisyCount_mean'] + (self.sp['numSDs'] * entry['sd'])
            # Make elastic constraints
            emin,emax = self.makeElastic(cmin,cmax,self.sp['elasticLcf'])
        else:
            # Compute the possible range of values
            cmin = entry['noisyCount_mean'] - (self.sp['numSDs'] * entry['sd'])
            cmax = entry['noisyCount_mean'] + (self.sp['numSDs'] * entry['sd'])
            # We know we can't have count lower than the suppression lowThresh
            # because that would be suppressed
            cmin = max(entry['minPossible'],cmin)
            cmax = max(entry['minPossible'],cmax)
            # Make elastic constraints
            emin,emax = self.makeElastic(cmin,cmax,self.sp['elasticNoise'])
        return cmin,cmax,emin,emax

    def makeProblem(self):
        # First check to see if there is already an LpProblem to read in. Note that the
        # problem runs in rounds, where each new solution generates more constraints to prevent
        # the prior solution
        self.an.makeTable()
        self.results['params']['columns'] = self.cols
        self.results['params']['numAids'] = self.an.numAids
        self.results['params']['valueFreqs'] = self.an.valueFreqs
        self.results['params']['numSymbols'] = self.an.numSymbols
        self.results['params']['aidLen'] = self.an.aidLen
        self.results['params']['attackerType'] = self.an.attackerType
        tempTable = self.an.df.to_dict()
        if self.force == False:
            prob = self.readProblem()
            if prob:
                return prob

        numAids = self.an.numAids
        # I want a variable for every user / column / bucket combination.
        if doprint: print("Here are the users")
        self.aids = [f"a{i}" for i in range(numAids)]
        if doprint: print(self.aids)
        if doprint: print("Here is the original table")
        # The original table is a dict of dicts, first key column ('i0'), second key
        # The index of the aid (0, 1, ...)
        if doprint: pp.pprint(tempTable)
        # Since I'm using 'aXX' to denote AID, I want to re-key the original table
        # and also make a reverse mapping
        self.origTab = {}
        for colKey,colVals in tempTable.items():
            self.origTab[colKey] = {}
            for aidKey,aidVal in colVals.items():
                newKey = f"a{aidKey}"
                self.origTab[colKey][newKey] = aidVal
        if doprint: print('origTab')
        if doprint: pp.pprint(self.origTab)
        if storeTableInResults:
            self.results['originalTable'] = self.origTab
        self.longAIDtoShortAID = {}
        for shortAID,longAID in self.origTab['aids'].items():
            self.longAIDtoShortAID[longAID] = shortAID
        if doprint: print('longAIDtoShortAID')
        if doprint: pp.pprint(self.longAIDtoShortAID)
        # self.aidsKnown here means that the attacker knows the column value associated
        # with the AID
        self.aidsKnown = self.makePriorKnowledge(self.aids)
        if doprint: print("Here are the prior known aids:")
        if doprint: print(self.aidsKnown)

        # In this attack, the attacker queries for different substrings of the
        # AID. In the untrusted case, the offset is always 1 (i.e. the substring
        # is always from the first character.) In the untrusted case, the substring
        # can be anywhere and any length (we expect this attack to succeed, sometimes).

        # Given this, we want to make a dict that has all of the substring combinations
        # and associated noisy count ranges.
        
        cols = self.an.colNames()
        self.an.sqlInit('orig')
        suppress,trueCount,sd,minPossible,noisyCount_mean = self.an.getDiffixAnswer(0)
        defaultSuppresedEntry = {
            'suppress': suppress,
            'trueCount': trueCount,
            'sd': sd,
            'minPossible': minPossible,
            'noisyCount_mean': noisyCount_mean,
        }
        lowThresh = self.an.getLowThresh()
        offLenGroups = {}
        for offset,length in self.substringIterator():
            if offset not in offLenGroups:
                offLenGroups[offset] = {}
            if length not in offLenGroups[offset]:
                offLenGroups[offset][length] = {}
            # This is the query the attacker makes:
            sql = f'''
                SELECT substr(aids,{offset+1},{length}),i1,count(*)
                FROM orig
                GROUP BY 1,2
                HAVING count(*) >= {lowThresh};
            '''
            bkts = self.an.sqlQuery(sql)
            if len(bkts) == 0:
                # In the case of the untrusted attack, we quickly get to the point
                # where each substring has a count of 1, and so will be suppressed
                # Longer substrings won't help us, so we quit
                break
            for bkt in bkts:
                substr = bkt[0]
                if substr not in offLenGroups[offset][length]:
                    offLenGroups[offset][length][substr] = {}
                    # Here we are really limiting our attack to two values
                    for i1Val in [0,1]:
                        # We prebuild the value entries in case they are not included
                        # in the attacker query (because of the HAVING clause in this case)
                        offLenGroups[offset][length][substr][i1Val] = defaultSuppresedEntry
                    # Each offLenGroups[offset][length][substr] group has a set of AIDVs that
                    # is known to the attacker (because we assume this knowledge). Here we use
                    # a simple query to the DB to get us that set
                    sql = f'''
                        SELECT aids
                        FROM orig
                        WHERE substr(aids,{offset+1},{length}) = '{substr}';
                    '''
                    bktAids = self.an.sqlQuery(sql)
                    # bktAids are the long strings, which we want to replace with short
                    # aXXX identifiers
                    offLenGroups[offset][length][substr]['aids'] = []
                    for row in bktAids:
                        longAID = row[0]
                        offLenGroups[offset][length][substr]['aids'].append(self.longAIDtoShortAID[longAID])
                i1Val = bkt[1]
                trueCount = bkt[2]
                # Note here that we are not doing any seeding. The nature of this attack is
                # such that every AIDV set will be different, so we won't get matching
                # seeds in any event
                suppress,trueCount,sd,minPossible,noisyCount_mean = self.an.getDiffixAnswer(trueCount)
                offLenGroups[offset][length][substr][i1Val] = {
                    'suppress': suppress,
                    'trueCount': trueCount,
                    'sd': sd,
                    'minPossible': minPossible,
                    'noisyCount_mean': noisyCount_mean,
                }
        # At this point, offLenGroups contains the raw anonymized buckets and
        # corresponding AIDV sets. I need to further compute cmin,cmax,emin, and emax
        for offset,length,substr,blob in self.offLenGroupsIter(offLenGroups):
            for i1Val in [0,1]:
                #entry = offLenGroups[offset][length][substr][i1Val]
                entry = blob[i1Val]
                cmin,cmax,emin,emax = self.getBoundsFromEntry(entry)
                entry['cmin'] = cmin
                entry['cmax'] = cmax
                entry['emin'] = emin
                entry['emax'] = emax
        if doprint: pp.pprint(offLenGroups)
        
        '''
        At this point, `aids` contains a list of all "users" (a1,a2...), and offLenGroups
        all queried buckets and buckets derived by combining those of both values 0 and 1.
        What I mean by this is the following. The basic query produces a histogram of:
           subset X1, value 0
           Subset X1, value 1
           subset X2, value 0
           subset X2, value 1
           etc.
        For each subset Xi, we know the subset of AIDVs. We therefore know that they are
        split between the corresponding value 0 and value 1. 
        Our variables are:
            a1_has_0 (true/false)
            a1_has_1 (true/false)
            a2_has_0 (true/false)
            a2_has_1 (true/false) 
            etc.
            Sum (a1_has_0,a2_has_0,a3_has_0, ...) = count(subset X1, value 0)
                where a1, a2, a3... are members of subset X1
            Also:
                Sum (a1_has_0,a1_has_1) == 1
        '''

        # The prob variable is created to contain the problem data
        prob = pulp.LpProblem("Attack-Problem",pulp.LpMinimize)
        cnum = 0

        print("The decision variables are created")
        i1Vals = [0,1]
        self.choices = pulp.LpVariable.dicts("Choice", (self.aids, i1Vals), cat='Binary')
        self.results['solution']['numChoices'] = len(self.aids) * len(i1Vals)
        self._addExplain("numChoices: Total number of variables for the solver")
        if doprint: pp.pprint(self.choices)
        if doprint: pp.pprint(prob)
        
        print("We do not define an objective function since none is needed")
        # Now we need to add to self.choices the variables for the prior known aids
        print("Constraints for the prior-known AIDs")
        for aid in self.aidsKnown:
            i1Val = self.origTab['i1'][aid]
            if i1Val == 1:
                prob += pulp.lpSum([self.choices[aid][1]]) == 1, f"{cnum}_prior_known_aid"
                prob += pulp.lpSum([self.choices[aid][0]]) == 0, f"{cnum+1}_prior_known_aid"
            else:
                prob += pulp.lpSum([self.choices[aid][1]]) == 0, f"{cnum+2}_prior_known_aid"
                prob += pulp.lpSum([self.choices[aid][0]]) == 1, f"{cnum+3}_prior_known_aid"
            cnum += 4
        if doprint: pp.pprint(prob)

        print("Constraints that each user is 0 or 1")
        for aid in self.aids:
            prob += pulp.lpSum([self.choices[aid][i1Val] for i1Val in i1Vals]) == 1, f"{cnum}_each_user_one_value"
            cnum += 1
        if doprint: pp.pprint(prob)

        print("Constraints ensuring that each bucket has sum attributed to its users")
        for offset,length,substr,blob in self.offLenGroupsIter(offLenGroups):
            for i1Val in i1Vals:
                cmin = blob[i1Val]['cmin']
                cmax = blob[i1Val]['cmax']
                emin = blob[i1Val]['emin']
                emax = blob[i1Val]['emax']
                aidsBkt = blob['aids']
                # Need to get set of aids...
                if cmin == cmax:
                    # Only one possible value
                    prob += pulp.lpSum([self.choices[aid][i1Val] for aid in aidsBkt]) == cmin, f"{cnum}_num_users_per_bkt"
                    cnum += 1
                else:
                    # Range of values, so need two constraints
                    prob += pulp.lpSum([self.choices[aid][i1Val] for aid in aidsBkt]) >= cmin, f"{cnum}_num_users_per_bkt"
                    cnum += 1
                    prob += pulp.lpSum([self.choices[aid][i1Val] for aid in aidsBkt]) <= cmax, f"{cnum}_num_users_per_bkt"
                    cnum += 1
                    if emax < cmax:
                        # Make the elastic constraints
                        constraint_LHS = pulp.LpAffineExpression([(self.choices[aid][i1Val],1) for aid in aidsBkt])
                        # `targetVal` is a point in the middle of the penalty-free range defined by emin and emax
                        targetVal = emin + ((emax - emin)/2)
                        # The penalty-free range is defined by a fraction of the target value:
                        # https://coin-or.github.io/pulp/guides/how_to_elastic_constraints.html
                        # Here, emin and emax are the actual low and high values of the penalty-free range.
                        # We need to convert these into a target value fraction
                        penaltyFracLow = (targetVal - emin) / targetVal
                        penaltyFracHigh = (emax - targetVal) / targetVal
                        constraint = pulp.LpConstraint(e=constraint_LHS, sense=pulp.LpConstraintEQ, name=f"{cnum}_elastic_num_users_per_bkt", rhs=targetVal)
                        conElastic = constraint.makeElasticSubProblem(penalty = 100, proportionFreeBoundList = [penaltyFracLow,penaltyFracHigh])
                        prob.extend(conElastic)
        
        self.results['solution']['numConstraints'] = cnum-1
        self._addExplain("numConstraints: Total number of constraints for the solver")
        if doprint: pp.pprint(prob)
        return prob

    def getTargetVal(self,emin,emax):
        targetVal = emin + ((emax - emin)/2)
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
