import json
import pprint
import itertools
import os.path
import random
import lrAttack
pp = pprint.PrettyPrinter(indent=4)

tableParams = {
    'tabType': None,
    'numValsPerColumn': None,
}
anonymizerParams = {
    'suppressPolicy': None,
    'suppressThreshold': None,
    'noisePolicy': None,
    'noiseAmount': None,
}

forceMeasure = True

prod = []
# numColumnVals is first because the larger numbers may take a long time to solve
numColumnVals = [[3,3,3],[5,5,5],[3,3,3,3],[10,10,10],[5,5,5,5],[10,10,10,10]]
prod.append(numColumnVals)
seeds = ['a','b']
prod.append(seeds)
tabTypes = ['random','complete']
prod.append(tabTypes)
suppressPolicies = ['hard','noisy']
prod.append(suppressPolicies)
suppressThresholds = [0,1,2,4,8]
prod.append(suppressThresholds)
noisePolicies = ['simple']
prod.append(noisePolicies)
noiseAmounts = [0]
prod.append(noiseAmounts)

for passType in ['justCheck','solve']:
    for numValsPerColumn,seed,tabType,suppressPolicy,suppressThreshold,noisePolicy,noiseAmount in itertools.product(*prod):
        print(passType)
        print(seed,tabType,suppressPolicy,suppressThreshold,noisePolicy,noiseAmount,numValsPerColumn)
        if seeds.index(seed) > 0 and tabType == 'complete':
            # Changing the seed won't lead to a different table for 'complete' tables, so don't bother
            print(f"Don't bother with seed {seed} and table type {tabType}")
            continue
        if suppressPolicy == 'noisy' and suppressThreshold < 4:
            print(f"Don't bother with suppress policy {suppressPolicy} and threshold {suppressThreshold}")
            continue
        tableParams['tabType'] = tabType
        tableParams['numValsPerColumn'] = numValsPerColumn
        anonymizerParams['suppressPolicy'] = suppressPolicy
        anonymizerParams['suppressThreshold'] = suppressThreshold
        anonymizerParams['noisePolicy'] = noisePolicy
        anonymizerParams['noiseAmount'] = noiseAmount
        pp.pprint(tableParams)
        pp.pprint(anonymizerParams)
    
        random.seed(seed)
        lra = lrAttack.lrAttack(seed, tableParams=tableParams, anonymizerParams=anonymizerParams, force=True)
        if lra.problemAlreadySolved():
            print(f"Attack {lra.fileName} already solved")
            if forceMeasure:
                print("    Measuring solution match (forced)")
                lra.measureMatch(force=True)
            else:
                if not lra.solutionAlreadyMeasured():
                    print("    Measuring solution match")
                    lra.measureMatch(force=False)
                else:
                    print("    Match already measured")
            continue
        if passType == 'solve':
            print(f"Running attack {lra.fileName}")
            prob = lra.makeProblem()
            lra.storeProblem(prob)
            print("Solving problem")
            solveStatus = lra.solve(prob)
            pp.pprint(f"Solve Status: {solveStatus}")
            lra.solutionToTable()
            lra.saveResults()
            lra.measureMatch(force=False)
        