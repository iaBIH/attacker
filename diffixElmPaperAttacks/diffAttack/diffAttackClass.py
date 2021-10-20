import random
import sys
import os
import statistics
filePath = __file__
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import anonymize.anonAlgs

class diffAttack():
    '''
    This code is for both the classic difference attack (positive AND), and
    before/after difference attacks that exploit changes in the table. Which
    attack is run is determined by configuring `attackType`
    '''

    def __init__(self,doLog=False):
        self.doLog = doLog
        if doLog:
            self.f = open('/root/paul/logs/out.txt','a')
            self.f.write("------------ Starting class diffAttack\n")
            self.f.flush()
        pass

    def makeAidvSet(self,base):
        init = base * 1000
        aidvSet = []
        for aidv in range(init,init+5):
            aidvSet.append(aidv)
        return(aidvSet)

    def selectVictimBucket(self,bktCountsLeft,bktCountsRight):
        maxDiff = -1000
        maxIndex = -1
        for i in range(len(bktCountsLeft)):
            diff = bktCountsRight[i] - bktCountsLeft[i]
            if diff > maxDiff:
                maxDiff = diff
                maxIndex = i
        return maxIndex,maxDiff
    
    def runOne(self,params,seedStuff):
        numUnknownVals = params['numUnknownVals']
        sd = params['SD']
        attackType = params['attackType']
        numSamples = params['numSamples']
        numIsolated = params['numIsolated']
        if numIsolated < 2 and attackType == 'diffAttackLed':
            print("Must set numIsolated if diffAttackLed")
            quit()
        N = 25          # arbitrary, big enough to avoid min reportable value lowThresh
        if attackType in ['diffAttack','diffAttackLed']:
            # left query always excludes victim by specifying gender='male'
            colsLeft = ['dept','gender','title']
        else:
            # Queries are the same for the change attack
            colsLeft = ['dept','title']
        # right query may include victim
        colsRight = ['dept','title']
        random.seed()
        addIndex,rmIndex = random.sample(range(numUnknownVals),k=2)
        if attackType == 'diffAttackLed':
            # These are the buckets the isolated individuals belong to
            isoBuckets = random.choices(range(numUnknownVals),k=numIsolated)
            addIndex = isoBuckets[0]
            #print('--------------------------------------------')
            #print(f"isoBuckets {isoBuckets}")
        bktCountsLeft = [0 for _ in range(numUnknownVals)]
        bktCountsRight = [0 for _ in range(numUnknownVals)]
        for sample in range(numSamples):
            saltLeft = (seedStuff+1) * (sample+1) * 123456967
            if attackType in ['diffAttack','diffAttackLed']:
                saltRight = saltLeft
            else:
                # Salt changes on change attack
                saltRight = saltLeft * 768595021
            for unknownVal in range(numUnknownVals):
                aidvSetLeft = self.makeAidvSet(seedStuff+(unknownVal*105389))
                aidvSetRight = self.makeAidvSet(seedStuff+(unknownVal*105389))
                trueCountLeft = N
                trueCountRight = N
                # These values for 'dept' and 'gender' columns are arbitrary
                if attackType in ['diffAttack','diffAttackLed']:
                    valsLeft = [50,51,unknownVal]
                    valsRight = [50,unknownVal]
                else:   # one of the change attack variants
                    valsLeft = [50,unknownVal]
                    valsRight = [50,unknownVal]
                if attackType != 'diffAttackLed':
                    if unknownVal == addIndex:
                        # We pick the victim as belonging to this bucket
                        trueCountRight += 1
                        aidvSetRight.append(1)
                    if unknownVal == rmIndex and attackType != 'diffAttack':
                        # We arbitrarily pick the victim as having been in this bucket
                        # (Note it doesn't matter that the AIDV we are removing doesn't match
                        # the one we add to the right, because hashing AIDV set)
                        trueCountLeft -= 1
                        aidvSetLeft.pop(0)
                elif len(set(isoBuckets)) != 1:
                    # not all isolated individuals are in the same bucket (if they are,
                    # we do nothing).
                    # So add them to the appropriate buckets
                    for bkt in isoBuckets:
                        if bkt == unknownVal:
                            #print(aidvSetRight)
                            aidvSetRight.append(random.randint(1000,100000000000))
                            #print(aidvSetRight)
                            trueCountRight += 1
                            #print(f"bkt {bkt} add 1 --> {trueCountRight}")
                else:
                    #print("   All isolated in same bucket!")
                    pass
                # We assume no suppression (so don't bother to specify the parameters)
                anon = anonymize.anonAlgs.anon(0,0,0,[sd],salt=saltLeft)
                noiseLeft,noisyCountLeft = anon.getNoise(trueCountLeft,aidvSet=aidvSetLeft,
                                                cols=colsLeft,vals=valsLeft)
                bktCountsLeft[unknownVal] += noisyCountLeft
                anon = anonymize.anonAlgs.anon(0,0,0,[sd],salt=saltRight)
                noiseRight,noisyCountRight = anon.getNoise(trueCountRight,aidvSet=aidvSetRight,
                                                cols=colsRight,vals=valsRight)
                bktCountsRight[unknownVal] += noisyCountRight
        # Divide the noisy counts by the number of samples
        bktCountsLeft = list(map(lambda x:x/numSamples,bktCountsLeft))
        bktCountsRight = list(map(lambda x:x/numSamples,bktCountsRight))
        guessedVal,difference = self.selectVictimBucket(bktCountsLeft,bktCountsRight)
        if guessedVal == addIndex:
            claimCorrect = True
            #print("-------------------- Correct!")
        else:
            claimCorrect = False
            #print("--------------- Wrong!")
        if self.doLog:
            self.f.write(f"Finished basicAttack:\n{params}\n{claimCorrect}\n{difference}\n")
            self.f.flush()
        return claimCorrect,difference

    def basicAttack(self,s,params,claimThresh,tries=10000,atLeast=100):
        # For the difference attack, the left bucket exludes the victim and the right
        # bucket conditionally includes the victim.
        # For the change attack, the left bucket is before the change, and the right
        # bucket is after the change.

        # Nominally we'll make `tries` attempts, but we need to have at
        # least `atLeast` claims that the victim has the attribute

        if self.doLog:
            self.f.write(f"Starting basicAttack:\n{params}\n")
            self.f.flush()
        numTries = 0
        numClaimHas = 0
        bailOutReason = ''
        while True:
            numTries += 1
            claimCorrect,difference = self.runOne(params,numTries)
            #---------------------------------------------------------------------------------
            # We need to decide if we want to make a claim at all.
            # We do so only if the difference exceeds the threshold
            if claimThresh and difference < claimThresh:
                # Don't make a claim
                makesClaim = False
                dontCare = True
                s.attempt(makesClaim,dontCare,dontCare)
                if numTries > tries * 100:
                    bailOutReason = f"Bail Out: too many tries (> {tries * 100})"
                    break
                continue
            makesClaim = True
            # We always believe that the victim has the attribute
            claimHas = True
            numClaimHas += 1
            s.attempt(makesClaim,claimHas,claimCorrect)
            if numTries > tries * 100:
                # If we can't get enough above threshold samples in this many tries,
                # then give up. This prevents us from never terminating because we
                # can't get `atLeast` above threshold samples
                bailOutReason = f"Bail Out: too many tries (> {tries * 100})"
                break
            if numTries >= tries and numClaimHas >= atLeast:
                break
            if claimThresh and numClaimHas > atLeast*2 and numClaimHas % atLeast*2 == 1:
                # We have some reasonable number of claims. If CI is not that high,
                # then we can quit early so the calling code can compute a larger threshold.
                claimRate,confImprove,confidence = s.computeScore()
                if confImprove < 0.9:
                    bailOutReason = f"Bail out: CI too low ({confImprove})"
                    break
        claimRate,confImprove,confidence = s.computeScore()
        cr,ci,c = s.prettyScore()
        if claimRate == 0:
            # We couldn't make even one claim, but don't want 0 rate because
            # that won't plot on a log scale!
            claimRate = 1/tries*100
            cr = str(claimRate)
        if numClaimHas < 10:
            # There just aren't enough samples to get a meaningful CI
            confImprove = 1.05
            confidence = 1.05
            ci = '1.05'
            c = '1.05'
        print(bailOutReason,flush=True)
        if claimThresh is None:
            claimThresh = 0
        return {'CR':claimRate,'CI':confImprove,'C':confidence,
                'PCR':cr,'PCI':ci,'PC':c,'claimThresh':claimThresh}