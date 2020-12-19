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

prod = []
# numColumnVals is first because the larger numbers may take a long time to solve
numColumnVals = [[3,3,3],[5,5,5],[10,10,10],[3,3,3,3],[5,5,5,5],[10,10,10,10]]
prod.append(numColumnVals)
seeds = ['a']
prod.append(seeds)
tabTypes = ['random','complete']
prod.append(tabTypes)
suppressPolicies = ['hard']
prod.append(suppressPolicies)
suppressThresholds = [0,1,2,4]
prod.append(suppressThresholds)
noisePolicies = ['simple']
prod.append(noisePolicies)
noiseAmounts = [0]
prod.append(noiseAmounts)

for numValsPerColumn,seed,tabType,suppressPolicy,suppressThreshold,noisePolicy,noiseAmount in itertools.product(*prod):
    print(seed,tabType,suppressPolicy,suppressThreshold,noisePolicy,noiseAmount,numValsPerColumn)
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
    prob = lra.makeProblem()
    print("Solving problem")
    lra.storeProblem(prob)
    solveStatus = lra.solve(prob)
    pp.pprint(f"Solve Status: {solveStatus}")
    lra.solutionToTable()
    lra.saveResults()
    