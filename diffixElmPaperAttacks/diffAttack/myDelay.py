import time

class test():
    def __init__(self,doLog=False):
        self.doLog = doLog
        if doLog:
            self.f = open('/root/paul/logs/out.txt','a')
            self.f.write("\n------------------------\nStarting class myDelay/test\n")
            pass
        pass

    def delay(self,delay):
        if self.doLog:
            self.f.write(f"Received delay request: delay {delay}\n")
        time.sleep(delay)
        if self.doLog:
            self.f.write(f"    Finished delay: delay {delay}\n")
        return {'delay':delay,'doLog':self.doLog}

if __name__ == "__main__":
    pass