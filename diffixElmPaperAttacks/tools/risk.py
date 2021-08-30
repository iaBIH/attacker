import matplotlib.patches as patches
import numpy as np
import pprint
pp = pprint.PrettyPrinter(indent=4)

class riskPatches:
    def __init__(self):
        pass

    def makePolygon(self,left,right,bottom,top):
        height = top-bottom
        width = right-left
        xy = []
        xy.append([left,top])
        xy.append([left,top-(height * 0.85)])
        xy.append([right-(width*0.9996),bottom])
        xy.append([right,bottom])
        xy.append([right,top])
        return np.array(xy)

    def getShapes(self,params):
        p = params
        shapes = []
        if p['toLeft'] != p['fromLeft']:
            factor = 1.14
            next = (p['toLeft'] - p['fromLeft']) / 100
            leftIncs = []
            for _ in range(p['numBoxes']):
                next *= factor
                leftIncs.append(next)
        botInc = (p['toBottom'] - p['fromBottom'])/(p['numBoxes']-1)
        leftNext = p['fromLeft']
        botNext = p['fromBottom']
        for i in range(p['numBoxes']):
            if p['toLeft'] == p['fromLeft']:
                # We want rectangles
                width = p['right'] - leftNext
                height = p['top'] - botNext
                shapes.append(
                    patches.Rectangle((leftNext,botNext),width,height, 
                            alpha=p['alpha'], facecolor="grey")
                )
            else:
                # We want polygon with rounded lower-left corner
                xy = self.makePolygon(leftNext,p['right'],botNext,p['top'])
                shapes.append(
                    patches.Polygon(xy, closed=True,
                            alpha=p['alpha'], facecolor="grey")
                )
                leftNext += leftIncs[i]
            botNext += botInc
        return shapes