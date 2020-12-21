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
            'tabType': 't.tab',
            'numValsPerColumn': 't.shape',
        }
        self.anonymizerParams = {
            'suppressPolicy': 'a.supP',
            'suppressThreshold': 'a.supT',
            'noisePolicy': 'a.noiP',
            'noiseAmount': 'a.noiA',
        }
        self.solutionParams = {
            'elapsedTime': 's.tim',
            'matchFraction': 's.mat',
            'numBuckets': 's.bkts',
            'numChoices': 's.choi',
            'numConstraints': 's.cons',
            'numIgnoredBuckets': 's.ign',
            'numStripped': 's.str',
            'numSuppressedBuckets': 's.sup',
            'solveStatus': 's.sol'
        }
    
    def makeColumns(self,result):
        columns = ['seed']
        for k,v in result['solution'].items():
            if k == 'explain':
                continue
            columns.append(self.solutionParams[k])
        for k,v in result['params']['anonymizerParams'].items():
            columns.append(self.anonymizerParams[k])
        for k,v in result['params']['tableParams'].items():
            columns.append(self.tableParams[k])
        return columns
    
    def loadRow(self,data,columns,result):
        data['seed'].append(result['params']['seed'])
        for k,v in result['solution'].items():
            if k not in self.solutionParams or self.solutionParams[k] not in columns:
                continue
            data[self.solutionParams[k]].append(v)
        for k,v in result['params']['anonymizerParams'].items():
            if k not in self.anonymizerParams or self.anonymizerParams[k] not in columns:
                continue
            data[self.anonymizerParams[k]].append(v)
        for k,v in result['params']['tableParams'].items():
            if self.tableParams[k] not in columns:
                continue
            data[self.tableParams[k]].append(v)
    
    def gatherResults(self):
        columns = []
        stuff = os.listdir('results')
        for thing in stuff:
            if 'results.json' in thing and 'swp' not in thing and '~' not in thing:
                path = os.path.join('results',thing)
                with open(path, 'r') as f:
                    result = json.load(f)
                    if len(columns) == 0:
                        columns = self.makeColumns(result)
                        data = {}
                        for col in columns:
                            data[col] = []
                    self.loadRow(data,columns,result)
        df = pd.DataFrame.from_dict(data)
        return df

if __name__ == "__main__":
    print("Example of resultGatherer")
    rg = resultGatherer()
    df = rg.gatherResults()
    print(df)
    print(list(df.columns))
    print(df['s.sol'])
    dfFailed = df[df['s.sol'] != 'Optimal']
    for rowi, s in dfFailed.iterrows():
        print(s)
    print(df[['s.sol','s.str', 's.sup', 's.tim', 's.choi', 's.cons']])