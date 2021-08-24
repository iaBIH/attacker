import matplotlib.patches as patches
import numpy as np
import pprint
pp = pprint.PrettyPrinter(indent=4)

class riskPatches:
    def __init__(self):
        pass

    def getRectangles(self,params):
        p = params
        rectangles = []
        leftInc = (p['toLeft'] - p['fromLeft'])/(p['numBoxes']-1)
        botInc = (p['toBottom'] - p['fromBottom'])/(p['numBoxes']-1)
        leftNext = p['fromLeft']
        botNext = p['fromBottom']
        for _ in range(p['numBoxes']):
            width = p['right'] - leftNext
            height = p['top'] - botNext
            rectangles.append(
                patches.Rectangle((leftNext,botNext),width,height, 
                        alpha=p['alpha'], facecolor="grey")
            )
            leftNext += leftInc
            botNext += botInc
        return rectangles