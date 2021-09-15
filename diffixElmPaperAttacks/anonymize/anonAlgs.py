import random
import hashlib

class anon:
    def __init__(self,lowThresh,gap,sdSupp,sd,mode='ta',version='elm',salt=None):
        self.lowThresh = lowThresh
        self.gap = gap
        self.sdSupp = sdSupp
        self.sd = sd
        self.mode = mode
        self.version = version
        if not salt:
            self.salt = random.randint(1,100000000)
        else:
            self.salt = salt

    def getMean(self):
        mean = self.lowThresh + (self.gap * self.sdSupp)
        return mean

    def doSuppress(self,count):
        if count < self.lowThresh:
            return True
        mean = self.getMean()
        cutoff = random.gauss(mean,self.sdSupp)
        #print(f"cutoff {cutoff}")
        if count < cutoff:
            return True
        return False

    def mb(self,thing):
        'make bytes from anything'
        thingStr = str(thing)
        return thingStr.encode('utf-8')

    def getNoise(self,trueCount,aidvSet=None,cols=[],vals=[]):
        ''' Note that trueCount might be count of rows, not distinct AIDVs'''
        if aidvSet is None:
            noise = random.gauss(0,self.sd)
            noisyCount = round(trueCount + noise)
            noisyCount = max(noisyCount,0)
            return noise,noisyCount
        if self.mode == 'ta':
            m = hashlib.sha256()
            m.update(self.mb(self.salt))
            for aidv in aidvSet:
                m.update(self.mb(aidv))
            bkt_aid_seed = m.digest()
            for col in cols:
                m.update(self.mb(col))
            for val in vals:
                m.update(self.mb(val))
            bkt_sql_aid_seed = m.digest()
            random.seed(bkt_aid_seed)
            bkt_aid_noise,_ = self.getNoise(trueCount)
            random.seed(bkt_sql_aid_seed)
            bkt_sql_aid_noise,_ = self.getNoise(trueCount)
            noise = bkt_aid_noise + bkt_sql_aid_noise
            noisyCount = round(trueCount + noise)
            noisyCount = max(noisyCount,0)
            return noise,noisyCount

if __name__ == "__main__":
    lowThresh = 2
    gap = 3
    sdSupp = 1.0
    sd = 1.0
    # first with simple random
    an = anon(lowThresh,gap,sdSupp,sd)
    n1,_ = an.getNoise(10)
    n2,_ = an.getNoise(10)
    if n1 == n2:
        print(f"Bad simple random {n1},{n2}")
    else:
        print("Simple random good")
    aidvSet = [1,2,3,4,5]
    cols = [1,2,3]
    vals = [4,5,6]
    an = anon(lowThresh,gap,sdSupp,sd,mode='ta',version='elm',salt=1)
    n1,_ = an.getNoise(10,aidvSet=aidvSet,cols=cols,vals=vals)
    n2,_ = an.getNoise(10,aidvSet=aidvSet,cols=cols,vals=vals)
    if n1 != n2:
        print(f"Bad seeded 1 {n1},{n2}")
    else:
        print("Seeded 1 good")
    an = anon(lowThresh,gap,sdSupp,sd,mode='ta',version='elm',salt=1)
    n1,_ = an.getNoise(10,aidvSet=aidvSet,cols=cols,vals=vals)
    vals = [7,8,9]
    n2,_ = an.getNoise(10,aidvSet=aidvSet,cols=cols,vals=vals)
    if n1 == n2:
        print(f"Bad seeded 2 {n1},{n2}")
    else:
        print("Seeded 2 good")