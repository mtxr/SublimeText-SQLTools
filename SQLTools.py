import sys
import os

dirpath = os.path.dirname(__file__)
if dirpath not in sys.path:
    sys.path.append(dirpath)

import sublime
import sublime_plugin
import SQLToolsModels as STM


class ST(sublime_plugin.EventListener):
    conn = None
    history = []
    tables = []
    functions = []
    columns = []
    connectionList = {}
    autoCompleteList = []

    @staticmethod
    def bootstrap():
        ST.connectionList = STM.Settings.getConnections()
        ST.checkDefaultConnection()

    @staticmethod
    def setAttrIfNotEmpty(attr, value):
        if isinstance(value, list) and len(value) == 0:
            return
        setattr(ST, attr, value)

    @staticmethod
    def loadConnectionData():
        if not ST.conn:
            return

        ST.conn.getTables(
            lambda tables: ST.setAttrIfNotEmpty('tables', tables))
        ST.conn.getColumns(
            lambda columns: ST.setAttrIfNotEmpty('columns', columns))
        ST.conn.getFunctions(
            lambda functions: ST.setAttrIfNotEmpty('functions', functions))

    @staticmethod
    def setConnection(index):
        if index < 0 or index > (len(ST.connectionList) - 1):
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
        for conn in ST.connectionList.values():
            menu.append(conn.toQuickPanel())
        menu.sort()
        STM.Window().show_quick_panel(menu, ST.setConnection)

    @staticmethod
    def on_query_completions(view, prefix, locations):
        if prefix == "":
            region = sublime.Region(locations[0], locations[0])
            try:
                prefix = view.substr(view.line(region)).split(" ").pop()
            except Exception:
                pass

        return ST.getAutoCompleteList(prefix)

    @staticmethod
    def getAutoCompleteList(word):
        ST.autoCompleteList = []
        for w in ST.tables:
            try:
                if word.lower() in w.lower():
                    ST.autoCompleteList.append(
                        ("{0}\t({1})".format(w, 'Table'), w))
            except UnicodeDecodeError:
                continue

        for w in ST.columns:
            try:
                if word.lower() in w.lower():
                    w = w.split(".")
                    ST.autoCompleteList.append(("{0}\t({1})".format(
                        w[1], w[0] + ' Col'), w[1]))
            except Exception:
                continue

        for w in ST.functions:
            try:
                if word.lower() in w.lower():
                    ST.autoCompleteList.append(
                        ("{0}\t({1})".format(w, 'Func'), w))
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
        except Exception:
            STM.Log.debug("Invalid connection setted")

    @staticmethod
    def getOutputPlace(name="SQLTools Result"):
        if not STM.Settings.get('show_result_on_window'):
            resultContainer = STM.Window().create_output_panel(name)
            STM.Window().run_command("show_panel", {"panel": "output." + name})
        else:
            resultContainer = None
            views = STM.Window().views()
            for view in views:
                if view.name() == name:
                    resultContainer = view
                    STM.Window().focus_view(resultContainer)
                    break
            if not resultContainer:
                resultContainer = STM.Window().new_file()
                resultContainer.set_name(name)

        resultContainer.set_scratch(True)  # avoids prompting to save
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
        resultContainer.set_name(
            ((name + " - ") if name != "" else "") + suffix)
        resultContainer.set_syntax_file('Packages/SQL/SQL.tmLanguage')
        resultContainer.run_command('append', {'characters': content})

#
# Commands
#


class StShowConnectionMenu(sublime_plugin.WindowCommand):
    @staticmethod
    def run():
        ST.showConnectionMenu()


class StShowRecords(sublime_plugin.WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.showConnectionMenu()
            return

        def cb(index):
            if index < 0:
                return None
            return ST.conn.getTableRecords(ST.tables[index], ST.display)

        STM.Window().show_quick_panel(ST.tables, cb)


class StDescTable(sublime_plugin.WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.showConnectionMenu()
            return

        def cb(index):
            if index < 0:
                return None
            return ST.conn.getTableDescription(ST.tables[index], ST.display)

        STM.Window().show_quick_panel(ST.tables, cb)


class StDescFunction(sublime_plugin.WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.showConnectionMenu()
            return

        def cb(index):
            if index < 0:
                return None
            functionName = ST.functions[index].split('(', 1)[0]
            return ST.conn.getFunctionDescription(functionName, ST.display)

        # get everything until first occurence of "(", e.g. get "function_name"
        # from "function_name(int)"
        STM.Window().show_quick_panel(ST.functions, cb)


class StHistory(sublime_plugin.WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.showConnectionMenu()
            return

        if len(STM.History.queries) == 0:
            sublime.message_dialog('History is empty.')
            return

        def cb(index):
            if index < 0:
                return None
            return ST.conn.execute(STM.History.get(index), ST.display)

        try:
            STM.Window().show_quick_panel(STM.History.queries, cb)
        except Exception:
            pass


class StExecute(sublime_plugin.WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.showConnectionMenu()
            return

        query = STM.Selection.get()
        ST.conn.execute(query, ST.display)


class StSaveQuery(sublime_plugin.WindowCommand):
    @staticmethod
    def run():
        STM.Storage.promptQueryAlias()


class StListQueries(sublime_plugin.WindowCommand):
    @staticmethod
    def run(mode="run"):
        if not ST.conn:
            ST.showConnectionMenu()
            return

        queries = STM.Storage.getSavedQueries().get('queries')

        if len(queries) == 0:
            sublime.message_dialog('No saved queries.')
            return

        options = []
        for alias, query in queries.items():
            options.append([alias, query])
        options.sort()

        def cb(index):
            if index < 0:
                return None

            param2 = ST.display if mode == "run" else options[index][0]
            func = ST.conn.execute if mode == "run" else ST.toBuffer
            return func(options[index][1], param2)

        try:
            STM.Window().show_quick_panel(options, cb)
        except Exception:
            pass


class StRemoveSavedQuery(sublime_plugin.WindowCommand):
    @staticmethod
    def run():
        queries = STM.Storage.getSavedQueries().get('queries')

        if len(queries) == 0:
            sublime.message_dialog('No saved queries.')
            return

        queriesArray = []
        for alias, query in queries.items():
            queriesArray.append([alias, query])
        queriesArray.sort()

        def cb(index):
            if index < 0:
                return None
            return STM.Storage.removeQuery(queriesArray[index][0])
        try:
            STM.Window().show_quick_panel(queriesArray, cb)
        except Exception:
            pass


class StFormat(sublime_plugin.TextCommand):
    @staticmethod
    def run(edit):
        STM.Selection.formatSql(edit)


class StVersion(sublime_plugin.WindowCommand):
    @staticmethod
    def run():
        sublime.message_dialog('Using SQLTools ' + STM.VERSION)


def plugin_loaded():
    # force reloading models when update
    try:
        # python 3.0 to 3.3
        import imp
        imp.reload(STM)
    except Exception:
        pass

    STM.Log.debug('%s loaded successfully' % (__name__))
    try:
        ST.bootstrap()
    except Exception:
        pass
