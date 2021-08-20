import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
import pprint
pp = pprint.PrettyPrinter(indent=4)

with open('data.json', 'r') as f:
    data = json.load(f)
for k,v in data.items():
    print(k)
df = pd.DataFrame.from_dict(data)
df = df.rename(columns={'Stat Guess':'Value Freq.'})
df['SDsp'] = df['SDsp'].replace([1.0,1.5,2.0],['P','XP','XXP'])
df = df.rename(columns={'Stat Guess':'Value Freq.','SDsp':'Setting'})
plt.figure(figsize=(6, 3))
ax = sns.scatterplot(data=df, x="CR", y="CI",style='Value Freq.',hue='Setting',s=80)
ax.set(xscale='log')
left, bottom, width, height = (0.001, 0.5, 2, 2)
rect=patches.Rectangle((left,bottom),width,height, 
                        alpha=0.2,
                       facecolor="grey")
plt.xlabel('Claim Rate (CR)',fontsize=12)
plt.ylabel('Confidence Improvement (CI)',fontsize=12)
ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.5), ncol=2)
plt.grid()
plt.gca().add_patch(rect)
plt.savefig('sim-know-suppress.png',bbox_inches='tight')
