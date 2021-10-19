import rpyc
import random
import pool

if __name__ == "__main__":
    pm = pool.pool()
    #print(pm.machines)
    numFinished = 0
    for i in range(500):
        mc = pm.getFreeMachine()
        if not mc:
            mc,result = pm.getNextResult()
            numFinished += 1
            print(f"finished job {mc['state']} with result {result}, num finished {numFinished}")
        if not mc:
            print("All Done!")
        # Do job
        asleep = rpyc.async_(mc.conn.modules.time.sleep)
        delay = random.randint(5,15)
        res = asleep(delay)
        pm.registerJob(mc,res,state=i)
        print(f"Start job {i} with delay {delay} ({mc.host}, {mc.port})")
    while True:
        mc,result = pm.getNextResult()
        numFinished += 1
        if mc:
            print(f"finished job {mc['state']} with result {result}, num finished {numFinished}")
        else:
            print("All Done!")
            break