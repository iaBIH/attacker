import time

class test():
    def __init__(self,doRtnAdd=False):
        self.doRtnAdd = doRtnAdd
        pass

    def delay(self,delay):
        time.sleep(delay)
        if self.doRtnAdd:
            return delay+10000
        else:
            return delay

if __name__ == "__main__":
    pass