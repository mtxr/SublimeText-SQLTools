import string
from collections import namedtuple

# TODO: back to local import
from .ParseUtils import extractTables

# this dict is used in prefixMatchScore to remove punctuation from strings
removePunctuationTable = str.maketrans({key: None for key in string.punctuation})
keywords_list = ['SELECT', 'UPDATE', 'DELETE', 'INSERT', 'INTO', 'FROM',
                 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING', 'JOIN',
                 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'USING',
                 'LIMIT', 'DISTINCT', 'SET']


def _stipQuotes(ident):
    return ident.strip('"\'`')


class CompletionItem(namedtuple('CompletionItem', ['type', 'ident', 'score'])):
    __slots__ = ()

    @property
    def parent(self):
        if self.ident.count('.') == 0:
            return None
        else:
            return self.ident.partition('.')[0]

    @property
    def name(self):
        return self.ident.split('.').pop()

    @property
    def matchIdent(self):
        if self.type == 'Function':
            return self.ident.partition('(')[0].lower()
        return self.ident.lower()

    @property
    def matchSublimeCompletion(self):
        if self.type == 'Function':
            return _stipQuotes(self.ident.split('.').pop().partition('(')[0])
        return _stipQuotes(self.ident.split('.').pop())

    def format(self):
        typeLabel = ''
        if self.type == 'Table':
            typeLabel = self.type
        elif self.type == 'Function':
            typeLabel = 'Func'
        elif self.type == 'Column':
            typeLabel = 'Col'
        elif self.type == 'Keyword':
            typeLabel = self.type
        elif self.type == 'Alias':
            typeLabel = self.type
        elif self.type == 'Unknown':
            typeLabel = ''

        if not typeLabel:
            return ("{0}".format(self.ident), self.ident)

        part = self.ident.split('.')
        if len(part) > 1:
            return ("{0}\t({1} {2})".format(part[1], part[0], typeLabel), part[1])
        else:
            return ("{0}\t({1})".format(part[0], typeLabel), part[0])

    @staticmethod
    def _stringMatched(target, search_str, exactly):
        if exactly:
            return target == search_str or search_str == ''
        else:
            if (len(search_str) == 1):
                return target.startswith(search_str)
            return search_str in target

    def prefixMatchScore(self, search_str, exactly=False):
        # matching parent object (before '.') exactly and
        # matching object (after '.') as fuzzy
        target = self.matchIdent
        search_str = search_str.lower()

        if '.' in target and '.' in search_str:
            search_list = search_str.split('.')
            search_object = _stipQuotes(search_list.pop())
            search_parent = _stipQuotes(search_list.pop())
            target_list = target.split('.')
            target_object = _stipQuotes(target_list.pop())
            target_parent = _stipQuotes(target_list.pop())
            # highest score if
            # prefix matches exactly and object is partially matches
            if search_parent == target_parent and self._stringMatched(target_object, search_object, exactly):
                return 1

        if '.' in target:
            target_object_noquote = _stipQuotes(target.split('.').pop())
            search_noquote = _stipQuotes(search_str)
            # second part matches ?
            if self._stringMatched(target_object_noquote, search_noquote, exactly):
                return 2
        else:
            target_noquote = _stipQuotes(target)
            search_noquote = _stipQuotes(search_str)

            if self._stringMatched(target_noquote, search_noquote, exactly):
                return 3
            else:
                return 0
        return 0


class Completion:
    def __init__(self, uppercaseKeywords, allTables, allColumns, allFunctions):
        self.allTables = [CompletionItem('Table', table, 0) for table in allTables]
        self.allColumns = [CompletionItem('Column', column, 0) for column in allColumns]
        self.allFunctions = [CompletionItem('Function', func, 0) for func in allFunctions]

        self.allKeywords = []
        for keyword in keywords_list:
            if uppercaseKeywords:
                keyword = keyword.upper()
            else:
                keyword = keyword.lower()

            self.allKeywords.append(CompletionItem('Keyword', keyword, 0))

    def getAutoCompleteList(self, prefix, sublimeCompletions, sql):
        """
        Since it's too complicated to handle the specifics of identifiers case sensivity
        as well as all nuances of quoting of those identifiers for each RDBMS, we always
        match against lower-cased and stripped quotes of both prefix and our internal saved
        identifiers (tables, columns, functions). E.g. "MyTable"."myCol" --> mytable.mycol
        """

        # TODO: add completions of function out fields
        prefix = prefix.lower()
        prefix_dots = prefix.count('.')

        # continue with empty identifiers list, even if we failed to parse identifiers
        identifiers = []
        try:
            identifiers = extractTables(sql)
        except Exception as e:
            print(e)

        autocompleteList = []
        inhibit = False
        if prefix_dots == 0:
            autocompleteList, inhibit = self._noDotsCompletions(prefix, sublimeCompletions, identifiers)
        elif prefix_dots == 1:
            autocompleteList, inhibit = self._singleDotCompletions(prefix, sublimeCompletions, identifiers)
        else:
            autocompleteList, inhibit = self._multiDotCompletions(prefix, sublimeCompletions, identifiers)

        if autocompleteList is not None and len(autocompleteList) > 0:
            autocompleteList = [item.format() for item in autocompleteList]
            return autocompleteList, inhibit

        return None, False

    def _noDotsCompletions(self, prefix, sublimeCompletions, identifiers):
        # output aliases first, then
        # output columns related to current statement, then
        # search for columns, tables, functions with prefix

        # use set, as we are interested only in unique idetifiers
        sql_aliases = set()
        sql_tables = set()
        sql_columns = set()
        sql_functions = set()

        for ident in identifiers:
            if ident.has_alias():
                    sql_aliases.add(CompletionItem('Alias', ident.alias, 0))

            if ident.is_function:
                functions = [fun for fun in self.allFunctions if fun.prefixMatchScore(ident.full_name, exactly=True) > 0]
                sql_functions.update(functions)
            else:
                tables = [table for table in self.allTables if table.prefixMatchScore(ident.full_name, exactly=True) > 0]
                sql_tables.update(tables)
                prefix_for_column_match = ident.name + '.'
                columns = [col for col in self.allColumns if col.prefixMatchScore(prefix_for_column_match, exactly=True) > 0]
                sql_columns.update(columns)

        autocompleteList = []

        for item in sql_aliases:
            score = item.prefixMatchScore(prefix)
            if score and item.ident != prefix:
                autocompleteList.append(CompletionItem(item.type, item.ident, score))

        for item in sql_columns:
            score = item.prefixMatchScore(prefix)
            if score:
                autocompleteList.append(CompletionItem(item.type, item.ident, score))

        for item in sql_tables:
            score = item.prefixMatchScore(prefix)
            if score:
                autocompleteList.append(CompletionItem(item.type, item.ident, score))

        for item in sql_functions:
            score = item.prefixMatchScore(prefix)
            if score:
                autocompleteList.append(CompletionItem(item.type, item.ident, score))

        for item in self.allKeywords:
            score = item.prefixMatchScore(prefix)
            if score:
                autocompleteList.append(CompletionItem(item.type, item.ident, score))

        # if len(autocompleteList) > 0:
        #     print("thats it: " + str(autocompleteList))
        #     return autocompleteList, True

        # #############################################
        for item in self.allColumns:
            score = item.prefixMatchScore(prefix)
            if score:
                if item not in sql_columns:
                    autocompleteList.append(CompletionItem(item.type, item.ident, score))

        for item in self.allTables:
            score = item.prefixMatchScore(prefix)
            if score:
                if item not in sql_tables:
                    autocompleteList.append(CompletionItem(item.type, item.ident, score))

        for item in self.allFunctions:
            score = item.prefixMatchScore(prefix)
            if score:
                if item not in sql_functions:
                    autocompleteList.append(CompletionItem(item.type, item.ident, score))

        return autocompleteList, False

    def _singleDotCompletions(self, prefix, sublimeCompletions, identifiers):
        prefix_list = prefix.split(".")
        prefix_obj = prefix_list.pop()
        prefix_ref = prefix_list.pop()

        sql_table_aliases = set()
        sql_query_aliases = set()

        # we use set, as we are interested only in unique idetifiers
        for ident in identifiers:
            if ident.has_alias() and ident.alias == prefix_ref:
                if ident.is_query_alias:
                    sql_query_aliases.add(ident.alias)

                if ident.is_table_alias:
                    tables = [(ident.alias, table) for table in self.allTables if table.prefixMatchScore(ident.full_name, exactly=True) > 0]
                    sql_table_aliases.update(tables)

        autocompleteList = []

        for alias, table_item in sql_table_aliases:
            prefix_to_match = table_item.name + '.' + prefix_obj
            for item in self.allColumns:
                score = item.prefixMatchScore(prefix_to_match)
                if score:
                    autocompleteList.append(CompletionItem(item.type, item.ident, score))

        for item in self.allColumns:
            score = item.prefixMatchScore(prefix)
            if score:
                autocompleteList.append(CompletionItem(item.type, item.ident, score))

        for item in self.allTables:
            score = item.prefixMatchScore(prefix)
            if score:
                autocompleteList.append(CompletionItem(item.type, item.ident, score))

        for item in self.allFunctions:
            score = item.prefixMatchScore(prefix)
            if score:
                autocompleteList.append(CompletionItem(item.type, item.ident, score))

        inhibit = True
        if prefix_ref in sql_query_aliases:
            inhibit = False

        return autocompleteList, inhibit

    def _multiDotCompletions(self, prefix, sublimeCompletions, identifiers):
        # prefix_list = prefix.split(".")
        # prefix_obj = _stipQuotes(prefix_list.pop())
        # prefix_ref = _stipQuotes(prefix_list.pop())
        # prefix = prefix_ref + '.' + prefix_obj
        print("match columns only, new prefix: " + prefix)

        autocompleteList = []
        for item in self.allColumns:
            score = item.prefixMatchScore(prefix)
            if score:
                autocompleteList.append(CompletionItem(item.type, item.ident, score))

        if len(autocompleteList) > 0:
            return autocompleteList, True

        return None, False

# itm = CompletionItem('Function', 'common.testing()');
# print(str(itm))
# print(str(itm.parent))
# print(str(itm.name))
# print(str(itm.matchIdent))
# print(str(itm.matchSublimeCompletion))
# print(str(itm.prefixMatchScore('common.test')))
# print(str(itm.format()))
