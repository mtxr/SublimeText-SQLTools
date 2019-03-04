import re
import logging
from collections import namedtuple

from .ParseUtils import extractTables

JOIN_COND_PATTERN = r"\s+?JOIN\s+?[\w\.`\"]+\s+?(?:AS\s+)?(\w+)\s+?ON\s+?(?:[\w\.]+)?$"
JOIN_COND_REGEX = re.compile(JOIN_COND_PATTERN, re.IGNORECASE)

keywords_list = [
    'SELECT', 'UPDATE', 'DELETE', 'INSERT', 'INTO', 'FROM',
    'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING', 'JOIN',
    'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'USING',
    'LIMIT', 'DISTINCT', 'SET'
]

logger = logging.getLogger(__name__)


# this function is generously used in completions code to get rid
# of all sorts of leading and trailing quotes in RDBMS identifiers
def _stripQuotes(ident):
    return ident.strip('"\'`')


# used for formatting output
def _stripQuotesOnDemand(ident, doStrip=True):
    if doStrip:
        return _stripQuotes(ident)
    return ident


def _startsWithQuote(ident):
    # ident is matched against any of the possible ident quotes
    quotes = ('`', '"')
    return ident.startswith(quotes)


def _stripPrefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


# escape $ sign when formatting output
def _escapeDollarSign(ident):
    return ident.replace("$", "\$")


class CompletionItem(namedtuple('CompletionItem', ['type', 'ident'])):
    """Represents a potential or actual completion item.
      * type - type of item (Table, Function, Column)
      * ident - identifier (table.column, schema.table, alias)
    """
    __slots__ = ()

    @property
    def parent(self):
        """Parent of identifier, e.g. "table" from "table.column" """
        if self.ident.count('.') == 0:
            return None
        else:
            return self.ident.partition('.')[0]

    @property
    def name(self):
        """Name of identifier, e.g. "column" from "table.column" """
        return self.ident.split('.').pop()

    # for functions - strip open bracket "(" and everything after that
    # e.g: mydb.myAdd(int, int) --> mydb.myadd
    def _matchIdent(self):
        if self.type == 'Function':
            return self.ident.partition('(')[0].lower()
        return self.ident.lower()

    # Helper method for string matching
    # When exactly is true:
    #   matches search string to target exactly, but empty search string matches anything
    # When exactly is false:
    #   if only one char given in search string match this single char with start
    #   of target string, otherwise match search string anywhere in target string
    @staticmethod
    def _stringMatched(target, search, exactly):
        if exactly:
            return target == search or search == ''
        else:
            if (len(search) == 1):
                return target.startswith(search)
            return search in target

    # Method to match completion item against search string (prefix).
    # Lower score means a better match.
    # If completion item matches prefix with parent identifier, e.g.:
    #     table_name.column ~ table_name.co, then score = 1
    # If completion item matches prefix without parent identifier, e.g.:
    #     table_name.column ~ co, then score = 2
    # If completion item matches, but prefix has no parent, e.g.:
    #     table ~ tab, then score = 3
    def prefixMatchScore(self, search, exactly=False):
        target = self._matchIdent()
        search = search.lower()

        # match parent exactly and partially match name
        if '.' in target and '.' in search:
            searchList = search.split('.')
            searchObject = _stripQuotes(searchList.pop())
            searchParent = _stripQuotes(searchList.pop())
            targetList = target.split('.')
            targetObject = _stripQuotes(targetList.pop())
            targetParent = _stripQuotes(targetList.pop())
            if (searchParent == targetParent):
                if self._stringMatched(targetObject, searchObject, exactly):
                    return 1   # highest score
            return 0

        # second part matches ?
        if '.' in target:
            targetObjectNoQuote = _stripQuotes(target.split('.').pop())
            searchNoQuote = _stripQuotes(search)
            if self._stringMatched(targetObjectNoQuote, searchNoQuote, exactly):
                return 2
        else:
            targetNoQuote = _stripQuotes(target)
            searchNoQuote = _stripQuotes(search)
            if self._stringMatched(targetNoQuote, searchNoQuote, exactly):
                return 3
            else:
                return 0
        return 0

    def prefixMatchListScore(self, searchList, exactly=False):
        for item in searchList:
            score = self.prefixMatchScore(item, exactly)
            if score:
                return score
        return 0

    # format completion item according to sublime text completions format
    def format(self, stripQuotes=False):
        typeDisplay = ''
        if self.type == 'Table':
            typeDisplay = self.type
        elif self.type == 'Keyword':
            typeDisplay = self.type
        elif self.type == 'Alias':
            typeDisplay = self.type
        elif self.type == 'Function':
            typeDisplay = 'Func'
        elif self.type == 'Column':
            typeDisplay = 'Col'

        if not typeDisplay:
            return (self.ident, _stripQuotesOnDemand(self.ident, stripQuotes))

        part = self.ident.split('.')
        if len(part) > 1:
            return ("{0}\t({1} {2})".format(part[1], part[0], typeDisplay),
                    _stripQuotesOnDemand(_escapeDollarSign(part[1]), stripQuotes))

        return ("{0}\t({1})".format(self.ident, typeDisplay),
                _stripQuotesOnDemand(_escapeDollarSign(self.ident), stripQuotes))


class Completion:
    def __init__(self, allTables, allColumns, allFunctions, settings=None):
        self.allTables = [CompletionItem('Table', table) for table in allTables]
        self.allColumns = [CompletionItem('Column', column) for column in allColumns]
        self.allFunctions = [CompletionItem('Function', func) for func in allFunctions]

        # we don't save the settings (we don't need them after init)
        if settings is None:
            settings = {}

        # check old setting name ('selectors') first for compatibility
        activeSelectors = settings.get('selectors', None)
        if not activeSelectors:
            activeSelectors = settings.get(
                'autocomplete_selectors_active',
                ['source.sql'])
        self.activeSelectors = activeSelectors

        self.ignoreSelectors = settings.get(
            'autocomplete_selectors_ignore',
            ['string.quoted.single.sql'])

        # determine type of completions
        self.completionType = settings.get('autocompletion', 'smart')
        if not self.completionType:
            self.completionType = None  # autocompletion disabled
        else:
            self.completionType = str(self.completionType).strip()
            if self.completionType not in ['basic', 'smart']:
                self.completionType = 'smart'

        # determine desired keywords case from settings
        formatSettings = settings.get('format', {})
        keywordCase = formatSettings.get('keyword_case', 'upper')
        uppercaseKeywords = keywordCase.lower().startswith('upper')

        self.allKeywords = []
        for keyword in keywords_list:
            if uppercaseKeywords:
                keyword = keyword.upper()
            else:
                keyword = keyword.lower()

            self.allKeywords.append(CompletionItem('Keyword', keyword))

    def getActiveSelectors(self):
        return self.activeSelectors

    def getIgnoreSelectors(self):
        return self.ignoreSelectors

    def isDisabled(self):
        return self.completionType is None

    def getAutoCompleteList(self, prefix, sql, sqlToCursor):
        if self.isDisabled():
            return None

        autocompleteList = []
        inhibit = False
        if self.completionType == 'smart':
            autocompleteList, inhibit = self._getAutoCompleteListSmart(prefix, sql, sqlToCursor)
        else:
            autocompleteList = self._getAutoCompleteListBasic(prefix)

        if not autocompleteList:
            return None, False

        # return completions with or without quotes?
        # determined based on ident after last dot
        startsWithQuote = _startsWithQuote(prefix.split(".").pop())
        autocompleteList = [item.format(startsWithQuote) for item in autocompleteList]

        return autocompleteList, inhibit

    def _getAutoCompleteListBasic(self, prefix):
        prefix = prefix.lower()
        autocompleteList = []

        # columns, tables and functions that match the prefix
        for item in self.allColumns:
            score = item.prefixMatchScore(prefix)
            if score:
                autocompleteList.append(item)

        for item in self.allTables:
            score = item.prefixMatchScore(prefix)
            if score:
                autocompleteList.append(item)

        for item in self.allFunctions:
            score = item.prefixMatchScore(prefix)
            if score:
                autocompleteList.append(item)

        if len(autocompleteList) == 0:
            return None

        return autocompleteList

    def _getAutoCompleteListSmart(self, prefix, sql, sqlToCursor):
        """
        Generally, we recognize 3 different variations in prefix:
          * ident|           // no dots (.) in prefix
            In this case we show completions for all available identifiers (tables, columns,
            functions) that have "ident" text in them. Identifiers relevant to current
            statement shown first.
          * parent.ident|   // single dot in prefix
            In this case, if "parent" matches on of parsed table aliases we show column
            completions for them, as well as we do prefix search for all other identifiers.
            If something is matched, we return results as well as set a flag to suppress
            Sublime completions.
            If we don't find any objects using prefix search or we know that "parent" is
            a query alias, we don't return anything and allow Sublime to do it's job by
            showing most relevant completions.
          * database.table.col|   // multiple dots in prefix
            In this case we only show columns for "table" column, as there is nothing else
            that could be referenced that way.
        Since it's too complicated to handle the specifics of identifiers case sensitivity
        as well as all nuances of quoting of those identifiers for each RDBMS, we always
        match against lower-cased and stripped quotes of both prefix and our internal saved
        identifiers (tables, columns, functions). E.g. "MyTable"."myCol" --> mytable.mycol
        """

        # TODO: add completions of function out fields
        prefix = prefix.lower()
        prefixDots = prefix.count('.')

        # continue with empty identifiers list, even if we failed to parse identifiers
        identifiers = []
        try:
            identifiers = extractTables(sql)
        except Exception as e:
            logger.debug('Failed to extact the list identifiers from SQL:\n {}'.format(sql),
                         exc_info=True)

        # joinAlias is set only if user is editing join condition with alias. E.g.
        # SELECT a.* from tbl_a a inner join tbl_b b ON |
        joinAlias = None
        if prefixDots <= 1:
            try:
                joinCondMatch = JOIN_COND_REGEX.search(sqlToCursor, re.IGNORECASE)
                if joinCondMatch:
                    joinAlias = joinCondMatch.group(1)
            except Exception as e:
                logger.debug('Failed search of join condition, SQL:\n {}'.format(sqlToCursor),
                             exc_info=True)

        autocompleteList = []
        inhibit = False
        if prefixDots == 0:
            autocompleteList, inhibit = self._noDotsCompletions(prefix, identifiers, joinAlias)
        elif prefixDots == 1:
            autocompleteList, inhibit = self._singleDotCompletions(prefix, identifiers, joinAlias)
        else:
            autocompleteList, inhibit = self._multiDotCompletions(prefix, identifiers)

        if not autocompleteList:
            return None, False

        return autocompleteList, inhibit

    def _noDotsCompletions(self, prefix, identifiers, joinAlias=None):
        """
        Method handles most generic completions when prefix does not contain any dots.
        In this case completions can be anything: cols, tables, functions that have this name.
        Still we try to predict users needs and output aliases, tables, columns and function
        that are used in currently parsed statement first, then show everything else that
        could be related.
        Order: statement aliases -> statement cols -> statement tables -> statement functions,
        then:  other cols -> other tables -> other functions that match the prefix in their names
        """

        # use set, as we are interested only in unique identifiers
        sqlAliases = set()
        sqlTables = []
        sqlColumns = []
        sqlFunctions = []
        otherTables = []
        otherColumns = []
        otherFunctions = []
        otherKeywords = []
        otherJoinConditions = []

        # utilitary temp lists
        identTables = set()
        identColumns = set()
        identFunctions = set()

        for ident in identifiers:
            if ident.has_alias():
                aliasItem = CompletionItem('Alias', ident.alias)
                score = aliasItem.prefixMatchScore(prefix)
                if score and aliasItem.ident != prefix:
                    sqlAliases.add(aliasItem)

            if ident.is_function:
                identFunctions.add(ident.full_name)
            elif ident.is_table_alias:
                identTables.add(ident.full_name)
                identColumns.add(ident.name + '.' + prefix)

        for table in self.allTables:
            score = table.prefixMatchScore(prefix, exactly=False)
            if score:
                if table.prefixMatchListScore(identTables, exactly=True) > 0:
                    sqlTables.append(table)
                else:
                    otherTables.append(table)

        for col in self.allColumns:
            score = col.prefixMatchScore(prefix, exactly=False)
            if score:
                if col.prefixMatchListScore(identColumns, exactly=False) > 0:
                    sqlColumns.append(col)
                else:
                    otherColumns.append(col)

        for fun in self.allFunctions:
            score = fun.prefixMatchScore(prefix, exactly=False)
            if score:
                if fun.prefixMatchListScore(identFunctions, exactly=True) > 0:
                    sqlColumns.append(fun)
                else:
                    otherColumns.append(fun)

        # keywords
        for item in self.allKeywords:
            score = item.prefixMatchScore(prefix)
            if score:
                otherKeywords.append(item)

        # join conditions
        if joinAlias:
            joinConditions = self._joinConditionCompletions(identifiers, joinAlias)

            for condition in joinConditions:
                if condition.ident.lower().startswith(prefix):
                    otherJoinConditions.append(condition)

        # collect the results in prefered order
        autocompleteList = []

        # first of all list join conditions (if applicable)
        autocompleteList.extend(otherJoinConditions)

        # then aliases and identifiers related to currently parsed statement
        autocompleteList.extend(sqlAliases)

        # then cols, tables, functions related to current statement
        autocompleteList.extend(sqlColumns)
        autocompleteList.extend(sqlTables)
        autocompleteList.extend(sqlFunctions)

        # then other matching cols, tables, functions
        autocompleteList.extend(otherKeywords)
        autocompleteList.extend(otherColumns)
        autocompleteList.extend(otherTables)
        autocompleteList.extend(otherFunctions)

        return autocompleteList, False

    def _singleDotCompletions(self, prefix, identifiers, joinAlias=None):
        """
        More intelligent completions can be shown if we have single dot in prefix in certain cases.
        """
        prefixList = prefix.split(".")
        prefixObject = prefixList.pop()
        prefixParent = prefixList.pop()

        # get join conditions
        joinConditions = []
        if joinAlias:
            joinConditions = self._joinConditionCompletions(identifiers, joinAlias)

        sqlTableAliases = set()  # set of CompletionItem
        sqlQueryAliases = set()  # set of strings

        # we use set, as we are interested only in unique identifiers
        for ident in identifiers:
            if ident.has_alias() and ident.alias.lower() == prefixParent:
                if ident.is_query_alias:
                    sqlQueryAliases.add(ident.alias)

                if ident.is_table_alias:
                    tables = [
                        table
                        for table in self.allTables
                        if table.prefixMatchScore(ident.full_name, exactly=True) > 0
                    ]
                    sqlTableAliases.update(tables)

        autocompleteList = []

        for condition in joinConditions:
            aliasPrefix = prefixParent + '.'
            if condition.ident.lower().startswith(aliasPrefix):
                autocompleteList.append(CompletionItem(condition.type,
                                                       _stripPrefix(condition.ident, aliasPrefix)))

        # first of all expand table aliases to real table names and try
        # to match their columns with prefix of these expanded identifiers
        # e.g. select x.co| from tab x   //  "x.co" will expland to "tab.co"
        for table_item in sqlTableAliases:
            prefix_to_match = table_item.name + '.' + prefixObject
            for item in self.allColumns:
                score = item.prefixMatchScore(prefix_to_match)
                if score:
                    autocompleteList.append(item)

        # try to match all our other objects (tables, columns, functions) with prefix
        for item in self.allColumns:
            score = item.prefixMatchScore(prefix)
            if score:
                autocompleteList.append(item)

        for item in self.allTables:
            score = item.prefixMatchScore(prefix)
            if score:
                autocompleteList.append(item)

        for item in self.allFunctions:
            score = item.prefixMatchScore(prefix)
            if score:
                autocompleteList.append(item)

        inhibit = len(autocompleteList) > 0
        # in case prefix parent is a query alias we simply don't know what those
        # columns might be so, set inhibit = False to allow sublime default completions
        if prefixParent in sqlQueryAliases:
            inhibit = False

        return autocompleteList, inhibit

    # match only columns if prefix contains multiple dots (db.table.col)
    def _multiDotCompletions(self, prefix, identifiers):
        autocompleteList = []
        for item in self.allColumns:
            score = item.prefixMatchScore(prefix)
            if score:
                autocompleteList.append(item)

        if len(autocompleteList) > 0:
            return autocompleteList, True

        return None, False

    def _joinConditionCompletions(self, identifiers, joinAlias=None):
        if not joinAlias:
            return None

        # use set, as we are interested only in unique identifiers
        sqlTableAliases = set()
        joinAliasColumns = set()
        sqlOtherColumns = set()

        for ident in identifiers:
            if ident.has_alias() and not ident.is_function:
                sqlTableAliases.add(CompletionItem('Alias', ident.alias))

                prefixForColumnMatch = ident.name + '.'
                columns = [
                    (ident.alias, col)
                    for col in self.allColumns
                    if (col.prefixMatchScore(prefixForColumnMatch, exactly=True) > 0 and
                        _stripQuotes(col.name).lower().endswith('id'))
                ]

                if ident.alias == joinAlias:
                    joinAliasColumns.update(columns)
                else:
                    sqlOtherColumns.update(columns)

        joinCandidatesCompletions = []
        for joinAlias, joinColumn in joinAliasColumns:
            # str.endswith can be matched against a tuple
            columnsToMatch = None
            if _stripQuotes(joinColumn.name).lower() == 'id':
                columnsToMatch = (
                    _stripQuotes(joinColumn.parent).lower() + _stripQuotes(joinColumn.name).lower(),
                    _stripQuotes(joinColumn.parent).lower() + '_' + _stripQuotes(joinColumn.name).lower()
                )
            else:
                columnsToMatch = (
                    _stripQuotes(joinColumn.name).lower(),
                    _stripQuotes(joinColumn.parent).lower() + _stripQuotes(joinColumn.name).lower(),
                    _stripQuotes(joinColumn.parent).lower() + '_' + _stripQuotes(joinColumn.name).lower()
                )

            for otherAlias, otherColumn in sqlOtherColumns:
                if _stripQuotes(otherColumn.name).lower().endswith(columnsToMatch):
                    sideA = joinAlias + '.' + joinColumn.name
                    sideB = otherAlias + '.' + otherColumn.name

                    joinCandidatesCompletions.append(CompletionItem('Condition', sideA + ' = ' + sideB))
                    joinCandidatesCompletions.append(CompletionItem('Condition', sideB + ' = ' + sideA))

        return joinCandidatesCompletions
