__version__ = "v0.6.6"

import sys
import os

import sublime
from sublime_plugin import WindowCommand, EventListener, TextCommand

from .SQLToolsAPI import Utils
from .SQLToolsAPI.Log import Log, Logger
from .SQLToolsAPI.Storage import Storage, Settings
from .SQLToolsAPI.Connection import Connection
from .SQLToolsAPI.History import History

USER_FOLDER                  = None
DEFAULT_FOLDER               = None
SETTINGS_FILENAME            = None
SETTINGS_FILENAME_DEFAULT    = None
CONNECTIONS_FILENAME         = None
CONNECTIONS_FILENAME_DEFAULT = None
QUERIES_FILENAME             = None
QUERIES_FILENAME_DEFAULT     = None
settings                     = None
queries                      = None
connections                  = None
history                      = None


def startPlugin():
    global USER_FOLDER, DEFAULT_FOLDER, SETTINGS_FILENAME, SETTINGS_FILENAME_DEFAULT, CONNECTIONS_FILENAME, CONNECTIONS_FILENAME_DEFAULT, QUERIES_FILENAME, QUERIES_FILENAME_DEFAULT, settings, queries, connections, history

    USER_FOLDER = os.path.join(sublime.packages_path(), 'User')
    DEFAULT_FOLDER = os.path.dirname(__file__)

    SETTINGS_FILENAME            = os.path.join(USER_FOLDER, "SQLTools.sublime-settings")
    SETTINGS_FILENAME_DEFAULT    = os.path.join(DEFAULT_FOLDER, "SQLTools.sublime-settings")
    CONNECTIONS_FILENAME         = os.path.join(USER_FOLDER, "SQLToolsConnections.sublime-settings")
    CONNECTIONS_FILENAME_DEFAULT = os.path.join(DEFAULT_FOLDER, "SQLToolsConnections.sublime-settings")
    QUERIES_FILENAME             = os.path.join(USER_FOLDER, "SQLToolsSavedQueries.sublime-settings")
    QUERIES_FILENAME_DEFAULT     = os.path.join(DEFAULT_FOLDER, "SQLToolsSavedQueries.sublime-settings")

    settings    = Settings(SETTINGS_FILENAME, default=SETTINGS_FILENAME_DEFAULT)
    queries     = Storage(QUERIES_FILENAME, default=QUERIES_FILENAME_DEFAULT)
    connections = Settings(CONNECTIONS_FILENAME, default=CONNECTIONS_FILENAME_DEFAULT)
    history     = History(settings.get('history_size', 100))

    Logger.setPackageVersion(__version__)
    Logger.setPackageName(__package__)
    Logger.setLogging(settings.get('debug', True))
    Connection.setTimeout(settings.get('thread_timeout', 5000))
    Connection.setHistoryManager(history)

    Log(__package__ + " Loaded!")


def getConnections():
    connectionsObj = {}

    # fixes #39 and #45
    if not connections:
        startPlugin()

    options = connections.get('connections', {})

    for name, config in options.items():
        connectionsObj[name] = Connection(name, config, settings=settings.all())

    # project settings
    try:
        options = Window().project_data().get('connections', {})
        for name, config in options.items():
            connectionsObj[name] = Connection(name, config, settings=settings.all())
    except Exception:
        pass

    return connectionsObj


def loadDefaultConnection():
    default = settings.get('default', False)
    if not default:
        return
    Log('Default database set to ' + default + '. Loading options and auto complete.')
    return default


def output(content, panel=None):
    if not panel:
        panel = getOutputPlace()
    panel.run_command('append', {'characters': content})
    panel.set_read_only(True)


def toNewTab(content, name="", suffix="SQLTools Saved Query"):
    resultContainer = Window().new_file()
    resultContainer.set_name(
        ((name + " - ") if name != "" else "") + suffix)
    resultContainer.set_syntax_file('Packages/SQL/SQL.tmLanguage')
    resultContainer.run_command('append', {'characters': content})


def getOutputPlace(name="SQLTools Result"):
        if not settings.get('show_result_on_window', True):
            resultContainer = Window().create_output_panel(name)
            Window().run_command("show_panel", {"panel": "output." + name})
        else:
            resultContainer = None
            views = Window().views()
            for view in views:
                if view.name() == name:
                    resultContainer = view
                    Window().focus_view(resultContainer)
                    break
            if not resultContainer:
                resultContainer = Window().new_file()
                resultContainer.set_name(name)

        resultContainer.set_scratch(True)  # avoids prompting to save
        resultContainer.settings().set("word_wrap", "false")
        resultContainer.set_read_only(False)
        resultContainer.set_syntax_file('Packages/SQL/SQL.tmLanguage')

        if settings.get('clear_output', False):
            resultContainer.run_command('select_all')
            resultContainer.run_command('left_delete')

        return resultContainer


def getSelection():
    text = []
    if View().sel():
        for region in View().sel():
            if region.empty():
                text.append(View().substr(View().line(region)))
            else:
                text.append(View().substr(region))
    return text


class ST(EventListener):
    conn             = None
    tables           = []
    functions        = []
    columns          = []
    connectionList   = None
    autoCompleteList = []

    @staticmethod
    def bootstrap():
        ST.connectionList = getConnections()
        ST.checkDefaultConnection()

    @staticmethod
    def checkDefaultConnection():
        default = loadDefaultConnection()
        if not default:
            return
        try:
            ST.conn = ST.connectionList.get(default)
            ST.loadConnectionData()
        except Exception:
            Log("Invalid connection setted")

    @staticmethod
    def loadConnectionData(tablesCallback=None, columnsCallback=None, functionsCallback=None):
        if not ST.conn:
            return

        def tbCallback(tables):
            setattr(ST, 'tables', tables)
            if tablesCallback:
                tablesCallback()

        def colCallback(columns):
            setattr(ST, 'columns', columns)
            if columnsCallback:
                columnsCallback()

        def funcCallback(functions):
            setattr(ST, 'functions', functions)
            if functionsCallback:
                functionsCallback()

        ST.conn.getTables(tbCallback)
        ST.conn.getColumns(colCallback)
        ST.conn.getFunctions(funcCallback)

    @staticmethod
    def setConnection(index, tablesCallback=None, columnsCallback=None, functionsCallback=None):
        if index < 0 or index > (len(ST.connectionList) - 1):
            return

        connListNames = list(ST.connectionList.keys())
        connListNames.sort()
        ST.conn = ST.connectionList.get(connListNames[index])

        ST.loadConnectionData(tablesCallback, columnsCallback, functionsCallback)

        Log('Connection {0} selected'.format(ST.conn))

    @staticmethod
    def selectConnection(tablesCallback=None, columnsCallback=None, functionsCallback=None):
        ST.connectionList = getConnections()
        if len(ST.connectionList) == 0:
            sublime.message_dialog('You need to setup your connections first.')
            return

        menu = []
        for name, conn in ST.connectionList.items():
            menu.append([name, conn._info()])
        menu.sort()
        Window().show_quick_panel(menu, lambda index: ST.setConnection(index, tablesCallback, columnsCallback, functionsCallback))

    @staticmethod
    def selectTable(callback):
        if len(ST.tables) == 0:
            sublime.message_dialog('Your database has no tables.')
            return

        Window().show_quick_panel(ST.tables, callback)

    @staticmethod
    def selectFunction(callback):
        if len(ST.functions) == 0:
            sublime.message_dialog('Your database has no functions.')
            return

        Window().show_quick_panel(ST.functions, callback)

    @staticmethod
    def on_query_completions(view, prefix, locations):
        completions = view.extract_completions(prefix)

        if prefix == "":
            region = sublime.Region(locations[0], locations[0])
            try:
                prefix = view.substr(view.line(region)).split(" ").pop()
            except Exception:
                pass

        selectors = settings.get('selectors', [])
        if not selectors:
            return completions + ST.getAutoCompleteList(prefix)
        for selector in selectors:
            if view.match_selector(locations[0], selector):
                return completions + ST.getAutoCompleteList(prefix)
        return None

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

# #
# # Commands
# #


# Usage for old keybindings defined by users
class StShowConnectionMenu(WindowCommand):
    @staticmethod
    def run():
        Window().run_command('st_select_connection')


class StSelectConnection(WindowCommand):
    @staticmethod
    def run():
        ST.selectConnection()


class StShowRecords(WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.selectConnection(tablesCallback=lambda: Window().run_command('st_show_records'))
            return

        def cb(index):
            if index < 0:
                return None
            return ST.conn.getTableRecords(ST.tables[index], output)

        ST.selectTable(cb)


class StDescTable(WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.selectConnection(tablesCallback=lambda: Window().run_command('st_desc_table'))
            return

        def cb(index):
            if index < 0:
                return None
            return ST.conn.getTableDescription(ST.tables[index], output)

        ST.selectTable(cb)


class StDescFunction(WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.selectConnection(functionsCallback=lambda: Window().run_command('st_desc_function'))
            return

        def cb(index):
            if index < 0:
                return None
            functionName = ST.functions[index].split('(', 1)[0]
            return ST.conn.getFunctionDescription(functionName, output)

        # get everything until first occurence of "(", e.g. get "function_name"
        # from "function_name(int)"
        ST.selectFunction(cb)


class StExecute(WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.selectConnection(tablesCallback=lambda: ST.conn.execute(getSelection(), output))
            return

        ST.conn.execute(getSelection(), output)


class StFormat(TextCommand):
    @staticmethod
    def run(edit):
        for region in View().sel():
            if region.empty():
                region = sublime.Region(0, View().size())
                selection = View().substr(region)
                View().replace(edit, region, Utils.formatSql(selection, settings.get('format', {})))
                View().set_syntax_file("Packages/SQL/SQL.tmLanguage")
            else:
                text = View().substr(region)
                View().replace(edit, region, Utils.formatSql(text, settings.get('format', {})))


class StVersion(WindowCommand):
    @staticmethod
    def run():
        sublime.message_dialog('Using {0} {1}'.format(__package__, __version__))


class StHistory(WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.selectConnection(functionsCallback=lambda: Window().run_command('st_history'))
            return

        if len(history.all()) == 0:
            sublime.message_dialog('History is empty.')
            return

        def cb(index):
            if index < 0:
                return None
            return ST.conn.execute(history.get(index), output)

        Window().show_quick_panel(history.all(), cb)


class StSaveQuery(WindowCommand):
    @staticmethod
    def run():
        query = getSelection()

        def cb(alias):
            queries.add(alias, query)
        Window().show_input_panel('Query alias', '', cb, None, None)


class StListQueries(WindowCommand):
    @staticmethod
    def run(mode="run"):
        if not ST.conn:
            ST.selectConnection(functionsCallback=lambda: Window().run_command('st_list_queries'))
            return

        queriesList = queries.all()
        if len(queriesList) == 0:
            sublime.message_dialog('No saved queries.')
            return

        options = []
        for alias, query in queriesList.items():
            options.append([str(alias), str(query)])
        options.sort()

        def cb(index):
            if index < 0:
                return None

            param2 = output if mode == "run" else options[index][0]
            func = ST.conn.execute if mode == "run" else toNewTab
            return func(options[index][1], param2)

        try:
            Window().show_quick_panel(options, cb)
        except Exception:
            pass


class StRemoveSavedQuery(WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.selectConnection(functionsCallback=lambda: Window().run_command('st_remove_saved_query'))
            return

        queriesList = queries.all()
        if len(queriesList) == 0:
            sublime.message_dialog('No saved queries.')
            return

        options = []
        for alias, query in queriesList.items():
            options.append([str(alias), str(query)])
        options.sort()

        def cb(index):
            if index < 0:
                return None

            return queries.delete(options[index][0])
        try:
            Window().show_quick_panel(options, cb)
        except Exception:
            pass


def Window():
    return sublime.active_window()


def View():
    return Window().active_view()


def reload():
    try:
        # python 3.0 to 3.3
        import imp
        imp.reload(sys.modules[__package__ + ".SQLToolsAPI"])
        imp.reload(sys.modules[__package__ + ".SQLToolsAPI.Utils"])
        imp.reload(sys.modules[__package__ + ".SQLToolsAPI.Storage"])
        imp.reload(sys.modules[__package__ + ".SQLToolsAPI.History"])
        imp.reload(sys.modules[__package__ + ".SQLToolsAPI.Log"])
        imp.reload(sys.modules[__package__ + ".SQLToolsAPI.Command"])
        imp.reload(sys.modules[__package__ + ".SQLToolsAPI.Connection"])
    except Exception as e:
        raise (e)
        pass

    try:
        ST.bootstrap()
    except Exception:
        pass


def plugin_loaded():
    try:
        from package_control import events

        if events.install(__name__):
            Log('Installed %s!' % events.install(__name__))
        elif events.post_upgrade(__name__):
            Log('Upgraded to %s!' % events.post_upgrade(__name__))
            sublime.message_dialog(('{0} was upgraded.' +
                                    'If you have any problem,' +
                                    'just restart your Sublime Text.'
                                    ).format(__name__)
                                   )

    except Exception:
        pass

    startPlugin()
    reload()
