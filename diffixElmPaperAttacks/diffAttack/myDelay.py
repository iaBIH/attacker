import time
import random

class test():
    def __init__(self,doLog=False):
        self.doLog = doLog
        if doLog:
            self.f = open('/root/paul/logs/out.txt','a')
            self.f.write("\n------------------------\nStarting class myDelay/test\n")
            self.f.flush()
            pass
        pass

    def delay(self,delay):
        x = 0
        while x < 100:
            # This is just to see what happens when the processes fully utilize the CPU
            # (The answer is that each process is indeed assigned one CPU.)
            for _ in range(100):
                boo = [random.randint(1000,100000) for i in range(10000)]
                boo.sort()
            if self.doLog:
                self.f.write(f"x {x}\n")
                x += 1
                self.f.flush()
        if self.doLog:
            self.f.write(f"Received delay request: delay {delay}\n")
        time.sleep(delay)
        if self.doLog:
            self.f.write(f"    Finished delay: delay {delay}\n")
        return {'delay':delay,'doLog':self.doLog}

if __name__ == "__main__":
    pass