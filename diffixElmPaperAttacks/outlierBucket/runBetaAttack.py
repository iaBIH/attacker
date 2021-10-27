import sys
import os
import json
import pprint
import rpyc
from pathlib import Path
filePath = os.path.abspath(__file__)
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import rpycTools.pool
import outlierBucket.betaAttackClass
import tools.dataHandler

'''
Script for running outlier attack using beta distributions
'''

# If True, execute on the local machine, one attack at a time
# If False, execute over the cluster using rpyc
runLocal = False

def recordResult(dh,params,result):
    print(f"Record result:",flush=True)
    pp.pprint(params)
    pp.pprint(result)
    dh.dataUpdate(params,result)
    dh.saveData()

def doJob(params,claimThresh):
    round = params['round']
    if dh.paramsAlreadySatisfied(round,params):
        print(f"Params already satisfied",flush=True)
        pp.pprint(params)
        return
    # Ok, we still have work to do
    if dh.alreadyHaveData(params):
        print(f"Already have data for this run",flush=True)
        pp.pprint(params)
        return
    scoreProb = 1/params['numUnknownVals']
    if runLocal:
        # Each unknown value happens with equal probability
        print(f"Run attack, claimThresh {claimThresh}:",flush=True)
        pp.pprint(params)
        result = att.basicAttack(scoreProb,json.dumps(params),claimThresh,tries=tries,atLeast=atLeast)
        recordResult(dh,params,result)
    else:
        mc = pm.getFreeMachine()
        if not mc:
            # Block on some job finishing
            print("------------------------------- Wait for a job to finish",flush=True)
            mc,result = pm.getNextResult()
            recordResult(dh,mc.state,result)
        attackClass = mc.conn.modules.betaAttackClass.betaAttack
        mcAttack = attackClass()
        basicAttack = rpyc.async_(mcAttack.basicAttack)
        res = basicAttack(scoreProb,json.dumps(params),claimThresh,tries=tries,atLeast=atLeast)
        pm.registerJob(mc,res,state=params)
        print(f"Start job with ({mc.host}, {mc.port})",flush=True)
        pp.pprint(params)

if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=4)
    tries=10000
    #tries=100
    atLeast=100
    #atLeast=10
    claimThresh = None
    sds = [1.5,2.25,3.0]
    sds = [2.25]
    outs = [[[1,2],[2,3]],
            [[2,3],[3,4]],
            [[3,4],[4,5]]
           ]
    abs = [[2,2],[2,4],[2,8]]
    numValues = [2,5,20]
    params = ['numUnknownVals','SD','outParams','alphbet','round']
    results = ['CR','CI','C','claimThresh','PCR','PCI','PC','excess','numCLaimHas']
    pathParts = Path(os.path.abspath(__file__)).parts
    dataDir = pathParts[-2]
    dataFile = 'betaData'
    dh = tools.dataHandler.dataHandler(params,results,dataDir,dataFile)
    print(f"data file at '{dh.dataFile}'")
    print(f"output print at '{dh.printFile}'")
    dh.addSatisfyCriteria('CI',0.95,'gt')
    dh.addSatisfyCriteria('CR',0.0001,'lt')
    if runLocal:
        att = outlierBucket.betaAttackClass.betaAttack()
    hostsAndPorts = [
                {'host':'paul03', 'portLow':20000, 'portHigh':20019},
                {'host':'paul04', 'portLow':20000, 'portHigh':20019},
                {'host':'paul04', 'portLow':20000, 'portHigh':20019},
                {'host':'paul05', 'portLow':20000, 'portHigh':20019},
                {'host':'paul06', 'portLow':20000, 'portHigh':20019},
                {'host':'paul07', 'portLow':20000, 'portHigh':20019},
                {'host':'paul08', 'portLow':20000, 'portHigh':20019},
                {'host':'paul09', 'portLow':20000, 'portHigh':20019},
    ]
    pm = rpycTools.pool.pool(hostsAndPorts=hostsAndPorts,runLocal=runLocal)
    ''' The 0th round has no claim threshold (claimThresh=None). The 1st round starts with
        claimThresh=1, and then subsequent rounds set claimThresh based on the value of the
        prior one. Which unfortunately means that we need to wait for the prior round to
        finish before we can start the next round
    '''
    claimThresholds = [None,1]
    # Kick off the first two rounds.
    for round in range(len(claimThresholds)):
        for numVals,sd,outParams,alphbet in [(v,w,x,y) for v in numValues for w in sds for x in outs for y in abs]:
            params = {
                'numUnknownVals': numVals,
                'SD': sd,
                'outParams': outParams,
                'alphbet': alphbet,
                'round': round,
            }
            claimThresh = claimThresholds[round]
            doJob(params,claimThresh)
    if runLocal:
        # TODO: code this up
        pass
    else:
        while True:
            mc,result = pm.getNextResult()
            if mc:
                recordResult(dh,mc.state,result)
                params = mc.state.copy()
                params['round'] += 1
                round = params['round']
                # doJob naturally does nothing if the conditions are satisfied
                # otherwise it starts a new remote attack job
                # zzzz we need the last claimthresh!
                claimThresh = result['claimThresh'] * 1.1
                doJob(params,claimThresh)
                if dh.paramsAlreadySatisfied(round,params):
                    print(f"Params already satisfied",flush=True)
                    pp.pprint(params)
                    continue
            else:
                break
    # Probably not necessary, but...
    dh.saveData()