import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import ScalarFormatter
import sys
import os
filePath = __file__
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
sys.path.append(parDir)
import pprint
pp = pprint.PrettyPrinter(indent=4)

with open('data.json', 'r') as f:
    data = json.load(f)
df = pd.DataFrame.from_dict(data)
plt.figure(figsize=(6, 2))
#ax = sns.scatterplot(data=df, x="Samples", y="Accuracy",hue='SD',s=80)
ax = sns.lineplot(data=df, x="Samples", y="Accuracy",hue='SD',style='SD',
                  markers=True,dashes=False,markersize=8)
plt.xlabel('Number of Samples Needed',fontsize=12)
plt.ylabel('Confidence',fontsize=12)
plt.xlim(10,500)
plt.ylim(0.945,1.005)
ax.set(xscale='log')
ax.xaxis.set_major_formatter(ScalarFormatter())
xticks = [10, 20, 50, 100, 200, 500]
ax.set_xticks(xticks)
yticks = [0.95,0.99,0.999]
ax.set_yticks(yticks)
ax.legend(title='Total SD',loc='lower center', bbox_to_anchor=(0.9, 0), ncol=1)
plt.grid()
plt.savefig('samples-needed.png',bbox_inches='tight')
