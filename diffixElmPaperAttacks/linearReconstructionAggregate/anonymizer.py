'''
Simulates whatever anonymizing mechanisms are in place
'''

import pandas as pd
import pprint
import itertools
import random
import os
import sys
filePath = __file__
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import anonymize.anonAlgs
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
                tabType = 'random' or 'complete'
                numValsPerColumn = [5,5,5]
        '''

        # Makes random thread-safe
        self.loc_random = random.Random()
        self.loc_random.seed(seed)
        if tableParams:
            self.tp = tableParams
        else:
            self.tp = {}
        if not self.tp['tabType']:
            self.tp['tabType'] = 'complete'
        if not self.tp['numValsPerColumn']:
            self.tp['numValsPerColumn'] = [5,5,5]

        if anonymizerParams:
            self.ap = anonymizerParams
        else:
            self.ap = {}
        if not self.ap['lowThresh']:
            self.ap['lowThresh'] = 0
        if not self.ap['gap']:
            self.ap['gap'] = 0
        if not self.ap['sdSupp']:
            self.ap['sdSupp'] = 0
        if not self.ap['standardDeviation']:
            self.ap['standardDeviation'] = 0
        if not self.ap['priorKnowledge']:
            self.ap['priorKnowledge'] = 'none'
        self.anon = anonymize.anonAlgs.anon(self.ap['lowThresh'],self.ap['gap'],
                                            self.ap['sdSupp'],self.ap['standardDeviation'],
                                            self.loc_random)
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

    def queryForCount(self, query):
        trueCount = self.df.query(query).shape[0]
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