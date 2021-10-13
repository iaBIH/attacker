import random
import math
import statistics
import os.path
import sys
filePath = __file__
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import tools.stuff

class anon:
    def __init__(self,lowThresh,gap,sdSupp,sd,mode='ta',version='elm',salt=None,
                  outRange=[],topRange=[]):
        self.lowThresh = lowThresh
        self.gap = gap
        self.sdSupp = sdSupp
        # This sd is a list, and its meaning depends on the version
        self.sd = sd
        self.mode = mode
        self.version = version
        self.outRange = outRange
        self.topRange = topRange
        if not salt:
            self.salt = random.randint(1,100000000)
        else:
            self.salt = salt

    def getMean(self):
        mean = self.lowThresh + (self.gap * self.sdSupp)
        return mean

    def doSuppress(self,count,aidvSet=None):
        if count < self.lowThresh:
            return True
        if aidvSet:
            aidSeed = self.getBktAidSeedElm(aidvSet)
            random.seed(aidSeed)
        mean = self.getMean()
        cutoff = random.gauss(mean,self.sdSupp)
        random.seed()
        if count < cutoff:
            return True
        return False

    def getBktAidSeedElm(self,aidvSet):
        m = tools.stuff.myHash()
        m.update(self.salt)
        for aidv in aidvSet:
            m.update(aidv)
        return m.digest()

    def getBktSqlSeedElm(self,cols,vals):
        m = tools.stuff.myHash()
        for col in cols:
            m.update(col)
        for val in vals:
            m.update(val)
        return m.digest()

    def getFlattenSeeds(self,aidvs,topRange,outRange):
        '''
        This isn't exactly as specified in the Elm doc, but does the right thing
        '''
        numAidvs = topRange[1] + outRange[1]
        m = tools.stuff.myHash()
        m.update(self.salt)
        for index in range(numAidvs):
            m.update(aidvs[index])
        topSeed = m.digest()
        m.update('outlier')
        outSeed = m.digest()
        return topSeed,outSeed

    def adjustTopOut(self,aidvs):
        topRange = self.topRange.copy()
        outRange = self.outRange.copy()
        return self.adjustTopOutWork(aidvs,topRange,outRange,'top')

    def adjustTopOutWork(self,aidvs,topRange,outRange,next):
        neededAidvs = topRange[1] + outRange[1]
        if neededAidvs <= len(aidvs):
            # no adjust needed
            return topRange,outRange
        if topRange[0] == topRange[1] and outRange[0] == outRange[1]:
            # We have too few AIDVs, so give up
            return None,None
        if outRange[0] == outRange[1]:
            # can't lower outRange max anyway, so just work on top
            topRange[1] -= 1
            return self.adjustTopOutWork(aidvs,topRange,outRange,'top')
        elif next == 'out':
            outRange[1] -= 1
            return self.adjustTopOutWork(aidvs,topRange,outRange,'top')
        else:
            topRange[1] -= 1
            return self.adjustTopOutWork(aidvs,topRange,outRange,'out')

    def sortAidCon(self,aidvSet,contributions):
        cons = {}
        for i in range(len(aidvSet)):
            con = contributions[i]
            aidv = aidvSet[i]
            if con in cons:
                cons[con].append(aidv)
            else:
                cons[con] = [aidv]
        # sort by AIDV within each contribution amount
        for con in cons.keys():
            cons[con].sort()
        newAidvs = []
        newCon = []
        sortedKeys = sorted(cons.keys(),reverse=True)
        for con in sortedKeys:
            for aidv in cons[con]:
                newAidvs.append(aidv)
                newCon.append(con)
        return newAidvs,newCon

    def flattenElm(self,aidvSet,contributions):
        flatten = 0
        sdFactor = 1
        if len(contributions) == 0:
            return flatten,sdFactor
        if len(contributions) != len(aidvSet):
            print(f"flattenElm bad input")
            quit()
        if len(self.topRange) == 0:
            print("flattenElm, no topRange")
            quit()
        aidvs,cons = self.sortAidCon(aidvSet,contributions)
        topRange,outRange = self.adjustTopOut(aidvs)
        topSeed,outSeed = self.getFlattenSeeds(aidvs,topRange,outRange)
        random.seed(topSeed)
        topCount = random.randint(topRange[0],topRange[1])
        random.seed(outSeed)
        outCount = random.randint(outRange[0],outRange[1])
        random.seed()
        outGroup = cons[:outCount]
        topGroup = cons[outCount:outCount+topCount]
        avgTop = statistics.mean(topGroup)
        flatten = 0
        for con in outGroup:
            flatten += con - avgTop
        totalCon = sum(cons)
        flattenedCon = totalCon - flatten
        avgAll = flattenedCon / len(cons)
        sdFactor = max(avgAll,avgTop*0.5)
        return flatten,sdFactor

    def getNoiseBase(self,trueCount,sd):
            noise = random.gauss(0,sd)
            noisyCount = round(trueCount + noise)
            noisyCount = max(noisyCount,0)
            return noise,noisyCount

    def getNoise(self,trueCount,aidvSet=None,contributions=[],cols=[],vals=[]):
        ''' Note that trueCount might be count of rows, not distinct AIDVs'''
        if self.version == 'elm' and aidvSet is None:
            # This is for attacks where seeding doesn't matter so we just want
            # the right amount of total noise. For Elm, self.sd contains one value,
            # which is the total SD
            sdTotal = self.sd[0]
            return self.getNoiseBase(trueCount,sdTotal)
        if self.version == 'elm' or self.version == 'elm1':
            # Since for Elm, self.sd[0] is the total noise, here we need to extract
            # the per layer noise
            sdLayer = math.sqrt((self.sd[0]**2)/2)
            bkt_aid_seed = self.getBktAidSeedElm(aidvSet)
            bkt_sql_seed = self.getBktSqlSeedElm(cols,vals)
            flatten,sdFactor = self.flattenElm(aidvSet,contributions)
            random.seed(bkt_aid_seed)
            bkt_aid_noise,_ = self.getNoiseBase(trueCount,sdLayer)
            random.seed(bkt_sql_seed)
            bkt_sql_noise,_ = self.getNoiseBase(trueCount,sdLayer)
            random.seed()
            noise = bkt_aid_noise + bkt_sql_noise
            if self.version == 'elm1':
                # for now, just throw in an extra, non-sticky layer
                random.seed()
                elm1_noise,_ = self.getNoiseBase(trueCount,sdLayer)
                noise += elm1_noise
            noise *= sdFactor
            flattenedCount = trueCount - flatten
            #print(f"true {trueCount}, flatten {flatten}, flatCount {flattenedCount}, noise {noise}")
            #print(f"sdFactor {sdFactor}, sdLayer {sdLayer}, sd {self.sd[0]}")
            noisyCount = round(flattenedCount + noise)
            noisyCount = max(noisyCount,self.lowThresh)
            return noise,noisyCount

if __name__ == "__main__":
    import string
    letters = list(string.ascii_lowercase)
    numbers = list(range(200))
    lowThresh = 2
    gap = 3
    sdSupp = 1.0
    sd = 2.0
    # first with simple random
    an = anon(lowThresh,gap,sdSupp,[sd])
    n1,_ = an.getNoise(10)
    n2,_ = an.getNoise(10)
    if n1 == n2:
        print(f"Bad simple random {n1},{n2}")
    else:
        print("Simple random good")
    aidvSet = [1,2,3,4,5]
    cols = [1,2,3]
    vals = [4,5,6]
    an = anon(lowThresh,gap,sdSupp,[sd],mode='ta',version='elm',salt=1)
    n1,_ = an.getNoise(10,aidvSet=aidvSet,cols=cols,vals=vals)
    n2,_ = an.getNoise(10,aidvSet=aidvSet,cols=cols,vals=vals)
    if n1 != n2:
        print(f"Bad seeded 1 {n1},{n2}")
    else:
        print("Seeded 1 good")
    an = anon(lowThresh,gap,sdSupp,[sd],mode='ta',version='elm',salt=1)
    n1,_ = an.getNoise(10,aidvSet=aidvSet,cols=cols,vals=vals)
    vals = [7,8,9]
    n2,_ = an.getNoise(10,aidvSet=aidvSet,cols=cols,vals=vals)
    if n1 == n2:
        print(f"Bad seeded 2 {n1},{n2}")
    else:
        print("Seeded 2 good")
    # Test suppression
    lowThresh = 2
    gap = 3
    sdSupp = 1.0
    sd = 2.0
    an = anon(lowThresh,gap,sdSupp,[sd])
    meanCutoff = round(an.getMean())
    # We expect different AIDVs to have different suppression thresholds
    suppressCount = 0
    reportCount = 0
    print(f"With AIDV sets of size {meanCutoff}, we expect about half of queries to suppress")
    for i in range(100):
        aidvSet = list(random.choices(numbers,k=meanCutoff))
        if an.doSuppress(len(aidvSet),aidvSet=aidvSet):
            suppressCount += 1
        else:
            reportCount += 1
    if suppressCount == 0 or reportCount == 0:
        print(f"Bad suppress: {suppressCount}, {reportCount}")
    else:
        print(f"    Good suppress: {suppressCount}, {reportCount}")

    aidvSetSize = 20
    an = anon(lowThresh,gap,sdSupp,[sd])
    print(f"- With AIDV sets of size {aidvSetSize}, and noise {sd}, we expect average")
    print(f"  answer to be around {aidvSetSize}, and stddev to be around {sd}")
    counts = []
    aidvs = []
    cols = []
    vals = []
    random.seed()
    for i in range(1000):
        aidvs.append(list(random.choices(numbers,k=aidvSetSize)))
        cols.append(list(random.choices(letters,k=4)))
        vals.append(list(random.choices(numbers,k=4)))
    for i in range(len(aidvs)):
        noise,noisyCount = an.getNoise(aidvSetSize,aidvSet=aidvs[i],cols=cols[i],vals=vals[i])
        counts.append(noisyCount)
    print(f"    Got mean {statistics.mean(counts)}, stddev {statistics.stdev(counts)}")

    aidvSetSize = 20
    an = anon(lowThresh,gap,sdSupp,[sd])
    print(f"- With AIDV sets of size {aidvSetSize}, and noise 2.0, but")
    print(f"  with the sql seed always the same, we expect")
    print(f"  answer to be off by 1 or 2, and stddev to be around 1.41")
    counts = []
    aidvs = []
    cols = list(random.choices(letters,k=4))
    vals = list(random.choices(numbers,k=4))
    random.seed()
    for i in range(1000):
        aidvs.append(list(random.choices(numbers,k=aidvSetSize)))
    for i in range(len(aidvs)):
        noise,noisyCount = an.getNoise(aidvSetSize,aidvSet=aidvs[i],cols=cols,vals=vals)
        counts.append(noisyCount)
    print(f"    Got mean {statistics.mean(counts)}, stddev {statistics.stdev(counts)}")

    aidvSetSize = 20
    outRange = [1,2]
    topRange = [2,3]
    an = anon(lowThresh,gap,sdSupp,[sd],outRange=outRange,topRange=topRange)
    print(f"- With AIDV sets of size {aidvSetSize}, and noise {sd}, but contributions")
    print(f"  all 2, we expect")
    print(f"  answer to be around {aidvSetSize*2}, and stddev to be around {2*sd}")
    counts = []
    aidvs = []
    cols = []
    vals = []
    contributions = [2 for i in range(aidvSetSize)]
    trueNoise = sum(contributions)
    random.seed()
    for i in range(1000):
        aidvs.append(list(random.choices(numbers,k=aidvSetSize)))
        cols.append(list(random.choices(letters,k=4)))
        vals.append(list(random.choices(numbers,k=4)))
    for i in range(len(aidvs)):
        noise,noisyCount = an.getNoise(trueNoise,aidvSet=aidvs[i],cols=cols[i],vals=vals[i],contributions=contributions)
        counts.append(noisyCount)
    print(f"    Got mean {statistics.mean(counts)}, stddev {statistics.stdev(counts)}")

    an = anon(lowThresh,gap,sdSupp,[sd],outRange=outRange,topRange=topRange)
    counts = []
    aidvs = []
    cols = []
    vals = []
    contributions = [2 for i in range(aidvSetSize)]
    contributions[-1] = 100
    trueNoise = sum(contributions)
    print(f'''
    - AIDV sets of size {aidvSetSize}, noise {sd}, contributions all 2
      except one outlier contribution 100. We expect the outlier to be flattened,
      so answer to be around {2*aidvSetSize}, and stddev to be around {2*sd}
    ''')
    random.seed()
    for i in range(1000):
        aidvs.append(list(random.choices(numbers,k=aidvSetSize)))
        cols.append(list(random.choices(letters,k=4)))
        vals.append(list(random.choices(numbers,k=4)))
    for i in range(len(aidvs)):
        noise,noisyCount = an.getNoise(trueNoise,aidvSet=aidvs[i],cols=cols[i],vals=vals[i],contributions=contributions)
        counts.append(noisyCount)
    print(f"      ---- Got mean {statistics.mean(counts)}, stddev {statistics.stdev(counts)}")

    an = anon(lowThresh,gap,sdSupp,[sd],outRange=outRange,topRange=topRange)
    counts = []
    aidvs = []
    cols = []
    vals = []
    contributions = [2 for i in range(aidvSetSize)]
    contributions[-1] = 100
    contributions[-2] = 100
    trueNoise = sum(contributions)
    print(f'''
    - AIDV sets of size {aidvSetSize}, noise {sd}, contributions all 2
      except two outlier contributions of 100. Sometimes both outliers will
      be flattened, sometimes only one of them. In latter case, we'll have a lot
      of noise.
    ''')
    random.seed()
    for i in range(1000):
        aidvs.append(list(random.choices(numbers,k=aidvSetSize)))
        cols.append(list(random.choices(letters,k=4)))
        vals.append(list(random.choices(numbers,k=4)))
    for i in range(len(aidvs)):
        noise,noisyCount = an.getNoise(trueNoise,aidvSet=aidvs[i],cols=cols[i],vals=vals[i],contributions=contributions)
        counts.append(noisyCount)
    print(f"      ---- Got mean {statistics.mean(counts)}, stddev {statistics.stdev(counts)}")

    an = anon(lowThresh,gap,sdSupp,[sd],outRange=outRange,topRange=topRange)
    counts = []
    aidvs = []
    cols = []
    vals = []
    contributions = [2 for i in range(aidvSetSize)]
    contributions[-1] = 100
    contributions[-2] = 100
    contributions[-3] = 100
    trueNoise = sum(contributions)
    print(f'''
    - AIDV sets of size {aidvSetSize}, noise {sd}, contributions all 2
      except three outlier contributions of 100. Always one outlier will be in
      top group, so flattening always at least 30 or so.
    ''')
    random.seed()
    for i in range(1000):
        aidvs.append(list(random.choices(numbers,k=aidvSetSize)))
        cols.append(list(random.choices(letters,k=4)))
        vals.append(list(random.choices(numbers,k=4)))
    for i in range(len(aidvs)):
        noise,noisyCount = an.getNoise(trueNoise,aidvSet=aidvs[i],cols=cols[i],vals=vals[i],contributions=contributions)
        counts.append(noisyCount)
    print(f"      ---- Got mean {statistics.mean(counts)}, stddev {statistics.stdev(counts)}")

    an = anon(lowThresh,gap,sdSupp,[sd],outRange=outRange,topRange=topRange)
    counts = []
    aidvs = []
    cols = []
    vals = []
    contributions = [5,6,7]
    trueNoise = sum(contributions)
    print(f'''
    - AIDV sets of size {len(contributions)}, noise {sd}, contibutions {contributions}.
      With this number of AIDVs,
      we expect the flatten parameters always to be out=1 and top=2. So topAvg
      of 5.5, and flatten of 1.5. So count should be around 16.5, and noise
      around 5.5x2=11, except that sometimes we'll report default count of 2, which
      will push up the average and reduce the noise.
    ''')
    random.seed()
    for i in range(1000):
        aidvs.append(list(random.choices(numbers,k=len(contributions))))
        cols.append(list(random.choices(letters,k=4)))
        vals.append(list(random.choices(numbers,k=4)))
    for i in range(len(aidvs)):
        noise,noisyCount = an.getNoise(trueNoise,aidvSet=aidvs[i],cols=cols[i],vals=vals[i],contributions=contributions)
        counts.append(noisyCount)
    print(f"      ---- Got mean {statistics.mean(counts)}, stddev {statistics.stdev(counts)}")

    an = anon(lowThresh,gap,sdSupp,[sd],outRange=outRange,topRange=topRange)
    counts = []
    aidvs = []
    cols = []
    vals = []
    contributions = [5,6,7,8]
    trueNoise = sum(contributions)
    print(f'''
    - AIDV sets of size {len(contributions)}, noise {sd}, contibutions {contributions}.
      With this number of AIDVs, we expect the flatten parameters always to be
      either out=2,1 and top=2,2. When out=1, we have flattening of 2, and flattened count of
      24. When out=2, we have flattening of 1.5+2.5=4 and flattened count of 22. So average
      count should be 23. Noise should be either 6*2=12 or 5.5*2=11, so average 11.5, except
      that lowThresh may push former up and latter down.
    ''')
    random.seed()
    for i in range(1000):
        aidvs.append(list(random.choices(numbers,k=len(contributions))))
        cols.append(list(random.choices(letters,k=4)))
        vals.append(list(random.choices(numbers,k=4)))
    for i in range(len(aidvs)):
        noise,noisyCount = an.getNoise(trueNoise,aidvSet=aidvs[i],cols=cols[i],vals=vals[i],contributions=contributions)
        counts.append(noisyCount)
    print(f"      ---- Got mean {statistics.mean(counts)}, stddev {statistics.stdev(counts)}")
