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

with open('betaData.json', 'r') as f:
    data = json.load(f)
df = pd.DataFrame.from_dict(data)
df['alphbet'] = df['alphbet'].apply(str)
df['outParams'] = df['outParams'].apply(str)

plt.figure(figsize=(6, 3))
ax = sns.scatterplot(data=df, x="CR", y="CI",hue='numUnknownVals',style='alphbet',s=80)
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
ax.legend(loc='upper center', bbox_to_anchor=(0.6, 1.0), ncol=2)
plt.grid()
plt.ylim(0,1.0)
for shape in shapes:
    plt.gca().add_patch(shape)
plt.savefig('beta-outlier.png',bbox_inches='tight')

with open('data.json', 'r') as f:
    data = json.load(f)
df = pd.DataFrame.from_dict(data)
df['CR'] = pd.to_numeric(df['CR'])
df['CI'] = pd.to_numeric(df['CI'])
df['C'] = pd.to_numeric(df['C'])
df['Num Outliers'] = df['Num Outliers'].apply(str)

plt.figure(figsize=(6, 3))
ax = sns.scatterplot(data=df, x="CR", y="CI",hue='Out Factor',style='setting',s=80)
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
ax.legend(loc='lower left', bbox_to_anchor=(1.0, 0.0), ncol=1)
plt.grid()
for shape in shapes:
    plt.gca().add_patch(shape)
plt.ylim(0,1.1)
plt.xlim(0.000001,2.0)
plt.savefig('worst-outlier.png',bbox_inches='tight')

plt.figure(figsize=(6, 3))
ax = sns.scatterplot(data=df, x="CR", y="CI",hue='Out Factor',style='setting',s=80)
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
ax.legend(loc='lower left', bbox_to_anchor=(1.0, 0.0), ncol=1)
plt.grid()
for shape in shapes:
    plt.gca().add_patch(shape)
plt.ylim(0.94,1.02)
plt.xlim(0.001,1.0)
plt.savefig('worst-outlier-close.png',bbox_inches='tight')
