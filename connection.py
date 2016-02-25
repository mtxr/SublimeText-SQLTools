import sublime, sys, re, shlex

from . import const
from .command import Command
from .general import Log

class Connection:
    def __init__(self, options):
        self.settings = sublime.load_settings('{0}.settings'.format(options.type))
        self.command  = sublime.load_settings(const.settingsFilename).get('commands').get(options.type)
        self.limit    = sublime.load_settings(const.settingsFilename).get('show_records').get('limit', 50)
        self.options  = options

    def _buildCommand(self, options):
        return re.sub('\s+', ' ', self.command + ' ' + ' '.join(options) + ' ' + self.settings.get('args').format(options=self.options)).strip()

    def _getCommand(self, options, queries, header = ''):
        queryToRun = ''

        for query in self.settings.get('before'):
            queryToRun += query + "\n"

        if type(queries) is str:
            queries = [queries];

        for query in queries:
            queryToRun += query + "\n"

        queryToRun = queryToRun.rstrip('\n')
        windowVars = sublime.active_window().extract_variables()
        if type(windowVars) is dict and 'file_extension' in windowVars:
            windowVars = windowVars['file_extension'].lstrip()
            unescapeExtension = sublime.load_settings(const.settingsFilename).get('unescape_quotes')
            if windowVars in unescapeExtension:
                queryToRun = queryToRun.replace("\\\"", "\"").replace("\\\'", "\'")


        Log.debug("Query: " + queryToRun)

        return Command(self._buildCommand(options), queryToRun)

    def execute(self, queries):
        command = self._getCommand(self.settings.get('options'), queries)
        command.start()
        self.killAftertimeout(command)

    def desc(self):
        query = self.settings.get('queries')['desc']['query']
        command = self._getCommand(self.settings.get('queries')['desc']['options'], query)

        tables = []
        for result in command.execute().splitlines():
            try:
                tables.append(result.split('|')[1].strip())
            except IndexError:
                pass

        return tables

    def getSchemaColumns(self):
        try:
            query = self.settings.get('queries')['columns']['query']
            command = self._getCommand(self.settings.get('queries')['columns']['options'], query)

            schemaColumns = []
            for result in command.execute().splitlines():
                try:
                    result = result.split('|')
                    schemaColumns.append('{0}.{1}'.format(result[0].strip(), result[1].strip()))
                except IndexError as e:
                    pass

            return schemaColumns
        except Exception:
            Log.debug("Support enabled just for postgresql and mysql")
            return []


    def descTable(self, tableName):
        query = self.settings.get('queries')['desc table']['query'] % tableName
        command = self._getCommand(self.settings.get('queries')['desc table']['options'], query)
        command.start()
        self.killAftertimeout(command)

    def showTableRecords(self, tableName):
        query = str(self.settings.get('queries')['show records']['query']).format(tableName, self.limit)
        command = self._getCommand(self.settings.get('queries')['show records']['options'], query)
        command.start()
        self.killAftertimeout(command)

    def killAftertimeout(self, command):
        timeout = sublime.load_settings(const.settingsFilename).get('thread_timeout', 5000)
        sublime.set_timeout(command.stop, timeout)
