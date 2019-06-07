__version__ = "v0.9.12"

import sys
import os
import re
import logging
from collections import OrderedDict

import sublime
from sublime_plugin import WindowCommand, EventListener, TextCommand
from Default.paragraph import expand_to_paragraph

from .SQLToolsAPI import Utils
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
settingsStore                = None
queriesStore                 = None
connectionsStore             = None
historyStore                 = None

# create pluggin logger
DEFAULT_LOG_LEVEL = logging.WARNING
plugin_logger = logging.getLogger(__package__)
# some plugins are not playing by the rules and configure the root loger
plugin_logger.propagate = False
if not plugin_logger.handlers:
    plugin_logger_handler = logging.StreamHandler()
    plugin_logger_formatter = logging.Formatter("[{name}] {levelname}: {message}", style='{')
    plugin_logger_handler.setFormatter(plugin_logger_formatter)
    plugin_logger.addHandler(plugin_logger_handler)
plugin_logger.setLevel(DEFAULT_LOG_LEVEL)
logger = logging.getLogger(__name__)


def getSublimeUserFolder():
    return os.path.join(sublime.packages_path(), 'User')


def startPlugin():
    global USER_FOLDER, DEFAULT_FOLDER
    global SETTINGS_FILENAME, SETTINGS_FILENAME_DEFAULT
    global CONNECTIONS_FILENAME, CONNECTIONS_FILENAME_DEFAULT
    global QUERIES_FILENAME, QUERIES_FILENAME_DEFAULT
    global settingsStore, queriesStore, connectionsStore, historyStore

    USER_FOLDER = getSublimeUserFolder()
    DEFAULT_FOLDER = os.path.dirname(__file__)

    SETTINGS_FILENAME            = os.path.join(USER_FOLDER, SQLTOOLS_SETTINGS_FILE)
    SETTINGS_FILENAME_DEFAULT    = os.path.join(DEFAULT_FOLDER, SQLTOOLS_SETTINGS_FILE)
    CONNECTIONS_FILENAME         = os.path.join(USER_FOLDER, SQLTOOLS_CONNECTIONS_FILE)
    CONNECTIONS_FILENAME_DEFAULT = os.path.join(DEFAULT_FOLDER, SQLTOOLS_CONNECTIONS_FILE)
    QUERIES_FILENAME             = os.path.join(USER_FOLDER, SQLTOOLS_QUERIES_FILE)
    QUERIES_FILENAME_DEFAULT     = os.path.join(DEFAULT_FOLDER, SQLTOOLS_QUERIES_FILE)

    try:
        settingsStore = Settings(SETTINGS_FILENAME, default=SETTINGS_FILENAME_DEFAULT)
    except Exception as e:
        msg = '{0}: Failed to parse {1} file'.format(__package__, SQLTOOLS_SETTINGS_FILE)
        logging.exception(msg)
        Window().status_message(msg)

    try:
        connectionsStore = Settings(CONNECTIONS_FILENAME, default=CONNECTIONS_FILENAME_DEFAULT)
    except Exception as e:
        msg = '{0}: Failed to parse {1} file'.format(__package__, SQLTOOLS_CONNECTIONS_FILE)
        logging.exception(msg)
        Window().status_message(msg)

    queriesStore = Storage(QUERIES_FILENAME, default=QUERIES_FILENAME_DEFAULT)
    historyStore = History(settingsStore.get('history_size', 100))

    if settingsStore.get('debug', False):
        plugin_logger.setLevel(logging.DEBUG)
    else:
        plugin_logger.setLevel(DEFAULT_LOG_LEVEL)

    Connection.setTimeout(settingsStore.get('thread_timeout', 15))
    Connection.setHistoryManager(historyStore)

    logger.info('plugin (re)loaded')
    logger.info('version %s', __version__)


def readConnections():
    mergedConnections = {}

    # fixes #39 and #45
    if not connectionsStore:
        startPlugin()

    # global connections
    globalConnectionsDict = connectionsStore.get('connections', {})
    # project-specific connections
    projectConnectionsDict = {}
    projectData = Window().project_data()
    if projectData:
        projectConnectionsDict = projectData.get('connections', {})

    # merge connections
    mergedConnections = globalConnectionsDict.copy()
    mergedConnections.update(projectConnectionsDict)

    ordered = OrderedDict(sorted(mergedConnections.items()))

    return ordered


def getDefaultConnectionName():
    default = connectionsStore.get('default', False)
    if not default:
        return
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
    viewSettings = view.settings()
    # saving the original settings for "auto_indent", or True if none set
    autoIndent = viewSettings.get('auto_indent', True)
    # turn off automatic indenting otherwise the tabbing of the original
    # string is not respected after a newline is encountered
    viewSettings.set('auto_indent', False)
    view.run_command('insert', {'characters': content})
    # restore "auto_indent" setting
    viewSettings.set('auto_indent', autoIndent)


def getOutputPlace(syntax=None, name="SQLTools Result"):
    showResultOnWindow = settingsStore.get('show_result_on_window', False)
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
        if settingsStore.get('clear_output', False):
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

        if settingsStore.get('focus_on_result', False):
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
    expandTo = settingsStore.get('expand_to', 'file')
    if not expandTo:
        expandTo = 'file'

    # keep compatibility with previous settings
    expandToParagraph = settingsStore.get('expand_to_paragraph')
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
    connectionDict   = None
    conn             = None
    tables           = []
    columns          = []
    functions        = []
    completion       = None

    @staticmethod
    def bootstrap():
        ST.connectionDict = readConnections()
        ST.setDefaultConnection()

    @staticmethod
    def setDefaultConnection():
        default = getDefaultConnectionName()
        if not default:
            return
        if default not in ST.connectionDict:
            logger.error('connection "%s" set as default, but it does not exists', default)
            return
        logger.info('default connection is set to "%s"', default)
        ST.setConnection(default)

    @staticmethod
    def setConnection(connectionName, callback=None):
        if not connectionName:
            return

        if connectionName not in ST.connectionDict:
            return

        settings = settingsStore.all()
        config = ST.connectionDict.get(connectionName)

        promptKeys = [key for key, value in config.items() if value is None]
        promptDict = {}
        logger.info('[setConnection] prompt keys {}'.format(promptKeys))

        def mergeConfig(config, promptedKeys=None):
            merged = config.copy()
            if promptedKeys:
                merged.update(promptedKeys)
            return merged

        def createConnection(connectionName, config, settings, callback=None):
            # if DB cli binary could not be found in path a FileNotFoundError is thrown
            try:
                ST.conn = Connection(connectionName, config, settings=settings)
            except FileNotFoundError as e:
                # use only first line of the Exception in status message
                Window().status_message(__package__ + ": " + str(e).splitlines()[0])
                raise e
            ST.loadConnectionData(callback)

        if not promptKeys:
            createConnection(connectionName, config, settings, callback)
            return


        def setMissingKey(key, value):
            nonlocal promptDict
            if value is None:
                return
            promptDict[key] = value
            if promptKeys:
                promptNext()
            else:
                merged = mergeConfig(config, promptDict)
                createConnection(connectionName, merged, settings, callback)

        def promptNext():
            nonlocal promptKeys
            if not promptKeys:
                merged = mergeConfig(config, promptDict)
                createConnection(connectionName, merged, settings, callback)
            key = promptKeys.pop();
            Window().show_input_panel(
                    'Connection ' + key,
                    '',
                    lambda userInput: setMissingKey(key, userInput),
                    None,
                    None)

        promptNext()

    @staticmethod
    def loadConnectionData(callback=None):
        # clear the list of identifiers (in case connection is changed)
        ST.tables = []
        ST.columns = []
        ST.functions = []
        ST.completion = None
        objectsLoaded = 0

        if not ST.conn:
            return

        def afterAllDataHasLoaded():
            ST.completion = Completion(ST.tables, ST.columns, ST.functions, settings=settingsStore)
            logger.info('completions loaded')
            if (callback):
                callback()

        def tablesCallback(tables):
            ST.tables = tables
            nonlocal objectsLoaded
            objectsLoaded += 1
            logger.info('loaded tables : "{0}"'.format(tables))
            if objectsLoaded == 3:
                afterAllDataHasLoaded()

        def columnsCallback(columns):
            ST.columns = columns
            nonlocal objectsLoaded
            objectsLoaded += 1
            logger.info('loaded columns : "{0}"'.format(columns))
            if objectsLoaded == 3:
                afterAllDataHasLoaded()

        def functionsCallback(functions):
            ST.functions = functions
            nonlocal objectsLoaded
            objectsLoaded += 1
            logger.info('loaded functions: "{0}"'.format(functions))
            if objectsLoaded == 3:
                logger.info('all objects loaded')
                afterAllDataHasLoaded()

        ST.conn.getTables(tablesCallback)
        ST.conn.getColumns(columnsCallback)
        ST.conn.getFunctions(functionsCallback)

    @staticmethod
    def selectConnectionQuickPanel(callback=None):
        ST.connectionDict = readConnections()
        if len(ST.connectionDict) == 0:
            sublime.message_dialog('You need to setup your connections first.')
            return

        def connectionMenuList(connDictionary):
            menuItemsList = []
            template = '{dbtype}://{user}{host}{port}{db}'
            for name, config in ST.connectionDict.items():
                dbtype = config.get('type', '')
                user = '{}@'.format(config.get('username', '')) if 'username' in config else ''
                # user = config.get('username', '')
                host=config.get('host', '')
                port = ':{}'.format(config.get('port', '')) if 'port' in config else ''
                db = '/{}'.format(config.get('database', '')) if 'database' in config else ''
                connectionInfo = template.format(
                    dbtype=dbtype,
                    user=user,
                    host=host,
                    port=port,
                    db=db)
                menuItemsList.append([name, connectionInfo])
                menuItemsList.sort()
            return menuItemsList

        def onConnectionSelected(index, callback):
            menuItemsList = connectionMenuList(ST.connectionDict)
            if index < 0 or index >= len(menuItemsList):
                return
            connectionName = menuItemsList[index][0]
            ST.setConnection(connectionName, callback)
            logger.info('Connection "{0}" selected'.format(connectionName))

        menu = connectionMenuList(ST.connectionDict)
        # show pannel with callback above
        Window().show_quick_panel(menu, lambda index: onConnectionSelected(index, callback))

    @staticmethod
    def showTablesQuickPanel(callback):
        if len(ST.tables) == 0:
            sublime.message_dialog('Your database has no tables.')
            return

        ST.showQuickPanelWithSelection(ST.tables, callback)

    @staticmethod
    def showFunctionsQuickPanel(callback):
        if len(ST.functions) == 0:
            sublime.message_dialog('Your database has no functions.')
            return

        ST.showQuickPanelWithSelection(ST.functions, callback)

    @staticmethod
    def showQuickPanelWithSelection(arrayOfValues, callback):
        w = Window();
        view = w.active_view()
        selection = view.sel()[0]

        initialText = ''
        # ignore obvious non-identifier selections
        if selection.size() <= 128:
            (row_begin,_) = view.rowcol(selection.begin())
            (row_end,_) = view.rowcol(selection.end())
            # only consider selections within same line
            if row_begin == row_end:
                initialText = view.substr(selection)

        w.show_quick_panel(arrayOfValues, callback)
        w.run_command('insert', {'characters': initialText})
        w.run_command("select_all")

    @staticmethod
    def on_query_completions(view, prefix, locations):
        # skip completions, if no connection
        if ST.conn is None:
            return None

        if ST.completion is None:
            return None

        if ST.completion.isDisabled():
            return None

        if not len(locations):
            return None

        ignoreSelectors = ST.completion.getIgnoreSelectors()
        if ignoreSelectors:
            for selector in ignoreSelectors:
                if view.match_selector(locations[0], selector):
                    return None

        activeSelectors = ST.completion.getActiveSelectors()
        if activeSelectors:
            for selector in activeSelectors:
                if view.match_selector(locations[0], selector):
                    break
            else:
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
            logger.debug(e)

        # use current paragraph as sql text to parse
        sqlRegion = expand_to_paragraph(view, currentPoint)
        sql = view.substr(sqlRegion)
        sqlToCursorRegion = sublime.Region(sqlRegion.begin(), currentPoint)
        sqlToCursor = view.substr(sqlToCursorRegion)

        # get completions
        autoCompleteList, inhibit = ST.completion.getAutoCompleteList(prefix, sql, sqlToCursor)

        # safe check here, so even if we return empty completions and inhibit is true
        # we return empty completions to show default sublime completions
        if autoCompleteList is None or len(autoCompleteList) == 0:
            return None

        if inhibit:
            return (autoCompleteList, sublime.INHIBIT_WORD_COMPLETIONS)

        return autoCompleteList


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
        ST.selectConnectionQuickPanel()


class StShowRecords(WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.selectConnectionQuickPanel(callback=lambda: Window().run_command('st_show_records'))
            return

        def onTableSelected(index):
            if index < 0:
                return None
            Window().status_message(MESSAGE_RUNNING_CMD)
            tableName = ST.tables[index]
            prependText = 'Table "{tableName}"\n'.format(tableName=tableName)
            return ST.conn.getTableRecords(
                tableName,
                createOutput(prependText=prependText))

        ST.showTablesQuickPanel(callback=onTableSelected)


class StDescTable(WindowCommand):
    @staticmethod
    def run():
        currentSyntax = getCurrentSyntax()

        if not ST.conn:
            ST.selectConnectionQuickPanel(callback=lambda: Window().run_command('st_desc_table'))
            return

        def onTableSelected(index):
            if index < 0:
                return None
            Window().status_message(MESSAGE_RUNNING_CMD)
            return ST.conn.getTableDescription(ST.tables[index], createOutput(syntax=currentSyntax))

        ST.showTablesQuickPanel(callback=onTableSelected)


class StDescFunction(WindowCommand):
    @staticmethod
    def run():
        currentSyntax = getCurrentSyntax()

        if not ST.conn:
            ST.selectConnectionQuickPanel(callback=lambda: Window().run_command('st_desc_function'))
            return

        def onFunctionSelected(index):
            if index < 0:
                return None
            Window().status_message(MESSAGE_RUNNING_CMD)
            functionName = ST.functions[index].split('(', 1)[0]
            return ST.conn.getFunctionDescription(functionName, createOutput(syntax=currentSyntax))

        # get everything until first occurrence of "(", e.g. get "function_name"
        # from "function_name(int)"
        ST.showFunctionsQuickPanel(callback=onFunctionSelected)


class StRefreshConnectionData(WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            return
        ST.loadConnectionData()


class StExplainPlan(WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.selectConnectionQuickPanel(callback=lambda: Window().run_command('st_explain_plan'))
            return

        Window().status_message(MESSAGE_RUNNING_CMD)
        ST.conn.explainPlan(getSelectionText(), createOutput())


class StExecute(WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.selectConnectionQuickPanel(callback=lambda: Window().run_command('st_execute'))
            return

        Window().status_message(MESSAGE_RUNNING_CMD)
        ST.conn.execute(getSelectionText(), createOutput())


class StExecuteAll(WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.selectConnectionQuickPanel(callback=lambda: Window().run_command('st_execute_all'))
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
            View().replace(edit, region, Utils.formatSql(textToFormat, settingsStore.get('format', {})))


class StFormatAll(TextCommand):
    @staticmethod
    def run(edit):
        region = sublime.Region(0, View().size())
        textToFormat = View().substr(region)
        View().replace(edit, region, Utils.formatSql(textToFormat, settingsStore.get('format', {})))


class StVersion(WindowCommand):
    @staticmethod
    def run():
        sublime.message_dialog('Using {0} {1}'.format(__package__, __version__))


class StHistory(WindowCommand):
    @staticmethod
    def run():
        if not ST.conn:
            ST.selectConnectionQuickPanel(callback=lambda: Window().run_command('st_history'))
            return

        if len(historyStore.all()) == 0:
            sublime.message_dialog('History is empty.')
            return

        def cb(index):
            if index < 0:
                return None
            return ST.conn.execute(historyStore.get(index), createOutput())

        Window().show_quick_panel(historyStore.all(), cb)


class StSaveQuery(WindowCommand):
    @staticmethod
    def run():
        query = getSelectionText()

        def cb(alias):
            queriesStore.add(alias, query)
        Window().show_input_panel('Query alias', '', cb, None, None)


class StListQueries(WindowCommand):
    @staticmethod
    def run(mode="run"):
        if mode == "run" and not ST.conn:
            ST.selectConnectionQuickPanel(callback=lambda: Window().run_command('st_list_queries',
                                                                               {'mode': mode}))
            return

        queriesList = queriesStore.all()
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
            ST.selectConnectionQuickPanel(callback=lambda: Window().run_command('st_remove_saved_query'))
            return

        queriesList = queriesStore.all()
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

            return queriesStore.delete(options[index][0])
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
        imp.reload(sys.modules[__package__ + ".SQLToolsAPI.Command"])
        imp.reload(sys.modules[__package__ + ".SQLToolsAPI.Connection"])
    except Exception as e:
        raise (e)

    try:
        ST.bootstrap()
    except Exception:
        pass


def plugin_loaded():

    try:
        from package_control import events

        if events.install(__name__):
            logger.info('Installed %s!' % events.install(__name__))
        elif events.post_upgrade(__name__):
            logger.info('Upgraded to %s!' % events.post_upgrade(__name__))
            sublime.message_dialog(('{0} was upgraded.' +
                                    'If you have any problem,' +
                                    'just restart your Sublime Text.'
                                    ).format(__name__)
                                   )

    except Exception:
        pass

    startPlugin()
    reload()


def plugin_unloaded():
    if plugin_logger.handlers:
        plugin_logger.handlers.pop()
