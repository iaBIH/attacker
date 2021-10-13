import pandas as pd
import os.path
import sqlite3
import pprint
import json
import itertools
import random
import sys
filePath = __file__
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import anonymize.anonAlgs

pp = pprint.PrettyPrinter(indent=4)

class findDiffConditions():
    def __init__(self,aidCol,data):
        '''
            This code can be used to measures the number of individuals that
            might be attackable using the GROUP BY difference attack.
        '''
        self.aidCol = aidCol
        self.cex = f"DISTINCT {aidCol}"
        self.attackable = {}
        self.totalCount = data[0]['totalIndividuals']
        self.valsPerCol = data[0]['distinctValsPerCol']
        self.subset = list(set(data[0]['workingByDistinctSubset'].keys()))
        self.unknownAndIsolating = list(set(list(data[0]['workingByDistinctUnknown'].keys()) +
                                       list(data[0]['workingByIsolatingCol'].keys())))
        self.explain = []
        self.results = {
            'friendly': {
                'opportunities': 0,
                'victimGroups': 0,
                'ratio': 0,
            },
            'common': {
                'opportunities': 0,
                'victimGroups': 0,
                'ratio': 0,
            },
            'all': {
                'opportunities': 0,
                'victimGroups': 0,
                'ratio': 0,
            },
        }

    def runMeasure(self,cur):
        '''
            cur is a cursor to an sqlite3 table with name 'test'
        '''
        print('Unknown and Isolating Cols:')
        print(self.unknownAndIsolating)
        print('Subset Cols:')
        print(self.subset)
        # The following loop uses all types of column combinations
        # (not just those susceptible to finding LED cases or
        # more likely to avoid LCF)
        allCols = self.valsPerCol.keys()
        print('All columns:')
        print(allCols)
        doThese = []
        doThese = list(itertools.permutations(allCols, 3))
        if len(doThese) > 20:
            doThese = random.sample(doThese,k=20)
        print(doThese)
        for doThis in doThese:
            sCol = doThis[0]
            iCol = doThis[1]
            uCol = doThis[2]
            res = self.results['all']
            self.runOneGroup(sCol,iCol,uCol,res)
            print(f"Opportunities: {res['opportunities']}")
            print(f"Victim Group Cases: {res['victimGroups']}")
            if res['victimGroups']:
                res['ratio'] = f"1/{round(res['opportunities']/res['victimGroups'])}"
                print(f"Fraction: {res['ratio']}")
    
        # The following loop focuses on "common" types of column combinations
        # (not those susceptible to finding LED cases)
        commonCols = []
        for col,vals in self.valsPerCol.items():
            if vals < self.totalCount/3:
                commonCols.append(col)
        print('Common columns:')
        print(commonCols)
        doThese = []
        doThese = list(itertools.permutations(commonCols, 3))
        if len(doThese) > 20:
            doThese = random.sample(doThese,k=20)
        print(doThese)
        for doThis in doThese:
            sCol = doThis[0]
            iCol = doThis[1]
            uCol = doThis[2]
            res = self.results['common']
            self.runOneGroup(sCol,iCol,uCol,res)
            print(f"Opportunities: {res['opportunities']}")
            print(f"Victim Group Cases: {res['victimGroups']}")
            if res['victimGroups']:
                res['ratio'] = f"1/{round(res['opportunities']/res['victimGroups'])}"
                print(f"Fraction: {res['ratio']}")
    
        # The following loop focuses on combinations that should be most
        # susceptible to LED. We pick 20 random ones.
        doThese = []
        combs = list(itertools.permutations(self.unknownAndIsolating, 2))
        for sCol,(iCol,uCol) in [(a,b) for a in self.subset for b in combs]:
            doThese.append([sCol,iCol,uCol])
        if len(doThese) > 20:
            doThese = random.sample(doThese,k=20)
        for doThis in doThese:
            sCol = doThis[0]
            iCol = doThis[1]
            uCol = doThis[2]
            res = self.results['friendly']
            self.runOneGroup(sCol,iCol,uCol,res)
            print(f"Opportunities: {res['opportunities']}")
            print(f"Victim Group Cases: {res['victimGroups']}")
            if res['victimGroups']:
                res['ratio'] = f"1/{round(res['opportunities']/res['victimGroups'])}"
                print(f"Fraction: {res['ratio']}")
    
    def runOneGroup(self,sCol,iCol,uCol,res):
        print(f"try sCol {sCol},iCol {iCol},uCol {uCol}")

        sql = f'''
            SELECT cast({sCol} AS text) AS sCol,
                    cast({iCol} AS text) AS icol,
                    cast({uCol} AS text) AS ucol,
                    count({self.cex}) AS cnt
            FROM test
            GROUP BY 1,2,3
        '''
        cur.execute(sql)
        ans = cur.fetchall()
        record = {}
        for row in ans:
            sVal = row[0]
            iVal = row[1]
            uVal = row[2]
            cnt = row[3]
            if sVal not in record:
                record[sVal] = {}
            if iVal not in record[sVal]:
                record[sVal][iVal] = {}
            record[sVal][iVal][uVal] = cnt
            res['opportunities'] += 1
        for sVal,iu in record.items():
            if len(iu) != 2:
                # LED only happens if there are two values to choose from
                continue
            uValCnt = []
            for iCol,u in iu.items():
                uValCnt.append(u)
            for vic,oth in [[0,1],[1,0]]:
                if len(uValCnt[vic]) != 1:
                    # Can't be the isolating value because more than one unknown col val
                    continue
                # i can be the isolating value
                if len(uValCnt[oth]) == 1:
                    # Can't be the other value because only one unknown col val to learn
                    continue
                # The victim group bucket must be low-count
                for cnt in uValCnt[vic].values(): pass
                lowThresh,gap,sdSupp = 2,3,1.5
                anon = anonymize.anonAlgs.anon(lowThresh,gap,sdSupp,[0])
                suppress = anon.doSuppress(cnt)
                if not suppress:
                    continue
                res['victimGroups'] += 1

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
    print(f"Using file '{csvPath}' with AID column {aidCol}")
    df = pd.read_csv(csvPath)
    if not aidCol:
        df['index_col'] = df.index
        aidCol = 'index_col'
    con = sqlite3.connect(':memory:')
    results = []
    df.to_sql('test',con,if_exists='replace',index=False)
    cur = con.cursor()
    inFileName = 'findConditionsResults.'+csvName+'.json'
    with open(inFileName, 'r') as f:
        data = json.load(f)
    fdc = findDiffConditions(aidCol,data)
    fdc.runMeasure(cur)
    print('-------------------------------------------------')
    pp.pprint(fdc.results)
    outFileName = 'findConditionsLedResults.'+csvName+'.json'
    with open(outFileName, 'w') as f:
        json.dump(fdc.results, f, indent=4, sort_keys=True)

'''
icol = isolating column
    We know this cause there is only one other bucket
    when all other columns match
ucol = unknown column
    We know this cause there are no other buckets when
    all other columns match
scol = selecting columns
    We know this cause there are more than one other bucket
    when all other columns match

There are only two isolating col values
One of them is LCF
All of the AIDVs in LCF column have the same unknown col val
    This is a possible victim group
The other icol value 

Two possibilities:
    The LCF col AIDVs push the other icol from LCF to non-LCF
'''