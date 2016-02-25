import sublime_plugin, sublime, sys

tableNames = []
columnNames = []

class SqlCompletePlugin(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        if prefix == "":
            region = sublime.Region(locations[0], locations[0])
            view = sublime.active_window().active_view()
            try:
                prefix = view.substr(view.line(region)).split(" ").pop()
            except Exception:
                pass

        return self.get_autocomplete_list(prefix)

    def get_autocomplete_list(self, word):
        global tableNames
        global columnNames

        autocomplete_list = []
        for w in tableNames:
            try:
                if word.lower() in w.lower():
                    autocomplete_list.append(("{0}\t({1})".format(w, 'Table'), w))
            except UnicodeDecodeError:
                continue

        for w in columnNames:
            try:
                if word.lower() in w.lower():
                    autocomplete_list.append(("{0}\t({1})".format(w.split(".")[1], w.split(".")[0] + ' Col'), w.split(".")[1]))
            except Exception:
                continue

        autocomplete_list.sort()
        return (list(set(autocomplete_list)), sublime.INHIBIT_EXPLICIT_COMPLETIONS)

class SqlToolsAddAutoCompleteData(sublime_plugin.WindowCommand):
    def run(self, tables=[], columns=[]):
        global columnNames
        global tableNames
        columnNames = columns
        tableNames  = tables
