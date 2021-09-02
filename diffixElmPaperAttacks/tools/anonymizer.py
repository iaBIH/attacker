'''
Simulates whatever anonymizing mechanisms are in place
'''

import pandas as pd
import pprint
import itertools
import random
import os
import sys
import sqlite3
filePath = __file__
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import anonymize.anonAlgs
import tools.score
pp = pprint.PrettyPrinter(indent=4)
doprint = False

class anonymizer:
    def __init__(self, seed, anonymizerParams, tableParams):
        '''
            anonymizerParams:
                lowThresh = lowest possible threshold
                sdSupp = standard deviation used for suppression noise
                gap = number of sdSupp deviations between lowThresh and mean
                standardDeviation = noise standard deviation
            tableParams:
                if aggregate attack:
                    tabType = 'random' or 'complete'
                    numValsPerColumn = [5,5,5]
                if random attack:
                    numAIDs
                    numSymbols (per character in the AID)
                    valueFreq (fraction of AIDs assigned to one of the two values)
        '''

        # Makes random thread-safe
        self.loc_random = random.Random()
        self.loc_random.seed(seed)
        self.tp = tableParams
        self.ap = anonymizerParams
        self.anon = anonymize.anonAlgs.anon(self.ap['lowThresh'],self.ap['gap'],
                                            self.ap['sdSupp'],self.ap['standardDeviation'],
                                            self.loc_random)
        if 'numValsPerColumn' in self.tp:
            self.attackType = 'aggregate'
            self.numCols = len(self.tp['numValsPerColumn'])
            self.cols = []
            for i in range(self.numCols):
                self.cols.append(f"i{i}")
            self.numAids = 1
            for numVals in self.tp['numValsPerColumn']:
                self.numAids *= numVals
            self.colVals = {}
            for i in range(self.numCols):
                col = self.cols[i]
                self.colVals[col] = list(range((10*i),(10*i+self.tp['numValsPerColumn'][i])))
            if doprint: pp.pprint(self.colVals)
        else:
            self.attackType = 'random'
            self.numCols = 2
            self.cols = ['aids','i1']
            self.numAids = self.tp['numAIDs']
            self.valueFreqs = self.tp['valueFreqs']
            self.numSymbols = self.tp['numSymbols']
            self.aidLen = self.tp['aidLen']
            self.attackerType = self.tp['attackerType']
    
    def sqlClose(self,table):
        self.cnx.close()

    def sqlInit(self,table):
        self.cnx = sqlite3.connect(':memory:')
        self.df.to_sql(name=table, con=self.cnx)
        self.cur = self.cnx.cursor()

    def sqlQuery(self,sql):
        self.cur.execute(sql)
        ans = self.cur.fetchall()
        # Following is if we want the sql query to return a dataframe
        #dfAns = pd.read_sql(sql, self.cnx)
        return ans

    def queryForCount(self, query):
        trueCount = self.df.query(query).shape[0]
        return self.getDiffixAnswer(trueCount)

    def getLowThresh(self):
        return self.anon.lowThresh

    def getDiffixAnswer(self,trueCount):
        suppress = self.anon.doSuppress(trueCount)
        minPossible = self.anon.lowThresh
        if suppress:
            mean = self.anon.getMean()
            return suppress,trueCount,self.ap['sdSupp'],minPossible,mean
        _,noisyCount = self.anon.getNoise(trueCount)
        return suppress,trueCount,self.ap['standardDeviation'],minPossible,noisyCount

    def colNames(self):
        return list(self.df.columns)

    def distinctVals(self,col):
        return list(self.df[col].unique())

    def makeRandomTable(self):
        data = {}
        for col in self.colVals:
            data[col] = []
            for _ in range(self.numAids):
                data[col].append(self.loc_random.choice(self.colVals[col]))
        df = pd.DataFrame.from_dict(data)
        df.sort_values(by=self.cols,inplace=True)
        df.reset_index(drop=True,inplace=True)
        return df

    def makeTable(self,tabType=None,returnOnly=False):
        if self.attackType == 'aggregate':
            self.makeTableAggregateAttack(tabType,returnOnly)
        else:
            self.makeTableRandomAttack()

    def makeTableRandomAttack(self):
        data = {'aids':[],'i1':[]}
        symbolSet = ['0','1','2','3','4','5','6','7','8','9',
                     'a','b','c','d','e','f','g','h','i','j',
                     'k','l','m','n','o','p','q','r','s','t',
                     'u','v','w','x','y','z']
        if self.numSymbols >= len(symbolSet):
            print(f"Number of symbols {self.numSymbols} too large")
            quit()
        for _ in range(self.numAids):
            aid = ''
            for _ in range(self.aidLen):
                symbol = random.choice(symbolSet[:self.numSymbols])
                aid += symbol
            data['aids'].append(aid)
        numFirstValue = round(self.numAids * self.valueFreqs)
        numFirstValue = max(1,numFirstValue)
        for _ in range(numFirstValue):
            data['i1'].append(0)
        for _ in range(self.numAids-numFirstValue):
            data['i1'].append(1)
        self.df = pd.DataFrame.from_dict(data)
        self.df.sort_values(by=self.cols,inplace=True)
        self.df.reset_index(drop=True,inplace=True)

    def makeTableAggregateAttack(self,tabType,returnOnly):
        if not tabType:
            tabType = self.tp['tabType']
        print(f"Make '{tabType}' table with {self.numCols} columns and {self.numAids} aids")
        data = {}
        if tabType == 'random':
            for col in self.colVals:
                data[col] = []
                for _ in range(self.numAids):
                    data[col].append(self.loc_random.choice(self.colVals[col]))
        if tabType == 'complete':
            prod = []
            for col in self.colVals:
                data[col] = []
                tups = []
                for val in self.colVals[col]:
                    tups.append(val)
                prod.append(tups)
            for vals in itertools.product(*prod):
                for i in range(len(vals)):
                    data[self.cols[i]].append(vals[i])
        self.df = pd.DataFrame.from_dict(data)
        self.df.sort_values(by=self.cols,inplace=True)
        self.df.reset_index(drop=True,inplace=True)
    
    def getTrueCountStatGuess(self,cols,vals,df):
        # We want to know the fraction of rows in df that have these vals
        query = ''
        for col,val in zip(cols,vals):
            if type(val) == str:
                query += f"({col} == '{val}') and "
            else:
                query += f"({col} == {val}) and "
        query = query[:-5]
        dfC = df.query(query)
        numMatchRows = len(dfC.index)
        matchingIds = list(dfC.index)
        totalRows = len(df.index)
        return numMatchRows, numMatchRows/totalRows, matchingIds

    def cleanOutKnown(self,dfOrig,dfRecon,aidsKnown):
        # We want to remove the known rows from the reconstructed data and
        # only measure the the unknown ones
        recon1 = dfRecon.to_dict('split')
        orig = dfOrig.to_dict('split')
        orig1 = dfOrig.to_dict('split')
        #pp.pprint(recon1)
        #pp.pprint(orig)
        # (It's a bit embarassing to convert these to dicts rather than man up
        # and manipulate them as dataframes, but....)
        for i in range(len(orig['index'])):
            aid = f"a{i}"
            if aid not in aidsKnown:
                continue
            # Known AID, so we want to remove it
            recon1['data'].remove(orig['data'][i])
            orig1['data'].remove(orig['data'][i])
        # and now rebuild as a dict that can be converted back to df
        reconNew = {}
        origNew = {}
        for cIndex,col in enumerate(orig['columns']):
            reconNew[col] = []
            origNew[col] = []
            for vals in orig1['data']:
                origNew[col].append(vals[cIndex])
            for vals in recon1['data']:
                reconNew[col].append(vals[cIndex])
            pass
        # and finally, convert (sheesh)
        dfReconNew = pd.DataFrame.from_dict(reconNew)
        dfOrigNew = pd.DataFrame.from_dict(origNew)
        return dfOrigNew, dfReconNew 

    def measureGdaScore(self,dfOrig,dfRecon,aidsKnown,statGuess=None):
        dfOrigNew, dfReconNew = self.cleanOutKnown(dfOrig,dfRecon,aidsKnown)
        incomingStatGuess = statGuess
        score = tools.score.score(statGuess=incomingStatGuess)
        cols = dfOrigNew.columns.tolist()
        sAggrNew = dfReconNew.groupby(cols).size()
        sAggr = dfRecon.groupby(cols).size()
        # sAggrNew represents unknown individuals. sAggr includes both known
        # and unknown
        for (vals,cnt) in sAggrNew.iteritems():
            if self.attackType == 'random' and vals[1] == 1:
                # We only want to measure '0' values (the less frequent)
                continue
            #print(f"---------------------- {vals},{cnt} --------------------------")
            if cnt == 1:
                # We get here if this set of vals is unique among the unknown entries.
                # We can make a singling out claim on this individual if the values
                # don't also match anything among the known individuals...
                match = False
                for (vals1,cnt1) in sAggr.iteritems():
                    #print("------")
                    #print(vals1)
                    #print(vals)
                    if vals1 == vals and cnt1 > 1:
                        #print(f"    match on {vals1} == {vals}!!!")
                        match = True
                if not match:
                    # We get here if the set of vals doesn't match any known sets
                    trueCount,statGuess,_ = self.getTrueCountStatGuess(cols,vals,dfOrig)
                    if incomingStatGuess:
                        statGuessToUse = incomingStatGuess
                    else:
                        statGuessToUse = statGuess
                    makesClaim = True  # We are making a claim
                    claimHas = True    # We are claiming that victim has attributes
                    if trueCount == 1:
                        claimCorrect = True
                    else:
                        claimCorrect = False
                    score.attempt(makesClaim,claimHas,claimCorrect,statGuess=statGuessToUse)
            else:
                trueCount,statGuess,_ = self.getTrueCountStatGuess(cols,vals,dfOrig)
                makesClaim = False
                claimHas = None      # don't care
                claimCorrect = None     # don't care
                statGuess = None
                for _ in range(cnt):
                    score.attempt(makesClaim,claimHas,claimCorrect,statGuess)
        cr,ci,c = score.computeScore()
        return cr,ci,c

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
