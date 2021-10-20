import sys
import os
import json
import pprint
import rpyc
filePath = __file__
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import rpycTools.pool
import diffAttack.diffAttackClass
import tools.score

'''
This code is for both the classic difference attack (positive AND), and
before/after difference attacks that exploit changes in the table. Which
attack is run is determined by configuring `attackType`
'''

# If True, execute on the local machine, one attack at a time
# If False, execute over the cluster using rpyc
runLocal = True

def dataInit():
    return {'numUnknownVals':[],'numSamples':[],'numIsolated':[],'SD':[],'attackType':[],'round':[],
            'CR':[],'CI':[],'C':[],'claimThresh':[], 'PCR':[],'PCI':[],'PC':[]}

def dataUpdate(data,params,results):
    for param,val in params.items():
        data[param].append(val)
    for result,val in results.items():
        data[result].append(val)

def alreadyHaveData(data,params):
    for i in range(len(data['SD'])):
        match = True
        for param in params.keys():
            if data[param][i] != params[param]:
                match = False
                break
        if match == True:
            return True
    return False

def paramsAlreadySatisfied(round,params):
    paramsCopy = params.copy()
    for r in range(round):
        paramsCopy['round'] = r
        for i in range(len(data['SD'])):
            match = True
            for param,val in paramsCopy.items():
                if data[param][i] != val:
                    match = False
                    break
            if match == True:
                cr = data['CR'][i]
                ci = data['CI'][i]
                if ci >= 0.95 or cr < 0.0001:
                    return True
    return False

def recordResult(data,dataFile,params,result):
    print(f"Record result:",flush=True)
    pp.pprint(params)
    pp.pprint(result)
    dataUpdate(data,params,result)
    with open(dataFile, 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True)
        
if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=4)
    tries=100000
    #tries=100
    atLeast=100
    #atLeast=10
    claimThresh = None
    sds = [1.5,2.25,3.0]
    sds = [2.25]
    unkn = [2,5,20]
    unkn = [5]
    numSamples = [1]
    numIsolated = [0]
    if False:
        # Classic difference attack
        attackType = 'diffAttack'
        dataFile = 'dataDiff.json'
    elif False:
        # Difference attack based on table change (salt changes too)
        attackType = 'changeDiffAttack'
        dataFile = 'dataChangeDiff.json'
    elif False:
        # Difference attack based on table change and averaging (salt changes too)
        attackType = 'changeAvgAttack'
        dataFile = 'dataChangeAvg.json'
        numSamples = [2,5,10,20]
        sds = [2.25]
        unkn = [5]
    else:
        # Classic difference attack with LED-lite
        attackType = 'diffAttackLed'
        dataFile = 'dataDiffLed.json'
        numIsolated = [3,2,4]
        numIsolated = [3]
    if os.path.exists(dataFile):
        with open(dataFile, 'r') as f:
            data = json.load(f)
    else:
        # Following are for plotting
        data = dataInit()
    if runLocal:
        att = diffAttack.diffAttackClass.diffAttack()
    pm = rpycTools.pool.pool(runLocal=runLocal)
    claimThresholds = [None,1.5]
    maxRound = 200
    maxRound = 5
    for i in range(2,maxRound):
        claimThresholds.append(claimThresholds[i-1]+1)
    # We work in rounds, increasing the threshold as we go, starting with
    # no threshold at all, until we get CI>0.95 or CR>0.0001
    for round in range(len(claimThresholds)):
        roundComplete = True
        for numIso,sd,numUnknownVals,samples in [(w,x,y,z) for w in numIsolated for x in sds for y in unkn for z in numSamples]:
            claimThresh = claimThresholds[round]
            params = {
                'numUnknownVals': numUnknownVals,
                'SD': sd,
                'attackType': attackType,
                'numSamples': samples,
                'numIsolated': numIso,
                'round': round,
            }
            if paramsAlreadySatisfied(round,params):
                print(f"Params already satisfied",flush=True)
                pp.pprint(params)
                continue
            # Ok, we still have work to do
            roundComplete = False
            if alreadyHaveData(data,params):
                print(f"Already have data for this run",flush=True)
                pp.pprint(params)
                continue
            if runLocal:
                # Each unknown value happens with equal probability
                s = tools.score.score(1/numUnknownVals)
                print(f"Run attack, claimThresh {claimThresh}:",flush=True)
                pp.pprint(params)
                result = att.basicAttack(s,params,claimThresh,tries=tries,atLeast=atLeast)
                recordResult(data,dataFile,params,result)
            else:
                mc = pm.getFreeMachine()
                if not mc:
                    # Block on some job finishing
                    print("------------------------------- Wait for a job to finish",flush=True)
                    mc,result = pm.getNextResult()
                    recordResult(data,dataFile,params,result)
                attackClass = mc.conn.modules.diffAttackClass.diffAttack
                mcAttack = attackClass(doLog=True)
                basicAttack = rpyc.async_(mcAttack.basicAttack)
                s = tools.score.score(1/numUnknownVals)
                res = basicAttack(s,params,claimThresh,tries=tries,atLeast=atLeast)
                pm.registerJob(mc,res,state=params)
                print(f"Start job with ({mc.host}, {mc.port})",flush=True)
                pp.pprint(params)
        if roundComplete:
            break
    print("Wait for remaining jobs to complete")
    while True:
        mc,result = pm.getNextResult()
        if mc:
            recordResult(data,dataFile,params,result)
        else:
            break

    with open(dataFile, 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True)

'''
Left query has gender, so female excluded from all male buckets
right query does not have gender, so female included in some male bucket

When all victims have the same unknown val, then LED happens and there is
no difference left/right. We don't need to measure this.

When all victims in the same bucket, then we do LED. When they are in different
buckets, then we won't do LED. 

So make X females, and assign one as victim. Assign them to buckets.
If all same bucket, then we can shortcut and don't assign them anywhere.
If different at all, then add them all to right buckets.
'''