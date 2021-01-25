import whereParser
import rowFiller
import statistics
import sqlite3
import pprint
import re
import requests
import pandas as pd
import numpy as np

defaultNumClaims = 100               # number of times each test should repeat (for average)

class tally:
    ''' Used to tally up and report overall results.
        Each class of attack has multiple variants.
        Each attack runs multiple times, recording the number of successes (correct guesses
            from the attacker).
        tally keeps stats on how well each of the variants does
    '''
    def __init__(self):
        self.t = {}

    def addResult(self,atk,numSucceed,numTries,doprint=True):
        if doprint:
            print(f"{atk.name}, {atk.attack['describe']}")
            rate = int((numSucceed/numTries)*100)
            print(f"    {numSucceed} of {numTries} ({rate} percent)")
        if atk.name not in self.t:
            self.t[atk.name] = {
                'attacks': [atk.attack],
                'numTries': numTries,
                'successes': [numSucceed],
            }
        else:
            self.t[atk.name]['successes'].append(numSucceed)
            self.t[atk.name]['attacks'].append(atk.attack)

    def printResults(self):
        for atk.name,res in self.t.items():
            print(f"{atk.name} ({res['numTries']} samples per attack):")
            print(f"    {len(res['successes'])} attack variants")
            print(f"    avg: {statistics.mean(res['successes'])}")
            maxi = res['successes'].index(max(res['successes']))
            print(f"    max: {res['successes'][maxi]}   ({res['attacks'][maxi]['describe']})")
            mini = res['successes'].index(min(res['successes']))
            print(f"    min: {res['successes'][mini]}   ({res['attacks'][mini]['describe']})")

class attackBase:
    '''
    '''
    def __init__(self,attack,tally,queryUrl='https://db-proto.probsteide.com/api',
                 fileUrl='https://db-proto.probsteide.com/api/upload-db'):
        self.pp = pprint.PrettyPrinter(indent=4)
        self.name = self.__class__.__name__
        self.attack = attack
        self.queryUrl = queryUrl
        self.fileUrl = fileUrl
        self.tally = tally
        dop = False
        if 'doprint' in self.attack:
            dop = self.attack['doprint']
        # build attack database
        self.sw = whereParser.simpleWhere(attack['table']['conditionsSql'])
        self.rf = rowFiller.rowFiller(self.sw,printIntermediateTables=False,dop=dop)
        self.rf.makeBaseTables()
        if len(self.rf.failedCombinations) > 0:
            print("Failed Combinations:")
            print(self.rf.failedCombinations)
        for change in attack['table']['changes']:
            if change['change'] == 'append':
                self.rf.appendDf(change['table'],change['spec'])
            elif change['change'] == 'strip':
                self.rf.stripDf(change['table'],change['query'])
        self.rf.baseTablesToDb()
        self.postDb()
        self.makeAttackQueries()

    def print(self):
        self.pp.pprint(self.attack)
    
    def postDb(self):
        fin = open(self.rf.getDbPath(), 'rb')
        data = fin.read()
        headers = {
            'db-name':self.rf.getDbName(),
            'password':'great success',
            'Content-Type': 'application/octet-stream',
        }
        r = requests.post(url=self.fileUrl, data=data, headers=headers)
        #print(r.text)
        fin.close()

    def queryDb(self,sql):
        self.conn = sqlite3.connect(self.rf.getDbPath())
        self.cur = self.conn.cursor()
        self.cur.execute(sql)
        answer = self.cur.fetchall()
        self.conn.close()
        return answer

    def queryAnon(self,sql,seed=1,anon=True,db='testAttack.db'):
        aidCols = self.rf.getAidColumns()
        req = {'Anonymize':anon,
               'database':db,
               'query':sql,
               'seed':seed,
               'aid_columns':aidCols,
               }
        response = requests.post(self.queryUrl, json=req)
        ans = response.json()
        if ans['success'] == False:
            #print("Query Error")
            #self.pp.pprint(ans)
            return None
        return ans

    def makeAttackQueries(self):
        ''' Makes a list of query groups, each group having one or more queries
        '''
        self.queries = []
        if 'sqls' in self.attack['attackQueries']:
            queryGroup = []
            for sql in self.attack['attackQueries']['sqls']:
                queryGroup.append(self._doSqlReplace(sql))
            repeats = 1             # default
            if 'repeats' in self.attack['attackQueries']:
                repeats = self.attack['attackQueries']['repeats']
            for _ in range(repeats):
                self.queries.append(queryGroup)
        elif 'attackTemplates' in self.attack['attackQueries']:
            for attackVal in self.attack['attackQueries']['attackVals']:
                queryGroup = []
                for sql in self.attack['attackQueries']['attackTemplates']:
                    queryGroup.append(sql.replace('---',str(attackVal)))
                self.queries.append(queryGroup)
        else:
            self._error('''ERROR: makeAttackQueries: missing label''')

    def attackQueriesDisallowed(self):
        for query in self.queries[0]:
            ans = self.queryAnon(query)
            if ans is None:
                # At least one of the attack queries fails, so no need to continue
                return True
        return False

    def runQueries(self,db,seed):
        # For each query in the query list of lists, we record an answer in
        # the same list of lists position
        self.answers = []
        for queryGroup in self.queries:
            ansGroup = []
            for query in queryGroup:
                if db == 'raw':
                    ansGroup.append(self.queryDb(query))
                else:
                    ansGroup.append(self.queryAnon(query,seed=seed))
            self.answers.append(ansGroup)

    def _doSqlReplace(self,sql):
        cols = re.findall('-..-',sql)
        for col in cols:
            val = self.rf.getNewRowColumn(col[1:3])
            pattern = f"-{col[1:3]}-"
            sql = re.sub(pattern,str(val),sql)
        return sql

    def _error(self,msg):
        print(msg)
        self.pp.pprint(self.attack)
        quit()

    def runAttackTest(self):
        return self.runAttack(db='raw')

    def runAttack(self,db='dummy'):
        print("ERROR: Every subclass must have a runAttack function")
        quit()

    def doCheck(self):
        self.check = self.attack['check']

    def _sortAnsByBucket(self,ans):
        s = {}
        for row in ans:
            s[row[0]] = row[1]
        return s

class simpleAveraging(attackBase):
    name = 'simpleAveraging'
    def runAttack(self,db='anon',seed=1):
        self.runQueries(db,seed)
        sumCounts = 0
        for ansGroup in self.answers:
            sumCounts += ansGroup[0][0][0]
        averagedCount = sumCounts / len(self.answers)
        if averagedCount == self.exactCount:
            return 'SUCCEED'
        else:
            return 'FAIL'

    def doCheck(self):
        sql1 = self._doSqlReplace(self.queries[0][0])
        self.exactCount = self.queryDb(sql1)[0][0]

class splitAveraging(attackBase):
    name = 'splitAveraging'
    def runAttack(self,db='anon',seed=1):
        self.runQueries(db,seed)
        sumCounts = 0
        for ansGroup in self.answers:
            sumCounts += ansGroup[0][0][0]
            sumCounts += ansGroup[1][0][0]
        averagedCount = sumCounts / len(self.answers)
        if averagedCount == self.exactCount:
            return 'SUCCEED'
        else:
            return 'FAIL'

    def doCheck(self):
        sql = self._doSqlReplace(self.attack['checkQuery'])
        self.exactCount = self.queryDb(sql)[0][0]

class simpleDifference(attackBase):
    def runAttack(self,db='anon',seed=1):
        self.runQueries(db,seed)
        diff = self.answers[0][0][0][0] - self.answers[0][1][0][0]
        if (self.check['correctIsLess'] and diff < self.check['threshold'] or
            self.check['correctIsLess']  is False and diff >= self.check['threshold']):
            return 'SUCCEED'
        else:
            return 'FAIL'

class simpleFirstDerivitiveDifference(attackBase):
    def runAttack(self,db='anon',seed=1):
        self.runQueries(db,seed)
        ans1 = self.answers[0][0]
        ans2 = self.answers[0][1]
        sort1 = self._sortAnsByBucket(ans1)
        sort2 = self._sortAnsByBucket(ans2)
        maxDiff = float('-inf')
        maxBucket = None
        for bucket,count1 in sort1.items():
            if bucket in sort2:
                count2 = sort2[bucket]
                diff = count2 - count1
                if diff > maxDiff:
                    maxBucket = bucket
                    maxDiff = diff
        if maxBucket != self.check['victimBucket']:
            return 'FAIL'
        else:
            return 'SUCCEED'

class simpleListUsers(attackBase):
    def runAttack(self,db='anon',seed=1):
        self.runQueries(db,seed)
        # Simply checking the number of rows in the answer against the raw data
        # query isn't a very thorough check, but I'm assuming that even this will
        # fail so no need to go further
        if len(self.answers[0][0]) == len(self.checkAns):
            return 'SUCCEED'
        else:
            return 'FAIL'

    def doCheck(self):
        sql1 = self._doSqlReplace(self.queries[0][0])
        self.checkAns = self.queryDb(sql1)

class justTesting(attackBase):
    def runAttack(self,db='anon',seed=1):
        self.runQueries(db,seed)
        return 'SUCCEED'

if False: testControl = 'firstOnly'    # executes only the first test
elif False: testControl = 'tagged'    # executes only tests so tagged
else: testControl = 'all'             # executes all tests
'''
The `testControl` parameter is used to determine which tests are run.
The following is a list of attacks. Each attack is an individual attack on
a custom-built table. Each attack works against a non-anonymized (raw) DB,
and may or not work against an anonymized DB. Each individual attack produces
either a correct or incorrect claim, and each attack is run multiple times to
compute the average success rate.

Each attack is one of a class of attacks (averaging attack, difference attack,
etc.). Each class may have one or more variants. Each attack in the following list
of attacks has the following parameters:
    doprint: set for verbose
    tagAsRun: if true, and testControl is 'tagged", then run the attack
    attackClass: the actual attack class name
    table: contains the information used to generate the custom table for the attack.
        conditionsSql is input to simpleWhere (whereParser.py). Look there for usage.
        changes is input to rowFiller (rowFiller.py). Look there for usage.
    attackQueries: config on how to compose the attack queries:
        sqls: a list of SQL statements for the attack. Note that by convention all column
            names are two characters in length. These SQL statements can contain a special
            string '-xx-', where 'xx' is a column name. The special string gets replaced by
            a value taken from the actual column (the value in the first row of the table,
            see '_doSqlReplace()`). This is generally used to exclude or include a single
            row of the table (i.e. a single AID), for instance in a difference attack. Here is
            an example, where '-i1-' is the replacement string for column i1:
                "select count(distinct aid1) from tab where t1 = 'y' and i1 <> -i1-"
        repeats: The number of times the list of SQL statement in `sqls` should be repeated
            (for instance for an averaging attack). Default zero repeats.
        attackTemplates: A list of SQL queries, each containing a single replacement string
            '---'.
        attackVals: For each entry in attackVals, the SQL queries in attackTemplates are
            repeated, replacing '---' with the value from attackVals.
    check: If present, this contains information needed to determine if the attack is
        correct or incorrect. This information is specific to each class of attack.

To build a new class of attack, a subclass of class `attackBase` is created. The subclass
must have a `runAttack()` method, which executes a single attack. The subclass may have a
`doCheck()` method, which generates the information needed to check whether the attack was
correct or incorrect. Generally this involves some custom query to the raw database.
'''
attacks = [
    {   
        'doprint': False,
        'tagAsRun': False,
        'attackClass': justTesting,
        'describe': 'Just testing a new conditionsSql',
        'table': {
            # The attack here is where there is one user with t2 = 'f'. Want to learn t1
            'conditionsSql': "select count(*) from tab where t1='y' and t2 in ('a','b','c')",
            # Remove all t2='f' then add one back in
            'changes': [
                #{'change':'strip', 'table':'tab','query': "t2 == 'f'"},
                #{'change':'append', 'table':'tab','spec': {'t1':['unique'],'t2':['f']}},
            ],
        },
        'attackQueries': {
            'sqls': [
                # The first query definately excludes the victim
                "select count(distinct aid1) from tab where t1='y' and t2 = 'zz'",
                # The second query may or may not (in this case does not).
                "select count(distinct aid1) from tab where t1='y'",
            ],
        },
        'check': {
            'difference': 0
        },
    },
    {   
        'tagAsRun': False,
        'attackClass': simpleDifference,
        'describe': 'Simple difference attack with lone woman, victim does not have attribute',
        'table': {
            # The attack here is where there is one user with t2 = 'f'. Want to learn t1
            'conditionsSql': "select count(*) from tab where t1='y' or t2 in ('f','m')",
            # Remove all t2='f' then add one back in
            'changes': [
                {'change':'strip', 'table':'tab','query': "t2 == 'f'"},
                {'change':'strip', 'table':'tab','query': "t2 == 'zz'"},
                {'change':'append', 'table':'tab','spec': {'t1':['unique'],'t2':['f']}},
            ],
        },
        'attackQueries': {
            'sqls': [
                # The first query definately excludes the victim
                "select count(distinct aid1) from tab where t1='y' and t2 = 'm'",
                # The second query may or may not (in this case does not).
                "select count(distinct aid1) from tab where t1='y'",
            ],
        },
        'check': {
            'threshold': 0.5,
            'correctIsLess': True,
        },
    },
    {   
        'tagAsRun': False,
        'attackClass': simpleDifference,
        'describe': "Simple difference attack with NAND'd AND group, victim does not have attribute",
        'table': {
            # The attack here is where there is one user with a unique combination of i1 and t2
            # values, though each individually is not unique
            'conditionsSql': "select count(*) from tab where t1='y' or i1=100 or t2='x'",
            'changes': [
                {'change':'strip', 'table':'tab','query': "t2 == 'x' and i1 == 100"},
                {'change':'append', 'table':'tab','spec': {'t1':['unique'],'i1':[100],'t2':['x']}},
            ],
        },
        'attackQueries': {
            'sqls': [
                # The first query definately excludes the victim
                "select count(distinct aid1) from tab where t1 = 'y' and not (i1 = 100 and t2 = 'x')",
                # The second query may or may not (but in this case does not).
                "select count(distinct aid1) from tab where t1 = 'y'",
            ],
        },
        'check': {
            'threshold': 0.5,
            'correctIsLess': True,
        },
    },
    {   
        'tagAsRun': False,
        'attackClass': simpleDifference,
        'describe': "Simple difference attack with NAND'd AND group, victim has attribute",
        'table': {
            # The attack here is where there is one user with a unique combination of i1 and t2
            # values, though each individually is not unique
            'conditionsSql': "select count(*) from tab where t1='y' or i1=100 or t2='x'",
            'changes': [
                {'change':'strip', 'table':'tab','query': "t2 == 'x' and i1 == 100"},
                {'change':'append', 'table':'tab','spec': {'t1':['y'],'i1':[100],'t2':['x']}},
            ],
        },
        'attackQueries': {
            'sqls': [
                # The first query definately excludes the victim
                "select count(distinct aid1) from tab where t1 = 'y' and not (i1 = 100 and t2 = 'x')",
                # The second query may or may not (but in this case also does).
                "select count(distinct aid1) from tab where t1 = 'y'",
            ],
        },
        'check': {
            # If the second query has the victim, then the difference is 0
            'threshold': -0.5,
            'correctIsLess': True,
        },
    },
    {   
        'tagAsRun': False,
        'attackClass': simpleDifference,
        'describe': 'Simple difference attack with single NAND, victim has attribute',
        'table': {
            # The attack here is where there is one user with a unique value in column i1
            # We want to know if that user has value t1='y' or not.
            'conditionsSql': "select count(*) from tab where t1='y' or i1=100",
            # I want to make a scenario where the victim has t1=y. So I add a row with unique
            # i1 and t1='y'
            'changes': [
                {'change':'append', 'table':'tab','spec': {'aid1':['unique'],'t1':['y'],'i1':['unique']}},
            ],
        },
        'attackQueries': {
            'sqls': [
                # The first query definately excludes the victim
                "select count(distinct aid1) from tab where t1 = 'y' and i1 <> -i1-",
                # The second query may or may not (but in this case also does).
                "select count(distinct aid1) from tab where t1 = 'y'",
            ],
        },
        'check': {
            # If the second query has the victim, then the difference is -1
            'threshold': -0.5,
            'correctIsLess': True,
        },
    },
    {   
        'tagAsRun': False,
        'attackClass': simpleDifference,
        'describe': 'Simple difference attack with single NAND, victim does not have attribute',
        'table': {
            # The attack here is where there is one user with a unique i1. We want to know
            # if that user has value t1='y' or not.
            'conditionsSql': "select count(*) from tab where t1='y' or i1=100",
            # I want to make a scenario where the victim does not have t1=y.
            'changes': [
                {'change':'append', 'table':'tab','spec': {'t1':['unique'],'i1':['unique']}},
            ],
        },
        'attackQueries': {
            'sqls': [
                # The first query definately excludes the user
                "select count(distinct aid1) from tab where t1='y' and i1 <> -i1-",
                # The second query may or may not (in this case does not).
                "select count(distinct aid1) from tab where t1='y'",
            ],
        },
        'check': {
            # If the second query does not have the victim, then the difference is 1
            'threshold': 0.5,
            'correctIsLess': True,
        },
    },
    {   
        'tagAsRun': False,
        'attackClass': simpleDifference,
        'describe': "Simple difference attack with OR'd AND group, victim does not have attribute",
        'table': {
            # The attack here is where there is one user with a unique combination of i1 and t2
            # values, though each individually is not unique
            'conditionsSql': "select count(*) from tab where t1='y' or i1=100 or t2='x'",
            'changes': [
                {'change':'strip', 'table':'tab','query': "t2 == 'x' and i1 == 100"},
                {'change':'append', 'table':'tab','spec': {'t1':['unique'],'i1':[100],'t2':['x']}},
            ],
        },
        'attackQueries': {
            'sqls': [
                # The first query definately has the victim
                "select count(distinct aid1) from tab where t1 = 'y' or (i1 = 100 and t2 = 'x')",
                # The second query may or may not (but in this case does not).
                "select count(distinct aid1) from tab where t1 = 'y'",
            ],
        },
        'check': {
        # If the second query has the victim, then the difference is 0
            'threshold': 0.5,
            'correctIsLess': False,
        },
    },
    {   
        'tagAsRun': False,
        'attackClass': simpleDifference,
        'describe': "Simple difference attack with OR'd AND group, victim has attribute",
        'table': {
            # The attack here is where there is one user with a unique combination of i1 and t2
            # values, though each individually is not unique
            'conditionsSql': "select count(*) from tab where t1='y' or i1=100 or t2='x'",
            'changes': [
                {'change':'strip', 'table':'tab','query': "t2 == 'x' and i1 == 100"},
                {'change':'append', 'table':'tab','spec': {'t1':['y'],'i1':[100],'t2':['x']}},
            ],
        },
        'attackQueries': {
            'sqls': [
                # The first query definately has the victim
                "select count(distinct aid1) from tab where t1 = 'y' or (i1 = 100 and t2 = 'x')",
                # The second query may or may not (but in this case also does).
                "select count(distinct aid1) from tab where t1 = 'y'",
            ],
        },
        'check': {
        # If the second query has the victim, then the difference is 0
            'threshold': 0.5,
            'correctIsLess': True,
        },
    },
    {   
        'tagAsRun': False,
        'attackClass': simpleDifference,
        'describe': 'Simple difference attack with single OR, victim has attribute',
        'table': {
            # The attack here is where there is one user with a unique value in column i1
            # We want to know if that user has value t1='y' or not.
            'conditionsSql': "select count(*) from tab where t1='y' or i1=3456",
            # I want to make a scenario where the victim has t1=y. So I add a row with unique
            # i1 and t1='y'
            'changes': [
                {'change':'append', 'table':'tab','spec': {'aid1':['unique'],'t1':['y'],'i1':['unique']}},
            ],
        },
        'attackQueries': {
            'sqls': [
                # The first query definately has the victim
                "select count(distinct aid1) from tab where t1 = 'y' or i1 = -i1-",
                # The second query may or may not (but in this case also does).
                "select count(distinct aid1) from tab where t1 = 'y'",
            ],
        },
        'check': {
        # If the second query has the victim, then the difference is 0
            'threshold': 0.5,
            'correctIsLess': True,
        },
    },
    {   
        'tagAsRun': False,
        'attackClass': simpleDifference,
        'describe': 'Simple difference attack with single OR, victim does not have attribute',
        'table': {
            # The attack here is where there is one user with a unique i1. We want to know
            # if that user has value t1='y' or not.
            'conditionsSql': "select count(*) from tab where t1='y' or i1=100",
            # I want to make a scenario where the victim does not have t1=y.
            'changes': [
                {'change':'append', 'table':'tab','spec': {'t1':['unique'],'i1':['unique']}},
            ],
        },
        'attackQueries': {
            'sqls': [
                # The first query definately has the user
                "select count(distinct aid1) from tab where t1='y' or i1 = -i1-",
                # The second query may or may not (in this case does not).
                "select count(distinct aid1) from tab where t1='y'",
            ],
        },
        'check': {
        # If the second query does not have the victim, then the difference is 1
            'threshold': 0.5,
            'correctIsLess': False,
        },
    },
    {   
        'tagAsRun': False,
        'attackClass': splitAveraging,
        'describe': 'Split averaging attack to learn exact count',
        'table': {
            'conditionsSql': '''select count(*) from tab where t1='y' or
                            i1 in (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20)''',
            'changes': [ ],
        },
        'checkQuery': "select count(distinct aid1) from tab where t1='y'",
        'attackQueries': {
            'attackTemplates': [
                "select count(distinct aid1) from tab where t1='y' and i1 = ---",
                "select count(distinct aid1) from tab where t1='y' and i1 <> ---",
            ],
            'attackVals': [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20],
        },
    },
    {   
        'tagAsRun': False,
        'attackClass': simpleAveraging,
        'describe': 'Simple averaging attack to learn exact count',
        'table': {
            'conditionsSql': "select count(*) from tab where t1='y' or i1=100",
            'changes': [ ],
        },
        'attackQueries': {
            'sqls': [
                "select count(distinct aid1) from tab where t1='y'",
            ],
            'repeats': 100,
        },
    },
    {   
        'tagAsRun': False,
        'attackClass': simpleListUsers,
        'describe': 'Select star',
        'table': {
            'conditionsSql': "select count(*) from tab where t1='y' or i1=100",
            'changes': [ ],
        },
        'attackQueries': {            
            'sqls': [
                "select * from tab",
            ],
        },
    },
    {   
        'tagAsRun': True,
        'attackClass': simpleListUsers,
        'describe': 'Select AID column',
        'table': {
            'conditionsSql': "select count(*) from tab where t1='y' or i1=100",
            'changes': [ ],
        },
        'attackQueries': {
            'sqls': [
                "select aid1 from tab",
            ],
        },
    },
    {   
        'tagAsRun': False,
        'attackClass': simpleFirstDerivitiveDifference,
        'describe': '''First derivitive difference attack with NAND'd AND group,
                       victim does not have attribute''',
        'table': {
        # We want to learn which t1 bucket the victim is in
            'conditionsSql': '''select count(*) from tab where t1 in ('a','b','c') or
                            i1 = 100 or t2 = 'x' or t3 = 'y' ''',
            # I want to make a scenario where the victim does not have t1=y.
            'changes': [
                {'change':'strip', 'table':'tab','query': "t2 == 'x' and i1 == 100 and t3 == 'y'"},
                {'change':'append', 'table':'tab','spec': {'t1':['a'],'t2':['x'],'i1':[100],'t3':['y']}},
            ],
        },
        'attackQueries': {
            'sqls': [
        # The first query definately has the user
                '''select t1, count(distinct aid1) from tab where
                             not (i1 = 100 and t2 = 'x' and t3 = 'y') group by 1''',
                "select t1, count(distinct aid1) from tab group by 1",
            ],
        },
        'check':{
            'victimBucket': 'a',
        },
    },
    {   
        'tagAsRun': False,
        'attackClass': simpleFirstDerivitiveDifference,
        'describe': 'First derivitive difference attack with single NAND, victim does not have attribute',
        'table': {
            # We want to learn which t1 bucket the victim is in
            'conditionsSql': "select count(*) from tab where t1 in ('a','b','c') and i1 = 100",
            # I want to make a scenario where the victim does not have t1=y.
            'changes': [
                {'change':'append', 'table':'tab','spec': {'t1':['a'],'i1':['unique']}},
            ],
        },
        'attackQueries': {
            'sqls': [
                # The first query definately has the user
                "select t1, count(distinct aid1) from tab where i1 <> -i1- group by 1",
                "select t1, count(distinct aid1) from tab group by 1",
            ],
        },
        'check':{
            'victimBucket': 'a',
        },
    },
]

tally = tally()
for attack in attacks:
    if (testControl == 'firstOnly' or testControl == 'all' or
        (testControl == 'tagged' and attack['tagAsRun'])):
        print(attack['describe'])
        atk = attack['attackClass'](attack,tally)
        # Do any work to compute check information against which claim is determined
        atk.doCheck()
        # Make sure the attack works with no anonymization
        result = atk.runAttackTest()
        if result != 'SUCCEED':
            atk.print()
            print("FAIL: test attack failed")
            quit()
        if atk.attackQueriesDisallowed():
            tally.addResult(atk,0,100)
        else:
            numSucceed = 0
            for i in range(defaultNumClaims):
                result = atk.runAttack(seed=i)
                if result == 'FAIL AND STOP':
                    break
                elif result == 'SUCCEED':
                    numSucceed += 1
            tally.addResult(atk,numSucceed,defaultNumClaims)
    if testControl == 'firstOnly':
        break
print("---- SUMMARY ----")
tally.printResults()
