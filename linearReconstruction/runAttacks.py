import threading
import logging as lg
import json
import pprint
import itertools
import os.path
import time
import lrAttack
pp = pprint.PrettyPrinter(indent=4)

def doAttack(params):
    tid = threading.get_ident()
    tableParams = {
        'tabType': None,
        'numValsPerColumn': None,
    }
    anonymizerParams = {
        'lcfMin': None,
        'lcfMax': None,
        'standardDeviation': None,
    }
    solveParams = {
        'elasticLcf': None,
        'elasticNoise': None,
    }
    numValsPerColumn,seed,tabType,lcf,sd,elastic = params['attack']
    lg.info(f"    {tid}: {params['passType']}")
    lg.info(f"    {tid}: {numValsPerColumn},{seed},{tabType},{lcf},{sd},{elastic}")
    tableParams['tabType'] = tabType
    tableParams['numValsPerColumn'] = numValsPerColumn
    anonymizerParams['lcfMin'] = lcf[0]
    anonymizerParams['lcfMax'] = lcf[1]
    anonymizerParams['standardDeviation'] = sd
    solveParams['elasticLcf'] = elastic[0]
    solveParams['elasticNoise'] = elastic[1]

    if (anonymizerParams['lcfMin'] == 0 and anonymizerParams['lcfMax'] == 0 and
        solveParams['elasticLcf'] != 1.0):
        lg.info(f"    {tid}:     Skip because elastic LCF parameter without LCF")
        return
    lra = lrAttack.lrAttack(seed, anonymizerParams, tableParams, solveParams, force=True)
    if not forceSolution and lra.problemAlreadySolved():
        lg.info(f"    {tid}: Attack {lra.fileName} already solved")
        if forceMeasure:
            lg.info(f"    {tid}:     Measuring solution match (forced)")
            lra.measureMatch()
            lra.saveResults()
        else:
            if not lra.solutionAlreadyMeasured():
                lg.info(f"    {tid}:     Measuring solution match")
                lra.measureMatch()
                lra.saveResults()
            else:
                lg.info(f"    {tid}:     Match already measured")
        return
    if params['passType'] == 'solve':
        lg.info(f"    {tid}: Running attack {lra.fileName}")
        prob = lra.makeProblem()
        if (doStoreProblem):
            lra.storeProblem(prob)
        lg.info(f"    {tid}: Solving problem")
        solveStatus = lra.solve(prob)
        lg.info(f"    {tid}: Solve Status: {solveStatus}")
        lra.solutionToTable(prob)
        lra.measureMatch()
        lra.saveResults()

def attackIterator():
    # This first group is for testing different seeds with elastic constraints
    prod = []
    numColumnVals = [[3,3,3]]
    prod.append(numColumnVals)
    seeds = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z']
    prod.append(seeds)
    tabTypes = ['random','complete']
    prod.append(tabTypes)
    lcf = [[4,4],[2,6]]
    prod.append(lcf)
    sf = [0]
    prod.append(sf)
    elastic = [[0.1,1.0],[0.25,1.0],[0.5,1.0],[0.75,1.0],[1.0,1.0]]
    prod.append(elastic)
    #for numValsPerColumn,seed,tabType,lcf,sd,elastic in itertools.product(*prod):
    for things in itertools.product(*prod):
        yield things
    return
    
    # This second group gets the remaining [3,3,3] shaped networks (without elastic constraints)
    # Start with five seeds. We can add more later
    prod = []
    seeds = ['a','b','c','d','e']
    prod.append(seeds)
    numColumnVals = [[3,3,3]]
    prod.append(numColumnVals)
    tabTypes = ['random','complete']
    prod.append(tabTypes)
    lcf = [[0,0],[2,2],[2,10]]
    prod.append(lcf)
    sf = [0]
    prod.append(sf)
    elastic = [[1.0,1.0]]
    prod.append(elastic)
    #for numValsPerColumn,seed,tabType,lcf,sd,elastic in itertools.product(*prod):
    for things in itertools.product(*prod):
        yield things
    
    # This group gets the other smallish network shapes across the desired parameters
    prod = []
    seeds = ['a','b','c','d','e']
    prod.append(seeds)
    numColumnVals = [[5,5,5],[10,10,10],[3,3,3,3]]
    prod.append(numColumnVals)
    tabTypes = ['random','complete']
    prod.append(tabTypes)
    lcf = [[0,0],[2,2],[4,4],[2,6],[2,10]]
    prod.append(lcf)
    sf = [0]
    prod.append(sf)
    elastic = [[1.0,1.0]]
    prod.append(elastic)
    #for numValsPerColumn,seed,tabType,lcf,sd,elastic in itertools.product(*prod):
    for things in itertools.product(*prod):
        yield things
    
    # This group gets the bigger network shapes across the desired parameters
    prod = []
    seeds = ['a','b','c','d','e']
    prod.append(seeds)
    numColumnVals = [[5,5,5,5],[10,10,10,10]]
    prod.append(numColumnVals)
    tabTypes = ['random','complete']
    prod.append(tabTypes)
    lcf = [[0,0],[2,2],[4,4],[2,6],[2,10]]
    prod.append(lcf)
    sf = [0]
    prod.append(sf)
    elastic = [[1.0,1.0]]
    prod.append(elastic)
    #for numValsPerColumn,seed,tabType,lcf,sd,elastic in itertools.product(*prod):
    for things in itertools.product(*prod):
        yield things

def getEmptyThreadIndex(threads):
    for i in range(len(threads)):
        if threads[i] is None:
            return i
    return None
    
forceMeasure = False
forceSolution = False
doStoreProblem = False
numThreads = 2
threads = [None for _ in range(numThreads)]
format = "%(asctime)s: %(message)s"
lg.basicConfig(format=format, level=lg.DEBUG, datefmt="%H:%M:%S")
for passType in ['justCheck','solve']:
    for attack in attackIterator():
        lg.info(f"Main: run attack {attack}")
        while True:
            # Find empty thread slot
            i = getEmptyThreadIndex(threads)
            if i is None:
                lg.debug("Main: no empty threads, so spin until we get one")
                while True:
                    emptyThreadIndex = -1
                    for i in range(len(threads)):
                        t = threads[i]
                        if t.is_alive() is True:
                            lg.debug(f"Main: join thread {t} at {i}")
                            t.join(timeout=0.1)
                            if t.is_alive() is False:
                                emptyThreadIndex = i
                                break
                        else:
                            lg.debug("Main: thread {t} at {i} not alive")
                            emptyThreadIndex = i
                            break
                    if emptyThreadIndex >= 0:
                        threads[i] = None
                        break
            else:
                # create a thread
                params = {
                    'attack':attack,
                    'passType':passType,
                    'forceMeasure':False,
                    'forceSolution':False,
                    'doStoreProblem':False
                }
                threads[i] = threading.Thread(target=doAttack, args=(params,))
                threads[i].start()
                lg.debug(f"Main: Created thread {threads[i]} at {i} ({threads})")
                break