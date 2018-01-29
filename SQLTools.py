__version__ = "v0.9.9"

import sys
import os
import re

import sublime
from sublime_plugin import WindowCommand, EventListener, TextCommand
from Default.paragraph import expand_to_paragraph

from .SQLToolsAPI import Utils
from .SQLToolsAPI.Log import Log, Logger
from .SQLToolsAPI.Storage import Storage, Settings
from .SQLToolsAPI.Connection import Connection
from .SQLToolsAPI.History import History
from .SQLToolsAPI.Completion import Completion

MESSAGE_RUNNING_CMD = 'Executing SQL command...'
SYNTAX_PLAIN_TEXT = 'Packages/Text/Plain text.tmLanguage'
SYNTAX_SQL = 'Packages/SQL/SQL.tmLanguage'
SQLTOOLS_SETTINGS_FILE = 'SQLTools.sublime-settings'
SQLTOOLS_CONNECTIONS_FILE = 'SQLToolsConnections.sublime-settings'
SQLTOOLS_QUERIES_FILE = 'SQLToolsSavedQueries.sublime-settings'

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


def getSublimeUserFolder():
    return os.path.join(sublime.packages_path(), 'User')


def startPlugin():
    global USER_FOLDER, DEFAULT_FOLDER
    global SETTINGS_FILENAME, SETTINGS_FILENAME_DEFAULT
    global CONNECTIONS_FILENAME, CONNECTIONS_FILENAME_DEFAULT
    global QUERIES_FILENAME, QUERIES_FILENAME_DEFAULT
    global settings, queries, connections, history

    USER_FOLDER = getSublimeUserFolder()
    DEFAULT_FOLDER = os.path.dirname(__file__)

    SETTINGS_FILENAME            = os.path.join(USER_FOLDER, SQLTOOLS_SETTINGS_FILE)
    SETTINGS_FILENAME_DEFAULT    = os.path.join(DEFAULT_FOLDER, SQLTOOLS_SETTINGS_FILE)
    CONNECTIONS_FILENAME         = os.path.join(USER_FOLDER, SQLTOOLS_CONNECTIONS_FILE)
    CONNECTIONS_FILENAME_DEFAULT = os.path.join(DEFAULT_FOLDER, SQLTOOLS_CONNECTIONS_FILE)
    QUERIES_FILENAME             = os.path.join(USER_FOLDER, SQLTOOLS_QUERIES_FILE)
    QUERIES_FILENAME_DEFAULT     = os.path.join(DEFAULT_FOLDER, SQLTOOLS_QUERIES_FILE)

    try:
        settings    = Settings(SETTINGS_FILENAME, default=SETTINGS_FILENAME_DEFAULT)
    except Exception as e:
        msg = __package__ + ": Failed to parse " + SQLTOOLS_SETTINGS_FILE + " file"
        print(msg + "\nError: " + str(e))
        Window().status_message(msg)

    try:
        connections = Settings(CONNECTIONS_FILENAME, default=CONNECTIONS_FILENAME_DEFAULT)
    except Exception as e:
        msg = __package__ + ": Failed to parse " + SQLTOOLS_CONNECTIONS_FILE + " file"
        print(msg + "\nError: " + str(e))
        Window().status_message(msg)

    queries     = Storage(QUERIES_FILENAME, default=QUERIES_FILENAME_DEFAULT)
    history     = History(settings.get('history_size', 100))

    Logger.setPackageVersion(__version__)
    Logger.setPackageName(__package__)
    Logger.setLogging(settings.get('debug', True))
    Connection.setTimeout(settings.get('thread_timeout', 15))
    Connection.setHistoryManager(history)

    Log(__package__ + " Loaded!")


def getConnections():
    connectionsObj = {}

    # fixes #39 and #45
    if not connections:
        startPlugin()

    options = connections.get('connections', {})

    for name, config in options.items():
        connectionsObj[name] = createConnection(name, config, settings=settings.all())

    # project settings
    projectData = Window().project_data()
    if projectData:
        options = projectData.get('connections', {})
        for name, config in options.items():
            connectionsObj[name] = createConnection(name, config, settings=settings.all())

    return connectionsObj


def createConnection(name, config, settings):
    newConnection = None
    # if DB cli binary could not be found in path a FileNotFoundError is thrown
    try:
        newConnection = Connection(name, config, settings=settings)
    except FileNotFoundError as e:
        # use only first line of the Exception in status message
        Window().status_message(__package__ + ": " + str(e).splitlines()[0])
        raise e
    return newConnection


def loadDefaultConnection():
    default = connections.get('default', False)
    if not default:
        return
    Log('Default database set to ' + default + '. Loading options and auto complete.')
    return default


def createOutput(panel=None, syntax=None, prependText=None):
    onInitialOutput = None
    if not panel:
        panel, onInitialOutput = getOutputPlace(syntax)
    if prependText:
        panel.run_command('append', {'characters': str(prependText)})

    initial = True

    def append(outputContent):
        nonlocal initial
        if initial:
            initial = False
            if onInitialOutput:
                onInitialOutput()

        # append content
        panel.set_read_only(False)
        panel.run_command('append', {'characters': outputContent})
        panel.set_read_only(True)

    return append


def toNewTab(content, name="", suffix="SQLTools Saved Query"):
    resultContainer = Window().new_file()
    resultContainer.set_name(
        ((name + " - ") if name != "" else "") + suffix)
    resultContainer.set_syntax_file(SYNTAX_SQL)
    resultContainer.run_command('append', {'characters': content})


def insertContent(content):
    view = View()
    # getting the settings local to this view/tab
    settings = view.settings()
    # saving the original settings for "auto_indent", or True if none set
    autoIndent = settings.get('auto_indent', True)
    # turn off automatic indenting otherwise the tabbing of the original
    # string is not respected after a newline is encountered
    settings.set('auto_indent', False)
    view.run_command('insert', {'characters': content})
    # restore "auto_indent" setting
    settings.set('auto_indent', autoIndent)


def getOutputPlace(syntax=None, name="SQLTools Result"):
    showResultOnWindow = settings.get('show_result_on_window', False)
    if not showResultOnWindow:
        resultContainer = Window().find_output_panel(name)
        if resultContainer is None:
            resultContainer = Window().create_output_panel(name)
    else:
        resultContainer = None
        views = Window().views()
        for view in views:
            if view.name() == name:
                resultContainer = view
                break
        if not resultContainer:
            resultContainer = Window().new_file()
            resultContainer.set_name(name)

    resultContainer.set_scratch(True)  # avoids prompting to save
    resultContainer.set_read_only(True)
    resultContainer.settings().set("word_wrap", "false")

    def onInitialOutputCallback():
        if settings.get('clear_output', False):
            resultContainer.set_read_only(False)
            resultContainer.run_command('select_all')
            resultContainer.run_command('left_delete')
            resultContainer.set_read_only(True)

        # set custom syntax highlight, only if one was passed explicitly,
        # otherwise use Plain Text syntax
        if syntax:
            # if custom and SQL related, use that, otherwise defaults to SQL
            if 'sql' in syntax.lower():
                resultContainer.set_syntax_file(syntax)
            else:
                resultContainer.set_syntax_file(SYNTAX_SQL)
        else:
            resultContainer.set_syntax_file(SYNTAX_PLAIN_TEXT)

        # hide previously set command running message (if any)
        Window().status_message('')

        if not showResultOnWindow:
            # if case this is an output pannel, show it
            Window().run_command("show_panel", {"panel": "output." + name})

        if settings.get('focus_on_result', False):
            Window().focus_view(resultContainer)

    return resultContainer, onInitialOutputCallback


def getSelectionText():
    text = []

    selectionRegions = getSelectionRegions()

    if not selectionRegions:
        return text

    for region in selectionRegions:
        text.append(View().substr(region))

    return text


def getSelectionRegions():
    expandedRegions = []

    if not View().sel():
        return None

    # If we would need to expand the empty selection, then which type:
    #   'file', 'view' = use text of current view
    #   'paragraph' =  paragraph(s) (text between newlines)
    #   'line' = current line(s)
    expandTo = settings.get('expand_to', 'file')
    if not expandTo:
        expandTo = 'file'

    # keep compatibility with previous settings
    expandToParagraph = settings.get('expand_to_paragraph')
    if expandToParagraph is True:
        expandTo = 'paragraph'

    expandTo = str(expandTo).strip()
    if expandTo not in ['file', 'view', 'paragraph', 'line']:
        expandTo = 'file'

    for region in View().sel():
        # if user did not select anything - expand selection,
        # otherwise use the currently selected region
        if region.empty():
            if expandTo in ['file', 'view']:
                region = sublime.Region(0, View().size())
                # no point in further iterating over selections, just use entire file
                return [region]
            elif expandTo == 'paragraph':
                region = expand_to_paragraph(View(), region.b)
            else:
                # expand to line
                region = View().line(region)

        # even if we could not expand, avoid adding empty regions
        if not region.empty():
            expandedRegions.append(region)

    return expandedRegions


def getCurrentSyntax():
    view = View()
    currentSyntax = None
    if view:
        currentSyntax = view.settings().get('syntax')
    return currentSyntax


class ST(EventListener):
    conn             = None
    tables           = []
    columns          = []
    functions        = []
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
        # clear list of identifiers in case connection is changed
        ST.tables = []
        ST.columns = []
        ST.functions = []

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
            menu.append([name, conn.info()])
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
        # skip completions, if no connection
        if ST.conn is None:
            return None

        if not len(locations):
            return None

        selectors = settings.get('selectors', [])
        selectorMatched = False
        if selectors:
            for selector in selectors:
                if view.match_selector(locations[0], selector):
                    selectorMatched = True
                    break

        if not selectorMatched:
            return None

        # completions enabled? if yes, determine which type
        completionType = settings.get('autocompletion', 'smart')
        if not completionType:
            return None         # autocompletion disabled
        completionType = str(completionType).strip()
        if completionType not in ['basic', 'smart']:
            completionType = 'smart'

        # no completions inside strings
        if view.match_selector(locations[0], 'string'):
            return None

        # sublimePrefix = prefix
        # sublimeCompletions = view.extract_completions(sublimePrefix, locations[0])

        # preferably get prefix ourselves instead of using default sublime "prefix".
        # Sublime will return only last portion of this preceding text. Given:
        # SELECT table.col|
        # sublime will return: "col", and we need: "table.col"
        # to know more precisely which completions are more appropriate

        # get a Region that starts at the beginning of current line
        # and ends at current cursor position
        currentPoint = locations[0]
        lineStartPoint = view.line(currentPoint).begin()
        lineStartToLocation = sublime.Region(lineStartPoint, currentPoint)
        try:
            lineStr = view.substr(lineStartToLocation)
            prefix = re.split('[^`\"\w.\$]+', lineStr).pop()
        except Exception as e:
            Log(e)

        # determine desired keywords case from settings
        formatSettings = settings.get('format', {})
        keywordCase = formatSettings.get('keyword_case', 'upper')
        uppercaseKeywords = keywordCase.lower().startswith('upper')

        inhibit = False
        completion = Completion(uppercaseKeywords, ST.tables, ST.columns, ST.functions)

        if completionType == 'basic':
            ST.autoCompleteList = completion.getBasicAutoCompleteList(prefix)
        else:
            # use current paragraph as sql text to parse
            sqlRegion = expand_to_paragraph(view, currentPoint)
            sql = view.substr(sqlRegion)
            sqlToCursorRegion = sublime.Region(sqlRegion.begin(), currentPoint)
            sqlToCursor = view.substr(sqlToCursorRegion)
            ST.autoCompleteList, inhibit = completion.getAutoCompleteList(prefix, sql, sqlToCursor)

        # safe check here, so even if we return empty completions and inhibit is true
        # we return empty completions to show default sublime completions
        if ST.autoCompleteList is None or len(ST.autoCompleteList) == 0:
            return None

        if inhibit:
            return (ST.autoCompleteList, sublime.INHIBIT_WORD_COMPLETIONS)

        return ST.autoCompleteList


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
            Window().status_message(MESSAGE_RUNNING_CMD)
            tableName = ST.tables[index]
            prependText = 'Table "{tableName}"\n'.format(tableName=tableName)
            return ST.conn.getTableRecords(
                tableName,
                createOutput(prependText=prependText))

        ST.selectTable(cb)


class StDescTable(WindowCommand):
    @staticmethod
    def run():
        currentSyntax = getCurrentSyntax()

        if not ST.conn:
            ST.selectConnection(tablesCallback=lambda: Window().run_command('st_desc_table'))
            return

        def cb(index):
            if index < 0:
                return None
            Window().status_message(MESSAGE_RUNNING_CMD)
            return ST.conn.getTableDescription(ST.tables[index], createOutput(syntax=currentSyntax))

        ST.selectTable(cb)


class StDescFunction(WindowCommand):
    @staticmethod
    def run():
        currentSyntax = getCurrentSyntax()

        if not ST.conn:
            ST.selectConnection(functionsCallback=lambda: Window().run_command('st_desc_function'))
            return

        def cb(index):
            if index < 0:
                return None
            Window().status_message(MESSAGE_RUNNING_CMD)
            functionName = ST.functions[index].split('(', 1)[0]
            return ST.conn.getFunctionDescription(functionName, createOutput(syntax=currentSyntax))

        # get everything until first occurrence of "(", e.g. get "function_name"
        # from "function_name(int)"
        ST.selectFunction(cb)


class StExplainPlan(WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.selectConnection(tablesCallback=lambda: Window().run_command('st_explain_plan'))
            return

        Window().status_message(MESSAGE_RUNNING_CMD)
        ST.conn.explainPlan(getSelectionText(), createOutput())


class StExecute(WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.selectConnection(tablesCallback=lambda: Window().run_command('st_execute'))
            return

        Window().status_message(MESSAGE_RUNNING_CMD)
        ST.conn.execute(getSelectionText(), createOutput())


class StExecuteAll(WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.selectConnection(tablesCallback=lambda: Window().run_command('st_execute_all'))
            return

        Window().status_message(MESSAGE_RUNNING_CMD)
        allText = View().substr(sublime.Region(0, View().size()))
        ST.conn.execute(allText, createOutput())


class StFormat(TextCommand):
    @staticmethod
    def run(edit):
        selectionRegions = getSelectionRegions()

        if not selectionRegions:
            return

        for region in selectionRegions:
            textToFormat = View().substr(region)
            View().replace(edit, region, Utils.formatSql(textToFormat, settings.get('format', {})))


class StFormatAll(TextCommand):
    @staticmethod
    def run(edit):
        region = sublime.Region(0, View().size())
        textToFormat = View().substr(region)
        View().replace(edit, region, Utils.formatSql(textToFormat, settings.get('format', {})))


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
            return ST.conn.execute(history.get(index), createOutput())

        Window().show_quick_panel(history.all(), cb)


class StSaveQuery(WindowCommand):
    @staticmethod
    def run():
        query = getSelectionText()

        def cb(alias):
            queries.add(alias, query)
        Window().show_input_panel('Query alias', '', cb, None, None)


class StListQueries(WindowCommand):
    @staticmethod
    def run(mode="run"):
        if mode == "run" and not ST.conn:
            ST.selectConnection(functionsCallback=lambda: Window().run_command('st_list_queries',
                                                                               {'mode': mode}))
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

            alias, query = options[index]
            if mode == "run":
                ST.conn.execute(query, createOutput())
            elif mode == "insert":
                insertContent(query)
            else:
                toNewTab(query, alias)

            return

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
        imp.reload(sys.modules[__package__ + ".SQLToolsAPI.Completion"])
        imp.reload(sys.modules[__package__ + ".SQLToolsAPI.Storage"])
        imp.reload(sys.modules[__package__ + ".SQLToolsAPI.History"])
        imp.reload(sys.modules[__package__ + ".SQLToolsAPI.Log"])
        imp.reload(sys.modules[__package__ + ".SQLToolsAPI.Command"])
        imp.reload(sys.modules[__package__ + ".SQLToolsAPI.Connection"])
    except Exception as e:
        raise (e)

    try:
        ST.bootstrap()
    except Exception:
        pass


def plugin_loaded():
    # this ensures we have empty settings file in 'User' directory during first start
    # otherwise sublime will copy entire contents of 'SQLTools.sublime-settings'
    # which is not desirable and prevents future changes to queries and other
    # sensible defaults defined in settings file, as those would be overridden by content
    # from older versions of SQLTools in 'User\SQLTools.sublime-settings'
    sublimeUserFolder = getSublimeUserFolder()
    userSettingFile = os.path.join(sublimeUserFolder, SQLTOOLS_SETTINGS_FILE)
    if not os.path.isfile(userSettingFile):
        # create empty settings file in 'User' folder
        sublime.save_settings(SQLTOOLS_SETTINGS_FILE)

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
