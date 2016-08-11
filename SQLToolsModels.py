import sublime, os, tempfile, threading, signal, shlex, subprocess, sys

sys.path.append(os.path.dirname(__file__))
if sys.version_info >= (3, 0):
    import sqlparse3 as sqlparse
else:
    import sqlparse2 as sqlparse

class Const:
    SETTINGS_EXTENSION    = "sublime-settings"
    SETTINGS_FILENAME     = "SQLTools.{0}".format(SETTINGS_EXTENSION)
    SGDB_FILENAME         = "SQLToolsSGBD.{0}".format(SETTINGS_EXTENSION)
    CONNECTIONS_FILENAME  = "SQLToolsConnections.{0}".format(SETTINGS_EXTENSION)
    USER_QUERIES_FILENAME = "SQLToolsSavedQueries.{0}".format(SETTINGS_EXTENSION)
    VERSION               = "v0.3.1"
    pass

class Log:

    @staticmethod
    def debug(message):
        if not sublime.load_settings(Const.SETTINGS_FILENAME).get('debug', False):
            return
        print ("SQLTools %s: %s" % (Const.VERSION, message))


class Settings:

    @staticmethod
    def getConnections():
        connections = {}
        options = sublime.load_settings(Const.CONNECTIONS_FILENAME).get('connections')

        for connection in options:
            connections[connection] = Connection(connection, options[connection])

        return connections

    @staticmethod
    def userFolder():
        return '{0}/User'.format(sublime.packages_path())



class Storage:
    savedQueries       = None
    savedQueriesArray  = None
    selectedQuery      = ''

    @staticmethod
    def getSavedQueries():
        Storage.savedQueries      = sublime.load_settings(Const.USER_QUERIES_FILENAME)
        Storage.savedQueriesArray = Storage.savedQueries.get('queries', {})
        return Storage.savedQueries

    @staticmethod
    def flushSavedQueries():
        if not Storage.savedQueries:
            Storage.getSavedQueries()

        return sublime.save_settings(Const.USER_QUERIES_FILENAME)

    @staticmethod
    def promptQueryAlias():
        Storage.selectedQuery = Selection.get()
        Window().show_input_panel('Query alias', '', Storage.saveQuery, None, None)

    @staticmethod
    def saveQuery(alias):
        if len(alias) <= 0:
            return

        Storage.getSavedQueries()
        Storage.savedQueriesArray[alias] = '\n'.join(Storage.selectedQuery)
        Storage.savedQueries.set('queries', Storage.savedQueriesArray)
        Storage.flushSavedQueries()

    @staticmethod
    def removeQuery(alias):
        if len(alias) <= 0:
            return

        Storage.getSavedQueries()
        Storage.savedQueriesArray.pop(alias)
        Storage.savedQueries.set('queries', Storage.savedQueriesArray)
        Storage.flushSavedQueries()

    @staticmethod
    def getSavedQuery(alias):
        if len(alias) <= 0:
            return

        Storage.getSavedQueries()
        return Storage.savedQueriesArray[alias]

class Connection:

    def __init__(self, name, options):
        self.cli         = sublime.load_settings(Const.SETTINGS_FILENAME).get('cli')[options['type']]
        self.rowsLimit   = sublime.load_settings(Const.SETTINGS_FILENAME).get('show_records').get('limit', 50)
        self.options     = options
        self.name        = name
        self.type        = options['type']
        self.host        = options['host']
        self.port        = options['port']
        self.username    = options['username']
        self.database    = options['database']

        if 'encoding' in options:
            self.encoding    = options['encoding']

        if 'password' in options:
            self.password = options['password']

        if 'service' in options:
            self.service  = options['service']

    def __str__(self):
        return self.name

    def _info(self):
        return 'DB: {0}, Connection: {1}@{2}:{3}'.format(self.database, self.username, self.host, self.port)

    def _quickPanel(self):
        return [self.name, self._info()]

    @staticmethod
    def killCommandAfterTimeout(command):
        timeout = sublime.load_settings(Const.SETTINGS_FILENAME).get('thread_timeout', 5000)
        sublime.set_timeout(command.stop, timeout)

    @staticmethod
    def loadDefaultConnectionName():
        default = sublime.load_settings(Const.CONNECTIONS_FILENAME).get('default', False)
        if not default:
            return
        Log.debug('Default database set to ' + default + '. Loading options and auto complete.')
        return default

    def getTables(self, callback):
        query   = self.getOptionsForSgdbCli()['queries']['desc']['query']
        self.runCommand(self.builArgs('desc'), query, lambda result: Utils.getResultAsList(result, callback))

    def getColumns(self, callback):
        try:
            query   = self.getOptionsForSgdbCli()['queries']['columns']['query']
            self.runCommand(self.builArgs('columns'), query, lambda result: Utils.getResultAsList(result, callback))
        except Exception:
            pass

    def getFunctions(self, callback):
        try:
            query   = self.getOptionsForSgdbCli()['queries']['functions']['query']
            self.runCommand(self.builArgs('functions'), query, lambda result: Utils.getResultAsList(result, callback))
        except Exception:
            pass

    def getTableRecords(self, tableName, callback):
        query   = self.getOptionsForSgdbCli()['queries']['show records']['query'].format(tableName, self.rowsLimit)
        self.runCommand(self.builArgs('show records'), query, lambda result: callback(result))

    def getTableDescription(self, tableName, callback):
        query   = self.getOptionsForSgdbCli()['queries']['desc table']['query'] % tableName
        self.runCommand(self.builArgs('desc table'), query, lambda result: callback(result))

    def getFunctionDescription(self, functionName, callback):
        query   = self.getOptionsForSgdbCli()['queries']['desc function']['query'] % functionName
        self.runCommand(self.builArgs('desc function'), query, lambda result: callback(result))


    def execute(self, queries, callback):
        queryToRun = ''

        for query in self.getOptionsForSgdbCli()['before']:
            queryToRun += query + "\n"

        if type(queries) is str:
            queries = [queries];

        for query in queries:
            queryToRun += query + "\n"

        queryToRun = queryToRun.rstrip('\n')
        windowVars = sublime.active_window().extract_variables()
        if type(windowVars) is dict and 'file_extension' in windowVars:
            windowVars = windowVars['file_extension'].lstrip()
            unescapeExtension = sublime.load_settings(Const.SETTINGS_FILENAME).get('unescape_quotes')
            if windowVars in unescapeExtension:
                queryToRun = queryToRun.replace("\\\"", "\"").replace("\\\'", "\'")


        Log.debug("Query: " + queryToRun)
        History.add(queryToRun)
        self.runCommand(self.builArgs(), queryToRun, lambda result: callback(result))

    def runCommand(self, args, query, callback):
        command = Command(args, callback, query)
        command.start()
        Connection.killCommandAfterTimeout(command)


    def builArgs(self, queryName=None):
        cliOptions = self.getOptionsForSgdbCli()
        args  = [self.cli]

        if len(cliOptions['options']) > 0:
            args = args + cliOptions['options']

        if queryName and len(cliOptions['queries'][queryName]['options']) > 0:
            args = args + cliOptions['queries'][queryName]['options']

        argsType = 'string'
        if type(cliOptions['args']) is list:
            argsType = 'list'
            cliOptions['args'] = ' '.join(cliOptions['args'])

        Log.debug('Usgin cli args ' + ' '.join(args + shlex.split(cliOptions['args'].format(**self.options))))
        return args + shlex.split(cliOptions['args'].format(**self.options))

    def getOptionsForSgdbCli(self):
        return sublime.load_settings(Const.SETTINGS_FILENAME).get('cli_options')[self.type]


class Selection:
    @staticmethod
    def get():
        text = []
        if View().sel():
            for region in View().sel():
                if region.empty():
                    text.append(View().substr(View().line(region)))
                else:
                    text.append(View().substr(region))
        return text

    @staticmethod
    def formatSql(edit):
        for region in View().sel():
            if region.empty():
                selectedRegion = sublime.Region(0, View().size())
                selection = View().substr(selectedRegion)
                View().replace(edit, selectedRegion, Utils.formatSql(selection))
                View().set_syntax_file("Packages/SQL/SQL.tmLanguage")
            else:
                text = View().substr(region)
                View().replace(edit, region, Utils.formatSql(text))

class Command(threading.Thread):
    def __init__(self, args, callback, query=None, encoding='utf-8'):
        self.query    = query
        self.process  = None
        self.args     = args
        self.encoding = encoding
        self.callback = callback
        threading.Thread.__init__(self)

    def run(self):
        if not self.query:
            return

        sublime.status_message(' ST: running SQL command')
        self.tmp = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sql')
        self.tmp.write(self.query)
        self.tmp.close()

        self.args = map(str, self.args)
        si = None
        if os.name == 'nt':
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        self.process = subprocess.Popen(self.args, stdout=subprocess.PIPE,stderr=subprocess.PIPE, stdin=open(self.tmp.name), env=os.environ.copy(), startupinfo=si)

        results, errors = self.process.communicate()

        if errors:
            self.callback(errors.decode(self.encoding, 'replace').replace('\r', ''))
            return

        self.callback(results.decode(self.encoding, 'replace').replace('\r', ''))

    def stop(self):
        if not self.process:
            return

        try:
            os.kill(self.process.pid, signal.SIGKILL)
            self.process = None
            sublime.message_dialog("Your command is taking too long to run. Try to run outside using your database cli.")
            Log.debug("Your command is taking too long to run. Process killed")
        except Exception:
            pass
        try:
            if self.tmp and os.path.exists(self.tmp.name):
                os.unlink(self.tmp.name)
        except Exception:
            Log.debug("Failed to remove tmp file" + self.tmp.name)
            pass

class Utils:
    @staticmethod
    def getResultAsList(results, callback=None):
        resultList = []
        for result in results.splitlines():
            try:
                resultList.append(result.split('|')[1].strip())
            except IndexError:
                pass

        if callback:
           callback(resultList)

        return resultList

    @staticmethod
    def formatSql(raw):
        settings = sublime.load_settings(Const.SETTINGS_FILENAME).get("format")
        try:
            result = sqlparse.format(raw,
                keyword_case    = settings.get("keyword_case"),
                identifier_case = settings.get("identifier_case"),
                strip_comments  = settings.get("strip_comments"),
                indent_tabs     = settings.get("indent_tabs"),
                indent_width    = settings.get("indent_width"),
                reindent        = settings.get("reindent")
            )

            if View().settings().get('ensure_newline_at_eof_on_save'):
                result += "\n"

            return result
        except Exception as e:
            return None

class History:
    queries = []

    @staticmethod
    def add(query):
        if len(History.queries) >= sublime.load_settings(Const.SETTINGS_FILENAME).get('history_size', 100):
            History.queries.pop(0)
        History.queries.insert(0, query)

    @staticmethod
    def get(index):
        if index < 0 or index > (len(History.queries) - 1):
            raise "No query selected"

        return History.queries[index]

def Window():
    return sublime.active_window()

def View():
    return Window().active_view()
