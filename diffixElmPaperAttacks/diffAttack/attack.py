import random
import sys
import os
import json
from tabulate import tabulate
filePath = __file__
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import tools.score
import anonymize.anonAlgs

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

def basicAttack(numUnknownVals,sd,claimThresh,tries=10000,atLeast=100):
    # We assume that each unknown value happens with equal probaiblity
    s = tools.score.score(1/numUnknownVals)
    # We assume no suppression (so don't bother to specify the parameters)
    anon = anonymize.anonAlgs.anon(0,0,0,sd)
    N = 25          # arbitrary

    # Nominally we'll make `tries` attempts, but we need to have at
    # least `atLeast` claims that the victim has the attribute

    numTries = 0
    numClaimHas = 0
    # left query always excludes victim by specifying gender='male'
    colsLeft = ['dept','gender','title']
    # right query may include victim
    colsRight = ['dept','title']
    while True:
        # We assume no suppression (so don't bother to specify the parameters)
        numTries += 1
        bktCountsLeft = []
        bktCountsRight = []
        anon = anonymize.anonAlgs.anon(0,0,0,sd,salt=numTries)
        for unknownVal in range(numUnknownVals):
            aidvSetLeft = makeAidvSet(numTries)
            aidvSetRight = makeAidvSet(numTries)
            trueCountLeft = N
            trueCountRight = N
            valsLeft = [50,51,unknownVal]
            valsRight = [50,unknownVal]
            if unknownVal == 0:
                # We arbitrarily pick the victim as belonging to this bucket
                trueCountRight += 1
                aidvSetRight.append(1)
            _,noisyCountLeft = anon.getNoise(trueCountLeft,aidvSet=aidvSetLeft,
                                             cols=colsLeft,vals=valsRight)
            bktCountsLeft.append(noisyCountLeft)
            _,noisyCountRight = anon.getNoise(trueCountRight,aidvSet=aidvSetRight,
                                             cols=colsRight,vals=valsRight)
            bktCountsRight.append(noisyCountRight)
        guessedVal,difference = selectVictimBucket(bktCountsLeft,bktCountsRight)
        # We need to decide if we want to make a claim at all.
        # We do so only if the difference exceeds the threshold
        if claimThresh and difference < claimThresh:
            # Don't make a claim
            makesClaim = False
            dontCare = True
            s.attempt(makesClaim,dontCare,dontCare)
            continue
        makesClaim = True
        # We always believe that the victim has the attribute
        claimHas = True
        numClaimHas += 1
        if guessedVal == 0:
            claimCorrect = True
        else:
            claimCorrect = False
        s.attempt(makesClaim,claimHas,claimCorrect)
        if numTries >= tries and numClaimHas >= atLeast:
            break
    claimRate,confImprove,confidence = s.computeScore()
    cr,ci,c = s.prettyScore()
    return claimRate,confImprove,confidence,cr,ci,c

def dataInit():
    return {'Unknown Vals':[],'SD':[],'CR':[],'CI':[]}

def dataUpdate(data,vals):
    data['Unknown Vals'].append(vals[0])
    data['SD'].append(vals[1])
    data['CR'].append(vals[2])
    data['CI'].append(vals[3])
        
if __name__ == "__main__":
    tries=100000
    #tries=100
    atLeast=100
    #atLeast=10
    claimThresh = None
    # Following are for tabulate
    results = []
    headers = ['vals','SD','CR','CI','C']
    # Following are for plotting
    data = dataInit()
    print("The following are for full claim rate (CR=1.0)")
    for sd,numUnknownVals in [(x,y) for x in [0.5,1.0,2.0,3.0] for y in [2,5,20]]:
        cr,ci,c,pcr,pci,pc = basicAttack(numUnknownVals,sd,claimThresh,tries=tries,atLeast=atLeast)
        results.append([numUnknownVals,sd,pcr,pci,pc,])
        dataUpdate(data,[numUnknownVals,sd,cr,ci,c,])
    print(tabulate(results,headers,tablefmt='latex_booktabs'))
    print(tabulate(results,headers,tablefmt='github'))

    # Now we compute claim rate given goal of CI=0.95
    results = []

    print("\nThe following attempts to find the Claim Rate when CI is high (> 0.95)")
    for sd,numUnknownVals in [(x,y) for x in [0.5,1.0,2.0,3.0] for y in [2,5,20]]:
        print(f"sd {sd}, numUnknown {numUnknownVals}",flush=True)
        claimThresh = -0.5
        while True:
            claimThresh += 1.0
            cr,ci,c,pcr,pci,pc = basicAttack(numUnknownVals,sd,claimThresh,tries=tries,atLeast=atLeast)
            print(f"claimThresh {claimThresh}, cr {pcr}, ci {pci}, c {pc}",flush=True)
            # We want to achieve a CI of at least 95%, but we won't go
            # beyond CR of 0.0001 to get it.
            if ci >= 0.95 or cr < 0.0001:
                results.append([numUnknownVals,sd,pcr,pci,pc,])
                dataUpdate(data,[numUnknownVals,sd,cr,ci,c,])
                break
    print(tabulate(results,headers,tablefmt='latex_booktabs'))
    print(tabulate(results,headers,tablefmt='github'))

    with open('data.json', 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True)
