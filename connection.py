import sublime, tempfile

from SQLTools import const
from SQLTools.command import Command
from SQLTools.general import Log

class Connection:
    def __init__(self, options):
        self.settings = sublime.load_settings('{0}.{1}'.format(options.type, const.settingsExtension))
        self.command  = sublime.load_settings(const.settingsFilename).get('commands').get(options.type)
        self.limit    = sublime.load_settings(const.settingsFilename).get('show_records').get('limit', 50)
        self.options  = options

    def _buildCommand(self, options):
        return self.command + ' ' + ' '.join(options) + ' ' + self.settings.get('args').format(options=self.options)

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

        self.tmp = tempfile.NamedTemporaryFile(mode = 'w', delete = False, suffix='.sql')
        self.tmp.write(queryToRun)
        self.tmp.close()

        cmd = '%s < "%s"' % (self._buildCommand(options), self.tmp.name)

        return Command(cmd, self.tmp.name)

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
