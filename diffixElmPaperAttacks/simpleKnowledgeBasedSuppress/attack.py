import random
import sys
import os
from tabulate import tabulate
filePath = __file__
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import scores.score
import anonymize.anonAlgs

def meanAttack(lowThresh,gap,sdSupp,probHas,
                tries=10000,atLeast=100):
    s = scores.score.score(probHas)
    anon = anonymize.anonAlgs.anon(lowThresh,gap,sdSupp,0)

    mean = anon.getMean()
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
        suppress = anon.doSuppress(trueCount)
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
        
def lowThreshAttack(lowThresh,gap,sdSupp,probHas,
                tries=10000,atLeast=100):
    s = scores.score.score(probHas)
    anon = anonymize.anonAlgs.anon(lowThresh,gap,sdSupp,0)
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
        suppress = anon.doSuppress(trueCount)
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
    headers = ['Stat','LMG','SDsp','CR','CI','C']
    sdLs = [[1.0,2],[1.5,3],[2.0,4]]
    pbs = [0.1,0.5,0.9]
    lowThresh = 2

    print('''
The following attacks the mean threshold value. The count is known
to be either one less than the mean (victim does not have attribute)
or equal to the mean (victim does have attribute). If the output
is not suppressed, then we guess that the victim has the attribute.
The following results are for:
    low_thresh = 2
    ''')
    results = []
    for sdlsTup,probHas in [(x,y) for x in sdLs for y in pbs]:
        sdSupp = sdlsTup[0]
        gap = sdlsTup[1]
        cr,ci,c = meanAttack(lowThresh,gap,sdSupp,probHas,
                              tries=tries)
        results.append([probHas,gap,sdSupp,cr,ci,c,])

    print(tabulate(results,headers,tablefmt='latex_booktabs'))
    print(tabulate(results,headers,tablefmt='github'))

    print('''
The following attacks the low_thresh values. The count is known
to be either one less than low_thresh (victim does not have attribute)
or equal to low_thresh (victim does have attribute). If the output
is not suppressed, then the victim definitely has the attribute.
The following results are for:
    low_thresh = 2
    ''')
    results = []
    for sdlsTup,probHas in [(x,y) for x in sdLs for y in pbs]:
        sdSupp = sdlsTup[0]
        gap = sdlsTup[1]
        cr,ci,c = lowThreshAttack(lowThresh,gap,sdSupp,probHas,
                              tries=tries)
        results.append([probHas,gap,sdSupp,cr,ci,c,])

    print(tabulate(results,headers,tablefmt='latex_booktabs'))
    print(tabulate(results,headers,tablefmt='github'))