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

rg = tools.results.resultGatherer(attackType='random')
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


df1 = dfAgg.query('t_atkr == "untrusted" and a_pri != "all" and a_lab != "None"')
plt.figure(figsize=(6, 3))
#ax2 = sns.boxplot(x='t_freq',y='s_ci_av',data=df1,hue='a_lab')
ax2 = sns.boxplot(x='a_pri',y='s_ci_av',data=df1,hue='a_lab',order=['none','half','all-but-one'])
ax2.set(ylabel = 'Confidence Improvement (CI)', xlabel='Attacker Prior Knowledge')
ax2.grid(axis='y')
ax2.legend(title='Strength of Anonymity',ncol=3)
ax2.set(xticklabels=["No Rows","Half of Rows","All Rows But One"])
plt.savefig('lr-ran-plot-untrusted',bbox_inches='tight')

df1 = dfAgg.query('t_atkr == "trusted" and a_pri != "all" and a_lab != "None"')
plt.figure(figsize=(6, 3))
ax2 = sns.boxplot(x='a_pri',y='s_ci_av',data=df1,hue='a_lab',order=['none','half','all-but-one'])
params = {
    'numBoxes':20,
    'fromLeft':-1,
    'toLeft':-1,
    'fromBottom':0.45,
    'toBottom':0.7,
    'right':5,
    'top':1.1,
    'alpha':0.03,
    #'alpha':0.5,
}
rp = tools.risk.riskPatches()
shapes = rp.getShapes(params)
ax2.set(ylabel = 'Confidence Improvement (CI)', xlabel='Attacker Prior Knowledge')
ax2.grid(axis='y')
ax2.set(xticklabels=["No Rows","Half of Rows","All Rows But One"])
#ax2.legend(title='Strength of Anonymity',loc='lower left',ncol=3)
ax2.legend(title='Strength of Anonymity',loc='lower left', bbox_to_anchor=(0,0), ncol=3)
for shape in shapes:
    plt.gca().add_patch(shape)
plt.savefig('lr-ran-plot-trusted',bbox_inches='tight')


df1 = dfAggNone.query('t_atkr == "trusted" and t_aids == 200 and t_sym == 8 and t_freq == 0.5')
plt.figure(figsize=(6, 3))
ax1 = sns.lineplot(x='t_alen',y='s_ci_av',data=df1,hue='a_lab')
rp = tools.risk.riskPatches()
params = {
    'numBoxes':20,
    'fromLeft':0,
    'toLeft':0,
    'fromBottom':0.45,
    'toBottom':0.7,
    'right':250,
    'top':1.0,
    'alpha':0.03,
    #'alpha':0.5,
}
shapes = rp.getShapes(params)
ax1.set(ylabel = 'Confidence Improvement (CI)', xlabel='Length of Random Value')
ax1.legend(title='Strength of Anonymity',loc='lower left', bbox_to_anchor=(0.4,0), ncol=3)
ax1.grid(axis='y')
plt.xlim(0,250)
plt.ylim(0,1)
for shape in shapes:
    plt.gca().add_patch(shape)
plt.savefig('lr-ran-plot-aid-len-trusted',bbox_inches='tight')
