import diffixRef
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

    def addResult(self,atk,numCorrect,numGuess,totalTrials,doprint=True):
        if atk.name not in self.t:
            self.t[atk.name] = {
                'attacks': [atk.attack],
                'numGuess': [numGuess],
                'numCorrect': [numCorrect],
                'totalTrials': [totalTrials],
            }
        else:
            self.t[atk.name]['numCorrect'].append(numCorrect)
            self.t[atk.name]['numGuess'].append(numGuess)
            self.t[atk.name]['totalTrials'].append(totalTrials)
            self.t[atk.name]['attacks'].append(atk.attack)

    def printResults(self):
        for atk.name,res in self.t.items():
            print(f"{atk.name}: ({len(res['numCorrect'])} attack variants)")
            print(atk.attack['long'])
            confidences = []
            guessProbs = []
            for i in range(len(res['numCorrect'])):
                if res['numGuess'][i]:
                    confidences.append(res['numCorrect'][i]/res['numGuess'][i])
                else:
                    confidences.append(0)
                guessProbs.append(res['numGuess'][i]/res['totalTrials'][i])
            print("  Confidence:")
            print(f"    avg: {statistics.mean(confidences)}")
            maxi = confidences.index(max(confidences))
            print(f"    max: {confidences[maxi]}   ({res['attacks'][maxi]['describe']})")
            mini = confidences.index(min(confidences))
            print(f"    min: {confidences[mini]}   ({res['attacks'][mini]['describe']})")
            print("  Guess Probability:")
            print(f"    avg: {statistics.mean(guessProbs)}")
            maxi = guessProbs.index(max(guessProbs))
            print(f"    max: {guessProbs[maxi]}   ({res['attacks'][maxi]['describe']})")
            mini = guessProbs.index(min(guessProbs))
            print(f"    min: {guessProbs[mini]}   ({res['attacks'][mini]['describe']})")

class attackBase:
    '''
        This is the base class for all attacks (which are sub-classes of this base)
    '''
    long = ''
    def __init__(self,attack,tally,defaultRef,
                 queryUrl='https://db-proto.probsteide.com/api',
                 fileUrl='https://db-proto.probsteide.com/api/upload-db'):
        self.pp = pprint.PrettyPrinter(indent=4)
        self.name = self.__class__.__name__
        self.attack = attack
        self.attack['long'] = self.long
        self.queryUrl = queryUrl
        self.fileUrl = fileUrl
        self.tally = tally
        self.defaultRef = defaultRef
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
        # Strip, then append
        for change in attack['table']['changes']:
            if change['change'] == 'strip':
                self.rf.stripDf(change['table'],change['query'])
        for change in attack['table']['changes']:
            if change['change'] == 'append':
                self.rf.appendDf(change['table'],change['spec'])
        self.rf.baseTablesToDb()
        self.makeAttackQueries()
        self.dr = diffixRef.diffixRef()
        self.defaultAids=[{'table':'tab','aid':'aid1'}]

    def getDiffixParams(self):
        diffix = {
            'lcfMin':1.5,
            'lcfMax':5.5,
            'lcfDist':'uniform',
        }
        return diffix

    def printRawTable(self):
        print(self.rf.baseDf)

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

    def _updateParamsLoop(self,par,ref,keyStack):
        for key,val in ref.items():
            if key not in par:
                self._error(f"ERROR: _updateParams: bad key {keyStack},{key}")
            keyStack.append(key)
            if type(val) is not dict:
                par[key] = val
                continue
            else:
                self._updateParamsLoop(par[key],ref[key],keyStack)

    def _updateParams(self,refParams):
        params = self.defaultRef.copy()
        self._updateParamsLoop(params,refParams,[])
        return params

    def _queryDbRaw(self,sql):
        self.conn = sqlite3.connect(self.rf.getDbPath())
        self.cur = self.conn.cursor()
        self.cur.execute(sql)
        answer = self.cur.fetchall()
        self.conn.close()
        return answer

    def _queryDbRef(self,sql,seed):
        if 'refParams' in self.attack:
            params = self._updateParams(self.attack['refParams'])
        else:
            params = self.defaultRef
        if 'aids' in self.attack:
            aids = self.attack[aids]
        else:
            aids = self.defaultAids
        db = self.rf.getDbPath()
        rtn = self.dr.query(sql,seed,aids,db,params)
        if rtn['success']:
            return rtn['answer']
        else:
            return None

    def queryDb(self,dbType,sql,seed=1):
        if dbType == 'raw':
            return self._queryDbRaw(sql)
        elif dbType == 'ref':
            return self._queryDbRef(sql,seed)
        self._error('''ERROR: queryDb: shouldn't get here''')

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
            ans = self.queryDb('ref',query)
            if ans is None:
                # At least one of the attack queries fails, so no need to continue
                return query
        return None

    def runQueries(self,dbType,seed):
        # For each query in the query list of lists, we record an answer in
        # the same list of lists position
        self.answers = []
        for queryGroup in self.queries:
            ansGroup = []
            for query in queryGroup:
                ansGroup.append(self.queryDb(dbType,query,seed=seed))
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

    def _bucketIsSuppressed(self, bucketVal):
        for bucket in self.answers[0][0][0]:
            if bucket[0] == bucketVal:
                return False
        return True

class simpleAveraging(attackBase):
    long = 'In the simple averaging attack, our goal is to remove noise by simply repeating ' + \
           'the exact same query on the hope that the noise sample will be different each time, ' + \
           'and the noise will average away. Diffix defeats this attack with sticky noise.'
    def runAttack(self,db='ref',seed=1):
        self.runQueries(db,seed)
        sumCounts = 0
        for ansGroup in self.answers:
            sumCounts += ansGroup[0][0][0]
        averagedCount = sumCounts / len(self.answers)
        if averagedCount == self.exactCount:
            return 'CORRECT'
        else:
            return 'WRONG'

    def doCheck(self):
        sql1 = self._doSqlReplace(self.queries[0][0])
        self.exactCount = self.queryDb('raw',sql1)[0][0]

class simpleStrongSuppressDetect(attackBase):
    long = "This attack exploits Diffix' suppression mechanism. " + \
           'The idea here is that an attacker knows that there are N AIDs with a certain ' + \
           'column value, and wants to figure out if the N+1th AID also has that value. ' + \
           'In the "strong" case, N is equal to the maximum number of distinct AIDs that ' + \
           'are always suppressed. Therefore if the bucket is not suppressed, the victim ' + \
           'must be present.'
    def runAttack(self,db='ref',seed=1):
        if db == 'raw':
            # The attack doesn't make sense on the raw DB
            return 'NOT APPLICABLE'
        self.runQueries(db,seed)
        suppressed = self._bucketIsSuppressed(self.check['bucketVal'])
        # alwaysSuppressed is the max number of AIDs that is always suppressed
        alwaysSuppressed = int(self.attack['refParams']['low_count_threshold']['lower'])
        if self.check['numKnown'] == alwaysSuppressed:
            # This is the case where, if the answer is not suppressed, then it MUST be
            # that the victim is present
            if not suppressed:
                    return 'CORRECT'
        else:
            return 'NO GUESS'

class splitAveraging(attackBase):
    long = 'In the split averaging attack, the attacker attempts to defeat sticky noise by ' + \
           'creating pairs of queries where each pair collectively has the same underlying ' + \
           'set of AIDs, but the individual queries have different AIDs. This is done with ' + \
           'a pair of WHERE clauses as "WHERE col = val" and "WHERE col <> val". These two ' + \
           'taken together include all users. Each pair of queries uses a different val ' +\
           'with the result that each individual bucket has different AIDs.  This attack ' +\
           'works against Diffix Publish, but not the other Diffix variants.'
    def runAttack(self,db='ref',seed=1):
        self.runQueries(db,seed)
        sumCounts = 0
        for ansGroup in self.answers:
            sumCounts += ansGroup[0][0][0]
            sumCounts += ansGroup[1][0][0]
        averagedCount = sumCounts / len(self.answers)
        if averagedCount == self.exactCount:
            return 'CORRECT'
        else:
            return 'WRONG'

    def doCheck(self):
        sql = self._doSqlReplace(self.attack['checkQuery'])
        self.exactCount = self.queryDb('raw',sql)[0][0]

class simpleSoftDifference(attackBase):
    long = 'The simple soft difference attack attempts to learn if an AID is present or absent ' + \
           'from whether there is a difference between a pair of queries whereby one query ' + \
           '(the "left" query) ' + \
           'definately includes or excludes the victim, and the other query (the "right" query) ' + \
           'may or may not include the victim. This "soft" version of the attack simply looks ' + \
           'to see if the right answer is above or below a threshold that falls in the middle of ' + \
           'the true difference between the left and right counts. '
    def runAttack(self,db='ref',seed=1):
        self.runQueries(db,seed)
        diff = self.answers[0][0][0][0] - self.answers[0][1][0][0]
        if (self.check['correctIsLess'] and diff < self.check['threshold'] or
            self.check['correctIsLess']  is False and diff >= self.check['threshold']):
            return 'CORRECT'
        else:
            return 'WRONG'

class simpleHardDifference(attackBase):
    long = 'The simple hard difference attack attempts to learn if an AID is present or absent ' + \
           'from whether there is a difference between a pair of queries whereby one query ' + \
           '(the "left" query) ' + \
           'definately includes or excludes the victim, and the other query (the "right" query) ' + \
           'may or may not include the victim. This "hard" version of the attack simply looks ' + \
           'to see if right and left answers differ at all. Diffix Publish is vulnerable to this ' + \
           'because it uses only a single AID noise layer. '
    def runAttack(self,db='ref',seed=1):
        self.runQueries(db,seed)
        if ((self.check['correctIfDifferent'] and 
                self.answers[0][0][0][0] != self.answers[0][1][0][0]) or
            (not self.check['correctIfDifferent'] and 
                self.answers[0][0][0][0] == self.answers[0][1][0][0])):
            return 'CORRECT'
        else:
            return 'WRONG'

class simpleFirstDerivitiveDifference(attackBase):
    long = 'In this variant of the difference attack, the attacker builds multiple pairs of ' + \
           'queries, with the left and right query each being part of a left and right histogram. ' + \
           'In this attack, left and right for each pair will differ, but the difference will be ' + \
           'the same for all pairs except the one with the victim. '
    def runAttack(self,db='ref',seed=1):
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
            return 'WRONG'
        else:
            return 'CORRECT'

class simpleListUsers(attackBase):
    long = 'The simple list attack simply tries to list the individual rows of one or more ' + \
           'columns. The "test" for whether the attack succeeded is simply to compare the number ' + \
           'rows received against the true number '
    def runAttack(self,db='ref',seed=1):
        self.runQueries(db,seed)
        # Simply checking the number of rows in the answer against the raw data
        # query isn't a very thorough check, but I'm assuming that even this will
        # fail so no need to go further
        if len(self.answers[0][0]) == len(self.checkAns):
            return 'CORRECT'
        else:
            return 'WRONG'

    def doCheck(self):
        sql1 = self._doSqlReplace(self.queries[0][0])
        self.checkAns = self.queryDb('raw',sql1)

class justTesting(attackBase):
    long = ''
    def runAttack(self,db='ref',seed=1):
        self.runQueries(db,seed)
        return 'CORRECT'

# Default reference anonymization parameters
defaultRef = {
    'low_count_threshold': {'lower': 2, 'upper': 5},
    'noise': {'cutoff': 5.0, 'standard_dev': 1.0},
    'outlier_count': {'lower': 1, 'upper': 2},
    'top_count': {'lower': 2, 'upper': 3}
}

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
        'tagAsRun': False,
        'attackClass': simpleHardDifference,
        'describe': 'Simple hard difference attack with lone woman, victim does not have attribute',
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
            'correctIfDifferent': False,
        },
        'refParams': {
            'low_count_threshold': {'lower': 2, 'upper': 5},
        }
    },
    {   
        'doprint': False,
        'tagAsRun': False,
        'attackClass': simpleStrongSuppressDetect,
        'describe': 'Simple strong detect suppression attack, one of two known, victim present',
        'table': {
            'conditionsSql': "select count(*) from tab where t1='i' and t2='j'",
            # This adds two users, all with t1=k, and all with unique t2. The attacker
            # knows that there are either two or three users with t1=k, and will use
            # the suppression signal to guess which
            'changes': [
                {'change':'append', 'table':'tab','spec': {'t1':['k'],'t2':['unique']}},
                {'change':'append', 'table':'tab','spec': {'t1':['k'],'t2':['unique']}},
            ],
        },
        'attackQueries': {
            'sqls': [
                "select t1, count(distinct aid1) from tab",
            ],
        },
        'check': {
            'bucketVal': 'k',
            'numKnown': 1,
        },
        'refParams': {
            'low_count_threshold': {'lower': 2, 'upper': 5},
        }
    },
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
        'attackClass': simpleSoftDifference,
        'describe': 'Simple soft difference attack with lone woman, victim does not have attribute',
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
        'attackClass': simpleSoftDifference,
        'describe': "Simple soft difference attack with NAND'd AND group, victim does not have attribute",
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
        'attackClass': simpleSoftDifference,
        'describe': "Simple soft difference attack with NAND'd AND group, victim has attribute",
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
        'attackClass': simpleSoftDifference,
        'describe': 'Simple soft difference attack with single NAND, victim has attribute',
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
        'attackClass': simpleSoftDifference,
        'describe': 'Simple soft difference attack with single NAND, victim does not have attribute',
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
        'attackClass': simpleSoftDifference,
        'describe': "Simple soft difference attack with OR'd AND group, victim does not have attribute",
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
        'attackClass': simpleSoftDifference,
        'describe': "Simple soft difference attack with OR'd AND group, victim has attribute",
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
        'attackClass': simpleSoftDifference,
        'describe': 'Simple soft difference attack with single OR, victim has attribute',
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
        'attackClass': simpleSoftDifference,
        'describe': 'Simple soft difference attack with single OR, victim does not have attribute',
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
        atk = attack['attackClass'](attack,tally,defaultRef)
        # Do any work to compute check information against which claim is determined
        atk.doCheck()
        # Make sure the attack works with no anonymization
        result = atk.runAttackTest()
        if result != 'CORRECT' and result != 'NOT APPLICABLE':
            atk.print()
            print("FAIL: test attack failed")
            quit()
        disallowedQuery = atk.attackQueriesDisallowed()
        if disallowedQuery:
            print(f'        Query rejected: "{disallowedQuery}"')
            tally.addResult(atk,0,100,100)
        else:
            numCorrect = 0
            numTry = 0
            for i in range(defaultNumClaims):
                result = atk.runAttack(seed=i)
                if result == 'FAIL':
                    numGuess += 1
                elif result == 'CORRECT':
                    numGuess += 1
                    numCorrect += 1
                elif result == 'NO GUESS':
                    # Do nothing on purpose
                    pass
            tally.addResult(atk,numCorrect,numGuess,defaultNumClaims)
    if testControl == 'firstOnly':
        break
print("---- SUMMARY ----")
tally.printResults()
