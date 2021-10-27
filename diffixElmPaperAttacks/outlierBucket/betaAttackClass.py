import sys
import os
import json
import statistics
import random
import pprint
from tabulate import tabulate
filePath = __file__
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import tools.score
import tools.stuff
import anonymize.anonAlgs

'''
This code is for the somewhat more realistic version of the outlier attack.
Here, we have a beta distribution with more or less skew at the top. The
attacker knows the highest contributor.
The attacker simply requests a histogram, and
then determines that the outliers are in buckets that have high counts.
For this to work, there needs to be more outliers than the minimum
out_range. Otherwise, the outliers will all be flattened.
'''

class betaAttack():
    def __init__(self):
        pass

    def selectVictimBucket(self,bktCountsLeft,bktCountsRight):
        maxDiff = -1000
        maxIndex = -1
        for i in range(len(bktCountsLeft)):
            diff = bktCountsRight[i] - bktCountsLeft[i]
            if diff > maxDiff:
                maxDiff = diff
                maxIndex = i
        return maxIndex,maxDiff
    
    def runOne(self,params,mcv,salt):
        numUnknownVals = params['numUnknownVals']
        sd = params['SD']
        alphbet = params['alphbet']
        outParams = params['outParams']
        aidvPerBucket = round(1000/numUnknownVals)
        alpha = alphbet[0]
        beta = alphbet[1]
        # The specific column names and values don't matter, so long as they are consistent
        # within the set of buckets
        cols = mcv.getCols(3)
        vals = mcv.getVals(3)
        # for each outlier, select a bucket where the outlier will go
        buckets = []
        maxContribution = 0
        victimBucket = 0
        for bktIndex in range(numUnknownVals):
            mas = tools.stuff.makeAidvSets(baseIndividuals=aidvPerBucket)
            mas.makeBase()
            contributions = []
            for _ in range(aidvPerBucket):
                cont = round(random.betavariate(alpha,beta) * 1000) + 1
                if cont > maxContribution:
                    maxContribution = cont
                    victimBucket = bktIndex
                contributions.append(cont)
            bkt = {
                'aidvSet': mas.aidvSet,
                'contributions': contributions,
            }
            buckets.append(bkt)
        # Compute the noisy count for each bucket
        noisyCounts = []
        noises = []
        anon = anonymize.anonAlgs.anon(0,0,0,[sd],salt=salt,
                                    outRange=outParams[0],topRange=outParams[1])
        for bktIndex in range(numUnknownVals):
            bkt = buckets[bktIndex]
            # By convention, assume that last column contains the unknown value
            vals[-1] = bktIndex
            trueCount = sum(bkt['contributions'])
            #print(f'{numTries} {numClaimHas}',flush=True)
            noise,noisyCount = anon.getNoise(trueCount,aidvSet=bkt['aidvSet'],cols=cols,vals=vals,
                                            contributions=bkt['contributions'])
            noisyCounts.append(noisyCount)
            noises.append(noise)
        # The attack is to select the bucket with the highest count as the victim bucket
        maxNoisyCount = max(noisyCounts)
        guessedBkt = noisyCounts.index(maxNoisyCount)
        if guessedBkt == victimBucket:
            claimCorrect = True
        else:
            claimCorrect = False
        meanNoisyCount = statistics.mean(noisyCounts)
        excess = maxNoisyCount/meanNoisyCount
        return claimCorrect,excess

    def basicAttack(self,scoreProb,jparams,claimThresh,tries=10000,atLeast=100):
        params = json.loads(jparams)
        bailOutReason = ''
        random.seed()
        salt = random.randint(1000,100000000)
        score = tools.score.score(scoreProb)
        mcv = tools.stuff.makeColsVals()
        # Nominally we'll make `tries` attempts, but we need to have at
        # least `atLeast` claims that the victim has the attribute
        numTries = 0
        numClaimHas = 0
        numNoClaims = 0
        while True:
            numTries += 1
            claimCorrect,excess = self.runOne(params,mcv,salt)
            # We need to decide if we want to make a claim at all.
            # We define a threshold as how much the max exceeds the average
            if claimThresh and excess < claimThresh:
                #print(f"claimThresh {claimThresh}, excess {excess}, max {maxNoisyCount}, mean {meanNoisyCount}",flush=True)
                # Don't make a claim
                numNoClaims += 1
                makesClaim = False
                dontCare = True
                score.attempt(makesClaim,dontCare,dontCare)
                if numTries > tries * 100:
                    bailOutReason = f"Bail Out: too many tries (> {tries * 100})"
                    break
                continue
            makesClaim = True
            claimHas = True
            numClaimHas += 1
            score.attempt(makesClaim,claimHas,claimCorrect)
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
                claimRate,confImprove,confidence = score.computeScore()
                if confImprove < 0.9:
                    bailOutReason = f"Bail out: CI too low ({confImprove})"
                    break
        claimRate,confImprove,confidence = score.computeScore()
        cr,ci,c = score.prettyScore()
        if claimRate == 0:
            # We couldn't make even one claim, but don't want 0 rate because
            # that won't plot on a log scale!
            claimRate = 1/(tries*100*10)
            cr = str(claimRate)
        if numClaimHas < 10:
            # There just aren't enough samples to get a meaningful CI
            confImprove = 1.05
            confidence = 1.05
            ci = '1.05'
            c = '1.05'
        print(bailOutReason,flush=True)
        print(f"numNoClaim {numNoClaims}, numClaimHas {numClaimHas}",flush=True)
        result = {'CR':claimRate,'CI':confImprove,'C':confidence,
                   'PCR':cr,'PCI':ci,'PC':c,'claimThresh':claimThresh,'excess':excess,
                   'numClaimHas':numClaimHas}
        return result