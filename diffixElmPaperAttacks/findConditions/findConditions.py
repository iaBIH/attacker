import pandas as pd
import os.path
import sqlite3
import pprint
import json

pp = pprint.PrettyPrinter(indent=4)

class findDiffConditions():
    def __init__(self,aidCol,isolateThresh=1):
        '''
            This code can be used to measures the number of individuals that
            might be attackable using the GROUP BY difference attack.
        '''
        self.aidCol = aidCol
        self.cex = f"DISTINCT {aidCol}"
        self.isolateThresh = isolateThresh
        self.explain = []
        self.attackable = {}
        self.explain.append('attackableIndividuals: the list of distinct attackable AIDVs')
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
        self.explain.append('isolatingColumnProfile: number of distinct AIDVs for each isolating column that worked')
        self.isolatingColumnProfile = {}
        self.explain.append('distinctValsPerCol: number of distinct values per column')
        self.distinctValsPerCol = {}
        self.explain.append('numIndividuals: total number of individuals (distinct AIDVs) in the table')
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
        sql = f"SELECT count({self.cex}) FROM test"
        cur.execute(sql)
        ans = cur.fetchall()
        self.numIndividuals = ans[0][0]
        sql = "PRAGMA table_info('test')"
        cur.execute(sql)
        ans = cur.fetchall()
        cols = [x[1] for x in ans]
        # The AID column is anyway not attackable, so we exclude it:
        cols.remove(self.aidCol)
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
                        SELECT {col}, count({self.cex})
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
                    SELECT col, icol, cnt, aid FROM
                        (  SELECT cast({sCol} AS text) AS col,
                                cast({iCol} AS text) AS icol,
                                max({self.cex}) AS aid,
                                count({self.cex}) AS cnt
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
                    aid = row[3]
                    if subsetVal in record:
                        record[subsetVal].append([isolateVal,count,aid])
                    else:
                        record[subsetVal] = [[isolateVal,count,aid]]
                for k,v in record.items():
                    self.opportunities += 1
                    if len(v) != 2:
                        # The attack only works if there are two values to
                        # choose from
                        continue
                    for i,j in [(0,1),(1,0)]:
                        if v[i][1] > self.isolateThresh:
                            # We are treating this as not low-count. On average it will be
                            # about right
                            continue
                        # If we get here, then i is the victim, and j is the other value
                        if v[j][1] >= minValues:
                            self.possibles += 1
                            self.possibleVictims.append(
                                {
                                    'subsetCol':sCol,
                                    'subsetVal':k,
                                    'isolateCol':iCol,
                                    'victimVal':v[i][0],
                                    'victimAid':v[i][2],
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
        self.pruneSpreadIsolated(cur,allCols)
        self.checkAttackability(cur,allCols)

    def pruneSpreadIsolated(self,cur,allCols):
        '''
            Go through all possible isolated groups (multiple victims), and
            remove those that do not all have the same unknown column value
        '''
        pass

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
                    SELECT {uCol}, count({self.cex}) FROM test
                    WHERE cast({vic['subsetCol']} AS text) == '{vic['subsetVal']}'
                    GROUP BY 1
                '''
                cur.execute(sql)
                ans = cur.fetchall()
                if len(ans) == 1:
                    # There is only one unknown column value, so can't be an attack
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
                            'aid': vic['victimAid'],
                            'numUnknownVals':numUnknownVals
                        }
                    )
                    self.attackable[vic['victimAid']] = 1
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
                'distinctAttackableIndividuals': len(self.attackable),
                'totalIndividuals': self.numIndividuals,
                'distinctValsPerCol': self.distinctValsPerCol,
                'isolatingColumnProfile': self.isolatingColumnProfile,
                'explain': self.explain,
                'workingByUnknownBuckets': self.workingByUnknownBuckets,
                'workingByDistinctSubset': self.workingByDistinctSubset,
                'workingByDistinctUnknown': self.workingByDistinctUnknown,
                'attackableIndividuals': self.attackable,
            }
        
if __name__ == "__main__":
    '''Put your CSV file path in csvPath, and AID column in aidCol'''
    #csvPath = os.path.join('c:\\','paul','downloads','usa_00001','census_big.csv')

    #csvPath = 'census_big.csv'
    #aidCol = None    # Not multi-row

    #csvPath = 'bankAccounts.csv'
    #aidCol = 'uid'

    csvPath = 'taxi.csv'
    aidCol = 'med'
    '''The following used in the output file name, so change if you wish:'''
    csvName = csvPath
    '''If multi-row, put AID column name here:'''
    print(f"Using file '{csvPath}' with AID column {aidCol}")
    df = pd.read_csv(csvPath)
    if not aidCol:
        df['index_col'] = df.index
        aidCol = 'index_col'
    con = sqlite3.connect(':memory:')
    results = []
    df.to_sql('test',con,if_exists='replace',index=False)
    cur = con.cursor()
    fdc = findDiffConditions(aidCol)
    fdc.runMeasure(cur)
    print('-------------------------------------------------')
    pp.pprint(fdc.possibleVictims)
    pp.pprint(fdc.workingVictims)
    print(f"Opportunities: {fdc.opportunities}")
    print(f"Possibles: {fdc.possibles}")
    print(f"Unknown Opportunities: {fdc.unknownOpportunities}")
    print(f"Working: {fdc.working}")
    print(f"Distinct individuals: {len(fdc.attackable)}")
    results.append(fdc.results())
    outFileName = 'findConditionsResults.'+csvName+'.json'
    with open(outFileName, 'w') as f:
        json.dump(results, f, indent=4, sort_keys=True)