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

def selectVictimBucket(bktCountsLeft,bktCountsRight):
    maxDiff = -1000
    maxIndex = -1
    for i in range(len(bktCountsLeft)):
        diff = bktCountsRight[i] - bktCountsLeft[i]
        if diff > maxDiff:
            maxDiff = diff
            maxIndex = i
    return maxIndex,maxDiff

def basicAttack(numValues,sd,outParams,alphbet,claimThresh,tries=1000,atLeast=10):
    bailOutReason = ''
    random.seed()
    alpha = alphbet[0]
    beta = alphbet[1]
    salt = random.randint(1000,100000000)
    score = tools.score.score(1/numValues)
    mcv = tools.stuff.makeColsVals()
    # Nominally we'll make `tries` attempts, but we need to have at
    # least `atLeast` claims that the victim has the attribute
    numTries = 0
    numClaimHas = 0
    numNoClaims = 0
    aidvPerBucket = round(1000/numValues)
    while True:
        numTries += 1
        # The specific column names and values don't matter, so long as they are consistent
        # within the set of buckets
        cols = mcv.getCols(3)
        vals = mcv.getVals(3)
        # for each outlier, select a bucket where the outlier will go
        buckets = []
        maxContribution = 0
        victimBucket = 0
        for bktIndex in range(numValues):
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
        for bktIndex in range(numValues):
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
        meanNoisyCount = statistics.mean(noisyCounts)
        excess = maxNoisyCount/meanNoisyCount
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
        if guessedBkt == victimBucket:
            claimCorrect = True
        else:
            claimCorrect = False
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
    return claimRate,confImprove,confidence,cr,ci,c,excess,numClaimHas

def dataInit():
    return {'Unknown Vals':[],'SD':[],'outParams':[],'alphbet':[],
            'thresh':[],'claims':[],'CR':[],'CI':[],'C':[]}

def dataUpdate(data,vals):
    data['Unknown Vals'].append(vals[0])
    data['SD'].append(vals[1])
    data['outParams'].append(vals[2])
    data['alphbet'].append(vals[3])
    data['thresh'].append(vals[4])
    data['claims'].append(vals[5])
    data['CR'].append(vals[6])
    data['CI'].append(vals[7])
    data['C'].append(vals[8])
        
def alreadyHaveData(data,vals,highCr):
    for i in range(len(data['SD'])):
        if ( data['Unknown Vals'][i] == vals[0] and
             data['SD'][i] == vals[1] and
             data['outParams'][i] == vals[2] and
             data['alphbet'][i] == vals[3]):
             if ((highCr is True and data['CR'][i] == '1.0') or
                 (highCr is False and data['CR'][i] != '1.0')):
                 return True
    return False
        
if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=4)
    tries=10000
    #tries=10000
    atLeast=100
    #atLeast=10
    claimThresh = None
    # Following are for tabulate
    results = []
    headers = ['vals','SD','outParams','alphbet','thresh','claims','CR','CI','C']
    # Following are for plotting
    if os.path.exists('betaData.json'):
        with open('betaData.json', 'r') as f:
            data = json.load(f)
    else:
        data = dataInit()
    sds = [1.5,2.25,3.0]
    sds = [2.25]
    outs = [[[1,2],[2,3]],
            [[2,3],[3,4]],
            [[3,4],[4,5]]
           ]
    abs = [[2,2],[2,4],[2,8]]
    numValues = [2,5,20]
    print("The following are for full claim rate (CR=1.0)",flush=True)
    for numVals,sd,outParams,alphbet in [(v,w,x,y) for v in numValues for w in sds for x in outs for y in abs]:
        if alreadyHaveData(data,[numVals,sd,outParams,alphbet],True):
            print(f"Already have {[numVals,sd,outParams,alphbet]}, highCr",flush=True)
            continue
        cr,ci,c,pcr,pci,pc,excess,claims = basicAttack(numVals,sd,outParams,alphbet,claimThresh,
                                                tries=tries,atLeast=atLeast)
        results.append([numVals,sd,outParams,alphbet,1,claims,pcr,pci,pc,])
        dataUpdate(data,[numVals,sd,outParams,alphbet,1,claims,pcr,pci,pc,])
        print(tabulate(results,headers,tablefmt='latex_booktabs'),flush=True)
        print(tabulate(results,headers,tablefmt='github'),flush=True)
        with open('betaData.json', 'w') as f:
            json.dump(data, f, indent=4, sort_keys=True)

    # Now we compute claim rate given goal of CI=0.95
    results = []
    print("\nThe following attempts to find the Claim Rate when CI is high (> 0.95)",flush=True)
    for numVals,sd,outParams,alphbet in [(v,w,x,y) for v in numValues for w in sds for x in outs for y in abs]:
        if alreadyHaveData(data,[numVals,sd,outParams,alphbet],False):
            print(f"Already have {[numVals,sd,outParams,alphbet]}, highCr",flush=True)
            continue
        claimThresh = 1
        while True:
            cr,ci,c,pcr,pci,pc,excess,claims = basicAttack(numVals,sd,outParams,alphbet,claimThresh,
                                                    tries=tries,atLeast=atLeast)
            print(f"claimThresh {claimThresh}, cr {pcr}, ci {pci}, c {pc}",flush=True)
            # We want to achieve a CI of at least 95%, but we won't go
            # beyond CR of 0.0001 to get it.
            if ci >= 0.95 or cr < 0.0001:
                results.append([numVals,sd,outParams,alphbet,claimThresh,claims,pcr,pci,pc,])
                dataUpdate(data,[numVals,sd,outParams,alphbet,claimThresh,claims,pcr,pci,pc,])
                break
            claimThresh = excess * 1.1
        print(tabulate(results,headers,tablefmt='latex_booktabs'),flush=True)
        print(tabulate(results,headers,tablefmt='github'),flush=True)
        with open('betaData.json', 'w') as f:
            json.dump(data, f, indent=4, sort_keys=True)
