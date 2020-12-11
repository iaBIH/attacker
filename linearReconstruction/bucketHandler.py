import pprint
import pandas as pd
import numpy as np

class bucketHandler:
    ''' Manages various combinations of buckets '''
    def __init__(self,columns):
        ''' columns here is a list of column names. our buckets, however,
            are going to have column/value tuples, so we want a dataframe
            with len(columns) * 2 columns
        '''
        self.pp = pprint.PrettyPrinter(indent=4)
        self.dfCols = []
        for col in columns:
            self.dfCols.append(col)
        self.dfCols.append('count')
        self.df = pd.DataFrame(columns=self.dfCols)

    def addBucket(self,cols,vals,count=0):
        # Make a row with NULL values
        s = [np.nan for _ in range(len(self.dfCols))]
        s[-1] = count
        for col,val in zip(cols,vals):
            i = self.dfCols.index(col)
            s[i] = str(val)
        df2 = pd.DataFrame([s], columns=self.dfCols)
        self.df = self.df.append(df2,ignore_index=True)

    def getAllKeys(self):
        return self._getKeys(self.df)

    def getOneColKeys(self,col):
        df1 = self.df.copy()
        for i, s in self.df.iterrows():
            if s.isna().sum() != len(self.dfCols) - 2:
                # This is a row with only one column bucket
                df1 = df1.drop([i])
        return self._getKeys(df1)

    def _getKeys(self,df):
        ''' Returns a dict where key is bucket expression and val is count
        '''
        keys = {}
        for _, row in df.iterrows():
            # This loop gives me the columns with values
            key = ''
            for i in range(len(self.dfCols)-1):
                if type(row[self.dfCols[i]]) == str:
                    key += f"C{self.dfCols[i]}"
                    key += f"V{row[self.dfCols[i]]}_"
            key = key[:-1]
            keys[key] = row['count']
        return keys

if __name__ == "__main__":
    import random
    pp = pprint.PrettyPrinter(indent=4)
    cols = ['c1','c2','c3']
    bh = bucketHandler(cols)
    print('-----\n',bh.df)
    bh.addBucket(['c1'],[1])
    print('-----\n',bh.df)
    bh.addBucket(['c2','c3'],[3,4])
    print('-----\n',bh.df)
    # populate
    pop = { 'c1':[1,2,3],
            'c2':[4,5,6],
            'c3':[7,8,9],
            }
    for col in pop:
        print(col)
