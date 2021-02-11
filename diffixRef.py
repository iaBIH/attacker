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

    def getVersion(self):
        if not self.queryRes:
            return None,None
        vStr = self.queryRes['version']['version']['version']
        vList = vStr.split('.')
        mult = 100000
        vNum = 0
        for v in reversed(vList):
            vNum += mult * int(v)
            mult *= 100
        return vStr,vNum

    def getDate(self):
        if not self.queryRes:
            return None
        dStr = self.queryRes['time']
        return dStr

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
                qp = params.copy()
                qp['seed'] = seed
                qp['table_settings'] = aids
                query['anonymization_parameters'] = qp
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
        ''' unused '''
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


'''
{
  "version": {
    "name": "OpenDiffix Reference implementation",
    "version": {
      "version": "0.0.356",
      "commit_number": 355,
      "branch": "sebastian/batch-mode-for-CLI",
      "sha": "b7a8b49",
      "dirty_build": false
    }
  },
  "time": "Friday, February 4, 2021",
  "query_results": [
  '''