import whereParser
import rowFiller
import itertools
import statistics
import sqlite3
import pprint
import re
import copy
import pandas as pd
import numpy as np
from datetime import date,datetime
import os.path
import shutil
import hashlib

class buildTable:
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
        # Strip, then random drop, then append
        for change in test['table']['changes']:
            if change['change'] == 'strip':
                self.rf.stripDf(change['table'],change['query'])
        for change in test['table']['changes']:
            if change['change'] == 'random_drop':
                self.rf.randomDropDf(change['table'],change['numDrop'])
        for change in test['table']['changes']:
            if change['change'] == 'append':
                self.rf.appendDf(change['table'],change['spec'])
        self.rf.baseTablesToDb()

class ledBase:
    '''
        This is the base class for all tests (which are sub-classes of this base)
    '''
    def __init__(self,test,bt,side,doPrint=False):
        self.pp = pprint.PrettyPrinter(indent=4)
        self.name = self.__class__.__name__
        self.test = test
        self.side = side
        self.dop = False
        if doPrint or ('doPrint' in self.test and self.test['doPrint'] is True):
            self.dop = True
        self.dfFull = bt.dfFull
        self.rf = bt.rf

    def doTest(self):
        # This is the original experiment table (with victim isolated)
        df = self.rf.baseDf['tab']
        if self.dop: print(df.to_string(index=False))
        # This is the original table with outcome added
        dfTruth = self.getTruthDf(df)
        if self.dop: print(dfTruth.to_string(index=False))
        # This is the full table (before the victim has been isolated) with outcome
        dfFullTruth = self.getTruthDf(self.dfFull)
        if self.dop: print(dfFullTruth.to_string(index=False))
        names = list(self.test[side]['expList'].keys())
        tt = truthTablesManager(self.rf.getAidColumns(),self.side,self.dop)
        # For each possible ordering of expressions, determine AID set
        for comb in itertools.permutations(names):
            if self.dop: print(f"--------------------------------------- {comb} -------------------------------")
            tt.initComb(comb)
            stk = stackManager(dfTruth,dfFullTruth,doPrint=self.dop)
            combIndex = 0
            boo = 0
            self.recurseConditions(tt,stk,comb,combIndex,boo)
            tt.findDontCares(comb)
        print("\n\nFINAL TRUTH TABLES:")
        print(f"    {self.test['describe']}")
        tt.print()

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
        for name in self.test[self.side]['expList']:
            comb[name] = []
        aidCols = self.rf.getAidColumns()
        for aidCol in aidCols:
            comb[aidCol] = []
        for index, row in df.iterrows():
            #print(f"----------- index {index}")
            # This makes a df composed of a single row
            dfRow = df.loc[[index],:]
            #print(dfRow)
            comb['outcome'].append(self.getOutcome(dfRow,self.test[self.side]['fullExp']))
            for name,query in self.test[self.side]['expList'].items():
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
    def __init__(self,aidCols,side,doPrint):
        self.pp = pprint.PrettyPrinter(indent=4)
        self.side = side
        self.dop = doPrint
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
        self._initTruthTable(self.truthTables[comb],comb)
        self.aidsLists[comb] = {}
        self._initAidsList(self.aidsLists[comb])

    def _initAidsList(self,alist):
        for aidCol in self.aidCols:
            alist[aidCol] = []

    def _initTruthTable(self,ttab,comb):
        for expName in comb:
            ttab[expName] = []
        ttab['outcome'] = []
        ttab['effect'] = []    # LE, sus, aid
        for aidCol in self.aidCols:
            ttab[self.numAids[aidCol]] = []
            ttab[self.seeds[aidCol]] = []

    def _ttRowMatchesUniqueComb(self,ttab,i,uComb,checkCols):
        for j in range(len(uComb)):
            col = checkCols[j]
            if ttab[col][i] != uComb[j]:
                return False
        return True

    def _mergeTtRows(self,uniqueCombs,checkCols,comb):
        ''' Merge truth table rows where a condition is don't care by replacing
            the 0,1 values of the don't care condition with '-', combining the uid
            lists, and recomputing the seed
            * uniqueCombs contains the combination values that we want to merge
            * checkCols contains the column names corresponding to uniqueCombs
        '''
        ttab = self.truthTables[comb]
        moveIndices = []
        mergeIndices = [[] for i in range(len(uniqueCombs))]
        # As a first step, find the truth table rows that don't need to be merged
        for i in range(len(ttab['outcome'])):
            matched = False
            for j in range(len(uniqueCombs)):
                if self._ttRowMatchesUniqueComb(ttab,i,uniqueCombs[j],checkCols):
                    matched = True
                    mergeIndices[j].append(i)
                    break
            if matched is False:
                # truth table row won't be merged
                moveIndices.append(i)
        if self.dop: print(f"mergeIndices = {mergeIndices}")
        if self.dop: print(f"moveIndices = {moveIndices}")
        # Now build the new truth table
        newtt = {}
        self._initTruthTable(newtt,comb)
        # And we'll need a new aidsList as well
        newal = {}
        self._initAidsList(newal)
        # First merge and put into the new truth table
        for j in range(len(mergeIndices)):
            if len(mergeIndices[j]) == 0:
                continue
            if len(mergeIndices) != 2:
                print(f"_mergeTtRows Error: Funny number of merge items ({mergeIndices})")
                print(comb)
                self.pp.pprint(ttab)
                quit()
            self._doTtMerge(comb,newtt,newal,ttab,self.aidsLists[comb],mergeIndices[j],uniqueCombs[j],checkCols)
        # Then copy over the truth table rows that don't need merging
        for i in moveIndices:
            self._doTtCopy(comb,newtt,newal,ttab,self.aidsLists[comb],i)
        # overwrite the old truth table and aids lists entries with the new
        if self.dop: print("old TruthTable:")
        if self.dop: self.printTruthTable(comb)
        if self.dop: print("new TruthTable:")
        if self.dop: self.printTruthTable(comb,newtt)
        self.truthTables[comb] = newtt
        self.aidsLists[comb] = newal

    def _doTtCopy(self,comb,newtt,newal,oldtt,oldal,oldIndex):
        for condName in comb:
            newtt[condName].append(oldtt[condName][oldIndex])
        newtt['outcome'].append(oldtt['outcome'][oldIndex])
        for aidCol in self.aidCols:
            newal[aidCol].append(oldal[aidCol][oldIndex])
            newtt[self.numAids[aidCol]].append(oldtt[self.numAids[aidCol]][oldIndex])
            newtt[self.seeds[aidCol]].append(oldtt[self.seeds[aidCol]][oldIndex])
        newtt['effect'].append(oldtt['effect'][oldIndex])

    def _doTtMerge(self,comb,newtt,newal,oldtt,oldal,toMerge,uComb,checkCols):
        ''' checkCols list has the columns whose values won't change and the outcome
            uComb list has the values corresponding to checkCols
            toMerge has the indices into oldtt of the truth table Rows to be merged
        '''
        for condName in comb:
            if condName in checkCols:
                i = checkCols.index(condName)
                newtt[condName].append(uComb[i])
            else:
                newtt[condName].append('-')
        # Then set the outcome
        i = checkCols.index('outcome')
        newtt['outcome'].append(uComb[i])
        # merge the corresponding AID lists
        for aidCol in self.aidCols:
            aidsMerged = list(set(list(oldal[aidCol][toMerge[0]]) + list(oldal[aidCol][toMerge[1]])))
            newal[aidCol].append(aidsMerged)
            newtt[self.numAids[aidCol]].append(len(aidsMerged))
            newtt[self.seeds[aidCol]].append(self.makeSeed(aidsMerged))
        newtt['effect'].append('NLE')

    def _noEffect(self,ttab,comb,testCol,checkCol,boo):
        if self.dop: print(f"Start noEffect with testCol {testCol}, checkCol {checkCol}, boo {boo}")
        df = pd.DataFrame.from_dict(ttab)
        if self.dop: print("noEffect starting df")
        if self.dop: print(df.to_string(index=False))
        # Grab only the relevent rows
        df = df.query(f"{checkCol} == '{boo}'")
        if self.dop: print("noEffect relevant rows")
        if self.dop: print(df.to_string(index=False))
        # list the unique combinations of everything except the test column
        checkCols = list(comb).copy()
        checkCols.remove(testCol)
        checkCols.append('outcome')
        uniqueCombs = df[checkCols].values
        # Remove dups (by making as list, then using itertools.groupby)
        uniqueCombs = uniqueCombs.tolist()
        uniqueCombs.sort()
        uniqueCombs = list(uniqueCombs for uniqueCombs,_ in itertools.groupby(uniqueCombs))
        # Now uniqueCombs (list of lists) contains the unique combinations of the outcome and all
        # other conditions except the test condition testCol
        if self.dop: print(f"noEffect unique combinations for {checkCols}")
        if self.dop: print(uniqueCombs)
        # Now for each unique combination, if we have both values of the test
        # condition testCol, then the test condition is a don't care and we presume
        # that postgres would not have tested it
        for uComb in uniqueCombs:
            query = ''
            for i in range(len(checkCols)):
                col = checkCols[i]
                val = uComb[i]
                query += f"{col} == '{val}' and "
            query = query[:-5]
            if self.dop: print(f'''noEffect query: "{query}"''')
            dfCheck = df.query(query)
            if self.dop: print("noEffect check df")
            if self.dop: print(dfCheck.to_string(index=False))
            uniqueVals = dfCheck[testCol].unique()
            if self.dop: print(f"    uniqueVals = {uniqueVals}")
            if '1' not in uniqueVals or '0' not in uniqueVals:
                if self.dop: print("    values 0 and 1, so can't say we don't care")
                return None
        if self.dop: print("    turns out we indeed don't care!")
        # Now we want to merge the truth table rows where the testCol is dontcare
        return self._mergeTtRows(uniqueCombs,checkCols,comb)

    def findDontCares(self,comb):
        ''' We are looking for situations where a column has no effect
            relative to the boolean value of a column to its left. These
            should be labeled '-' (don't care)
        '''
        ttab = self.truthTables[comb]
        for testI in range(1,len(comb)):
            # testCol is the column we are testing to see if don't care
            testCol = comb[testI]
            for checkI in range(0,testI):
                checkCol = comb[checkI]
                for boo in [0,1]:
                    self._noEffect(ttab,comb,testCol,checkCol,boo)

    def appendColBoolean(self,comb,name,val):
        self.truthTables[comb][name].append(val)

    def appendOutcome(self,comb,outcome):
        self.truthTables[comb]['outcome'].append(str(outcome))

    def appendEffect(self,comb,effect):
        self.truthTables[comb]['effect'].append(effect)

    def appendAidList(self,comb,aidCol,aidList):
        self.aidsLists[comb][aidCol].append(aidList)
        self.truthTables[comb][self.numAids[aidCol]].append(len(aidList))
        self.truthTables[comb][self.seeds[aidCol]].append(self.makeSeed(aidList))
    
    def makeSeed(self,aidList):
        aidStr = ''
        for aid in sorted(aidList):
            aidStr += str(aid)
        dig = hashlib.sha224(bytes(aidStr,'utf-8')).hexdigest()
        return(dig[0:4])

    def printTruthTable(self,comb,exceptTT=None):
        if exceptTT:
            df = pd.DataFrame.from_dict(exceptTT)
        else:
            df = pd.DataFrame.from_dict(self.truthTables[comb])
        print(df.to_string(index=False))

    def print(self):
        for comb in self.truthTables:
            print(f"{comb}, {self.side}")
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
                return str(thing['boo'])
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

#class a_or_i_and_j(ledBase):

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
        'doPrint': False,
        'tagAsRun': False,
        #'testClass': a_or_i_and_j,
        'describe': 'left: A or (I and J), right: A, victim does not have A',
        'table': {
            'conditionsSql': "select count(*) from tab where t1 in ('a','b') or i1 = 1 or i2 = 1",
            'changes': [
                {'change':'strip', 'table':'tab','query': "i1 == 1 and i2 == 1"},
                {'change':'random_drop', 'table':'tab','numDrop': 5},
                {'change':'append', 'table':'tab','spec': {'t1':['b'],'i1':[1],'i2':[1]}},
            ],
        },
        'left': {
            'fullExp': "t1 == 'a' or (i1 == 1 and i2 == 1)",
            'expList': { 'A':"t1 == 'a'", 'I':"i1 == 1", 'J':"i2 == 1" },
        },
        'right': {
            'fullExp': "t1 == 'a'",
            'expList': { 'A':"t1 == 'a'" }
        },
    },
    {   
        'doPrint': False,
        'tagAsRun': False,
        #'testClass': a_or_i_and_j,
        'describe': 'left: A or (I and J), right: A, victim has A',
        'table': {
            'conditionsSql': "select count(*) from tab where t1 in ('a','b') or i1 = 1 or i2 = 1",
            'changes': [
                {'change':'strip', 'table':'tab','query': "i1 == 1 and i2 == 1"},
                {'change':'random_drop', 'table':'tab','numDrop': 5},
                {'change':'append', 'table':'tab','spec': {'t1':['a'],'i1':[1],'i2':[1]}},
            ],
        },
        'left': {
            'fullExp': "t1 == 'a' or (i1 == 1 and i2 == 1)",
            'expList': { 'A':"t1 == 'a'", 'I':"i1 == 1", 'J':"i2 == 1" },
        },
        'right': {
            'fullExp': "t1 == 'a'",
            'expList': { 'A':"t1 == 'a'" }
        },
    },
]

for test in tests:
    bt = buildTable(test)
    tst = {}
    for side in ['left','right']:
        if (testControl == 'firstOnly' or testControl == 'all' or
            (testControl == 'tagged' and test['tagAsRun'])):
            print(test['describe'])
            tst[side] = ledBase(test,bt,side,doPrint=False)
            #tst = test['testClass'](test,doPrint=False)
            tst[side].doTest()