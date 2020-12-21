import json
import pprint
import itertools
import os.path
import pandas as pd
import numpy as np
pp = pprint.PrettyPrinter(indent=4)

tableParams = {
    'tabType': 't.tab',
    'numValsPerColumn': 't.shape',
}
anonymizerParams = {
    'suppressPolicy': 'a.supP',
    'suppressThreshold': 'a.supT',
    'noisePolicy': 'a.noiP',
    'noiseAmount': 'a.noiA',
}
solutionParams = {
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

def makeColumns(result):
    columns = []
    for k,v in result['solution'].items():
        if k == 'explain':
            continue
        columns.append(solutionParams[k])
    for k,v in result['params']['anonymizerParams'].items():
        columns.append(anonymizerParams[k])
    for k,v in result['params']['tableParams'].items():
        columns.append(tableParams[k])
    return columns

def loadRow(data,columns,result):
    for k,v in result['solution'].items():
        if k not in solutionParams or solutionParams[k] not in columns:
            continue
        data[solutionParams[k]].append(v)
    for k,v in result['params']['anonymizerParams'].items():
        if k not in anonymizerParams or anonymizerParams[k] not in columns:
            continue
        data[anonymizerParams[k]].append(v)
    for k,v in result['params']['tableParams'].items():
        if tableParams[k] not in columns:
            continue
        data[tableParams[k]].append(v)

def gatherResults():
    columns = []
    stuff = os.listdir('results')
    for thing in stuff:
        if 'results.json' in thing and 'swp' not in thing and '~' not in thing:
            path = os.path.join('results',thing)
            print(path)
            with open(path, 'r') as f:
                result = json.load(f)
                if len(columns) == 0:
                    columns = makeColumns(result)
                    data = {}
                    for col in columns:
                        data[col] = []
                loadRow(data,columns,result)
    df = pd.DataFrame.from_dict(data)
    return df

df = gatherResults()
print(df)
print(list(df.columns))
print(df['s.sol'])
dfFailed = df[df['s.sol'] != 'Optimal']
for rowi, s in dfFailed.iterrows():
    print(s)
print(df[['s.sol','s.str', 's.sup', 's.tim', 's.choi', 's.cons']])