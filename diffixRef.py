import pprint
import subprocess
import csv

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
        self.outliers = outliers
        self.top = top
        self.lcf = lcf
        self.noise = noise

    def query(self,sql,seed=1,aids=[{'table':'tab','aid':'aid1'}]):
        pp = pprint.PrettyPrinter(indent=4)
        command = []
        command.append(self.cmd)
        # database
        command.append('-d')
        command.append(self.db)
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
        if result.returncode != 0:
            return None
        # Turn result bytes into a string
        out = result.stdout.decode("utf-8")
        outList = str.splitlines(out)
        reader = csv.reader(iter(outList),delimiter=';')
        data = list(reader)
        return data
        

if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=4)
    dr = diffixRef()
    data = dr.query("select t1 from tab")
    if data:
        pp.pprint(data)
    else:
        print("Query in error")
    data = dr.query("select count(*) from tab")
    if data:
        pp.pprint(data)
    else:
        print("Query in error")