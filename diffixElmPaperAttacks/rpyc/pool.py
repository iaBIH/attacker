import time
import json
import os.path
import rpyc
import random

class machineClass():
    ''' State of one machine
    '''
    def __init__(self,host,port):
        self.host = host
        self.port = port
        self.conn = None
        self.ref = None
        if port:
            self.conn = rpyc.classic.connect(self.host,self.port)

class pool():
    ''' Used to find available rpyc instances. 
        This code assume that this class is only ever called once at a time
    '''
    def __init__(self,runLocal=False):
        if runLocal:
            self.machines = [{'host':'local','port':0}]
            return
        if os.path.exists('poolConfig.json'):
            with open('poolConfig.json', 'r') as f:
                self.machines = json.load(f)
        else:
            self.machines = []
            for host in ['paul01','paul02','paul03','paul04','paul05','paul06',
                         'paul07','paul08','paul09']:
                for port in range(20000,20020):
                    self.machines.append({'host':host,'port':port})
        random.shuffle(self.machines)
        self.inUse = []

    def getFreeMachine(self):
        if len(self.machines) > 0:
            # get a never-used machine
            machine = self.machines.pop()
            mc = machineClass(machine['host'],machine['port'])
            return mc
        return None

    def getNextResult(self):
        ''' Blocks until some machine completes computation
        '''
        if len(self.inUse) == 0:
            return None,None
        while True:
            for i in range(len(self.inUse)):
                if self.inUse[i].res:
                    # not local machine
                    if self.inUse[i].res.ready:
                        mc = self.inUse.pop(i)
                        return mc,mc.res.value
                else:
                    # local machine
                    mc = self.inUse.pop(i)
                    return mc,None

    def registerJob(self,mc,res):
        mc.res = res
        self.inUse.append(mc)

if __name__ == "__main__":
    pm = pool()
    #print(pm.machines)
    numFinished = 0
    for i in range(500):
        mc = pm.getFreeMachine()
        if not mc:
            mc,result = pm.getNextResult()
            numFinished += 1
            print(f"finished job with result {result}, num finished {numFinished}")
        if not mc:
            print("All Done!")
        # Do job
        asleep = rpyc.async_(mc.conn.modules.time.sleep)
        delay = random.randint(5,15)
        res = asleep(delay)
        pm.registerJob(mc,res)
        print(f"Start job {i} with delay {delay} ({mc.host}, {mc.port})")
    while True:
        mc,result = pm.getNextResult()
        numFinished += 1
        if mc:
            print(f"finished job with result {result}, num finished {numFinished}")
        else:
            print("All Done!")
            break