import shutil
import shlex
import sqlparse

from .Log import Log
from . import Utils as U
from . import Command as C


class Connection:
    history = None
    settings = None
    rowsLimit = None
    options = None
    name = None
    type = None
    database = None
    host = None
    port = None
    username = None
    encoding = None
    password = None
    service = None
    safe_limit = None
    show_query = None

    def __init__(self, name, options, settings={}, commandClass='ThreadCommand'):
        self.Command = getattr(C, commandClass)

        self.cli = settings.get('cli')[options['type']]
        cli_path = shutil.which(self.cli)

        if cli_path is None:
            Log((
                "'{0}' could not be found.\n\n" +
                "Please set the '{0}' path in your SQLTools settings " +
                "before continue.").format(self.cli))
            return

        self.settings  = settings
        self.rowsLimit = settings.get('show_records', {}).get('limit', 50)
        self.options   = options
        self.name      = name
        self.type      = options.get('type', None)
        self.database  = options.get('database', None)
        self.host      = options.get('host', None)
        self.port      = options.get('port', None)
        self.username  = options.get('username', None)
        self.encoding  = options.get('encoding', None)
        self.password  = options.get('password', None)
        self.service   = options.get('service', None)
        self.safe_limit = settings.get('safe_limit', None)
        self.show_query = settings.get('show_query', None)

    def __str__(self):
        return self.name

    def _info(self):
        return 'DB: {0}, Connection: {1}@{2}:{3}'.format(
            self.database, self.username, self.host, self.port)

    def getTables(self, callback):
        query = self.getOptionsForSgdbCli()['queries']['desc']['query']

        def cb(result):
            callback(U.getResultAsList(result))

        self.Command.createAndRun(self.builArgs('desc'), query, cb)

    def getColumns(self, callback):

        def cb(result):
            callback(U.getResultAsList(result))

        try:
            query = self.getOptionsForSgdbCli()['queries']['columns']['query']
            self.Command.createAndRun(self.builArgs('columns'), query, cb)
        except Exception:
            pass

    def getFunctions(self, callback):

        def cb(result):
            callback(U.getResultAsList(result))

        try:
            query = self.getOptionsForSgdbCli()['queries']['functions']['query']
            self.Command.createAndRun(self.builArgs(
                'functions'), query, cb)
        except Exception:
            pass

    def getTableRecords(self, tableName, callback):
        query = self.getOptionsForSgdbCli()['queries']['show records']['query'].format(tableName, self.rowsLimit)
        queryToRun = '\n'.join(self.getOptionsForSgdbCli()['before'] + [query])
        self.Command.createAndRun(self.builArgs('show records'), queryToRun, callback)

    def getTableDescription(self, tableName, callback):
        query = self.getOptionsForSgdbCli()['queries']['desc table']['query'] % tableName
        queryToRun = '\n'.join(self.getOptionsForSgdbCli()['before'] + [query])
        self.Command.createAndRun(self.builArgs('desc table'), queryToRun, callback)

    def getFunctionDescription(self, functionName, callback):
        query = self.getOptionsForSgdbCli()['queries']['desc function'][
            'query'] % functionName
        queryToRun = '\n'.join(self.getOptionsForSgdbCli()['before'] + [query])
        self.Command.createAndRun(self.builArgs('desc function'), queryToRun, callback)

    def execute(self, queries, callback):
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

        self.Command.createAndRun(self.builArgs(), queryToRun, callback, options={'show_query': self.show_query})

    def builArgs(self, queryName=None):
        cliOptions = self.getOptionsForSgdbCli()
        args = [self.cli]

        if len(cliOptions['options']) > 0:
            args = args + cliOptions['options']

        if queryName and len(cliOptions['queries'][queryName]['options']) > 0:
            args = args + cliOptions['queries'][queryName]['options']

        if isinstance(cliOptions['args'], list):
            cliOptions['args'] = ' '.join(cliOptions['args'])

        cliOptions = cliOptions['args'].format(**self.options)
        args = args + shlex.split(cliOptions)

        Log('Using cli args ' + ' '.join(args))
        return args

    def getOptionsForSgdbCli(self):
        return self.settings.get('cli_options', {}).get(self.type)

    @staticmethod
    def setTimeout(timeout):
        Connection.timeout = timeout
        Log('Connection timeout setted to {0} seconds'.format(timeout))

    @staticmethod
    def setHistoryManager(manager):
        Connection.history = manager
        Log('Connection history defined with max size {0}'.format(manager.getMaxSize()))
