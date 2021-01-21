# attacker
Script for testing Diffix by running attacks

# Requirements

Requires a directory called `tables` under the directory where attacks.py is executed.

# Basic workflow

* Build table to attack
* Upload table to reference Diffix
* Run attack, usually multiple times, measuring effectiveness in the process
  * When multiple attacks, each run with a different secret salt so that result differs (as opposed to using different tables to attack)

# Building table

Tables are built by the classes in `whereParser.py` and `rowFiller.py`.

There are two main steps:

1. Build table that has all possible combinations of columns and specified values.
2. Add or delete rows individually to create the required attack conditions.
