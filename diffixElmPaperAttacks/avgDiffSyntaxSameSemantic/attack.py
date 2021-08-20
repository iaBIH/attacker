import random
import math
import pprint
from tabulate import tabulate

pp = pprint.PrettyPrinter(indent=4)

'''
Here we are interested in how many queries it takes to average out the
noise with high confidence (>95% and >99.5%). We look at different amounts
of per-layer noise (SD=0.5 and SD=1.0), and different number of layers
(1, 2, and 3). We ignore the existance of the bkt-dynamic noise layer,
because we just want to see what it takes to get rid of the other noise
layers.
'''

def attackFailed(numSamples,layers,sd):
    # We want to see if we can determine if the true count is 0 or 1
    trueCount = round(random.uniform(0,1))
    testCount = 0
    thresh = numSamples / 2
    noise = 0
    for _ in range(numSamples):
        testCount += trueCount
        for _ in range(layers):
            noise += random.gauss(0,sd)
    noisyCount = testCount + noise
    if noisyCount > thresh:
        guessCount = 1
    else:
        guessCount = 0
    if guessCount != trueCount:
        return True
    return False

cnf = [[2,0.975],[3,0.9985]]
lyr = [1,2,3]
nse = [0.5,1.0]

# Ok, first let's do this according to the math
''' The total sd `sdSum` is
        sdSum = sdLayer * sqrt(layers * numSamples)
    The threshold we need to be within is:
        thresh = numSamples / 2
    To get 97.5% accuracy, we need (two standard deviations):
        thresh > sdSum * 2
        sdSum < thresh / 2
    And for 99.85% accuracy, we need (three standard deviations):
        sdSum < thresh / 3

    Which means that we are looking for the smallest numSamples
    that satisfy the following inequality:
        sdLayer * sqrt(layers * numSamples) > (numSamples/2)/conf
'''
headers = ['Acc','SD','GBs','Samples']
results = []
res = {}
for thing,layers,sdLayer in [(x,y,z) for x in cnf for y in lyr for z in nse]:
    # We'll just grow numSamples until the inequality is true...
    conf = thing[0]
    acc = thing[1]
    print(f"Try sd = {sdLayer}, num layers = {layers}, try for accuracy {acc} (conf {conf})")
    numSamples = 1
    while True:
        sdEquiv = sdLayer * math.sqrt(layers * numSamples)
        neededThresh = numSamples/2
        if sdEquiv < neededThresh/conf:
            break
        numSamples += 1
    print(f"We need {numSamples} samples")
    results.append([acc,sdLayer,layers,numSamples])
    if conf not in res:
        res[conf] = {}
    if layers not in res[conf]:
        res[conf][layers] = {}
    res[conf][layers][sdLayer] = numSamples
pp.pprint(res)
print(tabulate(results,headers,tablefmt='latex_booktabs'))
print(tabulate(results,headers,tablefmt='github'))

# And now we'll validate the above with simulated attacks
for thing,layers,sdLayer in [(x,y,z) for x in cnf for y in lyr for z in nse]:
    # We'll just grow numSamples until the inequality is true...
    conf = thing[0]
    acc = thing[1]
    numSamples = res[conf][layers][sdLayer]
    print(f"Try sd = {sdLayer}, num layers = {layers}, try for accuracy {acc} (conf {conf})")
    print(f"    We need {numSamples} samples")
    numAttacks = 1000000
    expectFail = round(((1-acc)/1) * numAttacks)
    numFail = 0
    for _ in range(numAttacks):
        if attackFailed(numSamples,layers,sdLayer):
            numFail += 1
    print(f"    Got {numFail} failures of expected {expectFail}")
