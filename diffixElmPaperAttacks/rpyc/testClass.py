import time

class test():
    def __init__(self):
        self.sum = 0

    def add(self,num): # this is an exposed method
        self.sum += num

    def subtract(self,num): # this is an exposed method
        self.sum -= num

    def getResultWithSleep(self,seconds):  # while this method is not exposed
        time.sleep(seconds)
        return self.sum

if __name__ == "__main__":
    pass