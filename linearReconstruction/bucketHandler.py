import pprint
import itertools
import pandas as pd
import numpy as np
import pprint
pp = pprint.PrettyPrinter(indent=4)


class bucketHandler:
    ''' Manages various combinations of buckets '''
    def __init__(self,columns,an):
        ''' columns here is a list of column names.
            an is the anonymizer class object
        '''
        self.pp = pprint.PrettyPrinter(indent=4)
        self.cols = columns
        self.an = an
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
            Returns the bucket and a list of sub-buckets.
        '''
        if df is None:
            df = self.df
        for i in range(len(self.cols)-1):
            # Get all combinations with i columns
            for colComb in itertools.combinations(self.cols,i+1):
                # Get all single columns not in the combination
                #combCounts = self.getColCounts(colComb,df=df)
                dfComb = self.getColDf(colComb,df=df)
                for col in self.cols:
                    if col in colComb:
                        continue
                    # Now, for every bucket of colComb, we want to find all buckets
                    # in colComb+col that are sub-buckets of colComb.
                    subCols = list(colComb)
                    subCols.append(col)
                    #subCounts = self.getColCounts(subCols,col=col,df=df)
                    dfAllSub = self.getColDf(subCols,df=df)
                    #for bkt1,cnts1 in combCounts.items():
                    for _, sComb in dfComb.iterrows():
                        dfSub = pd.DataFrame(columns=self.dfCols)
                        #for bkt2,cnts2 in subCounts.items():
                        for _, sSub in dfAllSub.iterrows():
                            if self.isSubBucket(sSub['bkt'],sComb['bkt']):
                                df2 = pd.DataFrame([sSub], columns=self.dfCols)
                                dfSub = dfSub.append(df2,ignore_index=True)
                        if len(dfSub.index) == 0:
                            continue
                        # bkt1 is the bucket, subBkts are the sub-buckets of bkt1
                        # col is the additional column that comprises the sub-buckets
                        yield sComb,dfSub,col

    def stripAwaySuppressedDimensions(self):
        ''' Strip away the rows for cases where all of the rows for a given dimension
            are suppressed because no constraints can be generated for these
        '''
        numRowsBefore = len(self.df.index)
        numNonSuppressed = [0 for _ in range(len(self.cols)+1)]
        # Make a first pass through the buckets table df, and for each dimension,
        # count number of non-suppressed buckets 
        for rowi, s in self.df.iterrows():
            if s['cmin'] > 0:
                numNonSuppressed[s['dim']] += 1
        for dim in range(1,len(self.cols)+1):
            if numNonSuppressed[dim] == 0:
                # All rows for this dimension are suppressed. Remove them.
                #self.df = self.df.query(f"dim != {dim}")
                self.df = self.df[self.df['dim'] != dim]
        numRowsAfter = len(self.df.index)
        return numRowsBefore - numRowsAfter
    
    def mergeSuppressedBuckets(self):
        # This merging turns out to be completely unecessary  :(
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
        # remove from the current df because we are looping on its contents.
        self.dfMerged = self.df.copy()
        print(self.dfMerged)
        # Remove all suppressed buckets from copy
        self.dfMerged = self.df[self.dfMerged['cmin'] != -1]
        print(self.dfMerged)
        for s,dfSub,scol in self.subBucketIterator(df=self.df):
            # count the number of suppressed buckets, and at the same time, get the
            # column values of the non-suppressed buckets
            print(s)
            print(dfSub)
            print(scol)
            vals = []
            sMerge = None
            for _, srow in dfSub.iterrows():
                if srow['cmin'] == -1:
                    vals.append(srow[scol])
                    sMerge = srow    # This will be the basis of the new row
                    # Just validate that this bucket is not in dfMerged
                    if len(self.dfMerged[self.dfMerged['bkt'] == srow['bkt']]) > 0:
                        print(f"ERROR: mergeSuppressedBuckets: Unexpected 2: {srow}")
                        quit()
            numSuppressed = len(vals)
            if numSuppressed == 0:
                # no suppressed sub-buckets, so continue
                if s['cmin'] == -1:
                    # Don't expect bucket to be suppressed when sub-buckets are not!
                    print(f"ERROR: mergeSuppressedBuckets: Unexpected 1: {s}")
                    quit()
                continue
            # We have one or more suppressed sub-buckets, so merge
            # The max count of the merged bucket is the sum of the
            # max possible counts of the suppressed buckets. For now at least
            # these max possible counts are all the same
            maxCnt = numSuppressed * self.an.getMaxSuppressedCount()
            if maxCnt == 0:
                # This would happen for instance if hard threshold of 1
                # Don't need a bucket because anyway it would never have anything assigned to it
                continue
            # The merged bucket's name
            sMerge['bkt'] = f"{s['bkt']}.merge.{scol}"
            sMerge[scol] = vals
            sMerge['cmin'] = 0
            sMerge['cmax'] = maxCnt
            print(sMerge)
            print("----")
            pass
        quit()

    def addBucket(self,cols,vals,cmin=0,cmax=0):
        # Make a row with empty lists
        df2 = pd.DataFrame(columns=self.dfCols)
        init = [[] for _ in range(len(self.dfCols))]
        df2.loc[0] = init
        s = df2.loc[0]
        s['cmin'] = cmin
        s['cmax'] = cmax
        dim = 0
        bkt = ''
        for col,val in zip(cols,vals):
            #i = self.dfCols.index(col)
            s[col] = [val]
            dim += 1
            bkt += f"C{col}"
            bkt += f"V{val}."
        bkt = bkt[:-1]
        s['dim'] = dim
        # add the bucket name
        s['bkt'] = bkt
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
            # bkt1 does not have one more dimension, so cannot be sub-bucket of bkt2.
            return False
        for bkt in bkts2:
            if bkt not in bkts1:
                return False
        return True

    def getAllCounts(self,df=None):
        if df is None:
            df = self.df
        return self._getCounts(df)

    def getColDf(self,cols,col=None,df=None):
        ''' Get all buckets comprised only of the given columns `cols`
            At the same time, build a list of the values in column col
        '''
        if df is None:
            df = self.df
        df1 = df.copy()
        for rowi, s in df.iterrows():
            keep = True
            for j in range(len(self.cols)):
                if self.dfCols[j] in cols and len(s[j]) == 0:
                    # we want this column but the entry is null
                    keep = False
                    break
                elif self.dfCols[j] not in cols and len(s[j]) > 0:
                    # we don't want this column, but the entry exists
                    keep = False
                    break
            if keep is False:
                df1 = df1.drop([rowi])
        return df1

    def _getCounts(self,df,col=None):
        ''' Returns a dict where key is bucket expression and val contains
            the pass
        '''
        keys = {}
        for _, row in df.iterrows():
            keys[row['bkt']] = {'cmin':row['cmin'],'cmax':row['cmax']}
            if col:
                keys[row['bkt']]['colVal'] = row[col]
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
