import pprint
import subprocess
import csv
import json

class diffixRef:
    """
    """
    def __init__(self,cmd='OpenDiffix.CLI.exe',
                      db='tables/testAttack.db',
                      outliers=None,
                      top=None,
                      lcf=None,
                      noise=None,
                ):
        self.cmd = cmd
        self.db = db
        rtn = self.getParams()
        if rtn['success']:
            self.params = rtn['params']
        else:
            print(f"ERROR diffixRef: bad getParams: {rtn['error']}")
            quit()
        self.outliers = outliers
        self.top = top
        self.lcf = lcf
        self.noise = noise
        if self.outliers:
            self.params['outlier_count']['lower'] = outliers[0]
            self.params['outlier_count']['upper'] = outliers[1]
        if self.top:
            self.params['top_count']['lower'] = top[0]
            self.params['top_count']['upper'] = top[1]
        if self.noise:
            self.params['noise']['standard_dev'] = noise[0]
            self.params['noise']['cutoff'] = noise[1]

    def getNoiseParams(self):
        return self.params['noise']

    def getOutlierParams(self):
        return self.params['outlier_count']

    def getTopParams(self):
        return self.params['top_count']

    def _getBasicCommands(self):
        command = []
        command.append(self.cmd)
        # database
        command.append('-d')
        command.append(self.db)
        return command

    def getParams(self):
        command = self._getBasicCommands()
        command.append('--aid-columns')
        command.append('a.b')
        # query
        command.append('-q')
        #command.append('select col from tab')
        command.append('anything')
        command.append('--dry-run')
        result = subprocess.run(command, stdout=subprocess.PIPE)
        rtn = {}
        out = result.stdout.decode("utf-8")
        if result.returncode != 0:
            rtn['success'] = False
            rtn['error'] = out
        else:
            rtn['success'] = True
            params = json.loads(out)
            rtn['params'] = params['anonymization_parameters']
        return rtn

    def query(self,sql,seed=1,aids=[{'table':'tab','aid':'aid1'}]):
        command = self._getBasicCommands()
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
        if self.outliers:
            command.append('--threshold-outlier-count')
            command.append(str(self.outliers[0]))  # lower
            command.append(str(self.outliers[1]))  # upper
        if self.top:
            command.append('--threshold-top-count')
            command.append(str(self.top[0]))  # lower
            command.append(str(self.top[1]))  # upper
        if self.lcf:
            command.append('--threshold-low-count')
            command.append(str(self.lcf[0]))  # lower
            command.append(str(self.lcf[1]))  # upper
        if self.noise:
            command.append('--noise')
            command.append(str(self.noise[0]))  # stddev
            command.append(str(self.noise[1]))  # cutof
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
    dr = diffixRef()
    rtn = dr.query("select t1 from tab")
    if rtn['success']:
        pp.pprint(rtn['answer'])
    else:
        print(f"ERROR: {rtn['error']}")
    rtn = dr.query("select count(*) from tab")
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