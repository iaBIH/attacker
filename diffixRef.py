import pprint
import subprocess
import csv
import json
import os.path

class diffixRef:
    """
    """
    def __init__(self,cmd='OpenDiffix.CLI.exe'):
        self.pp = pprint.PrettyPrinter(indent=4)
        self.cmd = cmd
        self.params = None
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

    def query(self,sql,seed,aids,db,params):
        command = []
        command.append(self.cmd)
        # database
        command.append('-d')
        command.append(db)
        # aid columns
        command.append('--aid-columns')
        for tabAid in aids:
            command.append(tabAid['table'] + '.' + tabAid['aid'])
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
            reader = csv.reader(iter(outList),delimiter=';')
            rtn['answer'] = list(reader)
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