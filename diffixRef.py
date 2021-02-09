import pprint
import subprocess
import csv
import json
import os.path
import ast

class diffixRef:
    """
    """
    def __init__(self,cmd='OpenDiffix.CLI.exe'):
        self.pp = pprint.PrettyPrinter(indent=4)
        self.cmd = cmd
        self.params = None
        self.queryRes = None
        self.answerList = []
        if os.path.isfile(cmd):
            self.isReady = True
        else:
            self.isReady = False

    def getNoiseParams(self):
        return self.params['noise']

    def ready(self):
        return self.isReady
    
    def getOutlierParams(self):
        return self.params['outlier_count']

    def getTopParams(self):
        return self.params['top_count']

    def getParams(self,db='tables/testAttack.db',force=False):
        rtn = {}
        if not force and self.params:
            rtn['success'] = True
            rtn['params'] = self.params
            return rtn
        command = []
        command.append(self.cmd)
        # database
        command.append('-d')
        command.append(db)
        command.append('--aid-columns')
        command.append('a.b')
        # query
        command.append('-q')
        command.append('select aid1 from tab')
        command.append('--dry-run')
        result = subprocess.run(command, stdout=subprocess.PIPE)
        out = result.stdout.decode("utf-8")
        if result.returncode != 0:
            rtn['success'] = False
            rtn['error'] = out
        else:
            rtn['success'] = True
            params = json.loads(out)
            rtn['params'] = params['anonymization_parameters']
            self.params = params['anonymization_parameters']
        return rtn

    def iterAnswers(self):
        for answer in self.answerList:
            yield answer

    def is_number(self,n):
        try:
            float(n)
            return True
        except ValueError:
            return False

    def buildAnswers(self):
        self.answerList = []
        for res in self.queryRes['query_results']:
            if res['success']:
                ans = res['result']['rows']
                for i in range(len(ans)):
                    for j in range(len(ans[i])):
                        if self.is_number(ans[i][j]):
                            ans[i][j] = ast.literal_eval(ans[i][j])
                self.answerList.append(ans)
            else:
                self.answerList.append(None)

    def queryAll(self,sqlList,numSeeds,aids,db,params):
        # prepare the query file
        queryFile = os.path.join('tables','queries.json')
        queries = []
        for seed in range(numSeeds):
            for sql in sqlList:
                query = {}
                query['query'] = sql
                query['db_path'] = db
                params['seed'] = seed
                params['table_settings'] = aids
                query['anonymization_parameters'] = params
                queries.append(query)
        with open(queryFile, 'w') as outfile:
            json.dump(queries, outfile, indent=4)
        # prepare the command line
        command = []
        command.append(self.cmd)
        command.append('--queries-path')
        command.append(queryFile)
        result = subprocess.run(command, stdout=subprocess.PIPE)
        out = result.stdout.decode("utf-8")
        try:
            self.queryRes = json.loads(out)
        except ValueError as e:
            print(f"diffixRef: queryAll: json parser error: '{e}'")
            print("Output from query:")
            print(out)
            quit()
        self.buildAnswers()

    def query(self,sql,seed,aids,db,params):
        command = []
        command.append(self.cmd)
        # database
        command.append('-d')
        command.append(db)
        # aid columns
        command.append('--aid-columns')
        for tabAid in aids:
            for aid in aids[tabAid]['aid_columns']:
                command.append(tabAid + '.' + aid)
        # query
        command.append('-q')
        command.append(sql)
        #seed
        command.append('-s')
        command.append(str(seed))
        # outlier counts
        command.append('--threshold-outlier-count')
        command.append(str(params['outlier_count']['lower']))
        command.append(str(params['outlier_count']['upper']))
        command.append('--threshold-top-count')
        command.append(str(params['top_count']['lower']))
        command.append(str(params['top_count']['upper']))
        command.append('--threshold-low-count')
        command.append(str(params['low_count_threshold']['lower']))
        command.append(str(params['low_count_threshold']['upper']))
        command.append('--noise')
        command.append(str(params['noise']['standard_dev']))
        command.append(str(params['noise']['cutoff']))
        result = subprocess.run(command, stdout=subprocess.PIPE)
        rtn = {}
        out = result.stdout.decode("utf-8")
        if result.returncode != 0:
            rtn['success'] = False
            rtn['error'] = out
        else:
            rtn['success'] = True
            # Turn result bytes into a string
            outList = str.splitlines(out)
            ans = list(csv.reader(iter(outList),delimiter=';'))
            for i in range(len(ans)):
                for j in range(len(ans[i])):
                    ans[i][j] = ast.literal_eval(ans[i][j])
            rtn['answer'] = ans
        return rtn
        

if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=4)
    defaultRef = {
        'low_count_threshold': {'lower': 2, 'upper': 5},
        'noise': {'cutoff': 5.0, 'standard_dev': 1.0},
        'outlier_count': {'lower': 1, 'upper': 2},
        'top_count': {'lower': 2, 'upper': 3}
    }
    aids=[{'table':'tab','aid':'aid1'}]
    db='tables/testAttack.db'
    seed=1
    dr = diffixRef()
    rtn = dr.query("select t1 from tab",seed,aids,db,defaultRef)
    if rtn['success']:
        pp.pprint(rtn['answer'])
    else:
        print(f"ERROR: {rtn['error']}")
    rtn = dr.query("select count(*) from tab",seed,aids,db,defaultRef)
    if rtn['success']:
        pp.pprint(rtn['answer'])
    else:
        print(f"ERROR: {rtn['error']}")
    rtn = dr.getParams()
    if rtn['success']:
        pp.pprint(rtn['params'])
    else:
        print(f"ERROR: {rtn['error']}")
    print("Noise")
    pp.pprint(dr.getNoiseParams())
    print("Outliers")
    pp.pprint(dr.getOutlierParams())
    print("Top")
    pp.pprint(dr.getTopParams())