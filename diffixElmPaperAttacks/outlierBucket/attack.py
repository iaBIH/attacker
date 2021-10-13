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
This code is for the pessimistic version of the outlier bucket attack.
There is a pessimal number of outliers, such that often outliers are in
the out group and one or two in the top group. This causes some flattening,
but not necessarily enough to really hide the victim when all of the outliers
are in the same bucket.
The attacker knows of one or
more outlier contributors. The attacker simply requests a histogram, and
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

def basicAttack(numValues,sd,outParams,factor,numOutliers,claimThresh,tries=1000,atLeast=10):
    bailOutReason = ''
    random.seed()
    salt = random.randint(1000,100000000)
    score = tools.score.score(1/numValues)
    mcv = tools.stuff.makeColsVals()
    # Nominally we'll make `tries` attempts, but we need to have at
    # least `atLeast` claims that the victim has the attribute
    numTries = 0
    numClaimHas = 0
    numNoClaims = 0
    while True:
        numTries += 1
        # The specific column names and values don't matter, so long as they are consistent
        # within the set of buckets
        cols = mcv.getCols(3)
        vals = mcv.getVals(3)
        # for each outlier, select a bucket where the outlier will go
        outlierBuckets = random.choices(range(numValues),k=numOutliers)
        # For each attribute value, we make a bucket
        buckets = []
        for bktIndex in range(numValues):
            moc = tools.stuff.makeOutlierContributions(factor)
            moc.makeBase()
            for outBkt in outlierBuckets:
                if outBkt == bktIndex:
                    moc.addOutliers()
            bkt = {
                'aidvSet': moc.aidvSet(),
                'contributions': moc.contributions,
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
        # Select one of the outliers as the victim
        victimBkt = random.choice(outlierBuckets)
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
        if guessedBkt == victimBkt:
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
    return {'Unknown Vals':[],'SD':[],'Out Factor':[],'Num Outliers':[],
            'setting':[],'thresh':[],'claims':[],'CR':[],'CI':[],'C':[]}

def dataUpdate(data,vals):
    data['Unknown Vals'].append(vals[0])
    data['SD'].append(vals[1])
    data['Out Factor'].append(vals[2])
    data['Num Outliers'].append(vals[3])
    data['setting'].append(vals[4])
    data['thresh'].append(vals[5])
    data['claims'].append(vals[6])
    data['CR'].append(vals[7])
    data['CI'].append(vals[8])
    data['C'].append(vals[9])
        
def alreadyHaveData(data,vals,highCr):
    for i in range(len(data['SD'])):
        if ( data['Unknown Vals'][i] == vals[0] and
             data['SD'][i] == vals[1] and
             data['Out Factor'][i] == vals[2] and
             data['Num Outliers'][i] == vals[3] and
             data['setting'][i] == vals[4]):
             if ((highCr is True and data['CR'][i] == '1.0') or
                 (highCr is False and data['CR'][i] != '1.0')):
                 return True
    return False
        
if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=4)
    tries=100000
    #tries=10000
    atLeast=100
    #atLeast=10
    claimThresh = None
    # Following are for tabulate
    results = []
    headers = ['vals','SD','fact','out','set','thresh','claims','CR','CI','C']
    # Following are for plotting
    if os.path.exists('data.json'):
        with open('data.json', 'r') as f:
            data = json.load(f)
    else:
        data = dataInit()
    sds = [1.5,2.25,3.0]
    sds = [2.25]
    outs = [[[1,2],[2,3]],
            [[2,3],[3,4]],
            [[3,4],[4,5]]
           ]
    outs = [
            [[2,3],[3,4]],
    ]
    factors = [1.2,1.5,2,5,10]
    factors = [1.2,5]
    outliers = ['min','max','max+1','max+max']
    outliers = ['max+1','max+max']
    numValues = [2,5,20]
    print("The following are for full claim rate (CR=1.0)",flush=True)
    for numVals,sd,outParams,factor,outType in [(v,w,x,y,z) for v in numValues for w in sds for x in outs for y in factors for z in outliers]:
        if outType == 'min':
            # No outliers in top group
            numOutliers = outParams[0][0]
        elif outType == 'max':
            # Sometimes one outlier in top group
            numOutliers = outParams[0][1]
        elif outType == 'max+1':
            # At least one outlier in top group
            numOutliers = outParams[0][1]+1
        else:
            # Outlier group and top group always full of outliers
            numOutliers = outParams[0][1]+outParams[1][1]
        if alreadyHaveData(data,[numVals,sd,factor,outParams,outType],True):
            print(f"Already have {[numVals,sd,factor,outParams,outType]}, highCr",flush=True)
            continue
        cr,ci,c,pcr,pci,pc,excess,claims = basicAttack(numVals,sd,outParams,factor,numOutliers,claimThresh,
                                                tries=tries,atLeast=atLeast)
        results.append([numVals,sd,factor,outParams,outType,1,claims,pcr,pci,pc,])
        dataUpdate(data,[numVals,sd,factor,outParams,outType,1,claims,pcr,pci,pc,])
        print(tabulate(results,headers,tablefmt='latex_booktabs'),flush=True)
        print(tabulate(results,headers,tablefmt='github'),flush=True)
        with open('data.json', 'w') as f:
            json.dump(data, f, indent=4, sort_keys=True)

    # Now we compute claim rate given goal of CI=0.95
    results = []
    print("\nThe following attempts to find the Claim Rate when CI is high (> 0.95)",flush=True)
    for numVals,sd,outParams,factor,outType in [(v,w,x,y,z) for v in numValues for w in sds for x in outs for y in factors for z in outliers]:
        if alreadyHaveData(data,[numVals,sd,factor,outParams,outType],False):
            print(f"Already have {[numVals,sd,factor,outParams,outType]}, lowCr",flush=True)
            continue
        claimThresh = 1
        while True:
            if outType == 'min':
                numOutliers = outParams[0][0]
            elif outType == 'max':
                numOutliers = outParams[0][1]
            else:
                numOutliers = outParams[0][1]+1
            cr,ci,c,pcr,pci,pc,excess,claims = basicAttack(numVals,sd,outParams,factor,numOutliers,claimThresh,
                                                    tries=tries,atLeast=atLeast)
            print(f"claimThresh {claimThresh}, cr {pcr}, ci {pci}, c {pc}",flush=True)
            # We want to achieve a CI of at least 95%, but we won't go
            # beyond CR of 0.0001 to get it.
            if ci >= 0.95 or cr < 0.0001:
                results.append([numVals,sd,factor,outParams,outType,claimThresh,claims,pcr,pci,pc,])
                dataUpdate(data,[numVals,sd,factor,outParams,outType,claimThresh,claims,pcr,pci,pc,])
                break
            claimThresh = excess * 1.1
        print(tabulate(results,headers,tablefmt='latex_booktabs'),flush=True)
        print(tabulate(results,headers,tablefmt='github'),flush=True)
        with open('data.json', 'w') as f:
            json.dump(data, f, indent=4, sort_keys=True)
