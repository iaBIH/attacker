import random
import matplotlib.pyplot as plt

for a,b in [(2,2),(2,4),(2,8)]:
    print(a,b)
    points = []
    for i in range(1000):
        points.append(random.betavariate(a,b))
    points.sort()
    print(points[-5:])
    plt.plot(points)
    plt.show()