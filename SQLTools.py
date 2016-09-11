import sys, os

dirpath = os.path.dirname(__file__)
if not dirpath in sys.path:
    sys.path.append(dirpath)

import sublime, sublime_plugin, imp
import SQLToolsModels as STM

# force reloading models when update
try:
    # python 3.0 to 3.3
    import imp
    imp.reload(STM)
except Exception as e:
    pass

try:
    # python 3.4 and newer
    import importlib
    importlib.reload(STM)
except Exception as e:
    pass

class ST(sublime_plugin.EventListener):
    conn             = None
    history          = []
    tables           = []
    functions        = []
    columns          = []
    connectionList   = {}
    autoCompleteList = []

    @staticmethod
    def bootstrap():
        ST.connectionList = STM.Settings.getConnections()
        ST.checkDefaultConnection()

    @staticmethod
    def setAttrIfNotEmpty(attr, value):
        if type(value) is list and len(value) == 0:
            # sublime.message_dialog('Connection failed. Check your settings and try again.')
            return
        setattr(ST, attr, value)

    @staticmethod
    def loadConnectionData():
        if not ST.conn:
            return

        ST.conn.getTables(lambda tables: ST.setAttrIfNotEmpty('tables', tables))
        ST.conn.getColumns(lambda columns: ST.setAttrIfNotEmpty('columns', columns))
        ST.conn.getFunctions(lambda functions: ST.setAttrIfNotEmpty('functions', functions))

    @staticmethod
    def setConnection(index):
        if index < 0 or index > (len(ST.connectionList) - 1) :
            return


        connListNames = list(ST.connectionList.keys())
        connListNames.sort()
        ST.conn = ST.connectionList.get(connListNames[index])
        ST.loadConnectionData()

        STM.Log.debug('Connection {0} selected'.format(ST.conn))

    @staticmethod
    def showConnectionMenu():
        ST.connectionList = STM.Settings.getConnections()
        if len(ST.connectionList) == 0:
            sublime.message_dialog('You need to setup your connections first.')
            return

        menu = []
        for name, conn in ST.connectionList.items():
            menu.append(conn._quickPanel())
        menu.sort()
        STM.Window().show_quick_panel(menu, ST.setConnection)

    def on_query_completions(self, view, prefix, locations):
        if prefix == "":
            region = sublime.Region(locations[0], locations[0])
            try:
                prefix = view.substr(view.line(region)).split(" ").pop()
            except Exception:
                pass

        return self.getAutoCompleteList(prefix)

    def getAutoCompleteList(self, word):
        ST.autoCompleteList = []
        for w in ST.tables:
            try:
                if word.lower() in w.lower():
                    ST.autoCompleteList.append(("{0}\t({1})".format(w, 'Table'), w))
            except UnicodeDecodeError:
                continue

        for w in ST.columns:
            try:
                if word.lower() in w.lower():
                    ST.autoCompleteList.append(("{0}\t({1})".format(w.split(".")[1], w.split(".")[0] + ' Col'), w.split(".")[1]))
            except Exception:
                continue

        for w in ST.functions:
            try:
                if word.lower() in w.lower():
                    ST.autoCompleteList.append(("{0}\t({1})".format(w, 'Func'), w))
            except Exception:
                continue

        ST.autoCompleteList.sort()
        return (ST.autoCompleteList)

    @staticmethod
    def checkDefaultConnection():
        default = STM.Connection.loadDefaultConnectionName()
        if not default:
            return
        try:
            ST.conn = ST.connectionList.get(default)
            ST.loadConnectionData()
        except Exception as e:
            STM.Log.debug("Invalid connection setted")

    @staticmethod
    def getOutputPlace(name="SQLTools Result"):
        if not sublime.load_settings(STM.Const.SETTINGS_FILENAME).get('show_result_on_window'):
            resultContainer = STM.Window().create_output_panel(name)
            STM.Window().run_command("show_panel", {"panel": "output." + name})
        else:
            resultContainer = None
            views = STM.Window().views()
            for view in views:
                if view.name() == name:
                    resultContainer = view
                    STM.Window().focus_view(resultContainer)
                    break;
            if not resultContainer:
                resultContainer = STM.Window().new_file()
                resultContainer.set_name(name)

        resultContainer.set_scratch(True) # avoids prompting to save
        resultContainer.settings().set("word_wrap", "false")
        resultContainer.set_read_only(False)
        resultContainer.set_syntax_file('Packages/SQL/SQL.tmLanguage')
        # resultContainer.run_command('select_all')
        # resultContainer.run_command('left_delete')
        return resultContainer

    @staticmethod
    def display(content, panel=None):
        if not panel:
            panel = ST.getOutputPlace()
        panel.run_command('append', {'characters': content})
        panel.set_read_only(True)

    @staticmethod
    def toBuffer(content, name="", suffix="SQLTools Saved Query"):
        resultContainer = STM.Window().new_file()
        resultContainer.set_name(((name + " - ") if name != "" else "") + suffix)
        resultContainer.set_syntax_file('Packages/SQL/SQL.tmLanguage')
        resultContainer.run_command('append', {'characters': content})

#
# Commands
#

class StShowConnectionMenu(sublime_plugin.WindowCommand):
    def run (self):
        ST.showConnectionMenu()

class StShowRecords(sublime_plugin.WindowCommand):
    def run(self):
        if not ST.conn:
            ST.showConnectionMenu()
            return

        STM.Window().show_quick_panel(ST.tables, lambda index: ST.conn.getTableRecords(ST.tables[index], ST.display) if index != -1 else None)

class StDescTable(sublime_plugin.WindowCommand):
    def run(self):
        if not ST.conn:
            ST.showConnectionMenu()
            return

        STM.Window().show_quick_panel(ST.tables, lambda index: ST.conn.getTableDescription(ST.tables[index], ST.display) if index != -1 else None)

class StDescFunction(sublime_plugin.WindowCommand):
    def run(self):
        if not ST.conn:
            ST.showConnectionMenu()
            return

        # get everything until first occurence of "(", e.g. get "function_name" from "function_name(int)"
        STM.Window().show_quick_panel(ST.functions, lambda index: ST.conn.getFunctionDescription(ST.functions[index].split('(', 1)[0], ST.display) if index != -1 else None)

class StHistory(sublime_plugin.WindowCommand):
    def run(self):
        if not ST.conn:
            ST.showConnectionMenu()
            return

        if len(STM.History.queries) == 0:
            sublime.message_dialog('History is empty.')
            return
        try:
            STM.Window().show_quick_panel(STM.History.queries, lambda index: ST.conn.execute(STM.History.get(index), ST.display) if index != -1 else None)
        except Exception:
            pass

class StExecute(sublime_plugin.WindowCommand):
    def run(self):
        if not ST.conn:
            ST.showConnectionMenu()
            return

        query = STM.Selection.get()
        ST.conn.execute(query, ST.display)

class StSaveQuery(sublime_plugin.WindowCommand):
    def run(self):
        STM.Storage.promptQueryAlias()

class StListQueries(sublime_plugin.WindowCommand):
    def run(self, mode="run"):
        print(mode)
        if not ST.conn:
            ST.showConnectionMenu()
            return

        queries = STM.Storage.getSavedQueries().get('queries')

        if len(queries) == 0:
            sublime.message_dialog('No saved queries.')
            return

        queriesArray = []
        for alias, query in queries.items():
            print (alias, query)
            queriesArray.append([alias, query])
        queriesArray.sort()
        try:
            if mode == "run":
                STM.Window().show_quick_panel(queriesArray, lambda index: ST.conn.execute(queriesArray[index][1], ST.display) if index != -1 else None)
            else:
                STM.Window().show_quick_panel(queriesArray, lambda index: ST.toBuffer(queriesArray[index][1], queriesArray[index][0]) if index != -1 else None)
        except Exception:
            pass

class StRemoveSavedQuery(sublime_plugin.WindowCommand):
    def run(self):
        queries = STM.Storage.getSavedQueries().get('queries')

        if len(queries) == 0:
            sublime.message_dialog('No saved queries.')
            return

        queriesArray = []
        for alias, query in queries.items():
            print (alias, query)
            queriesArray.append([alias, query])
        queriesArray.sort()
        try:
            STM.Window().show_quick_panel(queriesArray, lambda index: STM.Storage.removeQuery(queriesArray[index][0]) if index != -1 else None)
        except Exception:
            pass

class StFormat(sublime_plugin.TextCommand):
    def run(self, edit):
        STM.Selection.formatSql(edit)

class StVersion(sublime_plugin.WindowCommand):
    def run(self):
        sublime.message_dialog('Using SQLTools ' + STM.VERSION)

def plugin_loaded():
    STM.Log.debug('%s loaded successfully' % (__name__))
    try:
        ST.bootstrap()
    except Exception as e:
        pass
