import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
import sys
import os
filePath = __file__
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import tools.risk
import pprint
pp = pprint.PrettyPrinter(indent=4)

with open('data.json', 'r') as f:
    data = json.load(f)
dfInit = pd.DataFrame.from_dict(data)
df = dfInit.query('`Stat Guess` < 0.9')
df = df.rename(columns={'Stat Guess':'Value Freq.','SDsp':'Setting'})
df['Setting'] = df['Setting'].replace([1.0,1.5,2.0],['P','XP','XXP'])
plt.figure(figsize=(6, 3))
ax = sns.scatterplot(data=df, x="CR", y="CI",style='Value Freq.',hue='Setting',s=80)
ax.set(xscale='log')
params = {
    'numBoxes':20,
    'fromLeft':0.0008,
    'toLeft':0.008,
    'fromBottom':0.45,
    'toBottom':0.7,
    'right':2.0,
    'top':1.1,
    'alpha':0.03,
    #'alpha':0.5,
}
rp = tools.risk.riskPatches()
shapes = rp.getShapes(params)
plt.xlabel('Claim Rate (CR)',fontsize=12)
plt.ylabel('Confidence Improvement (CI)',fontsize=12)
ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.5), ncol=2)
plt.grid()
for shape in shapes:
    plt.gca().add_patch(shape)
plt.savefig('sim-know-suppress.png',bbox_inches='tight')
