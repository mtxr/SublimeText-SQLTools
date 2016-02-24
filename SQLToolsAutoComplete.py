import sublime_plugin, sublime

tableNames = []
columnNames = []

class SqlCompletePlugin(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        return self.get_autocomplete_list(prefix)
    def get_autocomplete_list(self, word):
        global tableNames
        global columnNames
        # return the array
        autocomplete_list = []
        for w in tableNames:
            try:
                if word.lower() in w.lower():
                    autocomplete_list.append(("{0}\t{1}".format(w, 'Table'), w))
            except UnicodeDecodeError:
                continue

        for w in columnNames:
            try:
                if word.lower() in w.lower():
                    autocomplete_list.append(("{0}\t{1}".format(w.split(".")[1], w.split(".")[0] + ' Column'), w))
            except UnicodeDecodeError:
                continue

        autocomplete_list.sort()

        return list(set(autocomplete_list))

    @staticmethod
    def setTableNames(tables):
        global tableNames
        tableNames = tables

    @staticmethod
    def setColumns(columns):
        global columnNames
        columnNames = columns
