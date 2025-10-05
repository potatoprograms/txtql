BASIC SYNTAX:
select <target> from <file> <conditions>
ex) select lines from 'log.txt' containing 'apple'

TARGETS:
lines: returns all lines meeting all conditions

KEYWORDS:
containing:
  containing count 'string'
  all targets containing count of the string
  if count is unspecified, it requires only at least one instance
  count may be used with comparison operators such as containing > 2 'apple'
  if no operator is specified, = will be defaulted to
ending:
  ending 'string'
  all targets that end with the string (excluding \n)
starting:
  starting 'string'
  all targets beginning with the string
length:
  length count
  all targets with the specified length
  length may be used with comparison operators such as length > 2
  if no operator is specified, = will be defaulted to

LOGICAL CONNECTORS:
not:
  negates the following condition such as not containing 'apple'
and:
  will combine the results of the two conditions before and after it, and return only the targets passing both conditions
or:
  will combine the results of the two conditions before and after it, and return the targets passing at least one of the conditions
**connectors are parsed left to right, meaning containing x and containing y or ending z parses as (containing x and containing y) or ending z

ADDITIONAL:
files and strings must be defined using ''
by default, nothing is case-sensitive, to change this, add casesensitive to the end of your query
