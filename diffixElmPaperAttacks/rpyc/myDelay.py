import time

class test():
    def __init__(self):
        pass

    def delay(self,delay): # this is an exposed method
        time.sleep(delay)
        return delay+1

if __name__ == "__main__":
    pass