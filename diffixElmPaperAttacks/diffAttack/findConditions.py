import pandas as pd
import os.path
import sqlite3
import pprint
import json

pp = pprint.PrettyPrinter(indent=4)

class findDiffConditions():
    def __init__(self):
        '''
            This code can be used to measures the number of individuals that
            might be attackable using the GROUP BY difference attack. The
            table being measured must have one row per individual.
        '''
        self.explain = []
        self.explain.append('opportunities: the total number of subset column, isolating column value combinations')
        self.opportunities = 0
        self.explain.append('possibles: the total number opportunities that have one victim and at least 8 others')
        self.possibles = 0
        self.explain.append('working: the total number unknownOpportunities that have working attacks')
        self.working = 0
        self.explain.append('unknownOpportunities: the total number of possibilities checked against unknown columns')
        self.unknownOpportunities = 0
        self.possibleVictims = []
        self.explain.append('workingVictims: details of all working attacks')
        self.workingVictims = []
        self.explain.append('isolatingColumnProfile: number of rows for each isolating column that worked')
        self.isolatingColumnProfile = {}
        self.explain.append('distinctValsPerCol: number of distinct values per column')
        self.distinctValsPerCol = {}
        self.explain.append('numIndividuals: total number of individuals (rows) in the table')
        self.numIndividuals = 0
        self.explain.append('workingByIsolatingCol: the number of working attacks per isolating column')
        self.workingByIsolatingCol = {}
        self.explain.append('workingByUnknownBuckets: the number of working attacks per number of unknown buckets')
        self.workingByUnknownBuckets = {}
        self.explain.append('workingByDistinctSubset: the number of times each subset column was used in a working attack')
        self.workingByDistinctSubset = {}
        self.explain.append('workingByDistinctUnknown: the number of times each unknown column was used in a working attack')
        self.workingByDistinctUnknown = {}

    def runMeasure(self,cur):
        '''
            cur is a cursor to an sqlite3 table with name 'test'
        '''
        sql = "SELECT count(*) FROM test"
        cur.execute(sql)
        ans = cur.fetchall()
        self.numIndividuals = ans[0][0]
        sql = "PRAGMA table_info('test')"
        cur.execute(sql)
        ans = cur.fetchall()
        cols = [x[1] for x in ans]
        for numDistinct in [2,3,4,5,6,7]:
            isolateCols = []
            print("Here are the number of distinct values per column:")
            for col in cols:
                sql = f'''
                    SELECT DISTINCT {col}
                    FROM test
                '''
                cur.execute(sql)
                ans = cur.fetchall()
                self.distinctValsPerCol[col] = len(ans)
                print(f"    {col}: {len(ans)}")
                if len(ans) == numDistinct:
                    isolateCols.append(col)
                    sql = f'''
                        SELECT {col}, count(*)
                        FROM test GROUP BY 1
                    '''
                    cur.execute(sql)
                    self.isolatingColumnProfile[col] = cur.fetchall()
            print(f"for {numDistinct} values, the possible attackable isolating")
            print(f"columns are {isolateCols}")
            self.checkVictimExists(cur,isolateCols,cols)
    
    def checkVictimExists(self,cur,isolateCols,allCols):
        '''
            First we need to see if there is any subset of rows for
            which there is only one individual with one of the isolating
            column values, and at least 8 individuals with the other
            isolating column value
        '''
        minValues = 8
        numNotEnoughOther = [0 for _ in range(minValues)]
        for iCol in isolateCols:
            for sCol in allCols:
                if sCol == iCol:
                    continue
                sql = f'''
                    SELECT col, icol, cnt FROM
                        (  SELECT cast({sCol} AS text) AS col,
                                cast({iCol} AS text) AS icol,
                                count(*) AS cnt
                        FROM test
                        GROUP BY 1,2 ) t
                '''
                cur.execute(sql)
                ans = cur.fetchall()
                record = {}
                for row in ans:
                    subsetVal = row[0]
                    isolateVal = row[1]
                    count = row[2]
                    if subsetVal in record:
                        record[subsetVal].append([isolateVal,count])
                    else:
                        record[subsetVal] = [[isolateVal,count]]
                for k,v in record.items():
                    self.opportunities += 1
                    if len(v) != 2:
                        # The attack only works if there are two values to
                        # choose from
                        continue
                    for i,j in [(0,1),(1,0)]:
                        if v[i][1] != 1:
                            # This is not the victim
                            continue
                        if v[j][1] >= minValues:
                            self.possibles += 1
                            self.possibleVictims.append(
                                {
                                    'subsetCol':sCol,
                                    'subsetVal':k,
                                    'isolateCol':iCol,
                                    'victimVal':v[i][0],
                                    'otherVal':v[j][0],
                                    'otherCount':v[j][1],
                                }
                            )
                        else:
                            # Not enough other individuals to be attackable, but
                            # count existance
                            numNotEnoughOther[v[j][1]] += 1
        print(f"There are {len(self.possibleVictims)} potential victims:")
        pp.pprint(self.possibleVictims)
        self.checkAttackability(cur,allCols)

    def getNumDistinctIndividuals(self):
        ''' Assumes that each distinct subset column / isolating column
            val pair represents a distinct user. May not always be true
        '''
        distinct = {}
        for w in self.workingVictims:
            key = w['isolateCol'] + w['subsetVal']
            distinct[key] = 1
        return len(distinct)

    def checkAttackability(self,cur,allCols):
        '''
            Go through all possible victims, and see how many can actually
            be used to learn about unknown columns
        '''
        for vic in self.possibleVictims:
            # For each possibility, we want to see if all of the other
            # individuals show up at least 6 times in the buckets for all
            # possible unknown columns
            for uCol in allCols:
                if uCol == vic['isolateCol'] or uCol == vic['subsetCol']:
                    continue
                self.unknownOpportunities += 1
                sql = f'''
                    SELECT {uCol}, count(*) FROM test
                    WHERE cast({vic['subsetCol']} AS text) == '{vic['subsetVal']}'
                    GROUP BY 1
                '''
                cur.execute(sql)
                ans = cur.fetchall()
                if len(ans) == 1:
                    continue
                attackWorks = True
                for row in ans:
                    if row[1] <= 6:
                        attackWorks = False
                        break
                if attackWorks:
                    numUnknownVals = len(ans)
                    self.workingVictims.append(
                        {
                            'subsetCol': vic['subsetCol'],
                            'subsetVal': vic['subsetVal'],
                            'unknownCol':uCol,
                            'isolateCol': vic['isolateCol'],
                            'numUnknownVals':numUnknownVals
                        }
                    )
                    self.working += 1
                    if numUnknownVals in self.workingByUnknownBuckets:
                        self.workingByUnknownBuckets[numUnknownVals] += 1
                    else:
                        self.workingByUnknownBuckets[numUnknownVals] = 1
                    if vic['isolateCol'] in self.workingByIsolatingCol:
                        self.workingByIsolatingCol[vic['isolateCol']] += 1
                    else:
                        self.workingByIsolatingCol[vic['isolateCol']] = 1
                    if uCol in self.workingByDistinctUnknown:
                        self.workingByDistinctUnknown[uCol] += 1
                    else:
                        self.workingByDistinctUnknown[uCol] = 1
                    if vic['subsetCol'] in self.workingByDistinctSubset:
                        self.workingByDistinctSubset[vic['subsetCol']] += 1
                    else:
                        self.workingByDistinctSubset[vic['subsetCol']] = 1

    def results(self):
        return {
                'opportunities': self.opportunities,
                'possibles': self.possibles,
                'unknownOpportunities': self.unknownOpportunities,
                'working': self.working,
                'workingByIsolatingCol': self.workingByIsolatingCol,
                'workingVictims': self.workingVictims,
                'distinctAttackableIndividuals': numDistinctIndividuals,
                'totalIndividuals': self.numIndividuals,
                'distinctValsPerCol': self.distinctValsPerCol,
                'isolatingColumnProfile': self.isolatingColumnProfile,
                'explain': self.explain,
                'workingByUnknownBuckets': self.workingByUnknownBuckets,
                'workingByDistinctSubset': self.workingByDistinctSubset,
                'workingByDistinctUnknown': self.workingByDistinctUnknown,
            }
        
if __name__ == "__main__":
    '''Put your CSV file path here:'''
    #csvPath = os.path.join('c:\\','paul','downloads','usa_00001','census_big.csv')
    csvPath = 'census_big.csv'
    print(f"Using file '{csvPath}'")
    df = pd.read_csv(csvPath)
    con = sqlite3.connect(':memory:')
    results = []
    df.to_sql('test',con,if_exists='replace',index=False)
    cur = con.cursor()
    fdc = findDiffConditions()
    fdc.runMeasure(cur)
    print('-------------------------------------------------')
    pp.pprint(fdc.possibleVictims)
    pp.pprint(fdc.workingVictims)
    print(f"Opportunities: {fdc.opportunities}")
    print(f"Possibles: {fdc.possibles}")
    print(f"Unknown Opportunities: {fdc.unknownOpportunities}")
    print(f"Working: {fdc.working}")
    numDistinctIndividuals = fdc.getNumDistinctIndividuals()
    print(f"Distinct individuals: {numDistinctIndividuals}")
    results.append(fdc.results())
    with open('findConditionsResults.json', 'w') as f:
        json.dump(results, f, indent=4, sort_keys=True)