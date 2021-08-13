import random

class anon:
    def __init__(self,locRandom=None):
        self.locRandom = locRandom

    def getMean(self,lowThresh, lowsds, sd):
        mean = lowThresh + (lowsds * sd)
        return mean

    def doSuppress(self,count,lowThresh,lowsds,sd):
        if count < lowThresh:
            return True
        mean = self.getMean(lowThresh, lowsds, sd)
        if self.locRandom:
            cutoff = self.locRandom.gauss(mean,sd)
        else:
            cutoff = random.gauss(mean,sd)
        #print(f"cutoff {cutoff}")
        if count < cutoff:
            return True
        return False

    def getNoise(self,trueCount,mean,sd):
        if self.locRandom:
            noise = self.locRandom.gauss(mean,sd)
        else:
            noise = random.gauss(mean,sd)
        noisyCount = round(trueCount + noise)
        return noise,noisyCount
