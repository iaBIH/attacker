import random
import sys
import os
from tabulate import tabulate
filePath = __file__
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import scores.score

def basicAttack(probHas,sd,claimThresh,tries=10000,atLeast=100):
    # Here we use midpoint between N and N+1 and see how often we
    # get it right when the answer is N+1 (i.e. victim has
    # the attribute) with 50% probability
    s = scores.score.score(probHas)
    N = 25          # arbitrary
    # Noisy counts above the threshold, victim probably has attribute
    threshold = N + 0.5

    # Nominally we'll make `tries` attempts, but we need to have at
    # least `atLeast` claims that the victim has the attribute

    numTries = 0
    numClaimHas = 0
    while True:
        numTries += 1
        ranVal = random.uniform(0.0, 1.0)
        if ranVal <= probHas:
            victimHas = True
            trueCount = N+1
        else:
            victimHas = False
            trueCount = N
        noise = random.gauss(0,sd)
        noisyCount = trueCount + noise
        # We need to decide if we want to make a claim at all.
        # We do so only if the noisyCount falls outside of a range
        # around the center point
        if (noisyCount < threshold + claimThresh and
            noisyCount > threshold - claimThresh):
            # Don't make a claim
            makesClaim = False
            dontCare = True
            s.attempt(makesClaim,dontCare,dontCare)
            continue
        makesClaim = True
        if noisyCount > threshold:
            # We believe that the victim has the attribute
            claimHas = True
            numClaimHas += 1
        else:
            claimHas = False
        if (victimHas and claimHas) or (not victimHas and not claimHas):
            claimCorrect = True
        else:
            claimCorrect = False
        s.attempt(makesClaim,claimHas,claimCorrect)
        if numTries >= tries and numClaimHas >= atLeast:
            break
    _,_,_ = s.computeScore()
    claimRate,confImprove,confidence = s.prettyScore()
    return claimRate,confImprove,confidence
        
if __name__ == "__main__":
    tries=1000000
    claimThresh = 0.0
    results = []
    headers = ['Stat','SD','CR','CI','C']
    print("The following are for full claim rate (CR=1.0)")
    for sd,probHas in [(x,y) for x in [1.0,2.0,3.0] for y in [0.1,0.5,0.9]]:
        cr,ci,c = basicAttack(probHas,sd,claimThresh,tries=tries)
        results.append([probHas,sd,cr,ci,c,])
    print(tabulate(results,headers,tablefmt='latex_booktabs'))
    print(tabulate(results,headers,tablefmt='github'))
    # Now we compute claim rate given goal of CI=0.95
    results = []

    print("\nThe following attempts to find the Claim Rate when CI is high (> 0.95)")
    for sd,probHas in [(x,y) for x in [1.0,2.0,3.0] for y in [0.1,0.5,0.9]]:
        claimThresh = 0.0
        while True:
            claimThresh += 0.5
            cr,ci,c = basicAttack(probHas,sd,claimThresh,tries=tries)
            # We want to achieve a CI of at least 95%, but we won't go
            # beyond CR of 0.0001 to get it.
            if ci >= 0.95 or cr < 0.0001:
                results.append([probHas,sd,cr,ci,c,])
                break
    print(tabulate(results,headers,tablefmt='latex_booktabs'))
    print(tabulate(results,headers,tablefmt='github'))