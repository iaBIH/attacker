import random
import pprint
import json
import statistics

pp = pprint.PrettyPrinter(indent=4)

'''
Here we are interested in how many queries it takes to average out the
noise with high confidence (>95% and >99.5%). We look at both naive
averaging (i.e. because the same table was released with minor increments),
and same-semantics averaging. In the former case, we use different amounts
of total noise (SD=1.5, 2.25, and 3.0), and in the latter we are only
trying to eliminate one layer, so we use SD=1.06, 1.59, and 2.12.
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

def dataInit():
    return {'Accuracy':[],'SD':[],'Samples':[]}

def dataUpdate(data,vals):
    data['Accuracy'].append(vals[0])
    data['SD'].append(vals[1])
    data['Samples'].append(vals[2])
        
acc = [0.95,0.99,0.999]
nse = [1.0,1.5,2.25,3.0]
data = dataInit()
neededSuccess = 5
for acc,sdTotal in [(x,z) for x in acc for z in nse]:
    # We'll just grow numSamples until the inequality is true...
    print(f"Try sd = {sdTotal}, try for accuracy {acc}")
    numSamples = 1
    samples = []
    while True:
        numFail = 0
        numPass = 0
        while True:
            if attackFailed(numSamples,1,sdTotal):
                numFail += 1
            else:
                numPass += 1
            if numFail > 100:
                break
        atkAcc = numPass / (numPass + numFail)
        print(f"          {numSamples} samples, pass {numPass}, fail {numFail}")
        if atkAcc > acc:
            samples.append(numSamples)
            if len(samples) >= neededSuccess:
                break
        if len(samples) > 0:
            increment = round(numSamples * 0.01)
        else:
            increment = round(numSamples * 0.1)
        increment = max(increment,1)
        numSamples += increment
    avgSamples = round(statistics.mean(samples))
    dataUpdate(data,[acc,sdTotal,avgSamples])
    print(f"Got accuracy {atkAcc} with {avgSamples} samples for noise {sdTotal}")

with open('data.json', 'w') as f:
    json.dump(data, f, indent=4, sort_keys=True)
