import json
import pprint
import itertools
import os.path
import pandas as pd
import numpy as np
pp = pprint.PrettyPrinter(indent=4)

tableParams = {
    'tabType': None,
    'numValsPerColumn': None,
}
anonymizerParams = {
    'suppressPolicy': None,
    'suppressThreshold': None,
    'noisePolicy': None,
    'noiseAmount': None,
}

def makeColumns(result):
    columns = []
    for k,v in result['solution'].items():
        if k == 'explain':
            continue
        columns.append(k)
    for k,v in result['params']['anonymizerParams'].items():
        columns.append(k)
    for k,v in result['params']['tableParams'].items():
        columns.append(k)
    return columns

def loadRow(data,columns,result):
    for k,v in result['solution'].items():
        if k not in columns:
            continue
        data[k].append(str(v))
    for k,v in result['params']['anonymizerParams'].items():
        if k not in columns:
            continue
        data[k].append(str(v))
    for k,v in result['params']['tableParams'].items():
        if k not in columns:
            continue
        data[k].append(str(v))

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
print(df['solveStatus'])
dfFailed = df[df['solveStatus'] != 'Optimal']
for rowi, s in dfFailed.iterrows():
    print(s)
print(df[['solveStatus','numStripped', 'numSuppressedBuckets', 'elapsedTime', 'numChoices', 'numConstraints']])