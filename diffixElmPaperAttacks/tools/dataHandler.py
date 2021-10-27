import pprint
import json
import os
import sys

class dataHandler():
    def __init__(self,params,results,dataDir,dataFile,printToFile=True):
        ''' `params` is a list of parameter names
            `results` is a list of result names
            `dataDir` is the directory under ATTACK_RESULTS_DIR where results go
            `dataFile` is the name of the file where results go
        '''
        rootDir = os.environ['ATTACK_RESULTS_DIR']
        homePath = os.path.join(rootDir,dataDir)
        if not os.path.exists(homePath):
            os.mkdir(homePath)
        self.dataFile = os.path.join(homePath,dataFile+'.json')
        self.printFile = None
        if printToFile:
            self.printFile = os.path.join(homePath,dataFile+'.txt')
            sys.stdout = open(self.printFile, 'a')
        self.params = {}
        self.results = {}
        if self.dataFile and os.path.exists(self.dataFile):
            with open(self.dataFile, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = {}
            for param in params:
                self.data[param] = []
                self.params[param] = None
            for result in results:
                self.data[result] = []
                self.results[result] = None
        self.aParam = params[0]
        self.criteria = []
        # Caller can ignore the returned data if already has some

    def saveData(self):
        with open(self.dataFile, 'w') as f:
            json.dump(self.data, f, indent=4, sort_keys=True)

    def dataUpdate(self,params,results):
        for param,val in params.items():
            self.data[param].append(val)
        for result,val in results.items():
            self.data[result].append(val)

    def getLastRound(self,params):
        maxRound = -1
        for i in range(len(self.data[self.aParam])):
            match = True
            round = self.data['round'][i]
            for param in params.keys():
                if param == 'round':
                    continue
                if self.data[param][i] != params[param]:
                    match = False
                    break
            if match == True:
                # We found the completed round, so go to the next one
                maxRound = max(round,maxRound)
        return maxRound

    def getResultsVal(self,resType,params,round):
        paramsCopy = params.copy()
        paramsCopy['round'] = round
        for i in range(len(self.data[self.aParam])):
            match = True
            for param in paramsCopy.keys():
                if self.data[param][i] != params[param]:
                    match = False
                    break
            if match == True:
                return self.data[resType][i]
        return None

    def alreadyHaveData(self,params):
        for i in range(len(self.data[self.aParam])):
            match = True
            for param in params.keys():
                if self.data[param][i] != params[param]:
                    match = False
                    break
            if match == True:
                return True
        return False

    def addSatisfyCriteria(self,name,value,action):
        ''' action can be 'gt' or 'lt'
        '''
        self.criteria.append({'name':name,'value':value,'action':action})

    def paramsAlreadySatisfied(self,round,params):
        paramsCopy = params.copy()
        for r in range(round):
            paramsCopy['round'] = r
            for i in range(len(self.data[self.aParam])):
                match = True
                for param,val in paramsCopy.items():
                    if self.data[param][i] != val:
                        match = False
                        break
                if match == True:
                    for cri in self.criteria:
                        val = self.data[cri['name']][i]
                        if ((cri['action'] == 'gt' and val > cri['value']) or
                            (cri['action'] == 'lt' and val < cri['value'])):
                            return True
        return False

if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=4)
    params = ['p1','p2','round']
    results = ['r1','r2']
    dh = dataHandler(params,results)
    # Use a copy of the data if we want to initialize the data:
    pp.pprint(dh.data)
    param = dh.params.copy()
    result = dh.results.copy()
    for i in range(5):
        param['round'] = i
        param['p1'] = i+3
        param['p2'] = i+1
        result['r1'] = 10*i
        result['r2'] = 1/(i+5)
        dh.dataUpdate(param,result)
    pp.pprint(dh.data)
    print(f"Should be True: {dh.alreadyHaveData(param)}")
    param['p1'] = 20
    print(f"Should be False: {dh.alreadyHaveData(param)}")
    for i in range(5):
        param['round'] = i
        param['p1'] = 10
        param['p2'] = 20
        result['r1'] = 10*i
        result['r2'] = 1/(i+5)
        dh.dataUpdate(param,result)
    pp.pprint(dh.data)
    # With these two criteria, the last two rounds should be satisfied
    dh.addSatisfyCriteria('r1',20,'gt')
    dh.addSatisfyCriteria('r2',0.13,'lt')
    print(f"Should be False: {dh.paramsAlreadySatisfied(1,param)}")
    print(f"Should be False: {dh.paramsAlreadySatisfied(2,param)}")
    print(f"Should be False: {dh.paramsAlreadySatisfied(3,param)}")
    print(f"Should be True: {dh.paramsAlreadySatisfied(4,param)}")
    print(f"Should be True: {dh.paramsAlreadySatisfied(5,param)}")