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
    'lcfMin': None,
    'lcfMax': None,
    'standardDeviation': None,
}

forceMeasure = False
forceSolution = False
doStoreProblem = False

def oneAttackGroup(prod):
    for passType in ['justCheck','solve']:
        for numValsPerColumn,seed,tabType,lcf,sd in itertools.product(*prod):
            print(passType)
            print(numValsPerColumn,seed,tabType,lcf,sd)
            tableParams['tabType'] = tabType
            tableParams['numValsPerColumn'] = numValsPerColumn
            anonymizerParams['lcfMin'] = lcf[0]
            anonymizerParams['lcfMax'] = lcf[1]
            anonymizerParams['standardDeviation'] = sd
            pp.pprint(tableParams)
            pp.pprint(anonymizerParams)
        
            random.seed(seed)
            lra = lrAttack.lrAttack(seed, tableParams=tableParams, anonymizerParams=anonymizerParams, force=True)
            if not forceSolution and lra.problemAlreadySolved():
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
                if (doStoreProblem):
                    lra.storeProblem(prob)
                print("Solving problem")
                solveStatus = lra.solve(prob)
                pp.pprint(f"Solve Status: {solveStatus}")
                lra.solutionToTable()
                lra.saveResults()
                lra.measureMatch(force=False)

prod = []
# numColumnVals is first because the larger numbers may take a long time to solve
numColumnVals = [[3,3,3]]
prod.append(numColumnVals)
seeds = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z']
prod.append(seeds)
tabTypes = ['random','complete']
prod.append(tabTypes)
lcf = [[2,6]]
prod.append(lcf)
sf = [0]
prod.append(sf)
oneAttackGroup(prod)
quit()

prod = []
# numColumnVals is first because the larger numbers may take a long time to solve
numColumnVals = [[3,3,3],[5,5,5],[3,3,3,3],[10,10,10]]
prod.append(numColumnVals)
seeds = ['a']
prod.append(seeds)
tabTypes = ['random','complete']
prod.append(tabTypes)
lcf = [[0,0],[2,2],[4,4],[8,8],[2,6],[2,14]]
prod.append(lcf)
sf = [0]
prod.append(sf)
oneAttackGroup(prod)

prod = []
# numColumnVals is first because the larger numbers may take a long time to solve
numColumnVals = [[5,5,5,5],[10,10,10,10]]
prod.append(numColumnVals)
seeds = ['a']
prod.append(seeds)
tabTypes = ['random','complete']
prod.append(tabTypes)
lcf = [[0,0],[2,2],[4,4],[8,8],[2,6],[2,14]]
prod.append(lcf)
sf = [0]
prod.append(sf)
oneAttackGroup(prod)