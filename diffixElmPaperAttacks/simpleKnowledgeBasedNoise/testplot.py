import matplotlib.pyplot as plt
w = 4
h = 3
d = 70
plt.figure(figsize=(w, h), dpi=d)
x = [[3,2,1],
     [4,3,2],
     [5,4,3]]

x = [
    [0,0,0,0,0,1,2,3,4,5],
    [0,0,0,0,0,1,2,3,4,4],
    [0,0,0,0,0,1,2,3,3,3],
    [0,0,0,0,0,1,2,2,2,2],
    [0,0,0,0,0,1,1,1,1,1],
    [0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0],
]

color_map = plt.imshow(x,interpolation='gaussian',alpha=0.7,cmap='Greys')
#color_map.set_cmap("Greys_r")
#plt.colorbar()

plt.savefig("out.png")