import shutil
import shlex
import codecs
import logging
import sqlparse

from . import Utils as U
from . import Command as C

logger = logging.getLogger(__name__)


def _encoding_exists(enc):
    try:
        codecs.lookup(enc)
    except LookupError:
        return False
    return True


class Connection(object):
    DB_CLI_NOT_FOUND_MESSAGE = """DB CLI '{0}' could not be found.
Please set the path to DB CLI '{0}' binary in your SQLTools settings before continuing.
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
    safe_limit = None
    show_query = None
    rowsLimit = None
    history = None
    timeout = None

    def __init__(self, name, options, settings=None, commandClass='ThreadCommand'):
        self.Command = getattr(C, commandClass)

        self.name = name
        self.options = {k: v for k, v in options.items() if v is not None}

        if settings is None:
            settings = {}
        self.settings = settings

        self.type       = self.options.get('type', None)
        self.host       = self.options.get('host', None)
        self.port       = self.options.get('port', None)
        self.database   = self.options.get('database', None)
        self.username   = self.options.get('username', None)
        self.password   = self.options.get('password', None)
        self.encoding   = self.options.get('encoding', 'utf-8')
        self.encoding   = self.encoding or 'utf-8'  # defaults to utf-8
        if not _encoding_exists(self.encoding):
            self.encoding = 'utf-8'

        self.safe_limit = settings.get('safe_limit', None)
        self.show_query = settings.get('show_query', False)
        self.rowsLimit  = settings.get('show_records', {}).get('limit', 50)
        self.useStreams = settings.get('use_streams', False)
        self.cli        = settings.get('cli')[self.options['type']]

        cli_path = shutil.which(self.cli)
        if cli_path is None:
            logger.info(self.DB_CLI_NOT_FOUND_MESSAGE.format(self.cli))
            raise FileNotFoundError(self.DB_CLI_NOT_FOUND_MESSAGE.format(self.cli))

    def __str__(self):
        return self.name

    def info(self):
        return 'DB: {0}, Connection: {1}@{2}:{3}'.format(
            self.database, self.username, self.host, self.port)

    def runInternalNamedQueryCommand(self, queryName, callback):
        query = self.getNamedQuery(queryName)
        if not query:
            emptyList = []
            callback(emptyList)
            return

        queryToRun = self.buildNamedQuery(queryName, query)
        args = self.buildArgs(queryName)
        env = self.buildEnv()

        def cb(result):
            callback(U.getResultAsList(result))

        self.Command.createAndRun(args=args,
                                  env=env,
                                  callback=cb,
                                  query=queryToRun,
                                  encoding=self.encoding,
                                  timeout=60,
                                  silenceErrors=True,
                                  stream=False)

    def getTables(self, callback):
        self.runInternalNamedQueryCommand('desc', callback)

    def getColumns(self, callback):
        self.runInternalNamedQueryCommand('columns', callback)

    def getFunctions(self, callback):
        self.runInternalNamedQueryCommand('functions', callback)

    def runFormattedNamedQueryCommand(self, queryName, formatValues, callback):
        query = self.getNamedQuery(queryName)
        if not query:
            return

        # added for compatibility with older format string
        query = query.replace("%s", "{0}", 1)
        query = query.replace("%s", "{1}", 1)

        if isinstance(formatValues, tuple):
            query = query.format(*formatValues)  # unpack the tuple
        else:
            query = query.format(formatValues)

        queryToRun = self.buildNamedQuery(queryName, query)
        args = self.buildArgs(queryName)
        env = self.buildEnv()
        self.Command.createAndRun(args=args,
                                  env=env,
                                  callback=callback,
                                  query=queryToRun,
                                  encoding=self.encoding,
                                  timeout=self.timeout,
                                  silenceErrors=False,
                                  stream=False)

    def getTableRecords(self, tableName, callback):
        # in case we expect multiple values pack them into tuple
        formatValues = (tableName, self.rowsLimit)
        self.runFormattedNamedQueryCommand('show records', formatValues, callback)

    def getTableDescription(self, tableName, callback):
        self.runFormattedNamedQueryCommand('desc table', tableName, callback)

    def getFunctionDescription(self, functionName, callback):
        self.runFormattedNamedQueryCommand('desc function', functionName, callback)

    def explainPlan(self, queries, callback):
        queryName = 'explain plan'
        explainQuery = self.getNamedQuery(queryName)
        if not explainQuery:
            return

        strippedQueries = [
            explainQuery.format(query.strip().strip(";"))
            for rawQuery in queries
            for query in filter(None, sqlparse.split(rawQuery))
        ]
        queryToRun = self.buildNamedQuery(queryName, strippedQueries)
        args = self.buildArgs(queryName)
        env = self.buildEnv()
        self.Command.createAndRun(args=args,
                                  env=env,
                                  callback=callback,
                                  query=queryToRun,
                                  encoding=self.encoding,
                                  timeout=self.timeout,
                                  silenceErrors=False,
                                  stream=self.useStreams)

    def execute(self, queries, callback, stream=None):
        queryName = 'execute'

        # if not explicitly overriden, use the value from settings
        if stream is None:
            stream = self.useStreams

        if isinstance(queries, str):
            queries = [queries]

        # add original (umodified) queries to the history
        if self.history:
            self.history.add('\n'.join(queries))

        processedQueriesList = []
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
                processedQueriesList.append(query)

        queryToRun = self.buildNamedQuery(queryName, processedQueriesList)
        args = self.buildArgs(queryName)
        env = self.buildEnv()

        logger.debug("Query: %s", str(queryToRun))

        self.Command.createAndRun(args=args,
                                  env=env,
                                  callback=callback,
                                  query=queryToRun,
                                  encoding=self.encoding,
                                  options={'show_query': self.show_query},
                                  timeout=self.timeout,
                                  silenceErrors=False,
                                  stream=stream)

    def getNamedQuery(self, queryName):
        if not queryName:
            return None

        cliOptions = self.getOptionsForSgdbCli()
        return cliOptions.get('queries', {}).get(queryName, {}).get('query')

    def buildNamedQuery(self, queryName, queries):
        if not queryName:
            return None

        if not queries:
            return None

        cliOptions = self.getOptionsForSgdbCli()
        beforeCli = cliOptions.get('before')
        afterCli = cliOptions.get('after')
        beforeQuery = cliOptions.get('queries', {}).get(queryName, {}).get('before')
        afterQuery = cliOptions.get('queries', {}).get(queryName, {}).get('after')

        # sometimes we preprocess the raw queries from user, in that case we already have a list
        if type(queries) is not list:
            queries = [queries]

        builtQueries = []
        if beforeCli is not None:
            builtQueries.extend(beforeCli)
        if beforeQuery is not None:
            builtQueries.extend(beforeQuery)
        if queries is not None:
            builtQueries.extend(queries)
        if afterQuery is not None:
            builtQueries.extend(afterQuery)
        if afterCli is not None:
            builtQueries.extend(afterCli)

        # remove empty list items
        builtQueries = list(filter(None, builtQueries))

        return '\n'.join(builtQueries)

    def buildArgs(self, queryName=None):
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

        # append generic options
        options = cliOptions.get('options', None)
        if options:
            args = args + options

        # append query specific options (if present)
        if queryName:
            queryOptions = cliOptions.get('queries', {}).get(queryName, {}).get('options')
            if queryOptions:
                if len(queryOptions) > 0:
                    args = args + queryOptions

        # append main args - could be a single value or a list
        mainArgs = cliOptions['args']
        if isinstance(mainArgs, list):
            mainArgs = ' '.join(mainArgs)

        mainArgs = mainArgs.format(**self.options)
        args = args + shlex.split(mainArgs)

        logger.debug('CLI args (%s): %s', str(queryName), ' '.join(args))
        return args

    def buildEnv(self):
        cliOptions = self.getOptionsForSgdbCli()
        env = dict()

        # append **optional** environment variables dict (if any)
        optionalEnv = cliOptions.get('env_optional')
        if optionalEnv:  # only if we have optional args
            if isinstance(optionalEnv, dict):
                for var, value in optionalEnv.items():
                    formattedValue = self.formatOptionalArgument(value, self.options)
                    if formattedValue:
                        env.update({var: formattedValue})

        # append environment variables dict (if any)
        staticEnv = cliOptions.get('env')
        if staticEnv:  # only if we have optional args
            if isinstance(staticEnv, dict):
                for var, value in staticEnv.items():
                    formattedValue = value.format(**self.options)
                    if formattedValue:
                        env.update({var: formattedValue})

        logger.debug('CLI environment: %s', str(env))
        return env

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
        logger.info('Connection timeout set to {0} seconds'.format(timeout))

    @staticmethod
    def setHistoryManager(manager):
        Connection.history = manager
        size = manager.getMaxSize()
        logger.info('Connection history size is {0}'.format(size))
