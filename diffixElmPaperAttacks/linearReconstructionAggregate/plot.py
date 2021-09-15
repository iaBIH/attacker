import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import os
filePath = __file__
print(filePath)
parDir = os.path.abspath(os.path.join(filePath, os.pardir, os.pardir))
print(parDir)
sys.path.append(parDir)
import tools.risk
import tools.results
import pprint
pp = pprint.PrettyPrinter(indent=4)

rg = tools.results.resultGatherer()
dfAll,dfAgg = rg.gatherResults()

dfTemp = dfAll.query("a_lab != 'None'")
dfTemp = dfTemp.query("a_pri != 'all'")
dfNone = dfTemp.query("a_pri == 'none'")
dfHalf = dfTemp.query("a_pri == 'half'")
dfNear = dfTemp.query("a_pri == 'all-but-one'")

dfTemp = dfAgg.query("a_lab != 'None'")
dfTemp = dfTemp.query("a_pri != 'all'")
dfAggNone = dfTemp.query("a_pri == 'none'")
dfAggHalf = dfTemp.query("a_pri == 'half'")
dfAggNear = dfTemp.query("a_pri == 'all-but-one'")

dfNone1 = dfNone.query('a_lab in ["P","XP","XXP"]')
dfNone1 = dfNone1.rename(columns={'a_lab':'Setting'})
plt.figure(figsize=(6, 3))
ax = sns.scatterplot(data=dfNone1, x="s_cr", y="s_ci",hue='Setting')
params = {
    'numBoxes':20,
    'fromLeft':0,
    'toLeft':0,
    'fromBottom':0.45,
    'toBottom':0.7,
    'right':0.7,
    'top':1.1,
    'alpha':0.03,
    #'alpha':0.5,
}
rp = tools.risk.riskPatches()
shapes = rp.getShapes(params)
plt.xlabel('Claim Rate (CR)',fontsize=12)
plt.ylabel('Confidence Improvement (CI)',fontsize=12)
plt.xlim(0,0.7)
plt.grid()
for shape in shapes:
    plt.gca().add_patch(shape)
plt.savefig('lr-agg-plot-no-avg.png',bbox_inches='tight')



dfAgg1 = dfAggNone.query('a_lab in ["P","XP","XXP"]')
dfAgg1 = dfAgg1.rename(columns={'a_lab':'Setting'})
plt.figure(figsize=(6, 3))
ax = sns.scatterplot(data=dfAgg1, x="s_cr_av", y="s_ci_av",hue='Setting')
params = {
    'numBoxes':20,
    'fromLeft':0.18,
    'toLeft':0.18,
    'fromBottom':0.45,
    'toBottom':0.7,
    'right':0.55,
    'top':1.1,
    'alpha':0.03,
    #'alpha':0.5,
}
rp = tools.risk.riskPatches()
shapes = rp.getShapes(params)
plt.ylim(0,1)
plt.xlim(0.18,0.55)
#plt.xlim(0,1)
plt.xlabel('Claim Rate (CR)',fontsize=12)
plt.ylabel('Confidence Improvement (CI)',fontsize=12)
plt.grid()
for shape in shapes:
    plt.gca().add_patch(shape)
ax.legend(loc='upper right')
plt.savefig('lr-agg-plot.png',bbox_inches='tight')



dfAgg1 = dfAggNone.query('a_lab in ["P","XP","XXP"]')
dfAgg1 = dfAgg1.rename(columns={'t_shape':'Table Shape'})
plt.figure(figsize=(6, 3))
ax = sns.scatterplot(data=dfAgg1, x="s_cr_av", y="s_ci_av",hue='Table Shape')
params = {
    'numBoxes':20,
    'fromLeft':0.18,
    'toLeft':0.18,
    'fromBottom':0.45,
    'toBottom':0.7,
    'right':0.55,
    'top':1.1,
    'alpha':0.03,
    #'alpha':0.5,
}
rp = tools.risk.riskPatches()
shapes = rp.getShapes(params)
plt.ylim(0,1)
plt.xlim(0.18,0.55)
plt.xlabel('Claim Rate (CR)',fontsize=12)
plt.ylabel('Confidence Improvement (CI)',fontsize=12)
plt.grid()
for shape in shapes:
    plt.gca().add_patch(shape)
ax.legend(loc='upper right')
plt.savefig('lr-agg-plot-table.png',bbox_inches='tight')





dfTemp = dfAgg.query('a_lab in ["P","XP","XXP"]')
dfTemp = dfTemp.query("a_pri != 'all'")
dfTemp = dfTemp.rename(columns={'a_lab':'Setting','a_pri':'Prior Knowledge'})
plt.figure(figsize=(6, 3))
ax = sns.scatterplot(data=dfTemp, x="s_cr_av", y="s_ci_av",hue='Prior Knowledge',style='Setting')
params = {
    'numBoxes':20,
    'fromLeft':0.05,
    'toLeft':0.05,
    'fromBottom':0.45,
    'toBottom':0.7,
    'right':1.05,
    'top':1.1,
    'alpha':0.03,
    #'alpha':0.5,
}
rp = tools.risk.riskPatches()
shapes = rp.getShapes(params)
plt.ylim(-0.05,1)
plt.xlim(0.1,1.05)
plt.xlabel('Claim Rate (CR)',fontsize=12)
plt.ylabel('Confidence Improvement (CI)',fontsize=12)
plt.grid()
for shape in shapes:
    plt.gca().add_patch(shape)
ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.5), ncol=2)
plt.savefig('lr-agg-plot-all-pri.png',bbox_inches='tight')