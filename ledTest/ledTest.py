import whereParser
import rowFiller
import itertools
import statistics
import sqlite3
import pprint
import re
import pandas as pd
import numpy as np
from datetime import date,datetime
import os.path
import shutil
import hashlib


class ledBase:
    '''
        This is the base class for all tests (which are sub-classes of this base)
    '''
    def __init__(self,test,doPrint=False):
        self.pp = pprint.PrettyPrinter(indent=4)
        self.name = self.__class__.__name__
        self.test = test
        self.dop = False
        if doPrint or ('doPrint' in self.test and self.test['doPrint'] is True):
            self.dop = True
        # build test database
        self.sw = whereParser.simpleWhere(test['table']['conditionsSql'])
        self.rf = rowFiller.rowFiller(self.sw,printIntermediateTables=False,dop=False)
        self.rf.makeBaseTables()
        # dfFull here is used to determine if a condition will in principle
        # have an effect
        self.dfFull = self.rf.baseDf['tab'].copy()
        if len(self.rf.failedCombinations) > 0:
            print("Failed Combinations:")
            print(self.rf.failedCombinations)
        # Strip, then append
        for change in test['table']['changes']:
            if change['change'] == 'strip':
                self.rf.stripDf(change['table'],change['query'])
        for change in test['table']['changes']:
            if change['change'] == 'append':
                self.rf.appendDf(change['table'],change['spec'])
        self.rf.baseTablesToDb()

    def printRawTable(self):
        print(self.rf.baseDf['tab'])

    def print(self):
        self.pp.pprint(self.test)
    
    def _error(self,msg):
        print(msg)
        self.pp.pprint(self.test)
        quit()

    def getOutcome(self,df,query):
        df2 = df.query(query)
        if df2.empty:
            return(0)
        else:
            return(1)

    def getTruthDf(self,df):
        comb = {'outcome':[]}
        for name in self.test['expList']:
            comb[name] = []
        aidCols = self.rf.getAidColumns()
        for aidCol in aidCols:
            comb[aidCol] = []
        for index, row in df.iterrows():
            #print(f"----------- index {index}")
            # This makes a df composed of a single row
            dfRow = df.loc[[index],:]
            #print(dfRow)
            comb['outcome'].append(self.getOutcome(dfRow,self.test['fullExp']))
            for name,query in self.test['expList'].items():
                comb[name].append(self.getOutcome(dfRow,query))
            for aidCol in aidCols:
                #print(dfRow.iloc[0][aidCol])
                comb[aidCol].append(dfRow.iloc[0][aidCol])
        dfTruth = pd.DataFrame.from_dict(comb)
        return dfTruth

    def recurseConditions(self,tt,stk,comb,combIndex,boo):
        aidCols = self.rf.getAidColumns()
        name = comb[combIndex]
        if self.dop: print(f"Call recurse, name {name}, bool {boo} ({comb})")
        stk.add(name,boo)
        # outcomes is a list of distinct outcomes (either [0], [1], or [0,1])
        outcomes,outcomesFull = stk.outcomesLastSplit()
        if len(outcomesFull) == 1:
            # splitLen is the number of rows of the table split off by the condition
            splitLen = stk.lenLastSplit()
            # No need to check subsequent conditions, so make the truth table row
            # First set the column values (1, 0, or -)
            if self.dop: print(f"Recurse: exactly one outcome {outcomes}: check truth table add'")
            if splitLen == 0:
                # no entry in truth table
                if self.dop: print("    query result empty, don't add")
            else:
                for name in comb:
                    val = stk.booleanFromStack(name)
                    tt.appendColBoolean(comb,name,val)
                # Then set the outcome
                tt.appendOutcome(comb,outcomes[0])
                # And the effect
                if splitLen == 1:
                    tt.appendEffect(comb,'LE')
                else:
                    tt.appendEffect(comb,'NLE')
                for aidCol in aidCols:
                    aidList = stk.aidListLastSplit(aidCol)
                    tt.appendAidList(comb,aidCol,aidList)
                if self.dop: tt.printTruthTable(comb)
        else:
            if self.dop: print(f"Recurse: two outcomes: go down a level'")
            if combIndex == len(comb) - 1:
                print("ERROR, should not reach here")
                stk.print()
                quit()
            self.recurseConditions(tt,stk,comb,combIndex+1,0)
            stk.pop()
        if boo == 0:
            stk.pop()
            self.recurseConditions(tt,stk,comb,combIndex,1)

class truthTablesManager():
    def __init__(self,aidCols):
        self.truthTables = {}
        self.aidsLists = {}
        self.aidCols = aidCols
        self.numAids = {}
        self.seeds = {}
        for aid in self.aidCols:
            self.numAids[aid] = 'num_' + aid
            self.seeds[aid] = 'seed_' + aid

    def initComb(self,comb):
        self.truthTables[comb] = {}
        for expName in comb:
            self.truthTables[comb][expName] = []
        self.truthTables[comb]['outcome'] = []
        self.truthTables[comb]['effect'] = []    # LE, sus, aid
        for aidCol in self.aidCols:
            self.truthTables[comb][self.numAids[aidCol]] = []
            self.truthTables[comb][self.seeds[aidCol]] = []
        self.aidsLists[comb] = {}
        for aidCol in self.aidCols:
            self.aidsLists[comb][aidCol] = []

    def appendColBoolean(self,comb,name,val):
        self.truthTables[comb][name].append(val)

    def appendOutcome(self,comb,outcome):
        self.truthTables[comb]['outcome'].append(outcome)

    def appendEffect(self,comb,effect):
        self.truthTables[comb]['effect'].append(effect)

    def appendAidList(self,comb,aidCol,aidList):
        self.aidsLists[comb][aidCol].append(aidList)
        self.truthTables[comb][self.numAids[aidCol]].append(len(aidList))
        self.truthTables[comb][self.seeds[aidCol]].append(self.makeSeed(aidList))
    
    def makeSeed(self,aidList):
        aidStr = ''
        for aid in aidList:
            aidStr += str(aid)
        dig = hashlib.sha224(bytes(aidStr,'utf-8')).hexdigest()
        return(dig[0:4])

    def printTruthTable(self,comb):
        df = pd.DataFrame.from_dict(self.truthTables[comb])
        print(df.to_string(index=False))

    def print(self):
        for comb in self.truthTables:
            print(comb)
            self.printTruthTable(comb)

class stackManager():
    def __init__(self,dfTruth,dfFullTruth,doPrint=False):
        self.stack = [{'name':None,'boo':None,'df':dfTruth,'dfFull':dfFullTruth}]
        self.pp = pprint.PrettyPrinter(indent=4)
        self.dop = doPrint
        if self.dop: print("---------------------------- Stack Init")
        if self.dop: self.print()
    
    def add(self,name,boo):
        dfLastSplit = self.stack[len(self.stack)-1]['df']
        dfSplit = dfLastSplit.query(f"{name} == {boo}")
        dfLastSplitFull = self.stack[len(self.stack)-1]['dfFull']
        dfSplitFull = dfLastSplitFull.query(f"{name} == {boo}")
        self.stack.append({'name':name,'boo':boo,'df':dfSplit,'dfFull':dfSplitFull})
        if self.dop: print(f"---------------------------- Stack Add (query '{name} == {boo}')")
        if self.dop: self.print()

    def pop(self):
        self.stack.pop()
        if self.dop: print("---------------------------- Stack Pop")

    def outcomesLastSplit(self):
        ''' returns set of distinct outcomes [0], [1], or [0,1] '''
        dfLastSplit = self.stack[len(self.stack)-1]['df']
        dfLastSplitFull = self.stack[len(self.stack)-1]['dfFull']
        return dfLastSplit['outcome'].unique(), dfLastSplitFull['outcome'].unique()

    def lenLastSplit(self):
        ''' returns number of rows '''
        dfLastSplit = self.stack[len(self.stack)-1]['df']
        #dfLastSplitFull = self.stack[len(self.stack)-1]['dfFull']
        return len(dfLastSplit.index)  #, len(dfLastSplitFull.index)

    def aidListLastSplit(self,aidCol):
        ''' returns list of distinct aid values from df '''
        dfLastSplit = self.stack[len(self.stack)-1]['df']
        return set(dfLastSplit[aidCol].tolist())

    def booleanFromStack(self,name):
        for i in range(1,len(self.stack)):
            thing = self.stack[i]
            if name == thing['name']:
                return thing['boo']
        return '-'

    def print(self):
        print(f"Stack has {len(self.stack)} entries:")
        for i in range(len(self.stack)):
            thing = self.stack[i]
            print(f"---- ({i})  name:{thing['name']}, bool:{thing['boo']}, df len {len(thing['df'].index)}")
            if i == len(self.stack)-1:
                print('Actual DF:')
                print(thing['df'].to_string(index=False))
                print('Full DF:')
                print(thing['dfFull'].to_string(index=False))

class a_or_i_and_j(ledBase):
    def doTest(self):
        # This is the original experiment table (with victim isolated)
        df = self.rf.baseDf['tab']
        print(df.to_string(index=False))
        # This is the original table with outcome added
        dfTruth = self.getTruthDf(df)
        print(dfTruth.to_string(index=False))
        # This is the full table (before the victim has been isolated) with outcome
        dfFullTruth = self.getTruthDf(self.dfFull)
        print(dfFullTruth.to_string(index=False))
        names = list(self.test['expList'].keys())
        tt = truthTablesManager(self.rf.getAidColumns())
        # For each possible ordering of expressions, determine AID set
        for comb in itertools.permutations(names):
            if self.dop: print(f"--------------------------------------- {comb} -------------------------------")
            tt.initComb(comb)
            stk = stackManager(dfTruth,dfFullTruth,doPrint=self.dop)
            combIndex = 0
            boo = 0
            self.recurseConditions(tt,stk,comb,combIndex,boo)
        print("\n\nFINAL TRUTH TABLES:")
        tt.print()







# ------------------- CONTROL CENTRAL ---------------------- #
if False: testControl = 'firstOnly'    # executes only the first test
elif False: testControl = 'tagged'    # executes only tests so tagged
else: testControl = 'all'             # executes all tests
'''
The `testControl` parameter is used to determine which tests are run.

By convention, t1 is the attribute we want to test
    i1, i2, etc. are the isolator columns.
By convention, victim has values 1 for all isolator columns
    victim attribute is always t1='a'
'''
tests = [
    {   
        'doPrint': True,
        'tagAsRun': False,
        'testClass': a_or_i_and_j,
        'describe': 'A or (I and J), victim has A',
        'table': {
            'conditionsSql': "select count(*) from tab where t1 in ('a','b') or i1 = 1 or i2 = 1",
            'changes': [
                {'change':'strip', 'table':'tab','query': "i1 == 1 and i2 == 1"},
                {'change':'append', 'table':'tab','spec': {'t1':['a'],'i1':[1],'i2':[1]}},
            ],
        },
        'fullExp': "t1 == 'a' or (i1 == 1 and i2 == 1)",
        'expList': { 'A':"t1 == 'a'", 'I':"i1 == 1", 'J':"i2 == 1" },
    },
]

for test in tests:
    if (testControl == 'firstOnly' or testControl == 'all' or
        (testControl == 'tagged' and test['tagAsRun'])):
        print(test['describe'])
        tst = test['testClass'](test,doPrint=False)
        tst.doTest()
print("---- SUMMARY ----")