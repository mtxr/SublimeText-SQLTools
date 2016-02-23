import sublime_plugin, sublime

class SqlCompletePlugin(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        return self.get_autocomplete_list(prefix)
    def get_autocomplete_list(self, word):
        global tableNames
        completions = list(set(tableNames))
        completions.sort()
        # return the array
        print (word)
        autocomplete_list = []
        for w in tableNames:
            try:
                if word.lower() in w.lower():
                    autocomplete_list.append((w, w))
            except UnicodeDecodeError:
                continue
        return autocomplete_list
