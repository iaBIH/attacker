import rpyc
import time

if __name__ == "__main__":
    c2 = rpyc.classic.connect("paul02",port=20000)
    c1 = rpyc.classic.connect("paul02",port=20001)
    # try without async
    rtest2 = c2.modules.test.test
    test2 = rtest2()
    result2 = test2.getResultWithSleep(1)
    print(f"Result, no async, should be 0: {result2}")
    test2.add(5)
    result = test2.getResultWithSleep(1)
    print(f"Result, no async, should be 5: {result}")
    rtest1 = c1.modules.test.test
    test1 = rtest1()
    test1.subtract(5)
    result1 = test1.getResultWithSleep(1)
    print(f"Result, no async, should be -5: {result1}")
    # try with async
    test1 = rtest1()
    a_add1 = rpyc.async_(test1.add)
    a_subtract1 = rpyc.async_(test1.subtract)
    a_result1 = rpyc.async_(test1.getResultWithSleep)
    test2 = rtest2()
    a_add2 = rpyc.async_(test2.add)
    a_subtract2 = rpyc.async_(test2.subtract)
    a_result2 = rpyc.async_(test2.getResultWithSleep)
    a_subtract1(5)
    a_add2(8)
    res1 = a_result1(5)
    res2 = a_result2(8)
    res1Done = False
    res2Done = False
    while True:
        if not res1Done and res1.ready:
            result1 = res1.value
            print(f"Result1, no async, should be -5: {result1}")
            res1Done = True
        if not res2Done and res2.ready:
            result2 = res2.value
            print(f"Result2, no async, should be 8: {result2}")
            res2Done = True
        if not res1Done or not res2Done:
            time.sleep(1)
            print('.',end='',flush=True)
        else:
            break