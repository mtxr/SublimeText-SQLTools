import shutil
import shlex
import sqlparse

from .Log import Log
from . import Utils as U
from . import Command as C


class Connection(object):
    DB_CLI_NOT_FOUND_MESSAGE = """'{0}' could not be found.
Please set the path to '{0}' binary in your SQLTools settings before continuing.
Example of "cli" section in SQLTools.sublime-settings:
    /* ...  (note the use of forward slashes) */
    "cli" : {{
        "mysql"   : "c:/Program Files/MySQL/MySQL Server 5.7/bin/mysql.exe",
        "pgsql"   : "c:/Program Files/PostgreSQL/9.6/bin/psql.exe"
    }}
You might need to restart the editor for settings to be refreshed."""

    name = None
    options = None
    settings = None
    type = None
    host = None
    port = None
    database = None
    username = None
    password = None
    encoding = None
    service = None
    safe_limit = None
    show_query = None
    rowsLimit = None
    history = None
    timeout = None

    def __init__(self, name, options, settings=None, commandClass='ThreadCommand'):
        self.Command = getattr(C, commandClass)

        self.name = name
        self.options = options

        if settings is None:
            settings = {}
        self.settings = settings

        self.type       = options.get('type', None)
        self.host       = options.get('host', None)
        self.port       = options.get('port', None)
        self.database   = options.get('database', None)
        self.username   = options.get('username', None)
        self.password   = options.get('password', None)
        self.encoding   = options.get('encoding', None)
        self.service    = options.get('service', None)

        self.safe_limit = settings.get('safe_limit', None)
        self.show_query = settings.get('show_query', None)
        self.rowsLimit  = settings.get('show_records', {}).get('limit', 50)
        self.cli        = settings.get('cli')[options['type']]

        cli_path = shutil.which(self.cli)
        if cli_path is None:
            Log(self.DB_CLI_NOT_FOUND_MESSAGE.format(self.cli))
            raise FileNotFoundError(self.DB_CLI_NOT_FOUND_MESSAGE.format(self.cli))

    def __str__(self):
        return self.name

    def info(self):
        return 'DB: {0}, Connection: {1}@{2}:{3}'.format(
            self.database, self.username, self.host, self.port)

    def getTables(self, callback):
        query = self.getOptionsForSgdbCli()['queries']['desc']['query']

        def cb(result):
            callback(U.getResultAsList(result))

        self.Command.createAndRun(self.builArgs('desc'),
                                  query, cb, silenceErrors=True)

    def getColumns(self, callback):

        def cb(result):
            callback(U.getResultAsList(result))

        try:
            query = self.getOptionsForSgdbCli()['queries']['columns']['query']
            self.Command.createAndRun(self.builArgs('columns'),
                                      query, cb, silenceErrors=True)
        except Exception:
            pass

    def getFunctions(self, callback):

        def cb(result):
            callback(U.getResultAsList(result))

        try:
            query = self.getOptionsForSgdbCli()['queries']['functions']['query']
            self.Command.createAndRun(self.builArgs('functions'),
                                      query, cb, silenceErrors=True)
        except Exception:
            pass

    def getTableRecords(self, tableName, callback):
        query = self.getOptionsForSgdbCli()['queries']['show records']['query'].format(tableName, self.rowsLimit)
        queryToRun = '\n'.join(self.getOptionsForSgdbCli()['before'] + [query])
        self.Command.createAndRun(self.builArgs('show records'), queryToRun, callback, timeout=self.timeout)

    def getTableDescription(self, tableName, callback):
        query = self.getOptionsForSgdbCli()['queries']['desc table']['query'] % tableName
        queryToRun = '\n'.join(self.getOptionsForSgdbCli()['before'] + [query])
        self.Command.createAndRun(self.builArgs('desc table'), queryToRun, callback)

    def getFunctionDescription(self, functionName, callback):
        query = self.getOptionsForSgdbCli()['queries']['desc function'][
            'query'] % functionName
        queryToRun = '\n'.join(self.getOptionsForSgdbCli()['before'] + [query])
        self.Command.createAndRun(self.builArgs('desc function'), queryToRun, callback)

    def explainPlan(self, queries, callback):
        try:
            queryFormat = self.getOptionsForSgdbCli()['queries']['explain plan']['query']
        except KeyError:
            return  # do nothing, if DBMS has no support for explain plan

        stripped_queries = [
            queryFormat.format(query.strip().strip(";"))
            for rawQuery in queries
            for query in filter(None, sqlparse.split(rawQuery))
        ]
        queryToRun = '\n'.join(self.getOptionsForSgdbCli()['before'] + stripped_queries)
        self.Command.createAndRun(self.builArgs('explain plan'), queryToRun, callback, timeout=self.timeout)

    def execute(self, queries, callback, stream=False):
        queryToRun = ''

        for query in self.getOptionsForSgdbCli()['before']:
            queryToRun += query + "\n"

        if isinstance(queries, str):
            queries = [queries]

        for rawQuery in queries:
            for query in sqlparse.split(rawQuery):
                if self.safe_limit:
                    parsedTokens = sqlparse.parse(query.strip().replace("'", "\""))
                    if ((parsedTokens[0][0].ttype in sqlparse.tokens.Keyword and
                            parsedTokens[0][0].value == 'select')):
                        applySafeLimit = True
                        for parse in parsedTokens:
                            for token in parse.tokens:
                                if token.ttype in sqlparse.tokens.Keyword and token.value == 'limit':
                                    applySafeLimit = False
                        if applySafeLimit:
                            if (query.strip()[-1:] == ';'):
                                query = query.strip()[:-1]
                            query += " LIMIT {0};".format(self.safe_limit)
                queryToRun += query + "\n"

        Log("Query: " + queryToRun)

        if Connection.history:
            Connection.history.add(queryToRun)

        self.Command.createAndRun(self.builArgs(), queryToRun, callback, options={'show_query': self.show_query}, timeout=self.timeout, stream=stream)

    def builArgs(self, queryName=None):
        cliOptions = self.getOptionsForSgdbCli()
        args = [self.cli]

        # append otional args (if any) - could be a single value or a list
        optionalArgs = cliOptions.get('args_optional')
        if optionalArgs:  # only if we have optional args
            if isinstance(optionalArgs, list):
                for item in optionalArgs:
                    formattedItem = self.formatOptionalArgument(item, self.options)
                    if formattedItem:
                        args = args + shlex.split(formattedItem)
            else:
                formattedItem = self.formatOptionalArgument(optionalArgs, self.options)
                if formattedItem:
                    args = args + shlex.split(formattedItem)

        # append query specific options
        if queryName:
            queryOptions = cliOptions['queries'][queryName]['options']
            if len(queryOptions) > 0:
                args = args + queryOptions
        else:
            # append generic options (only if not custom query)
            options = cliOptions.get('options', None)
            if options:
                args = args + options

        # append main args - could be a single value or a list
        mainArgs = cliOptions['args']
        if isinstance(mainArgs, list):
            mainArgs = ' '.join(mainArgs)

        mainArgs = mainArgs.format(**self.options)
        args = args + shlex.split(mainArgs)

        Log('Using cli args ' + ' '.join(args))
        return args

    def getOptionsForSgdbCli(self):
        return self.settings.get('cli_options', {}).get(self.type)

    @staticmethod
    def formatOptionalArgument(argument, formatOptions):
        try:
            formattedArg = argument.format(**formatOptions)
        except (KeyError, IndexError):
            return None

        if argument == formattedArg:  # string not changed after format
            return None
        return formattedArg

    @staticmethod
    def setTimeout(timeout):
        Connection.timeout = timeout
        Log('Connection timeout set to {0} seconds'.format(timeout))

    @staticmethod
    def setHistoryManager(manager):
        Connection.history = manager
        Log('Connection history defined with max size {0}'.format(manager.getMaxSize()))
