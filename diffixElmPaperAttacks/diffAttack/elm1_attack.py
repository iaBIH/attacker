import random
import sys
import os
import json
import statistics
from tabulate import tabulate
filePath = __file__
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import tools.score
import anonymize.anonAlgs

'''
This code is for both the classic difference attack (positive AND), and
before/after difference attacks that exploit changes in the table. Which
attack is run is determined by configuring `attackType`
'''

def makeAidvSet(base):
    init = base * 1000
    aidvSet = []
    for aidv in range(init,init+5):
        aidvSet.append(aidv)
    return(aidvSet)

def selectVictimBucket(bktCountsLeft,bktCountsRight):
    maxDiff = -1000
    maxIndex = -1
    for i in range(len(bktCountsLeft)):
        diff = bktCountsRight[i] - bktCountsLeft[i]
        if diff > maxDiff:
            maxDiff = diff
            maxIndex = i
    return maxIndex,maxDiff

def basicAttack(numUnknownVals,sd,claimThresh,attackType,numSamples,tries=10000,atLeast=100):
    # For the difference attack, the left bucket exludes the victim and the right
    # bucket conditionally includes the victim.
    # For the change attack, the left bucket is before the change, and the right
    # bucket is after the change.
    # We assume that each unknown value happens with equal probaiblity
    s = tools.score.score(1/numUnknownVals)
    N = 25          # arbitrary, big enough to avoid min reportable value lowThresh

    # Nominally we'll make `tries` attempts, but we need to have at
    # least `atLeast` claims that the victim has the attribute

    numTries = 0
    numClaimHas = 0
    if attackType == 'diffAttack':
        # left query always excludes victim by specifying gender='male'
        colsLeft = ['dept','gender','title']
    else:
        # Queries are the same for the change attack
        colsLeft = ['dept','title']
    # right query may include victim
    colsRight = ['dept','title']
    noisesDiff = []
    bailOutReason = ''
    while True:
        numTries += 1
        addIndex,rmIndex = random.sample(range(numUnknownVals),k=2)
        #print(addIndex,rmIndex)
        bktCountsLeft = [0 for _ in range(numUnknownVals)]
        bktCountsRight = [0 for _ in range(numUnknownVals)]
        #print(f"init left: {bktCountsLeft}")
        #print(f"init right: {bktCountsRight}")
        for sample in range(numSamples):
            saltLeft = (numTries+1) * (sample+1) * 123456967
            if attackType == 'diffAttack':
                saltRight = saltLeft
            else:
                # Salt changes on change attack
                saltRight = saltLeft * 768595021
            for unknownVal in range(numUnknownVals):
                aidvSetLeft = makeAidvSet(numTries+(unknownVal*105389))
                aidvSetRight = makeAidvSet(numTries+(unknownVal*105389))
                trueCountLeft = N
                trueCountRight = N
                # These values for 'dept' and 'gender' columns are arbitrary
                if attackType == 'diffAttack':
                    valsLeft = [50,51,unknownVal]
                    valsRight = [50,unknownVal]
                else:   # one of the change attack variants
                    valsLeft = [50,unknownVal]
                    valsRight = [50,unknownVal]
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
                #print(f"true left = {trueCountLeft}, true right = {trueCountRight}")
                # We assume no suppression (so don't bother to specify the parameters)
                anon = anonymize.anonAlgs.anon(0,0,0,[sd],salt=saltLeft,version='elm1')
                noiseLeft,noisyCountLeft = anon.getNoise(trueCountLeft,aidvSet=aidvSetLeft,
                                                cols=colsLeft,vals=valsLeft)
                bktCountsLeft[unknownVal] += noisyCountLeft
                anon = anonymize.anonAlgs.anon(0,0,0,[sd],salt=saltRight,version='elm1')
                noiseRight,noisyCountRight = anon.getNoise(trueCountRight,aidvSet=aidvSetRight,
                                                cols=colsRight,vals=valsRight)
                bktCountsRight[unknownVal] += noisyCountRight
                noisesDiff.append(noiseLeft - noiseRight)
                #print(f"append left: {bktCountsLeft}")
                #print(f"append right: {bktCountsRight}")
                #print(f"noiseleft {noiseLeft}, noiseright {noiseRight}")
        # Divide the noisy counts by the number of samples
        #print(f"final1 left: {bktCountsLeft}")
        #print(f"final1 right: {bktCountsRight}")
        bktCountsLeft = list(map(lambda x:x/numSamples,bktCountsLeft))
        bktCountsRight = list(map(lambda x:x/numSamples,bktCountsRight))
        #print(f"final2 left: {bktCountsLeft}")
        #print(f"final2 right: {bktCountsRight}")
        guessedVal,difference = selectVictimBucket(bktCountsLeft,bktCountsRight)
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
        if guessedVal == addIndex:
            claimCorrect = True
            #print("-------------------- Correct!")
        else:
            claimCorrect = False
            #print("--------------- Wrong!")
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
    print(f"average noise diff {statistics.mean(noisesDiff)}")
    print(f"stddev noise diff {statistics.stdev(noisesDiff)}")
    print(bailOutReason,flush=True)
    return claimRate,confImprove,confidence,cr,ci,c

def dataInit():
    return {'Unknown Vals':[],'Samples':[],'SD':[],'CR':[],'CI':[]}

def dataUpdate(data,vals):
    data['Unknown Vals'].append(vals[0])
    data['Samples'].append(vals[1])
    data['SD'].append(vals[2])
    data['CR'].append(vals[3])
    data['CI'].append(vals[4])

def alreadyHaveData(data,vals):
    for i in range(len(data['SD'])):
        if ( data['Unknown Vals'][i] == vals[0] and
             data['Samples'][i] == vals[1] and
             data['SD'][i] == vals[2]):
             return True
    return False
        
if __name__ == "__main__":
    tries=100000
    #tries=100
    atLeast=100
    #atLeast=10
    claimThresh = None
    sds = [1.5,2.25,3.0]
    unkn = [2,5,20]
    numSamples = [1]
    # Following are for tabulate
    results = []
    headers = ['vals','samp','SD','CR','CI','C']
    if True:
        # Classic difference attack
        attackType = 'diffAttack'
        dataFile = 'dataDiffElm1.json'
    elif False:
        # Difference attack based on table change (salt changes too)
        attackType = 'changeDiffAttack'
        dataFile = 'dataChangeDiffElm1.json'
    else:
        # Difference attack based on table change (salt changes too)
        attackType = 'changeAvgAttack'
        dataFile = 'dataChangeAvgElm1.json'
        numSamples = [2,5,10,20]
        sds = [2.25]
        unkn = [5]
    if os.path.exists(dataFile):
        with open(dataFile, 'r') as f:
            data = json.load(f)
    else:
        # Following are for plotting
        data = dataInit()
    print("The following are for full claim rate (CR=1.0)",flush=True)
    for sd,numUnknownVals,samples in [(x,y,z) for x in sds for y in unkn for z in numSamples]:
        if alreadyHaveData(data,[numUnknownVals,samples,sd]):
            print(f"Already have numUnknown {numUnknownVals}, samples {samples}, sd {sd}",flush=True)
            continue
        cr,ci,c,pcr,pci,pc = basicAttack(numUnknownVals,sd,claimThresh,attackType,
                                         samples,tries=tries,atLeast=atLeast)
        results.append([numUnknownVals,samples,sd,pcr,pci,pc,])
        dataUpdate(data,[numUnknownVals,samples,sd,cr,ci,c,])
        print(tabulate(results,headers,tablefmt='latex_booktabs'),flush=True)
        print(tabulate(results,headers,tablefmt='github'),flush=True)
        with open(dataFile, 'w') as f:
            json.dump(data, f, indent=4, sort_keys=True)

    # Now we compute claim rate given goal of CI=0.95
    results = []

    print("\nThe following attempts to find the Claim Rate when CI is high (> 0.95)",flush=True)
    for sd,numUnknownVals,samples in [(x,y,z) for x in sds for y in unkn for z in numSamples]:
        print(f"sd {sd}, numUnknown {numUnknownVals}",flush=True)
        claimThresh = -0.5
        while True:
            claimThresh += 1.0
            cr,ci,c,pcr,pci,pc = basicAttack(numUnknownVals,sd,claimThresh,attackType,
                                         samples,tries=tries,atLeast=atLeast)
            print(f"claimThresh {claimThresh}, cr {pcr}, ci {pci}, c {pc}",flush=True)
            # We want to achieve a CI of at least 95%, but we won't go
            # beyond CR of 0.0001 to get it.
            if ci >= 0.95 or cr < 0.0001:
                results.append([numUnknownVals,samples,sd,pcr,pci,pc,])
                dataUpdate(data,[numUnknownVals,samples,sd,cr,ci,c,])
                print(tabulate(results,headers,tablefmt='latex_booktabs'),flush=True)
                print(tabulate(results,headers,tablefmt='github'),flush=True)
                with open(dataFile, 'w') as f:
                    json.dump(data, f, indent=4, sort_keys=True)
                break
    print(tabulate(results,headers,tablefmt='latex_booktabs'),flush=True)
    print(tabulate(results,headers,tablefmt='github'),flush=True)

    with open(dataFile, 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True)
