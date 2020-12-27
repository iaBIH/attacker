import json
import pprint
import itertools
import os.path
import pandas as pd
pp = pprint.PrettyPrinter(indent=4)

class resultGatherer:
    '''
    '''
    def __init__(self):
        self.tableParams = {
            'tabType': 't_tab',
            'numValsPerColumn': 't_shape',
        }
        self.anonymizerParams = {
            'lcfMin': 'a_lcfL',
            'lcfMax': 'a_lcfH',
            'standardDeviation': 'a_sd',
        }
        self.solutionParams = {
            'elapsedTime': 's_tim',
            'matchFraction': 's_matc',
            'attackableAndRightFrac': 's_rght',
            'attackableButWrongFrac': 's_wrng',
            'nonAttackableFrac': 's_nona',
            'matchImprove': 's_impv',
            'numBuckets': 's_bkts',
            'numChoices': 's_choi',
            'numConstraints': 's_cons',
            'numIgnoredBuckets': 's_ign',
            'numStripped': 's_str',
            'numSuppressedBuckets': 's_sup',
            'solveStatus': 's_sol',
            # These are out of date or should otherwise be ignored
            'susceptibleFraction': 'ignore',
            'explain': 'ignore',
        }
    
    def makeColumns(self,result):
        columns = ['seed']
        for k,v in result['solution'].items():
            if self.solutionParams[k] == 'ignore':
                continue
            columns.append(self.solutionParams[k])
        for k,v in result['params']['anonymizerParams'].items():
            columns.append(self.anonymizerParams[k])
        for k,v in result['params']['tableParams'].items():
            columns.append(self.tableParams[k])
        columns.append('l_lcf')
        return columns
    
    def loadRowWork(self,data,res,check,columns):
        numAppend = 0
        for k,v in res.items():
            if k not in check or check[k] not in columns:
                continue
            if type(v) is list:
                data[check[k]].append(str(v))
            else:
                data[check[k]].append(v)
            numAppend += 1
        return numAppend

    def addLcfLabel(self,data,ap,columns):
        data['l_lcf'].append(f"LCF({ap['lcfMin']},{ap['lcfMax']})")
        return 1

    def loadRow(self,data,columns,result,path,doprint):
        numAppend = 1
        data['seed'].append(result['params']['seed'])
        numAppend += self.loadRowWork(data,result['solution'],self.solutionParams,columns)
        numAppend += self.loadRowWork(data,result['params']['anonymizerParams'],self.anonymizerParams,columns)
        numAppend += self.loadRowWork(data,result['params']['tableParams'],self.tableParams,columns)
        numAppend += self.addLcfLabel(data,result['params']['anonymizerParams'],columns)
        if numAppend != len(columns):
            print(f"Wrong number of values ({numAppend} vs. {len(columns)} on {path}")
            print(columns)
            pp.pprint(result['params'])
            pp.pprint(result['solution'])
            quit()
    
    def updateResult(self,result,path):
        ''' Here we modify the results as per new versions of results
        '''
        madeChange = False
        if madeChange:
            with open(path, 'w') as f:
                json.dump(result, f, indent=4, sort_keys=True)

    def gatherResults(self,doprint=False):
        columns = []
        stuff = os.listdir('results')
        for thing in stuff:
            if 'results.json' in thing and 'swp' not in thing and '~' not in thing:
                path = os.path.join('results',thing)
                with open(path, 'r') as f:
                    result = json.load(f)
                self.updateResult(result,path)
                if len(columns) == 0:
                    columns = self.makeColumns(result)
                    data = {}
                    for col in columns:
                        data[col] = []
                    if doprint: print(f"Columns:")
                    if doprint: pp.pprint(columns)
                self.loadRow(data,columns,result,path,doprint)
        df = pd.DataFrame.from_dict(data)
        return df

if __name__ == "__main__":
    print("Example of resultGatherer")
    rg = resultGatherer()
    df = rg.gatherResults(doprint=True)
    print(df)
    print(list(df.columns))
    print(df['s_sol'])
    dfFailed = df[df['s_sol'] != 'Optimal']
    for rowi, s in dfFailed.iterrows():
        print(s)
    print(df[['s_sol','s_str', 's_sup', 's_tim', 's_choi', 's_cons']])