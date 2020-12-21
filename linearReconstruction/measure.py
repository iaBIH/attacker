import json
import pprint
import itertools
import os.path
import pandas as pd
import numpy as np
pp = pprint.PrettyPrinter(indent=4)

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

df1 = {
    'a': [1,1],
    'b': [2,2],
    'c': [3,3],
}
df2 = {
    'a': [1],
    'b': [2],
    'c': [3],
}
df = df[]