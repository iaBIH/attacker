import random
import matplotlib.pyplot as plt

for a,b in [(2,4),(2,16),(2,32)]:
    print(a,b)
    points = []
    for i in range(1000):
        points.append(random.betavariate(a,b))
    points = [(x*1000)+1 for x in points]
    points.sort()
    print(points[-5:])
    plt.plot(points,'o')
    #plt.xlabel(f"Alpha = {a}, Beta = {b}",fontsize=12)
    plt.show()