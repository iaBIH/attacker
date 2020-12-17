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
    def __init__(self, anonymizerParams, tableParams):
        '''
            anonymizerParams:
                suppressPolicy = 'hard' or 'noisy'
                suppressThreshold = 0,
                noisePolicy = 'simple' or 'layered'
                noiseType = 'normal' or 'uniform'
                noiseAmount = 0
            tableParams:
                tabType = 'random' or 'complete'
                numValsPerColumn = [5,5,5]
        '''
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
        if not self.ap['suppressPolicy']:
            self.ap['suppressPolicy'] = 'hard'
        if not self.ap['suppressThreshold']:
            self.ap['suppressThreshold'] = 0
        if not self.ap['noisePolicy']:
            self.ap['noisePolicy'] = 'simple'
        if not self.ap['noiseAmount']:
            self.ap['noiseAmount'] = 0

    def queryForCount(self, query):
        ''' Returns -1 if the count is suppressed, otherwise returns the
            (possibly noisy) count. Noisy count never less than 0.
        '''
        trueCount = self.df.query(query).shape[0]
        if self.ap['suppressPolicy'] == 'hard':
            if trueCount < self.ap['suppressThreshold']:
                return -1,-1
        else:
            pass
        if self.ap['noiseAmount'] == 0:
            return trueCount, trueCount
        elif self.ap['noisePolicy'] == 'simple' and self.ap['noiseType'] == 'uniform':
            span = int(self.ap['noiseAmount']/2)
            cmin = min(0,trueCount-span)
            return trueCount+span, cmin
        print("queryForCount: shouldn't get here")
        quit()

    def colNames(self):
        return list(self.df.columns)

    def distinctVals(self,col):
        return list(self.df[col].unique())

    def getMaxSuppressedCount(self):
        if self.ap['suppressPolicy'] == 'hard':
            return self.ap['suppressThreshold'] - 1
        print("getMaxSuppressedCount: shouldn't get here")
        quit()

    def makeFileName(self, seed):
        fileName = f"s{seed}_"
        for key in sorted(list(self.tp.keys())):
            val = self.tp[key]
            if type(val) == list:
                for lv in val:
                    fileName += f"{lv}_"
            else:
                fileName += f"{val}_"
        for key in sorted(list(self.ap.keys())):
            val = self.ap[key]
            if type(val) == list:
                for lv in val:
                    fileName += f"{lv}_"
            else:
                fileName += f"{val}_"
        fileName = fileName[:-1]
        return fileName

    def makeTable(self):
        self.numCols = len(self.tp['numValsPerColumn'])
        self.cols = []
        for i in range(self.numCols):
            self.cols.append(f"i{i}")
        self.numAids = 1
        for numVals in self.tp['numValsPerColumn']:
            self.numAids *= numVals
        print(f"Make '{self.tp['tabType']}' table with {self.numCols} columns and {self.numAids} aids")
        self.colVals = {}
        for i in range(self.numCols):
            col = self.cols[i]
            self.colVals[col] = list(range((10*i),(10*i+self.tp['numValsPerColumn'][i])))
        if doprint: pp.pprint(self.colVals)
        data = {}
        if self.tp['tabType'] == 'random':
            for col in self.colVals:
                data[col] = []
                for _ in range(self.numAids):
                    data[col].append(random.choice(self.colVals[col]))
        if self.tp['tabType'] == 'complete':
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