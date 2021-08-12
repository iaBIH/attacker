import random
import sys
import os
from tabulate import tabulate
filePath = __file__
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import scores.score

def getMean(lowThresh, lowsd, sd):
    mean = lowThresh + (lowsd * sd)
    return mean

def doSuppress(count,lowThresh,lowsd,highsd,sd):
    #print(f"count {count},lowThresh {lowThresh},lowsd {lowsd}, highsd {highsd}, sd {sd}")
    if count < lowThresh:
        return True
    mean = getMean(lowThresh, lowsd, sd)
    highThresh = mean + (highsd * sd)
    #print(f"mean {mean},highThresh {highThresh}")
    if count > highThresh:
        return False
    cutoff = random.gauss(mean,sd)
    #print(f"cutoff {cutoff}")
    if count < cutoff:
        return True
    return False

def meanAttack(lowThresh,lowsd,highsd,sd,probHas,
                tries=10000,atLeast=100):
    s = scores.score.score(probHas)

    mean = getMean(lowThresh, lowsd, sd)
    # N is known number of individuals with the attribute
    N = mean - 1
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
        suppress = doSuppress(trueCount,lowThresh,lowsd,highsd,sd)
        # In attacking the mean, there is a 50/50 chance of
        # suppression or not, so we can effectively make a claim
        # with every attack
        makesClaim = True
        if suppress:
            claimHas = False
        else:
            # We believe that the victim has the attribute
            claimHas = True
            numClaimHas += 1
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
        
def lowThreshAttack(lowThresh,lowsd,highsd,sd,probHas,
                tries=10000,atLeast=100):
    s = scores.score.score(probHas)
    N = lowThresh - 1       # definitely suppress if N

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
        suppress = doSuppress(trueCount,lowThresh,lowsd,highsd,sd)
        if suppress:
            # In attacking low_thresh, suppression is the norm regardless of
            # whether the victim has the attribute or not, so we
            # are not able to make a claim
            claimHas = False
            makesClaim = False
        else:
            # We believe that the victim has the attribute
            claimHas = True
            numClaimHas += 1
            makesClaim = True
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

    print('''
The following attacks the mean threshold value. The count is known
to be either one less than the mean (victim does not have attribute)
or equal to the mean (victim does have attribute). If the output
is not suppressed, then we guess that the victim has the attribute.
The following results are for:
    low_thresh = 2
    sd = 1.0
    hishsd = 2.0 (though this has no effect on the attack)
    ''')
    results = []
    headers = ['Stat','lowsd','CR','CI','C']
    sd = 1.0
    lowThresh = 2
    highsd = 2
    for lowsd,probHas in [(x,y) for x in [2,3,4] for y in [0.1,0.5,0.9]]:
        cr,ci,c = meanAttack(lowThresh,lowsd,highsd,sd,probHas,
                              tries=tries)
        results.append([probHas,lowsd,cr,ci,c,])

    print(tabulate(results,headers,tablefmt='latex_booktabs'))
    print(tabulate(results,headers,tablefmt='github'))

    print('''
The following attacks the low_thresh values. The count is known
to be either one less than low_thresh (victim does not have attribute)
or equal to low_thresh (victim does have attribute). If the output
is not suppressed, then the victim definitely has the attribute.
The following results are for:
    low_thresh = 2
    sd = 1.0
    hishsd = 2.0 (though this has no effect on the attack)
    ''')
    results = []
    headers = ['Stat','lowsd','CR','CI','C']
    sd = 1.0
    lowThresh = 2
    highsd = 2
    for lowsd,probHas in [(x,y) for x in [2,3,4] for y in [0.1,0.5,0.9]]:
        cr,ci,c = lowThreshAttack(lowThresh,lowsd,highsd,sd,probHas,
                              tries=tries)
        results.append([probHas,lowsd,cr,ci,c,])

    print(tabulate(results,headers,tablefmt='latex_booktabs'))
    print(tabulate(results,headers,tablefmt='github'))