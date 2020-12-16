import pprint
import itertools
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
        self.cols = columns
        self.dfCols = []
        for col in columns:
            self.dfCols.append(col)
        self.dfCols.append('cmin')    # min probable count
        self.dfCols.append('cmax')    # max probable count
        self.dfCols.append('dim')     # bucket dimension
        self.dfCols.append('bkt')     # the bucket name
        self.df = pd.DataFrame(columns=self.dfCols)

    def subBucketIterator(self,df=None):
        ''' Iterates through every bucket / sub-bucket combination in df
            Returns the combination and a list of sub-buckets.
        '''
        if df is None:
            df = self.df
        for i in range(len(self.cols)-1):
            # Get all combinations with i columns
            for colComb in itertools.combinations(self.cols,i+1):
                # Get all single columns not in the combination
                combCounts = self.getColCounts(colComb,df=df)
                for col in self.cols:
                    if col in colComb:
                        continue
                    # Now, for every bucket of colComb, we want to find all buckets
                    # in colComb+col that are sub-buckets of colComb.
                    subCols = list(colComb)
                    subCols.append(col)
                    subCounts = self.getColCounts(subCols,df=df)
                    for bkt1,cnts1 in combCounts.items():
                        subBkts = []
                        subCnts = []
                        for bkt2,cnts2 in subCounts.items():
                            if self.isSubBucket(bkt2,bkt1):
                                subBkts.append(bkt2)
                                subCnts.append(cnts2)
                        if len(subBkts) == 0:
                            continue
                        # bkt1 is the bucket, subBkts are the sub-buckets of bkt1
                        yield bkt1,subBkts,cnts1,subCnts

    def stripAwaySuppressedDimensions(self):
        ''' Strip away the rows for cases where all of the rows for a given dimension
            are suppressed because no constraints can be generated for these
        '''
        numNonSuppressed = [0 for _ in range(len(self.cols)+1)]
        # Make a first pass through the buckets table df, and for each dimension,
        # count number of non-suppressed buckets 
        for rowi, s in self.df.iterrows():
            dim = len(self.cols) - s.isna().sum()
            if s['cmin'] != -1:
                numNonSuppressed[dim] += 1
        for dim in range(1,len(self.cols)+1):
            if numNonSuppressed[dim] == 0:
                # All rows for this dimension are suppressed. Remove them.
                #self.df = self.df.query(f"dim != {dim}")
                self.df = self.df[self.df['dim'] != dim]
    
    def mergeSuppressedBuckets(self):
        ''' Say column c1 has values a,b,c,d,e and c2 has values i,j,k,l,m.
            For the 2-dim buckets c1.c2, supposed that the 2D buckets with
            c1a and c2 l and m are suppressed, but not c1a and c2 i, j, and k.
            In this case we want to merge c1a.c2l and c1a.c2m into a single
            non-suppressed bucket so that we can use it for a constraint.
            It is possible that at the same time, c2m when combined with c1 a and b
            is suppressed, but not with c1 c, d, and e. In this case we want to
            merge c1a.c2m and c1b.c2m into a single bucket. So:
                c1a.c2l + c1a.c2m --> c1a.c2l+m
                ca1.c2m + c1b.c2m --> c1a+b.c2m
            In this example, three 2D buckets are merged into two 2D buckets. The
            two merged buckets will have less-than equations allowing for a number
            of possible distributions of (for instance) c2m with c1a and c1b.
        '''
        # Make a copy of the df. We'll add and remove from this copy. Note that we can't
        # remove 
        for bkt,sbkts,cnts,scnts in self.subBucketIterator():
            pass

    def addBucket(self,cols,vals,cmin=0,cmax=0):
        # Make a row with NULL values
        pass
        df2 = pd.DataFrame(columns=self.dfCols)
        init = [np.nan for _ in range(len(self.dfCols))]
        df2.loc[0] = init
        s = df2.loc[0]
        s['cmin'] = cmin
        s['cmax'] = cmax
        dim = 0
        bkt = ''
        for col,val in zip(cols,vals):
            #i = self.dfCols.index(col)
            s[col] = str(val)
            dim += 1
            bkt += f"C{col}"
            bkt += f"V{val}."
        bkt = bkt[:-1]
        s['dim'] = dim
        s['bkt'] = bkt
        # add the bucket name
        pass
        df2 = pd.DataFrame([s], columns=self.dfCols)
        self.df = self.df.append(df2,ignore_index=True)

    def getColsValsFromBkt(self,bktIn):
        cols = []
        vals = []
        bkts = bktIn.split('.')
        for bkt in bkts:
            # This strips the leading 'C' before split
            col,val = bkt[1:].split('V')
            cols.append(col)
            vals.append(val)
        return cols,vals
    
    def isSubBucket(self,bkt1,bkt2):
        ''' Returns True if bkt1 is a sub-bucket of bkt2. This means that bkt1 has one
            more column dimension than bkt2, and all of the bucket names of bkt2 are
            also in bkt1.
            example: Ci1V1.Ci2V1 is a sub-bucket of Ci1V1
        '''
        bkts1 = bkt1.split('.')
        bkts2 = bkt2.split('.')
        if len(bkts1) != len(bkts2) + 1:
            # bkt1 does not have one more dimenstion, so cannot be sub-bucket of bkt2.
            return False
        for bkt in bkts2:
            if bkt not in bkts1:
                return False
        return True

    def getAllCounts(self,df=None):
        if df is None:
            df = self.df
        return self._getCounts(df)

    def getColCounts(self,cols,df=None):
        ''' Get all buckets comprised only of the given columns `cols`
        '''
        if df is None:
            df = self.df
        df1 = df.copy()
        for rowi, s in df.iterrows():
            keep = True
            for j in range(len(self.cols)):
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
            for i in range(len(self.cols)):
                if type(row[self.cols[i]]) == str:
                    key += f"C{self.cols[i]}"
                    key += f"V{row[self.cols[i]]}."
            key = key[:-1]
            keys[key] = {'cmin':row['cmin'],'cmax':row['cmax']}
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
