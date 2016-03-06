import sublime, sublime_plugin, sys, os

sys.path.append(os.path.dirname(__file__))
from SQLToolsModels import Log, Settings, Connection, Selection, Window, View, Const, History

class ST(sublime_plugin.EventListener):
    conn             = None
    history          = []
    tables           = []
    columns          = []
    connectionList   = {}
    autoCompleteList = []

    @staticmethod
    def bootstrap():
        ST.connectionList = Settings.getConnections()
        ST.checkDefaultConnection()

    @staticmethod
    def loadConnectionData():
        if not ST.conn:
            return

        ST.conn.getTables(lambda tables: setattr(ST, 'tables', tables))
        ST.conn.getColumns(lambda columns: setattr(ST, 'columns', columns))

    @staticmethod
    def setConnection(index):
        if index < 0 or index > (len(ST.connectionList) - 1) :
            return


        connListNames = list(ST.connectionList.keys())
        connListNames.sort()
        ST.conn = ST.connectionList.get(connListNames[index])
        ST.loadConnectionData()

        Log.debug('Connection {0} selected'.format(ST.conn))

    @staticmethod
    def showConnectionMenu():
        ST.connectionList = Settings.getConnections()
        if len(ST.connectionList) == 0:
            sublime.message_dialog('You need to setup your connections first.')
            return

        menu = []
        for name, conn in ST.connectionList.items():
            menu.append(conn._quickPanel())
        menu.sort()
        Window().show_quick_panel(menu, ST.setConnection)

    def on_query_completions(self, view, prefix, locations):
        if prefix == "":
            region = sublime.Region(locations[0], locations[0])
            try:
                prefix = view.substr(view.line(region)).split(" ").pop()
            except Exception:
                pass

        return self.getAutoCompleteList(prefix)

    def getAutoCompleteList(self, word):
        ST.autoCompleteList = []
        for w in ST.tables:
            try:
                if word.lower() in w.lower():
                    ST.autoCompleteList.append(("{0}\t({1})".format(w, 'Table'), w))
            except UnicodeDecodeError:
                continue

        for w in ST.columns:
            try:
                if word.lower() in w.lower():
                    ST.autoCompleteList.append(("{0}\t({1})".format(w.split(".")[1], w.split(".")[0] + ' Col'), w.split(".")[1]))
            except Exception:
                continue

        ST.autoCompleteList.sort()
        return (ST.autoCompleteList, sublime.INHIBIT_EXPLICIT_COMPLETIONS)

    @staticmethod
    def checkDefaultConnection():
        default = Connection.loadDefaultConnectionName()
        if not default:
            return
        try:
            ST.conn = ST.connectionList.get(default)
            ST.loadConnectionData()
        except Exception as e:
            Log.debug("Invalid connection setted")

    @staticmethod
    def display(content, name="SQLTools Result"):
        if not sublime.load_settings(Const.SETTINGS_FILENAME).get('show_result_on_window'):
            resultContainer = Window().create_output_panel(name)
            Window().run_command("show_panel", {"panel": "output." + name})
        else:
            resultContainer = Window().new_file()
            resultContainer.set_name(name)

        resultContainer.settings().set("word_wrap", "false")
        resultContainer.set_read_only(False)
        resultContainer.set_syntax_file('Packages/SQL/SQL.tmLanguage')
        resultContainer.run_command('append', {'characters': content})
        resultContainer.set_read_only(True)

#
# Commands
#

class StShowConnectionMenu(sublime_plugin.WindowCommand):
    def run (self):
        ST.showConnectionMenu()

class StShowRecords(sublime_plugin.WindowCommand):
    def run(self):
        if not ST.conn:
            ST.showConnectionMenu()
            return

        Window().show_quick_panel(ST.tables, lambda index: ST.conn.getTableRecords(ST.tables[index], ST.display) if index != -1 else None)

class StDescTable(sublime_plugin.WindowCommand):
    def run(self):
        if not ST.conn:
            ST.showConnectionMenu()
            return

        Window().show_quick_panel(ST.tables, lambda index: ST.conn.getTableDescription(ST.tables[index], ST.display) if index != -1 else None)

class StHistory(sublime_plugin.WindowCommand):
    def run(self):
        if not ST.conn:
            ST.showConnectionMenu()
            return

        if len(History.queries) == 0:
            sublime.message_dialog('History is empty.')
            return
        try:
            Window().show_quick_panel(History.queries, lambda index: ST.conn.execute(History.get(index), ST.display) if index != -1 else None)
        except Exception:
            pass

class StExecute(sublime_plugin.WindowCommand):
    def run(self):
        if not ST.conn:
            ST.showConnectionMenu()
            return

        query = Selection.get()
        ST.conn.execute(query, ST.display)

class StFormat(sublime_plugin.TextCommand):
    def run(self, edit):
        Selection.formatSql(edit)

def plugin_loaded():
    Log.debug(__name__ + ' loaded successfully')

    ST.bootstrap()
