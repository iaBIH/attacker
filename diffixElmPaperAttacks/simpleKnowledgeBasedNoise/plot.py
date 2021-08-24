import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
import pprint
pp = pprint.PrettyPrinter(indent=4)

with open('data.json', 'r') as f:
    data = json.load(f)
dfInit = pd.DataFrame.from_dict(data)
df = dfInit.query('SD > 0.5')
df = df.rename(columns={'Stat Guess':'Value Freq.'})
df['SD'] = df['SD'].replace([1.0,2.0,3.0],['1.0 (P)','2.0 (XP)','3.0 (XXP)'])
#df['SD'] = df['SD'].astype(str)
plt.figure(figsize=(6, 3))
x = [
    [0,0.0,0.0,0.0,0.0,0.1,0.2,0.3,0.4,0.5],
    [0,0.0,0.0,0.0,0.0,0.1,0.2,0.3,0.4,0.4],
    [0,0.0,0.0,0.0,0.0,0.1,0.2,0.3,0.3,0.3],
    [0,0.0,0.0,0.0,0.0,0.1,0.2,0.2,0.2,0.2],
    [0,0.0,0.0,0.0,0.0,0.1,0.1,0.1,0.1,0.1],
    [0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0],
    [0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0],
    [0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0],
    [0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0],
    [0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0],
]
#plt.imshow(x,interpolation='gaussian',alpha=0.7,cmap='Greys',
             #extent=[0.000001,1.1,0,1.1])
ax = sns.scatterplot(data=df, x="CR", y="CI",style='Value Freq.',hue='SD',s=80)
ax.set(xscale='log')
plt.xlabel('Claim Rate (CR)',fontsize=12)
plt.ylabel('Confidence Improvement (CI)',fontsize=12)
ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.5), ncol=2)
plt.grid()
plt.savefig('sim-know-noise.png',bbox_inches='tight')
