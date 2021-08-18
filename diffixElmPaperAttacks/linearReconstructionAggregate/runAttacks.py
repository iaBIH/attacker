import logging as lg
import pprint
import itertools
import lrAttack
pp = pprint.PrettyPrinter(indent=4)

def getAnonParamsFromLabel(label):
    # These are the preset anonymization parameters
    if label == 'None':
        # No anonymization of any kind (used to validate models)
        return {'label':'None','lowThresh':0, 'gap':0, 'sdSupp':0, 'standardDeviation':0}
    elif label == 'SP':
        # Suppression only, private (used to test case where noise has been eliminated)
        return {'label':'SP','lowThresh':2, 'gap':2, 'sdSupp':1, 'standardDeviation':0}
    elif label == 'SXP':
        # Suppression only, extra private (used to test case where noise has been eliminated)
        return {'label':'SXP','lowThresh':2, 'gap':3, 'sdSupp':1.5, 'standardDeviation':0}
    elif label == 'SXXP':
        # Suppression only, extra extra private (used to test case where noise has been eliminated)
        return {'label':'SXXP','lowThresh':2, 'gap':4, 'sdSupp':2, 'standardDeviation':0}
    elif label == 'P':
        # Suppression and noise, private
        return {'label':'P','lowThresh':2, 'gap':2, 'sdSupp':1, 'standardDeviation':1}
    elif label == 'XP':
        # Suppression and noise, extra private
        return {'label':'XP','lowThresh':2, 'gap':3, 'sdSupp':1.5, 'standardDeviation':2}
    elif label == 'XXP':
        # Suppression and noise, extra extra private
        return {'label':'XXP','lowThresh':2, 'gap':4, 'sdSupp':2, 'standardDeviation':3}
    return None

def doAttack(params,tid=None):
    tableParams = {
        'tabType': None,
        'numValsPerColumn': None,
    }
    anonymizerParams = {
        'label': None,
        'lowThresh': None,
        'gap': None,
        'sdSupp': None,
        'standardDeviation': None,
    }
    solveParams = {
        'elasticLcf': None,
        'elasticNoise': None,
        'numSDs': None,
    }
    seed,numValsPerColumn,tabType,anonLabel,elastic = params['attack']
    lg.info(f"    {tid}: {params['passType']}")
    lg.info(f"    {tid}: {numValsPerColumn},{seed},{tabType},{anonLabel},{elastic}")
    tableParams['tabType'] = tabType
    tableParams['numValsPerColumn'] = numValsPerColumn
    anonymizerParams = getAnonParamsFromLabel(anonLabel)
    solveParams['elasticLcf'] = elastic[0]
    solveParams['elasticNoise'] = elastic[1]

    numSDsList = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0]
    # First we need to decide if we need to run the attack
    problemAlreadySolved = False
    for numSDs in numSDsList:
        # numSds is the number of noise standard deviations within which the
        # solution is constrained. Smaller number means more accurate solution,
        # but greater chance of not finding a solution. So we start with more
        # accurate, and increase until we get a solution.
        solveParams['numSDs'] = numSDs
        if (anonymizerParams['lowThresh'] == 0 and solveParams['elasticLcf'] != 1.0):
            lg.info(f"    {tid}:     Skip because elastic suppress parameter without suppression")
            return
        lra = lrAttack.lrAttack(seed, anonymizerParams, tableParams, solveParams, force=True)
        if not forceSolution and lra.problemAlreadySolved():
            lg.info(f"    {tid}: Attack {lra.fileName} already solved")
            return

    # Ok, we need to solve it
    for numSDs in numSDsList:
        solveParams['numSDs'] = numSDs
        lra = lrAttack.lrAttack(seed, anonymizerParams, tableParams, solveParams, force=True)
        if params['passType'] == 'solve':
            lg.info(f"    {tid}: Running attack {lra.fileName}")
            prob = lra.makeProblem()
            if (doStoreProblem):
                lra.storeProblem(prob)
            lg.info(f"    {tid}: Solving problem")
            solveStatus = lra.solve(prob)
            lg.info(f"    {tid}: Solve Status: {solveStatus}")
            if solveStatus == 'Optimal':
                lra.solutionToTable(prob)
                lra.measureMatch(force=False)
                lra.saveResults()
                return
    lg.info(f"    {tid}: Unable to solve")

def attackIterator():
    ''' This routine contains multiple sets of attack parameters. For each such set,
        one or more parameter values are set for each parameter. All combinations of
        all parameters for each group are run.
    '''
    # This group tests base set, without large networks
    prod = []
    seeds = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t']
    prod.append(seeds)
    numColumnVals = [[3,3],[5,5],[3,3,3],[5,5,5],[3,3,3,3],[3,3,3,3,3]]
    prod.append(numColumnVals)
    tabTypes = ['random']
    prod.append(tabTypes)
    anonLabels = ['None','SP','SXP','SXXP','P','XP','XXP']
    prod.append(anonLabels)
    elastic = [[1.0,1.0]]
    prod.append(elastic)
    for things in itertools.product(*prod):
        yield things
    return

    # This group tests base set, with large networks
    prod = []
    seeds = ['a','b','c','d','e','f','g','h','i','j']
    prod.append(seeds)
    numColumnVals = [[5,5,5,5],[10,10,10]]
    prod.append(numColumnVals)
    tabTypes = ['random']
    prod.append(tabTypes)
    anonLabels = ['None','SP','SXP','SXXP','P','XP','XXP']
    prod.append(anonLabels)
    elastic = [[1.0,1.0]]
    prod.append(elastic)
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