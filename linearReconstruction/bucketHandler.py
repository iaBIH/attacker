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

    def isSubBucket(self,bkt1,bkt2):
        ''' Returns True if bkt1 is a sub-bucket of bkt2. This means that bkt1 has one
            more column dimension than bkt2, and all of the bucket names of bkt2 are
            also in bkt1.
            example: Ci1V1_Ci2V1 is a sub-bucket of Ci1V1
        '''
        bkts1 = bkt1.split('_')
        bkts2 = bkt2.split('_')
        if len(bkts1) != len(bkts2) + 1:
            # bkt1 does not have one more dimenstion, so cannot be sub-bucket of bkt2.
            return False
        for bkt in bkts2:
            if bkt not in bkts1:
                return False
        return True

    def getAllCounts(self):
        return self._getCounts(self.df)

    def getColCounts(self,cols):
        ''' Get all buckets comprised only of the given columns `cols`
        '''
        df1 = self.df.copy()
        for rowi, s in self.df.iterrows():
            keep = True
            for j in range(len(self.dfCols) - 1):
                if self.dfCols[j] in cols and type(s[j]) is not str:
                    # we want this column but the entry is null
                    keep = False
                    break
                elif self.dfCols[j] not in cols and type(s[j]) is str:
                    # we don't want this column, but the entry exists
                    keep = False
                    break
            if keep is False:
                df1 = df1.drop([rowi])
        return self._getCounts(df1)

    def _getCounts(self,df):
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
