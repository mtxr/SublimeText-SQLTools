__version__ = "v0.2.0"

import json
import os
import re
import sys

dirpath = os.path.join(os.path.dirname(__file__), 'lib')
if dirpath not in sys.path:
    sys.path.append(dirpath)

import sqlparse

# Regular expression for comments
comment_re = re.compile(
    '(^)?[^\S\n]*/(?:\*(.*?)\*/[^\S\n]*|/[^\n]*)($)?',
    re.DOTALL | re.MULTILINE
)


def parseJson(filename):
    """ Parse a JSON file
        First remove comments and then use the json module package
        Comments look like :
            // ...
        or
            /*
            ...
            */
    """

    with open(filename, mode='r', encoding='utf-8') as f:
        content = ''.join(f.readlines())

        # Looking for comments
        match = comment_re.search(content)
        while match:
            # single line comment
            content = content[:match.start()] + content[match.end():]
            match = comment_re.search(content)

        # remove trailing commas
        content = re.sub(r',([ \t\r\n]+)}', r'\1}', content)
        content = re.sub(r',([ \t\r\n]+)\]', r'\1]', content)

        # Return json file
        return json.loads(content, encoding='utf-8')


def saveJson(content, filename):
    with open(filename, mode='w', encoding='utf-8') as outfile:
        json.dump(content, outfile,
                  sort_keys=True, indent=2, separators=(',', ': '))


def getResultAsList(results):
    resultList = []
    for result in results.splitlines():
        lineResult = ''
        for element in result.strip('|').split('|'):
            lineResult += element.strip()
        if lineResult:
            resultList.append(lineResult)
    return resultList


def formatSql(raw, settings):
    try:
        result = sqlparse.format(raw, **settings)

        return result
    except Exception:
        return None


def merge(source, destination):
    """
    run me with nosetests --with-doctest file.py

    >>> a = { 'first' : { 'all_rows' : { 'pass' : 'dog', 'number' : '1' } } }
    >>> b = { 'first' : { 'all_rows' : { 'fail' : 'cat', 'number' : '5' } } }
    >>> merge(b, a) == { 'first' : { 'all_rows' : { 'pass' : 'dog', 'fail' : 'cat', 'number' : '5' } } }
    True
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            merge(value, node)
        else:
            destination[key] = value

    return destination
