'''
Variables: 
    one per user per column-bucket combination
        Each variable is a Binary (0/1)
Constraints:
    Each column has sum equal to number of users
        sum of all variables is equal to number of users
    Each user is in one column only.
        So for each user the sum of that user/column variables is 1
    Each bucket has a certain range of number of users
        Sum of all variables assigned to that bucket is between X and Y
    Pairs of buckets have a certain range of number of users
        Sum of all V's assigned to those two buckets is between X and Y
    And so on....
'''

# Import PuLP modeler functions
import pulp
import json
import pandas as pd
import numpy as np
import pprint
import bucketHandler
import itertools
import random
import os.path
pp = pprint.PrettyPrinter(indent=4)
doprint = False

class lrAttack:
    def __init__(self, seed, tabType, numValsPerColumn, force=False):
        self.seed = seed
        self.tabType = tabType
        self.numValsPerColumn = numValsPerColumn
        self.fileName = self._makeFileName()
        self.tabInfo = self._makeTable()
        self.force = force

    def checkSolution(self):
        # This will hold the table determined by the solution
        data = {}
        for col in self.cols:
            data[col] = []
        for aid in self.choices:
            for bkt in self.choices[aid]:
                if pulp.value(self.choices[aid][bkt]) == 1:
                    cols,vals = self.bh.getColsValsFromBkt(bkt)
                    if len(cols) == 1:
                        # This is a one-dimensional bucket, so we'll use it in our new table
                        data[cols[0]].append(int(vals[0]))
        dfNew = pd.DataFrame.from_dict(data)
        dfNew.sort_values(by=self.cols,inplace=True)
        dfNew.reset_index(drop=True,inplace=True)
        df = self.tabInfo['df']
        diff_loc = np.where(dfNew != df)
        return len(diff_loc[0]) + len(diff_loc[1]), diff_loc

    def saveTable(self):
        js = self.tabInfo['df'].to_json()
        name = self.fileName + '_tab.json'
        path = os.path.join('results',name)
        with open(path, 'w') as f:
            json.dump(js, f)
    
    def _makeFileName(self):
        fileName = f"s{self.seed}_{self.tabType}_"
        for num in self.numValsPerColumn:
            fileName += f"{num}_"
        fileName = fileName[:-1]
        return fileName
    
    def _makeTable(self):
        numCols = len(self.numValsPerColumn)
        self.cols = []
        for i in range(numCols):
            self.cols.append(f"i{i}")
        numAids = 1
        for numVals in self.numValsPerColumn:
            numAids *= numVals
        print(f"Make '{self.tabType}' table with {numCols} columns and {numAids} aids")
        colVals = {}
        for i in range(numCols):
            col = self.cols[i]
            colVals[col] = list(range((10*i),(10*i+self.numValsPerColumn[i])))
        if doprint: pp.pprint(colVals)
        data = {}
        if self.tabType == 'random':
            for col in colVals:
                data[col] = []
                for _ in range(numAids):
                    data[col].append(random.choice(colVals[col]))
        df = pd.DataFrame.from_dict(data)
        df.sort_values(by=self.cols,inplace=True)
        df.reset_index(drop=True,inplace=True)
        tabInfo = {'df':df,
                   'numCols':numCols,
                   'numAids':numAids,}
        return tabInfo
    
    def makeProblem(self):
        # First check to see if there is already an LpProblem to read in. Note that the
        # problem runs in rounds, where each new solution generates more constraints to prevent
        # the prior solution
        if self.force == False:
            prob = self.readProblem()
            if prob:
                return prob
        df = self.tabInfo['df']
        numAids = self.tabInfo['numAids']
        # I want a variable for every user / column / bucket combination.
        if doprint: print("Here are the users")
        aids = [f"a{i}" for i in range(numAids)]
        if doprint: print(aids)
        
        # I'm going to make a dict that has all the column/bucket combinations and associated counts
        buckets = {}
        cols = list(df.columns)
        if doprint: print(cols)
        for col in cols:
            buckets[col] = list(df[col].unique())
        if doprint: pp.pprint(buckets)
        
        # This probably not the most efficient, but I'm going to determine the count of every combination
        # of columns and values individually
        self.bh = bucketHandler.bucketHandler(cols)
        for i in range(len(cols)):
            # Get all combinations with i columns
            for colComb in itertools.combinations(cols,i+1):
                prod = []
                for col in colComb:
                    tups = []
                    for bkt in df[col].unique():
                        tups.append((col,bkt))
                    prod.append(tups)
                for fullComb in itertools.product(*prod):
                    # Now we make a dataframe query out of the combination
                    query = ''
                    varName = ''
                    combCols = []
                    combVals = []
                    for entry in fullComb:
                        # entry[0] is the column name, entry[1] is the bucket value
                        query += f"{entry[0]} == {entry[1]} and "
                        varName += f"{entry[0]}.v{entry[1]}."
                        combCols.append(entry[0])
                        combVals.append(entry[1])
                    query = query[:-5]
                    varName = varName[:-1]
                    # shape[0] gives the number of rows, which is also the count
                    self.bh.addBucket(combCols,combVals,count=df.query(query).shape[0])
        if doprint: print(self.bh.df)
        
        # At this point, `aids` contains a list of all "users", and bh.df contains
        # all the buckets and associated counts
        
        # The prob variable is created to contain the problem data
        prob = pulp.LpProblem("Attack-Problem",pulp.LpMinimize)
        cnum = 0

        print("The decision variables are created")
        allCounts = self.bh.getAllCounts()
        if doprint: pp.pprint(allCounts)
        self.choices = pulp.LpVariable.dicts("Choice", (aids, allCounts.keys()), cat='Binary')
        if doprint: pp.pprint(prob)
        if doprint: pp.pprint(self.choices)
        
        print("We do not define an objective function since none is needed")
        # The following dummy objecting is a work-around for a but in the
        # to_json call.
        dummy=pulp.LpVariable("dummy",0,0,pulp.LpInteger)
        prob += 0.0*dummy
        
        print("Constraints ensuring that each bucket has sum equal to number of its users")
        for bkt in allCounts:
            prob += pulp.lpSum([self.choices[aid][bkt] for aid in aids]) == allCounts[bkt], f"{cnum}: num_users_per_bkt"
            cnum += 1
        if doprint: pp.pprint(prob)
        
        print("Constraints ensuring that each user is in one bucket per column or combination")
        # scales as buckets * aids
        for i in range(len(cols)-1):
            # Get all combinations with i columns
            for colComb in itertools.combinations(cols,i+1):
                combCounts = self.bh.getColCounts(colComb)
                for aid in aids:
                    prob += pulp.lpSum([self.choices[aid][bkt] for bkt in combCounts.keys()]) == 1, f"{cnum}: one_user_per_bkt_set"
                    cnum += 1
        
        if doprint: pp.pprint(prob)
        
        print("Constraints ensuring that each user in c1b1 is in one of c1b1.c2bX")
        print("    or users in c1b1.c2b1 are in one of c1b1.c2b1.c3bX")
        # TO do this, we want to loop through every combination of columns, and for each
        # combination, find one additional column and get all the sub-buckets
        # Note this constraint scales poorly and we might need to think of a work-around
        for i in range(len(cols)-1):
            # Get all combinations with i columns
            for colComb in itertools.combinations(cols,i+1):
                # Get all single columns not in the combination
                combCounts = self.bh.getColCounts(colComb)
                for col in cols:
                    if col in colComb:
                        continue
                    # Now, for every bucket of colComb, we want to find all buckets
                    # in colComb+col that are sub-buckets of colComb.
                    subCols = list(colComb)
                    subCols.append(col)
                    subCounts = self.bh.getColCounts(subCols)
                    for bkt1 in combCounts:
                        subBkts = []
                        for bkt2 in subCounts:
                            if self.bh.isSubBucket(bkt2,bkt1):
                                subBkts.append(bkt2)
                        if len(subBkts) == 0:
                            continue
                        allBkts = subBkts
                        allBkts.append(bkt1)
                        # Now I have buckets and sub-buckets (in `allBkts`). Any user is either
                        # in the bucket and one sub-bucket (sum==2), or in neither (sum==0).
                        # Because of earlier constraints, the user can't be in more than one bucket
                        # or more than one sub-bucket. As a result, we don't need to worry about
                        # a user being in more than 2 buckets, and obviously we don't need to worry
                        # about the user being in less than 0 buckets. So all we need to do here
                        # is make sure the user isn't in one bucket total. We can do this with
                        # sum of subBkts + -1*bkt1 = 0
                        # Make the per-variable factors
                        factors = [1.0 for _ in range(len(allBkts))]
                        factors[-1] = -1.0
                        for aid in aids:
                            prob += pulp.lpSum([factors[j]*self.choices[aid][allBkts[j]] for j in range(len(allBkts))]) == 0, f"{cnum}: bkt_sub-bkt"
                            cnum += 1
        return prob

    def _buildChoicesDict(self,vars):
        self.choices = {}
        for key,val in vars.items():
            _,aid,bkt = key.split('_')
            if aid not in self.choices:
                self.choices[aid] = {}
            if bkt in self.choices[aid]:
                pp.pprint(self.choices)
                print("ERROR: buildChoicesDict: aid {aid}, bkt {bkt}")
            self.choices[aid][bkt] = val

    def readProblem(self):
        # Read the PuLP problem
        name = self.fileName + '_prob.json'
        path = os.path.join('results',name)
        if not os.path.isfile(path):
            return None
        vars, prob = pulp.LpProblem.from_json(path)
        self._buildChoicesDict(vars)
        print(f"Reading problem from file {path}")
        '''
        # Read the choices
        name = self.fileName + '_choices.json'
        path = os.path.join('results',name)
        with open(path, 'w') as f:
            self.choices = json.load(f)
        '''
        return prob

    def storeProblem(self,prob):
        # Store the PuLP problem
        name = self.fileName + '_prob.json'
        path = os.path.join('results',name)
        prob.to_json(path)
        # Store the choices
        '''
        name = self.fileName + '_choices.json'
        path = os.path.join('results',name)
        pp.pprint(self.choices)
        with open(path, 'w') as f:
            json.dump(self.choices, f)
        '''
    
# Build a table to attack
# complete has one user for every possible column/value combination
# random has same number of users, but ranomly assigned values. The result
# should be that many users are random, some are not
seed = 'a'
random.seed(seed)
tabTypes = ['random','complete']
tabType = tabTypes[0]
numValsPerColumn = [5,5,5]

lra = lrAttack(seed, tabType, numValsPerColumn, force=True)
lra.saveTable()
prob = lra.makeProblem()
lra.storeProblem(prob)

print("Solving problem")
lra.storeProblem(prob)
prob.solve()
numDiff, diff = lra.checkSolution()
print(f"Num different rows between solution and original table is {numDiff}")
print("Status:", pulp.LpStatus[prob.status])
quit()

'''
Now what happens is that solutions are generated. In each run of the loop, one solution
is found. Then that solution is prevented from being found again through yet more constraints
that prevent the same assignment as a previous solution
'''
while True:
    prob.solve()
    # The status of the solution is printed to the screen
    print("Status:", LpStatus[prob.status])
    # The solution is printed if it was deemed "optimal" i.e met the constraints
    if LpStatus[prob.status] == "Optimal":
        # The solution is written to the sudokuout.txt file
        for r in ROWS:
            if r in [1, 4, 7]:
                sudokuout.write("+-------+-------+-------+\n")
            for c in COLS:
                for v in VALS:
                    if value(choices[v][r][c]) == 1:
                        if c in [1, 4, 7]:
                            sudokuout.write("| ")
                        sudokuout.write(str(v) + " ")
                        if c == 9:
                            sudokuout.write("|\n")
        sudokuout.write("+-------+-------+-------+\n\n")
        # The constraint is added that the same solution cannot be returned again
        prob += lpSum([choices[v][r][c] for v in VALS for r in ROWS for c in COLS
                       if value(choices[v][r][c]) == 1]) <= 80
    # If a new optimal solution cannot be found, we end the program
    else:
        break
'''
After each loop, a single new constraint like this is created:
_C351: Choice_1_1_8 + Choice_1_2_4 + Choice_1_3_1 + Choice_1_4_2
 + Choice_1_5_7 + Choice_1_6_6 + Choice_1_7_3 + Choice_1_8_5 + Choice_1_9_9
 + Choice_2_1_3 + Choice_2_2_9 + Choice_2_3_6 + Choice_2_4_8 + Choice_2_5_2
 + Choice_2_6_5 + Choice_2_7_7 + Choice_2_8_1 + Choice_2_9_4 + Choice_3_1_2
 + Choice_3_2_8 + Choice_3_3_4 + Choice_3_4_9 + Choice_3_5_6 + Choice_3_6_3
 + Choice_3_7_5 + Choice_3_8_7 + Choice_3_9_1 + Choice_4_1_7 + Choice_4_2_3
 + Choice_4_3_5 + Choice_4_4_6 + Choice_4_5_1 + Choice_4_6_8 + Choice_4_7_9
 + Choice_4_8_4 + Choice_4_9_2 + Choice_5_1_1 + Choice_5_2_6 + Choice_5_3_9
 + Choice_5_4_7 + Choice_5_5_5 + Choice_5_6_2 + Choice_5_7_4 + Choice_5_8_8
 + Choice_5_9_3 + Choice_6_1_4 + Choice_6_2_1 + Choice_6_3_8 + Choice_6_4_5
 + Choice_6_5_3 + Choice_6_6_7 + Choice_6_7_2 + Choice_6_8_9 + Choice_6_9_6
 + Choice_7_1_5 + Choice_7_2_2 + Choice_7_3_7 + Choice_7_4_4 + Choice_7_5_9
 + Choice_7_6_1 + Choice_7_7_6 + Choice_7_8_3 + Choice_7_9_8 + Choice_8_1_6
 + Choice_8_2_7 + Choice_8_3_3 + Choice_8_4_1 + Choice_8_5_4 + Choice_8_6_9
 + Choice_8_7_8 + Choice_8_8_2 + Choice_8_9_5 + Choice_9_1_9 + Choice_9_2_5
 + Choice_9_3_2 + Choice_9_4_3 + Choice_9_5_8 + Choice_9_6_4 + Choice_9_7_1
 + Choice_9_8_6 + Choice_9_9_7 <= 80
Relative to a solution like this:
+-------+-------+-------+
| 5 3 2 | 6 7 8 | 4 1 9 |
| 6 7 4 | 1 9 5 | 8 3 2 |
| 1 9 8 | 3 4 2 | 7 6 5 |
+-------+-------+-------+
| 8 1 9 | 7 6 4 | 5 2 3 |
| 4 2 6 | 8 5 3 | 1 9 7 |
| 7 5 3 | 9 2 1 | 6 4 8 |
+-------+-------+-------+
| 9 6 1 | 5 3 7 | 2 8 4 |
| 2 8 7 | 4 1 9 | 3 5 6 |
| 3 4 5 | 2 8 6 | 9 7 1 |
+-------+-------+-------+
The sum of all those choices is 81, so the set of choices can't be made again.
'''
sudokuout.close()

# The location of the solutions is give to the user
print("Solutions Written to sudokuout.txt")
