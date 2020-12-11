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
from pulp import *
import pprint
import whereParser
import rowFiller
import bucketHandler
import itertools
pp = pprint.PrettyPrinter(indent=4)

# Build a table to attack
# This makes two columns with two values per column
tableSql = "select count(*) from tab where i1=1 or i2=5"
#tableSql = "select count(*) from tab where i1=1 or i2=5 or i3=11"
sw = whereParser.simpleWhere(tableSql)
rf = rowFiller.rowFiller(sw,printIntermediateTables=False)
rf.makeBaseTables()
df = rf.baseDf['tab']
# Ok, df now is a table (data frame) with no unique users, actually, but ok for now

numAids = df.groupby('aid1').count()
numAids = df['aid1'].nunique()
print(f"Number of distinct users: {numAids}")

# We don't need the AID column after this, so slice it off
df.drop('aid1', inplace=True, axis=1)

# I want a variable for every user / column / bucket combination.
print("Here are the users")
aids = [f"a{i}" for i in range(numAids)]
print(aids)

# I'm going to make a dict that has all the column/bucket combinations and associated counts
buckets = {}
cols = list(df.columns)
print(cols)
for col in cols:
    buckets[col] = list(df[col].unique())
pp.pprint(buckets)

# This probably not the most efficient, but I'm going to determine the count of every combination
# of columns and values individually
bh = bucketHandler.bucketHandler(cols)
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
                varName += f"{entry[0]}_v{entry[1]}_"
                combCols.append(entry[0])
                combVals.append(entry[1])
            query = query[:-5]
            varName = varName[:-1]
            # shape[0] gives the number of rows, which is also the count
            bh.addBucket(combCols,combVals,count=df.query(query).shape[0])
print(bh.df)

# At this point, `aids` contains a list of all "users", and bh.df contains
# all the buckets and associated counts

# The prob variable is created to contain the problem data
prob = LpProblem("Attack-Problem")

print("The decision variables are created")
allKeys = bh.getAllKeys()
pp.pprint(allKeys)
choices = LpVariable.dicts("Choice", (aids, allKeys.keys()), cat='Binary')
pp.pprint(prob)
pp.pprint(choices)

print("We do not define an objective function since none is needed")

print("Constraints ensuring that each bucket has sum equal to number of its users")
for bkt in allKeys:
    prob += lpSum([choices[aid][bkt] for aid in aids]) == allKeys[bkt]
pp.pprint(prob)
quit()

print("Constraints ensuring that each user is in one bucket per column")
for col in cols:
    # Get all the buckets that are only for a single column
    zzzz
    for aid in aids:
        prob += lpSum([choices[aid][bkt] for bkt in colBkts[col]]) == 1

pp.pprint(prob)

# The problem data is written to an .lp file
prob.writeLP("attack.lp")

# A file called attack.txt is created/overwritten for writing to
attack = open('attack.txt','w')

prob.solve()
print("Status:", LpStatus[prob.status])
for aid in aids:
    print(f"AID {aid}:")
    for bkt in allCombs:
        if value(choices[aid][bkt]) == 1:
            print(f"    {bkt}")
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
