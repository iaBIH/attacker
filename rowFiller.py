import sqlite3
import pprint
import os.path
import itertools
import random
import string
import pandas as pd
import numpy as np
import whereParser

class aidManager:
    """ Assigns the next aid value """
    def __init__(self,alg='distinctPerRow'):
        self.alg = alg
        if self.alg == 'distinctPerRow':
            self.nextVal = -1

    def nextAid(self):
        if self.alg == 'distinctPerRow':
            self.nextVal += 1
            return self.nextVal

'''
Building tables operates in two phases: first a base table is built that has
multiple rows of every possible column/value combination (default numRowsPerCombination=10).
Then rows are selectively added or deleted from the base table.

The columns of the table are either AID columns or data columns. The AID columns are
named `aid1`, `aid2`, ..., `aidN`. The data columns are named `xy` (two characters), 
where `x` is 'i' if integer, 'r' if real, 't' if text, 'd' if date, and y is a single digit.

The spec for building the base table is literally an SQL string. (This might be a
dumb way to do it ... we'll see if that is the case when we get to more complex tables.)
The SQL is of the form:
    SELECT foo
    FROM table
    WHERE condition1 or condition2 or ...

Each condition in the WHERE clause is one of the following:
    col = val:
    col IN (val1, val2, ...)
These WHERE clauses cause the given values to be added to the base table. All possible
combinations of columns and values are added to the base table. One additional value per
column is also added. (These SQL strings are encoded in the `attacks` dict as 'conditionsSql'.)

For deleting or adding rows, the methods `stripDf()` and `appendDf()` are used:
    stripDf(): The argument to stripDf is literally a dataframes query. Everything matching
        that query will be stripped from the base table. For example, "t2 == 'f'" will remove
        all rows where column 't2' has value 'f'.
    appendDf(): The argument to appendDf is a dict indexed by data column name (not AID columns).
        For each column name, a list is supplied. The length of the list matches the number of
        rows to add to the base table. Each entry in the list if the value that should be added.
        The special sting 'unique' causes a unique value to be added. For example, the following
        dict:
            {'t1':['unique'],'i1':[100],'t2':['x']}
        adds a single row with a unique value for column 't1', the value 100 for column 'i1', and
        the value 'x' for column 't2'.

'''

class rowFiller:
    """Generates the rows and outputs the table as sqlite
    """
    def __init__(self, sw,
            aidSpec=['distinctPerRow'],
            useTestDbName=True,
            printIntermediateTables=True,
            numRowsPerCombination=10,
            dop=False):
        self.pp = pprint.PrettyPrinter(indent=4)
        self.dop = dop
        self.sw = sw
        self.printIntermediateTables = printIntermediateTables
        self.useTestDbName = useTestDbName
        self.aidSpec = aidSpec
        self.aidManagers = []
        self.aidDummies = []
        self.aidCols = []
        self._makeAidColumns()
        for i in range(len(self.aidSpec)):
            self.aidManagers.append(aidManager(self.aidSpec[i]))
            self.aidDummies.append('x')
        self.numRowsPerCombination = numRowsPerCombination
        self.maxDbName = 50
        self.dbName = self._makeDbName()
        self.dbPath = os.path.join('tables',self.dbName)
        self.failedCombinations = []
        self.allColumns = []
        self.newRows = []
        # This will be one list per table
        self.baseData = {}
        self.baseDf = {}

    def getDbName(self):
        return self.dbName

    def getDbPath(self):
        return self.dbPath

    def queryDf(self,table,query):
        df = self.baseDf[table].query(query)
        return df

    def _makeAidColumns(self):
        self.aidCols = []
        for i in range(len(self.aidSpec)):
            self.aidCols.append(f"aid{i+1}")

    def getAidColumns(self):
        return self.aidCols

    def makeBaseTables(self):
        ''' This builds the basic table that has as many matching combinations
            as possible. It also makes the base dataframe from the baseData
        '''
        for table in self.sw.iterTabs():
            self.baseData[table] = []
            self.conditions = list(self.sw.iterConditions(table))
            if self.dop:
                print(f"Conditions (table {table}):")
                self.pp.pprint(self.conditions)
            self._processOneTable(table,self.baseData[table])
            if self.printIntermediateTables:
                self.pp.pprint(self.baseData[table])
        for table,data in self.baseData.items():
            self.allColumns = []
            for aidCol in self.aidCols:
                self.allColumns.append(aidCol)
            for column in list(self.sw.iterCols(table)):
                self.allColumns.append(column)
            self.baseDf[table] = pd.DataFrame(data, columns=self.allColumns) 
    
    def baseTablesToDb(self):
        ''' This takes the base table and writes it to an sql db '''
        self.conn = sqlite3.connect(self.dbPath)
        for table,df in self.baseDf.items():
            df.to_sql(table,con=self.conn, if_exists='replace')
        self.conn.close()

    def appendDf(self,table,spec):
        ''' This adds the rows defined by the spec to the base dataframe
            Columns that are absent in the spec are assumed to require new distinct values
        '''
        dfSpec = {}
        # First figure out how many rows we need
        numRows = 1   # default assumption
        for _,vals in spec.items():
            numRows = max(numRows,len(vals))
        for column in self.allColumns:
            dfSpec[column] = []
            for i in range(numRows):
                if column not in spec or len(spec[column]) <= i or spec[column][i] == 'unique':
                    dfSpec[column].append(self._getNewVal(table,column))
                else:
                    dfSpec[column].append(spec[column][i])
        df = pd.DataFrame(dfSpec)
        self._addToNewRows(dfSpec)
        self.baseDf[table] = self.baseDf[table].append(df)

    def stripDf(self,table,query):
        ''' This removes the rows that match the dataframe query
        '''
        bdf = self.baseDf[table]
        notQuery = f"not({query})"
        dfKeep = bdf.query(notQuery)
        # dfKeep contains everything except what matches the query
        self.baseDf[table] = dfKeep
    
    def iterNewRows(self):
        for newRow in self.newRows:
            yield newRow

    def getNewRowColumn(self,col):
        return(self.newRows[0][col])

    def _addToNewRows(self,spec):
        someCol = next(iter(spec))
        numRows = len(spec[someCol])
        for i in range(numRows):
            newRow = {}
            for col,val in spec.items():
                newRow[col] = val[i]
            self.newRows.append(newRow)

    def _getNewVal(self,table,column):
        col = self.baseDf[table][column]
        maxVal = col.max()
        if type(maxVal) is str:
            return ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
        elif np.issubdtype(maxVal,np.integer) or np.issubdtype(maxVal,np.float):
            return maxVal + 1
        else:
            print(f"ERROR: _getNewVal: {table}, {column}, {maxVal}")
            quit()

    def stripAllButX(self,table,query,numLeft=1):
        ''' This removes the rows that match the dataframe query leaving numLeft
            number of distinct AIDs
        '''
        bdf = self.baseDf[table]
        dfRemove = bdf.query(query)
        notQuery = f"not({query})"
        dfKeep = bdf.query(notQuery)
        # dfRemove contains the rows that we want to drop
        # dfKeep contains everything else
        # We want to shift rows for numLeft distinct users from dfRemove to dfKeep
        for _ in range(numLeft):
            aidVal = dfRemove['aid1'].iloc[0]
            dfShift = dfRemove.query("aid1 == @aidVal")
            dfKeep = dfKeep.append(dfShift)
            dfRemove = dfRemove.query("aid1 != @aidVal")
        self.baseDf[table] = dfKeep
        self.conn = sqlite3.connect(self.dbPath)
        dfKeep.to_sql(table,con=self.conn, if_exists='replace')
        self.conn.close()
    
    def _processOneTable(self,table,data):
        columns = list(self.sw.iterCols(table))
        # Make all possible True/False column combinations
        for comb in itertools.product([True,False],repeat=len(self.conditions)):
            ''' For each combination, loop through each column and try to find a value
                that satisfies all of the conditions in the combination (noting that a
                given column can be in more than one condition). The approach will be
                to find valid values for all conditions, and then check each one against
                all other conditions to see if it passes all. If no values work for all
                conditions, then we presume that the conditions can't be satisfied and
                we move on. (This may fail to find working values when such values exist.)
            '''
            values = []
            # We are going to find all of the candidate values for all columns in advance,
            # and then resolve them, because some conditions can involve multiple columns
            candidateValues = {}
            relevantConditions = {}
            relevantResults = {}
            for column in columns:
                candidateValues[column] = []
                relevantConditions[column],relevantResults[column] = self._getRelevantConditions(column,comb)
                if self.dop:
                    print(f"column {column}, relevantConditions {relevantConditions}, relevantResults {relevantResults}")
                for i in range(len(relevantConditions[column])):
                    condition = relevantConditions[column][i]
                    result = relevantResults[column][i]
                    # At this point, `result` is the desired True/False result of `condition`
                    self._addCandidateValues(candidateValues[column],condition,result)
            # Now see if any of the candidate values work. For now we don't deal with multi-column
            # conditions
            allValuesWork = True
            for column in columns:
                workingValueList = self._findWorkingValue(candidateValues,column,
                                                      relevantConditions, relevantResults)
                if len(workingValueList) == 0:
                    # can't find values for this combination
                    self._addFailedCombination(columns,column,comb,
                                               relevantConditions[column],candidateValues[column])
                    allValuesWork = False
                else:
                    values.append(workingValueList)
            if allValuesWork is False:
                continue
            # `values` contains the list of working values in the order that the columns
            # appear in the sqlite table
            for _ in range(self.numRowsPerCombination):
                self._makeRows(data,values)

    def _addFailedCombination(self,columns,column,comb,conditions,values):
        self.failedCombinations.append({'columns':columns,
                                        'column':column,
                                        'combination':comb,
                                        'candidateValues':values,
                                        'conditions':conditions})

    def _getRelevantConditions(self,column,comb):
        relevantConditions = []
        relevantResults = []
        for i in range(len(self.conditions)):
            condition = self.conditions[i]
            result = comb[i]
            # At this point, `result` is the desired True/False result of `condition`
            condColumn = self.sw.getColName(condition)
            if column == condColumn:
                relevantConditions.append(condition)
                relevantResults.append(result)
        return relevantConditions,relevantResults

    def _findWorkingValue(self,candidateValues,column,relevantConditions,relevantResults):
        values = []
        for valueList in candidateValues[column]:
            for value in valueList:
                if self.dop: print(f"findWorkingValue: column {column}, value {value}")
                passed = True
                for i in range(len(relevantConditions[column])):
                    if self._valuePasses(value,relevantConditions[column][i],
                                         relevantResults[column][i]) is False:
                        passed = False
                        break
                if passed is True:
                    # Found working value
                    values.append(value)
                else:
                    continue    # try next value
        return values

    def _makeRows(self,data,values):
        ''' Because of IN(), coming in here one or more of the items in `values`
            can be a list of more than one value. In that case, we want to make
            a row for all possible combinations of those values.
        '''
        rows = []
        for row in itertools.product(*self.aidDummies,*values):
            rows.append(list(row))
        for row in rows:
            for i in range(len(self.aidDummies)):
                row[i] = self.aidManagers[i].nextAid()
            data.append(row)

    def _addCandidateValues(self,candidateValues,condition,result):
        operation = self.sw.getOperation(condition)
        operands = self.sw.getOperands(condition)
        if ((operation == 'eq' and result is True) or
            (operation == 'neq' and result is False) or
            (operation == 'between' and result is True)):
            candidateValues.append([operands[0]])
            if operation == 'between':
                candidateValues.append([operands[1]])
        elif ((operation == 'eq' and result is False) or
            (operation == 'neq' and result is True) or
            ((operation == 'gt' or operation == 'gte') and result is True) or
            ((operation == 'lt' or operation == 'lte') and result is False)):
            self._addBiggerValues(operands[0],candidateValues)
        elif (((operation == 'gt' or operation == 'gte') and result is False) or
            ((operation == 'lt' or operation == 'lte') and result is True)):
            self._addSmallerValues(operands[0],candidateValues)
        elif (operation == 'between' and result is False):
            self._addSmallerValues(operands[0],candidateValues)
            self._addBiggerValues(operands[1],candidateValues)
        elif (operation == 'in' and result is True):
            candidateValues.append(operands[0])
        elif (operation == 'in' and result is False):
            self._addBiggerValues(max(operands[0]),candidateValues)
        else:
            print(f"Error: addCandidateValues: no matching branch {condition}, {result}")
            quit()

    def _valuePasses(self,value,condition,result):
        operation = self.sw.getOperation(condition)
        operands = self.sw.getOperands(condition)
        pass
        retVal = False
        if self.dop: print(f"    valuePasses, value {value} operation {operation}, operands {operands}, result {result}")
        if ((operation == 'eq' and result is True) or
            (operation == 'neq' and result is False)):
            if value == operands[0]: retVal = True
        elif ((operation == 'eq' and result is False) or
            (operation == 'neq' and result is True)):
            if value != operands[0]: retVal = True
        elif ((operation == 'gt' and result is True) or
            (operation == 'lte' and result is False)):
            if value > operands[0]: retVal = True
        elif ((operation == 'gt' and result is False) or
            (operation == 'lte' and result is True)):
            if value <= operands[0]: retVal = True
        elif ((operation == 'lt' and result is True) or
            (operation == 'gte' and result is False)):
            if value < operands[0]: retVal = True
        elif ((operation == 'lt' and result is False) or
            (operation == 'gte' and result is True)):
            if value >= operands[0]: retVal = True
        elif (operation == 'between' and result is True):
            if value >= operands[0] and value <= operands[1]: retVal = True
        elif (operation == 'between' and result is False):
            if value < operands[0] or value > operands[1]: retVal = True
        elif (operation == 'in' and result is True):
            if value in operands[0]: retVal = True
        elif (operation == 'in' and result is False):
            if value not in operands[0]: retVal = True
        else:
            print(f"Error: valuePasses: no matching branch {condition}, {result}")
            quit()
        if self.dop: print(f"        return value is {retVal}")
        return retVal

    def _addBiggerValues(self,value,valList):
        if type(value) is str:
            # Not guaranteed to be bigger, but good chance
            valList.append(['zz'])
        else:
            valList.append([value+1])
            valList.append([value+2])

    def _makeBiggerValue(self,value):
        if type(value) is str:
            # Not guaranteed to be bigger, but good chance
            return 'zz'
        else:
            return value+1

    def _addSmallerValues(self,value,valList):
        if type(value) is str:
            # Not guaranteed to be bigger, but good chance
            valList.append(['AA'])
        else:
            valList.append([value-1])
            valList.append([value-2])

    def _makeSmallerValue(self,value):
        if type(value) is str:
            # Not guaranteed to be smaller, but good chance
            return 'AA'
        else:
            return value-1

    def _makeDbName(self):
        if self.useTestDbName:
            return 'testAttack.db'
        dbName = ''
        for table in self.sw.iterTabs():
            if len(dbName) > self.maxDbName:
                break
            dbName += table
            for condition in self.sw.iterConditions(table):
                dbName += '_'
                dbName += self.sw.getColName(condition)
                dbName += self.sw.getOperation(condition)
                dbName += str(self.sw.getOperands(condition)[0])
        return dbName + '.db'

if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=4)
    tests = [
        {   # The attack here is where there is one user with i1=12345. We want to know
            # if that user has value t1='y' or not.
            'sql': "select count(*) from tab where t1='y' or i1=12345",
            'attack1': "select count(*) from tab where t1='y' or i1=12345",
            'attack2': "select count(*) from tab where t1='y'",
            # I want to make a scenario where the victim does not have t1=y. So I remove all
            # but one of the users that has i1=12345 but not t1=y
            'strip': {'table':'tab','query': "t1 != 'y' and i1 == 12345"},
        },
    ]
    for test in tests:
        sw = whereParser.simpleWhere(test['sql'])
        rf = rowFiller(sw)
        rf.makeBaseTables()
        if len(rf.failedCombinations) > 0:
            print("Failed Combinations:")
            pp.pprint(rf.failedCombinations)
        rf.baseTablesToDb()
        print("Original base dataframe:")
        pp.pprint(rf.baseDf)
        print(rf.dbPath)
        rf.stripAllButX(test['strip']['table'],test['strip']['query'])
        print("Stripped base dataframe:")
        pp.pprint(rf.baseDf)
        print(f"{test['attack1']}:")
        pp.pprint(rf.queryDb(test['attack1']))
        print(f"{test['attack2']}:")
        pp.pprint(rf.queryDb(test['attack2']))