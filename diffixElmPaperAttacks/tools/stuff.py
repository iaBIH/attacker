import hashlib
import string
import statistics
import pprint
import random
pp = pprint.PrettyPrinter(indent=4)

class makeAidvSets():
    def __init__(self,baseIndividuals=20,seed=None):
        self.seed = seed
        self.baseIndividuals = baseIndividuals
        self.aidvLow = 1000
        self.aidvHigh = 100000000000

    def doSeed(self):
        if self.seed:
            random.seed(self.seed)
        else:
            random.seed()

    def makeBase(self):
        self.doSeed()
        self.aidvSet = []
        for _ in range(self.baseIndividuals):
            self.aidvSet.append(random.randint(self.aidvLow,self.aidvHigh))
        random.seed()

    def addAidv(self,numAidvs=1):
        self.doSeed()
        for _ in range(numAidvs):
            self.aidvSet.append(random.randint(self.aidvLow,self.aidvHigh))
        random.seed()

class makeOutlierContributions():
    def __init__(self,increaseFactor,baseIndividuals=20,
                 lowBase=1,highBase=10,seed=None):
        ''' We'll have a set of users that contribute a base amount on average,
            and then add numOutliers outliers whose values are increaseFactor times
            bigger than the average of the base users. The outliers contribute an
            amount within 10% of each other
        '''
        self.seed = seed
        self.baseIndividuals = baseIndividuals
        self.lowBase = lowBase
        self.highBase = highBase
        self.increaseFactor = increaseFactor
        self.mas = makeAidvSets(baseIndividuals=baseIndividuals)

    def doSeed(self):
        if self.seed:
            random.seed(self.seed)
        else:
            random.seed()

    def makeBase(self):
        self.mas.makeBase()
        self.doSeed()
        self.contributions = []
        for _ in range(self.baseIndividuals):
            self.contributions.append(random.randint(self.lowBase,self.highBase))
        random.seed()
        random.shuffle(self.contributions)

    def aidvSet(self):
        return(self.mas.aidvSet)

    def addOutliers(self,numOutliers=1):
        self.mas.addAidv(numAidvs=numOutliers)
        self.doSeed()
        meanBase = statistics.mean(self.contributions)
        maxBase = max(self.contributions)
        meanOutlier = round(maxBase + (meanBase * self.increaseFactor))
        minOutlier = round(meanOutlier - (meanOutlier*0.1))
        maxOutlier = round(meanOutlier + (meanOutlier*0.1))
        for _ in range(numOutliers):
            self.contributions.append(random.randint(minOutlier,maxOutlier))
        random.seed()
        random.shuffle(self.contributions)

class makeColsVals:
    '''
    '''
    def __init__(self):
        self.letters = list(string.ascii_lowercase)
        self.numbers = list(range(200))

    def getCols(self,numCols):
        return list(random.choices(self.letters,k=numCols))

    def getVals(self,numVals):
        return list(random.choices(self.numbers,k=numVals))

class myHash:
    ''' Used to avoid high cost of secure hashes
    '''
    def __init__(self,strength='weak'):
        self.strength = strength
        if strength != 'weak':
            self.m = hashlib.sha256()
        else:
            self.h = 0
        
    def update(self,s):
        if self.strength != 'weak':
            self.m.update(self.mb(s))
        else:
            self.h ^= hash(s)

    def digest(self):
        if self.strength != 'weak':
            return self.m.digest()
        else:
            return self.h
    
    def mb(self,thing):
        'make bytes from anything'
        thingStr = str(thing)
        return thingStr.encode('utf-8')
