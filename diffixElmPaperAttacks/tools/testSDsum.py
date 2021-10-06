import math
import statistics
import random
'''
This just checks to make sure that 
sdLayer = math.sqrt((sd**2)/N)
and
sdLayer = sd / sqrt(N)
are the same, and that both give the stats I expect
'''

for N in [2,3,5,9]:
    for sd in [2,3,4]:
        base = []
        layered = []
        sdl1 = round(math.sqrt((sd**2)/N),5)
        sdl2 = round(sd / math.sqrt(N),5)
        if sdl1 != sdl2:
            print(f"boo boo {sd}, {N}, {sdl1}, {sdl2}")
            quit()
        for _ in range(100000):
            base.append(random.gauss(0,sd))
            noise = 0
            for _ in range(N):
                noise += random.gauss(0,sdl1)
            layered.append(noise)
        sdBase = round(statistics.stdev(base),2)
        sdLayered = round(statistics.stdev(layered),2)
        print(f"sd = {sd}, N = {N}")
        print(f"    base sd = {sdBase}, layered sd = {sdLayered}")

