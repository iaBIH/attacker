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
        # These dicts show how the parameter names in the results files are mapped to the
        # column names in the notebook. (This is done simply to have more compact column
        # names in the notebook)
        self.tableParams = {
            'tabType': 't_tab',
            'numValsPerColumn': 't_shape',
        }
        self.anonymizerParams = {
            'lcfMin': 'a_lcfL',
            'lcfMax': 'a_lcfH',
            'standardDeviation': 'a_sd',
        }
        self.solveParams = {
            'elasticLcf': 'v_lcf',
            'elasticNoise': 'v_nse',
            'numSDs': 'v_nsds',
        }
        self.solutionParams = {
            'elapsedTime': 's_tim',
            'matchFraction': 's_matc',
            'attackableAndRightFrac': 's_rght',
            'attackableButWrongFrac': 's_wrng',
            'nonAttackableFrac': 's_nona',
            'matchImprove': 's_impv',
            'aggregateErrorAvg': 's_err',
            'aggregateErrorTargetAvg': 's_errt',
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
        self.pCols = ['a_lcfH','a_lcfL','a_sd','t_shape','t_tab','v_lcf','v_nse','v_nsds','l_lcf']
    
    def makeColumns(self,result):
        columns = ['seed']
        columns.append('t_aids')
        for k,v in result['solution'].items():
            if self.solutionParams[k] == 'ignore':
                continue
            columns.append(self.solutionParams[k])
        for k,v in result['params']['anonymizerParams'].items():
            columns.append(self.anonymizerParams[k])
        for k,v in result['params']['solveParams'].items():
            columns.append(self.solveParams[k])
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
                data[check[k]].append(str(v).replace(' ',''))
            else:
                if k == 'solveStatus':
                    if v == 'Optimal':
                        v = 1
                    else:
                        v = 0
                data[check[k]].append(v)
            numAppend += 1
        return numAppend

    def addLcfLabel(self,data,ap,columns):
        data['l_lcf'].append(f"LCF({ap['lcfMin']},{ap['lcfMax']})")
        return 1

    def loadRow(self,data,columns,result,path,doprint):
        data['seed'].append(result['params']['seed'])
        data['t_aids'].append(result['params']['numAids'])
        numAppend = 2
        numAppend += self.loadRowWork(data,result['solution'],self.solutionParams,columns)
        numAppend += self.loadRowWork(data,result['params']['anonymizerParams'],self.anonymizerParams,columns)
        numAppend += self.loadRowWork(data,result['params']['solveParams'],self.solveParams,columns)
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
        if 'numSDs' not in result['params']['solveParams']:
            result['params']['solveParams']['numSDs'] = None
            madeChange = True
        if madeChange:
            with open(path, 'w') as f:
                json.dump(result, f, indent=4, sort_keys=True)
        return madeChange

    def gatherResults(self,doprint=False):
        self.columns = []
        stuff = os.listdir('results')
        for thing in stuff:
            if 'results.json' in thing and 'swp' not in thing and '~' not in thing:
                path = os.path.join('results',thing)
                with open(path, 'r') as f:
                    result = json.load(f)
                madeChange = self.updateResult(result,path)
                if madeChange:
                    with open(path, 'r') as f:
                        result = json.load(f)
                if len(self.columns) == 0:
                    self.columns = self.makeColumns(result)
                    data = {}
                    for col in self.columns:
                        data[col] = []
                    if doprint: print(f"Columns:")
                    if doprint: pp.pprint(self.columns)
                self.loadRow(data,self.columns,result,path,doprint)
        df = pd.DataFrame.from_dict(data)
        if doprint: print(df)
        # This dataframe `df` contains all of the individual attack runs (each seed)
        # Now we want to take summary results for the multiple seeds of the same attack
        # Start with a dataframe containing only the parameters columns (distinct values)
        dfParams = df[self.pCols]
        dfParams = dfParams.drop_duplicates()
        if doprint: print(dfParams)
        # For each distinct parameters set, we want to take the avg, min, and max for the
        # other columns and add to a new aggregates table
        agg = {'num':[]}
        for col in self.columns:
            if col in self.pCols:
                agg[col] = []
            elif pd.api.types.is_numeric_dtype(df[col]):
                # This is a numeric column, so we'll be taking the stats
                agg[col+'_av'] = []
                agg[col+'_mn'] = []
                agg[col+'_mx'] = []
                agg[col+'_sd'] = []
        # Now agg is the basic dict. for building the aggregates dataframe
        for rowi, s in dfParams.iterrows():
            query = ''
            for col in dfParams.columns:
                query += f'({col} == "{s[col]}") and '
            query = query[:-5]
            dfTemp = df.query(query)
            agg['num'].append(dfTemp.shape[0])
            for col in self.columns:
                if col in self.pCols:
                    agg[col].append(s[col])
                elif pd.api.types.is_numeric_dtype(df[col]):
                    agg[col+'_av'].append(dfTemp[col].mean())
                    agg[col+'_mn'].append(dfTemp[col].min())
                    agg[col+'_mx'].append(dfTemp[col].max())
                    agg[col+'_sd'].append(dfTemp[col].std())
        #pp.pprint(agg)
        dfAgg = pd.DataFrame.from_dict(agg)
        if doprint: print(dfAgg)
        return df,dfAgg

if __name__ == "__main__":
    print("Example of resultGatherer")
    rg = resultGatherer()
    df,dfAgg = rg.gatherResults(doprint=True)
    print(df)
    print(list(df.columns))
    print(df[['s_sol','s_str', 's_sup', 's_tim', 's_choi', 's_cons']])