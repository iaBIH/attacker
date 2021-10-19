import sys
import os
import json
import pprint
from tabulate import tabulate
filePath = __file__
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import diffAttack.attackClass
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
    return {'Unknown Vals':[],'Samples':[],'Num Isolated':[],'SD':[],'CR':[],'CI':[],'highCR':[]}

def dataUpdate(data,vals):
    data['Unknown Vals'].append(vals[0])
    data['Samples'].append(vals[1])
    data['Num Isolated'].append(vals[2])
    data['SD'].append(vals[3])
    data['CR'].append(vals[4])
    data['CI'].append(vals[5])
    data['C'].append(vals[6])
    data['highCR'].append(vals[7])

def alreadyHaveData(data,vals):
    for i in range(len(data['SD'])):
        if ( data['Unknown Vals'][i] == vals[0] and
             data['Samples'][i] == vals[1] and
             data['Num Isolated'][i] == vals[2] and
             data['SD'][i] == vals[3] and
             data['highCR'][i] == vals[4]):
             return True
    return False
        
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
    # Following are for tabulate
    results = []
    headers = ['vals','samp','isolated','SD','CR','CI','C']
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
    if os.path.exists(dataFile):
        with open(dataFile, 'r') as f:
            data = json.load(f)
    else:
        # Following are for plotting
        data = dataInit()
    if runLocal:
        att = diffAttack.attackClass.diffAttack()
    else:
        import rpyc.pool
        pm = rpyc.pool.pool()
    print("The following are for full claim rate (CR=1.0)",flush=True)
    highCR = 1
    for numIso,sd,numUnknownVals,samples in [(w,x,y,z) for w in numIsolated for x in sds for y in unkn for z in numSamples]:
        if alreadyHaveData(data,[numUnknownVals,samples,numIso,sd,highCR]):
            print(f"Already have numUnknown {numUnknownVals}, samples {samples}, sd {sd}, high {highCR}",flush=True)
            continue
        if runLocal:
            # We assume that each unknown value happens with equal probaiblity
            s = tools.score.score(1/numUnknownVals)
            params = {
                'numUnknownVals': numUnknownVals,
                'sd': sd,
                'attackType': attackType,
                'numSamples': samples,
                'numIsolated': numIso,
            }
            print(f"Run attack, claimThresh {claimThresh}:")
            pp.pprint(params)
            cr,ci,c,pcr,pci,pc = att.basicAttack(s,params,claimThresh,tries=tries,atLeast=atLeast)
        results.append([numUnknownVals,samples,numIso,sd,pcr,pci,pc,])
        dataUpdate(data,[numUnknownVals,samples,numIso,sd,cr,ci,c,highCR])
        print(tabulate(results,headers,tablefmt='latex_booktabs'),flush=True)
        print(tabulate(results,headers,tablefmt='github'),flush=True)
        with open(dataFile, 'w') as f:
            json.dump(data, f, indent=4, sort_keys=True)

    # Now we compute claim rate given goal of CI=0.95
    results = []

    print("\nThe following attempts to find the Claim Rate when CI is high (> 0.95)",flush=True)
    highCR = 0
    for numIso,sd,numUnknownVals,samples in [(w,x,y,z) for w in numIsolated for x in sds for y in unkn for z in numSamples]:
        if alreadyHaveData(data,[numUnknownVals,samples,numIso,sd,highCR]):
            print(f"Already have numUnknown {numUnknownVals}, samples {samples}, sd {sd}, high {highCR}",flush=True)
            continue
        print(f"sd {sd}, numUnknown {numUnknownVals}",flush=True)
        claimThresh = -0.5
        while True:
            claimThresh += 1.0
            # We assume that each unknown value happens with equal probaiblity
            s = tools.score.score(1/numUnknownVals)
            params = {
                'numUnknownVals': numUnknownVals,
                'sd': sd,
                'attackType': attackType,
                'numSamples': samples,
                'numIsolated': numIso,
            }
            print(f"Run attack, claimThresh {claimThresh}:")
            pp.pprint(params)
            cr,ci,c,pcr,pci,pc = att.basicAttack(s,params,claimThresh,tries=tries,atLeast=atLeast)
            print(f"claimThresh {claimThresh}, cr {pcr}, ci {pci}, c {pc}",flush=True)
            # We want to achieve a CI of at least 95%, but we won't go
            # beyond CR of 0.0001 to get it.
            if ci >= 0.95 or cr < 0.0001:
                results.append([numUnknownVals,samples,numIso,sd,pcr,pci,pc,])
                dataUpdate(data,[numUnknownVals,samples,numIso,sd,cr,ci,c,highCR])
                print(tabulate(results,headers,tablefmt='latex_booktabs'),flush=True)
                print(tabulate(results,headers,tablefmt='github'),flush=True)
                with open(dataFile, 'w') as f:
                    json.dump(data, f, indent=4, sort_keys=True)
                break
    print(tabulate(results,headers,tablefmt='latex_booktabs'),flush=True)
    print(tabulate(results,headers,tablefmt='github'),flush=True)

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