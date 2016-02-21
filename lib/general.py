import sublime
from SQLTools import const

class Selection:
    def __init__(self, view):
        self.view = view
    def getQueries(self):
        text = []
        if self.view.sel():
            for region in self.view.sel():
                if region.empty():
                    text.append(self.view.substr(self.view.line(region)))
                else:
                    text.append(self.view.substr(region))
        return text

class Options:
    def __init__(self, name):
        self.name     = name
        connections   = sublime.load_settings(const.connectionsFilename).get('connections')
        self.type     = connections[self.name]['type']
        self.host     = connections[self.name]['host']
        self.port     = connections[self.name]['port']
        self.username = connections[self.name]['username']
        self.database = connections[self.name]['database']

        if 'password' in connections[self.name]:
            self.password = connections[self.name]['password']

        if 'service' in connections[self.name]:
            self.service  = connections[self.name]['service']

        Log.debug("Options loaded for {0} connection".format(self.name))

    def __str__(self):
        return self.name

    @staticmethod
    def list():
        names = []
        connections = sublime.load_settings(const.connectionsFilename).get('connections')

        Log.debug("Found {0} connections".format(len(connections)))

        for connection in connections:
            names.append(connection)
        names.sort()
        return names

class Log:

    @staticmethod
    def debug(message):
        if not sublime.load_settings(const.settingsFilename).get('debug', False):
            return
        print ("SQLTools: " + message)
