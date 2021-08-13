'''
Simulates whatever anonymizing mechanisms are in place
'''

# Import PuLP modeler functions
import pulp
import json
import pandas as pd
import numpy as np
import pprint
import time
import bucketHandler
import itertools
import random
import os.path
pp = pprint.PrettyPrinter(indent=4)
doprint = False

class anonymizer:
    def __init__(self, seed, anonymizerParams, tableParams):
        '''
            anonymizerParams:
                lcfMin = lowest possible threshold
                lcfMax = highest possible threshold
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
        ''' Returns two values. If suppressed, the first value is -1 and the second is
            the maximum possible true count.
            If not suppressed, the first value is the rounded noisy count, and the second is the
            standard deviation of the noise. The noisy count is never less than 0.
        '''
        trueCount = self.df.query(query).shape[0]
        zzzz
        lcfThresh = self.loc_random.randrange(self.ap['lcfMin'],self.ap['lcfMax']+1)
        if trueCount < lcfThresh:
            maxTrueValue = self.ap['lcfMax'] - 1
            return trueCount,-1,maxTrueValue
        noise = self.loc_random.gauss(0,self.ap['standardDeviation'])
        noisyCount = round(trueCount + noise)
        noisyCount = max(0,noisyCount)
        return trueCount,noisyCount,self.ap['standardDeviation']

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

    def getColumnsValues(self):
        return