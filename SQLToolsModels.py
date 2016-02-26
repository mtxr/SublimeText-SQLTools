import sublime, os, tempfile, threading, signal, shlex, subprocess

class Const:
    SETTINGS_EXTENSION    = "sublime-settings"
    SETTINGS_FILENAME     = "SQLTools.{0}".format(SETTINGS_EXTENSION)
    CONNECTIONS_FILENAME  = "SQLToolsConnections.{0}".format(SETTINGS_EXTENSION)
    USER_QUERIES_FILENAME = "SQLToolsSavedQueries.{0}".format(SETTINGS_EXTENSION)
    pass

class Log:

    @staticmethod
    def debug(message):
        if not sublime.load_settings(Const.SETTINGS_FILENAME).get('debug', False):
            return
        print ("SQLTools: " + message)


class Settings:

    @staticmethod
    def getConnections():
        connections = {}
        options = sublime.load_settings(Const.CONNECTIONS_FILENAME).get('connections')

        for connection in options:
            connections[connection] = Connection(connection, options[connection])

        return connections

    def userFolder():
        return '{0}/User'.format(sublime.packages_path())



class Storage:
    savedQueries  = None
    selectedQuery = ''

    def getSavedQueries():
        Storage.savedQueries = sublime.load_settings(Const.USER_QUERIES_FILENAME)
        return Storage.savedQueries

    def flushSavedQueries():
        if not Storage.savedQueries:
            Storage.getSavedQueries()

        return sublime.save_settings(Const.USER_QUERIES_FILENAME)

    def promptQueryAlias():
        Storage.selectedQuery = Selection.get()
        Window().show_input_panel('Query alias', '', Storage.saveQuery, None, None)

    def saveQuery(alias):
        if len(alias) <= 0:
            return

        Storage.getSavedQueries()
        Storage.savedQueries.set(alias, '\n'.join(Storage.selectedQuery))
        Storage.flushSavedQueries()


    def getSavedQuery(alias):
        if len(alias) <= 0:
            return

        Storage.getSavedQueries()
        return Storage.savedQueries.get(alias)

class Connection:

    def __init__(self, name, options):
        self.cliSettings = sublime.load_settings('{0}.settings'.format(options['type']))
        self.cli         = sublime.load_settings(Const.SETTINGS_FILENAME).get('cli')[options['type']]
        self.rowsLimit   = sublime.load_settings(Const.SETTINGS_FILENAME).get('show_records').get('limit', 50)
        self.options     = options
        self.name        = name
        self.type        = options['type']
        self.host        = options['host']
        self.port        = options['port']
        self.username    = options['username']
        self.database    = options['database']

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
        query   = self.cliSettings.get('queries')['desc']['query']
        args    = self.builArgs('desc')
        command = Command(args, lambda result: Utils.getResultAsList(result, callback), query)
        command.start()
        Connection.killCommandAfterTimeout(command)

    def getColumns(self, callback):
        query   = self.cliSettings.get('queries')['columns']['query']
        args    = self.builArgs('columns')
        command = Command(args, lambda result: Utils.getResultAsList(result, callback), query)
        command.start()
        Connection.killCommandAfterTimeout(command)

    def getTableRecords(self, tableName, callback):
        query   = self.cliSettings.get('queries')['show records']['query'].format(tableName, self.rowsLimit)
        args    = self.builArgs('show records')
        command = Command(args, lambda result: callback(result), query)
        command.start()
        Connection.killCommandAfterTimeout(command)

    def getTableDescription(self, tableName, callback):
        query   = self.cliSettings.get('queries')['desc table']['query'] % tableName
        args    = self.builArgs('desc table')
        command = Command(args, lambda result: callback(result), query)
        command.start()
        Connection.killCommandAfterTimeout(command)

    def execute(self, queries, callback):
        queryToRun = ''

        for query in self.cliSettings.get('before'):
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
        self.runCommand(self.builArgs(), queryToRun, lambda result: callback(result))

    def runCommand(self, args, query, callback):
        command = Command(args, callback, query)
        command.start()
        Connection.killCommandAfterTimeout(command)


    def builArgs(self, queryName=None):
        args  = [self.cli]
        if queryName and len(self.cliSettings.get('queries')[queryName]['options']) > 0:
            args = args + self.cliSettings.get('queries')[queryName]['options']

        return args + shlex.split(self.cliSettings.get('args').format(**self.options))


class Selection:
    def get():
        text = []
        if View().sel():
            for region in View().sel():
                if region.empty():
                    text.append(View().substr(View().line(region)))
                else:
                    text.append(View().substr(region))
        return text

class Command(threading.Thread):
    def __init__(self, args, callback, query=None):
        self.query    = query
        self.process  = None
        self.args     = args
        self.callback = callback
        threading.Thread.__init__(self)

    def run(self):
        if not self.query:
            return

        sublime.status_message(' ST: running SQL command')
        self.tmp = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sql')
        self.tmp.write(self.query)
        self.tmp.close()

        self.process = subprocess.Popen(self.args, stdout=subprocess.PIPE,stderr=subprocess.PIPE, stdin=open(self.tmp.name))

        results, errors = self.process.communicate(input=self.query.encode('utf-8'))

        if errors:
            self.callback(errors.decode('utf-8', 'replace').replace('\r', ''))
            return

        self.callback(results.decode('utf-8', 'replace').replace('\r', ''))

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
        if self.tmp and os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

class Utils:
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

def Window():
    return sublime.active_window()

def View():
    return Window().active_view()
