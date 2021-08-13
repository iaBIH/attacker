import random

class anon:
    def __init__(self,lowThresh,gap,sdSupp,sd,locRandom=None):
        # locRandom is a local random number generator. Used to preserve
        # seeding in case of multi-thread
        self.lowThresh = lowThresh
        self.gap = gap
        self.sdSupp = sdSupp
        self.sd = sd
        self.locRandom = locRandom

    def getMean(self):
        mean = self.lowThresh + (self.gap * self.sdSupp)
        return mean

    def doSuppress(self,count):
        if count < self.lowThresh:
            return True
        mean = self.getMean()
        if self.locRandom:
            cutoff = self.locRandom.gauss(mean,self.sdSupp)
        else:
            cutoff = random.gauss(mean,self.sdSupp)
        #print(f"cutoff {cutoff}")
        if count < cutoff:
            return True
        return False

    def getNoise(self,trueCount):
        if self.locRandom:
            noise = self.locRandom.gauss(0,self.sd)
        else:
            noise = random.gauss(0,self.sd)
        noisyCount = round(trueCount + noise)
        noisyCount = max(noisyCount,0)
        return noise,noisyCount
