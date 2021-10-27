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
import tools.dataHandler

'''
This code is for both the classic difference attack (positive AND), and
before/after difference attacks that exploit changes in the table. Which
attack is run is determined by configuring `attackType`
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
        
if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=4)
    tries=100000
    #tries=100
    atLeast=100
    #atLeast=10
    claimThresh = None
    sds = [1.5,2.25,3.0]
    unkn = [2,5,20]
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
    elif True:
        # Difference attack based on table change and averaging (salt changes too)
        attackType = 'changeAvgAttack'
        dataFile = 'dataChangeAvg.json'
        numSamples = [2,5,10,20,50]
        sds = [2.25]
        unkn = [5]
    else:
        # Classic difference attack with LED-lite
        attackType = 'diffAttackLed'
        dataFile = 'dataDiffLed.json'
        numIsolated = [3,2,4]
    dataPath = os.path.abspath(os.path.join(filePath, os.pardir, dataFile))
    print(f"Using data at {dataPath}")
    params = ['numUnknownVals','numSamples','numIsolated','SD','attackType','round']
    results = ['CR','CI','C','claimThresh', 'PCR','PCI','PC']
    dh = tools.dataHandler.dataHandler(params,results,dataFile=dataPath)
    dh.addSatisfyCriteria('CI',0.95,'gt')
    dh.addSatisfyCriteria('CR',0.0001,'lt')
    if runLocal:
        att = diffAttack.diffAttackClass.diffAttack()
    pm = rpycTools.pool.pool(runLocal=runLocal)
    claimThresholds = [None,1.5]
    maxRound = 200
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
            if dh.paramsAlreadySatisfied(round,params):
                print(f"Params already satisfied",flush=True)
                pp.pprint(params)
                continue
            # Ok, we still have work to do
            roundComplete = False
            if dh.alreadyHaveData(params):
                print(f"Already have data for this run",flush=True)
                pp.pprint(params)
                continue
            if runLocal:
                # Each unknown value happens with equal probability
                scoreProb = 1/numUnknownVals
                print(f"Run attack, claimThresh {claimThresh}:",flush=True)
                pp.pprint(params)
                # We divide the number of tries by the number of samples so that the
                # runs don't take so long
                result = att.basicAttack(scoreProb,json.dumps(params),claimThresh,
                                         tries=tries/samples,atLeast=atLeast)
                recordResult(dh,params,result)
            else:
                mc = pm.getFreeMachine()
                if not mc:
                    # Block on some job finishing
                    print("------------------------------- Wait for a job to finish",flush=True)
                    mc,result = pm.getNextResult()
                    recordResult(dh,mc.state,result)
                attackClass = mc.conn.modules.diffAttackClass.diffAttack
                mcAttack = attackClass(doLog=False)
                basicAttack = rpyc.async_(mcAttack.basicAttack)
                scoreProb = 1/numUnknownVals
                res = basicAttack(scoreProb,json.dumps(params),claimThresh,tries=tries,atLeast=atLeast)
                pm.registerJob(mc,res,state=params)
                print(f"Start job with ({mc.host}, {mc.port})",flush=True)
                pp.pprint(params)
        if roundComplete:
            break
    print("Wait for remaining jobs to complete")
    while True:
        mc,result = pm.getNextResult()
        if mc:
            recordResult(dh,mc.state,result)
        else:
            break

    dh.saveData()

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