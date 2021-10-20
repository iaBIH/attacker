import time

class test():
    def __init__(self,doRtnAdd=False):
        self.doRtnAdd = doRtnAdd
        pass

    def delay(self,delay):
        time.sleep(delay)
        return {'delay':delay,'doRtnAdd':self.doRtnAdd}

if __name__ == "__main__":
    pass