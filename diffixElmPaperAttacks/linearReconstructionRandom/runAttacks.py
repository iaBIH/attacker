import logging as lg
import pprint
import itertools
import lrAttack
import tools.anonymizer
pp = pprint.PrettyPrinter(indent=4)

def doAttack(params):
    tableParams = {
        'numAIDs': None,
        'numSymbols': None,
        'valueFreqs': None,
        'aidLen': None,
        'valueFreqs': None,
        'attackerType': None,
    }
    anonymizerParams = {
        'label': None,
        'lowThresh': None,
        'gap': None,
        'sdSupp': None,
        'standardDeviation': None,
        'priorKnowledge': None
    }
    solveParams = {
        'elasticLcf': None,
        'elasticNoise': None,
        'numSDs': None,
    }
    numAIDs,numSymbols,aidLen,valueFreqs,attackerType,anonLabel,elastic,priorSeeds = params['attack']
    prior = priorSeeds[0]
    numSeeds = priorSeeds[1]
    lg.info(f"    {params['passType']}")
    tableParams['numSymbols'] = numSymbols
    tableParams['numAIDs'] = numAIDs
    tableParams['aidLen'] = aidLen
    tableParams['valueFreqs'] = valueFreqs
    tableParams['attackerType'] = attackerType
    anonymizerParams = tools.anonymizer.getAnonParamsFromLabel(anonLabel)
    anonymizerParams['priorKnowledge'] = prior
    solveParams['elasticLcf'] = elastic[0]
    solveParams['elasticNoise'] = elastic[1]

    checkSDsList = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0]
    trySDsList = [3.0, 4.0, 5.0, 7.0, 10.0]
    # First we need to decide if we need to run the attack
    for seedNum in range(numSeeds):
        seed = f"{seedNum:03d}"
        skip = False
        for numSDs in checkSDsList:
            # numSds is the number of noise standard deviations within which the
            # solution is constrained. Smaller number means more accurate solution,
            # but greater chance of not finding a solution. So we start with more
            # accurate, and increase until we get a solution.
            solveParams['numSDs'] = numSDs
            if (anonymizerParams['lowThresh'] == 0 and solveParams['elasticLcf'] != 1.0):
                lg.info(f"        Skip because elastic suppress parameter without suppression")
                skip = True
                break
            lra = lrAttack.lrAttack(seed, anonymizerParams, tableParams, solveParams, force=True)
            if not forceSolution and lra.problemAlreadySolved():
                lg.info(f"    Attack {lra.fileName} already solved")
                skip = True
                break
        if skip:
            continue

        # Ok, we need to solve it
        solved = False
        for numSDs in trySDsList:
            solveParams['numSDs'] = numSDs
            pp.pprint(tableParams)
            pp.pprint(anonymizerParams)
            lra = lrAttack.lrAttack(seed, anonymizerParams, tableParams, solveParams, force=True)
            if params['passType'] == 'solve':
                lg.info(f"    Running attack {lra.fileName}")
                prob = lra.makeProblem()
                if (doStoreProblem):
                    lra.storeProblem(prob)
                lg.info(f"    Solving problem")
                solveStatus = lra.solve(prob)
                lg.info(f"    Solve Status: {solveStatus}")
                if solveStatus == 'Optimal':
                    lra.solutionToTable()
                    lra.measureMatch(force=False)
                    lra.saveResults()
                    solved = True
                    break
        if not solved:
            lg.info(f"    Unable to solve")

def attackIterator():
    ''' This routine contains multiple sets of attack parameters. For each such set,
        one or more parameter values are set for each parameter. All combinations of
        all parameters for each group are run.
    '''
    # For testing one experiment
    prod = []
    numAIDs = [10]
    prod.append(numAIDs)
    numSymbols = [8]
    prod.append(numSymbols)
    aidLen = [120]
    prod.append(aidLen)
    valueFreqs = [0.5]
    prod.append(valueFreqs)
    attackerType = ['untrusted']
    prod.append(attackerType)
    anonLabels = ['None']
    prod.append(anonLabels)
    elastic = [[1.0,1.0]]
    prod.append(elastic)
    priorSeeds = [['none',1]]
    #priorSeeds = [['half',1]]
    prod.append(priorSeeds)
    for things in itertools.product(*prod):
        yield things

    # This group tests no anonymization
    prod = []
    numAIDs = [50]
    prod.append(numAIDs)
    numSymbols = [2]
    prod.append(numSymbols)
    aidLen = [120]
    prod.append(aidLen)
    valueFreqs = [0.5]
    prod.append(valueFreqs)
    attackerType = ['trusted']
    prod.append(attackerType)
    anonLabels = ['None']
    prod.append(anonLabels)
    elastic = [[1.0,1.0]]
    prod.append(elastic)
    priorSeeds = [['none',10]]
    prod.append(priorSeeds)
    for things in itertools.product(*prod):
        yield things

    for numSeeds in [10]:
        # This is basic set
        prod = []
        numAIDs = [10,50,100]
        prod.append(numAIDs)
        numSymbols = [2,8,32]
        prod.append(numSymbols)
        aidLen = [120]
        prod.append(aidLen)
        valueFreqs = [0.1,0.5]
        prod.append(valueFreqs)
        attackerType = ['trusted','untrusted']
        prod.append(attackerType)
        anonLabels = ['P','XP','XXP']
        prod.append(anonLabels)
        elastic = [[1.0,1.0]]
        prod.append(elastic)
        priorSeeds = [['half',numSeeds],['none',numSeeds],['all-but-one',numSeeds*2],['all',2]]
        prod.append(priorSeeds)
        for things in itertools.product(*prod):
            yield things

        # This looks at some additional numbers of AIDs
        prod = []
        numAIDs = [200,400,800]
        prod.append(numAIDs)
        numSymbols = [2,8,32]
        prod.append(numSymbols)
        aidLen = [120]
        prod.append(aidLen)
        valueFreqs = [0.1,0.5]
        prod.append(valueFreqs)
        attackerType = ['trusted','untrusted']
        prod.append(attackerType)
        anonLabels = ['P','XP','XXP']
        prod.append(anonLabels)
        elastic = [[1.0,1.0]]
        prod.append(elastic)
        priorSeeds = [['none',numSeeds]]
        prod.append(priorSeeds)
        for things in itertools.product(*prod):
            yield things

        # This looks at different AID lengths for trusted
        prod = []
        numAIDs = [200]
        prod.append(numAIDs)
        numSymbols = [8]
        prod.append(numSymbols)
        aidLen = [15,30,60,120,240]
        prod.append(aidLen)
        valueFreqs = [0.5]
        prod.append(valueFreqs)
        attackerType = ['trusted']
        prod.append(attackerType)
        anonLabels = ['P','XP','XXP']
        prod.append(anonLabels)
        elastic = [[1.0,1.0]]
        prod.append(elastic)
        priorSeeds = [['none',numSeeds*3]]
        prod.append(priorSeeds)
        for things in itertools.product(*prod):
            yield things

# This is used to force experimental measurement based on the reconstructed table. It is
# used when we want to add a new measure, but don't need to rerun the solutions
forceMeasure = False

# This is used to force the solver to run again even though it has already run with the
# given set of parameters. This is used when we make changes to the solver and want to overwrite
# prior solutions.
forceSolution = False

# This forces the LP problem itself to be stored.
doStoreProblem = False

format = "%(asctime)s: %(message)s"
lg.basicConfig(format=format, level=lg.DEBUG, datefmt="%H:%M:%S")
#for passType in ['justCheck','solve']:
for passType in ['solve']:
    for attack in attackIterator():
        lg.info(f"Main: run attack {attack}")
        pp.pprint(attack)
        params = {
            'attack':attack,
            'passType':passType,
            'forceMeasure':False,
            'forceSolution':False,
            'doStoreProblem':False
        }
        doAttack(params)