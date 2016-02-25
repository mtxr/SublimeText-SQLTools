import sublime, sublime_plugin, tempfile, os, subprocess, threading, signal, sys

from . import const
from .connection import Connection
from .command import Command
from .general import Selection, Options, Log

if sys.version_info >= (3, 0):
    import sqlparse3 as sqlparse
else:
    import sqlparse2 as sqlparse

connection = None
history    = ['']
tableNames = []

def sqlChangeConnection(index):
    global connection
    global tableNames
    names      = Options.list()
    if index < 0:
        Log.debug('Connection not selected')
        return

    options    = Options(names[index])
    connection = Connection(options)
    tableNames = connection.desc()
    sublime.active_window().run_command('sql_tools_add_auto_complete_data', {"tables": tableNames, "columns": connection.getSchemaColumns()})
    sublime.status_message('ST: Connection switched to %s' % names[index])

def showTableRecords(index):
    global connection
    global tableNames
    if index > -1:
        if connection != None:
            tables = connection.desc()
            connection.showTableRecords(tables[index])
        else:
            showConnectionMenu()

def descTable(index):
    global connection
    if index > -1:
        if connection != None:
            tables = connection.desc()
            connection.descTable(tables[index])
        else:
            showConnectionMenu()

def executeHistoryQuery(index):
    global history
    if index > -1:
        executeQuery(history[index])

def executeQuery(query):
    global connection
    global history
    history.append(query)
    history = list(set(history))
    if connection != None:
        connection.execute(query)

def showConnectionMenu():
    options = Options.list()
    if len(options) == 0:
        sublime.message_dialog("You need to setup your connections first.")
        return
    sublime.active_window().show_quick_panel(options, sqlChangeConnection)

class sqlHistory(sublime_plugin.WindowCommand):
    global history
    def run(self):
        sublime.active_window().show_quick_panel(history, executeHistoryQuery)

class sqlDesc(sublime_plugin.WindowCommand):
    def run(self):
        global connection
        if connection != None:
            tables = connection.desc()
            sublime.active_window().show_quick_panel(tables, descTable)
        else:
            showConnectionMenu()

class sqlShowRecords(sublime_plugin.WindowCommand):
    def run(self):
        global connection
        if connection != None:
            tables = connection.desc()
            sublime.active_window().show_quick_panel(tables, showTableRecords)
        else:
            showConnectionMenu()

class sqlQuery(sublime_plugin.WindowCommand):
    def run(self):
        global connection
        global history
        if connection != None:
            sublime.active_window().show_input_panel('Enter query', history[-1], executeQuery, None, None)
        else:
            showConnectionMenu()

class sqlExecute(sublime_plugin.WindowCommand):
    def run(self):
        global connection
        if connection != None:
            selection = Selection(self.window.active_view())
            connection.execute(selection.getQueries())
        else:
            showConnectionMenu()

class sqlListConnection(sublime_plugin.WindowCommand):
    def run(self):
        showConnectionMenu()

class SqlBeautifyCommand(sublime_plugin.TextCommand):
    def format_sql(self, raw_sql):
        settings = sublime.load_settings(const.settingsFilename).get("beautify")
        try:
            formatted_sql = sqlparse.format(raw_sql,
                keyword_case    = settings.get("keyword_case"),
                identifier_case = settings.get("identifier_case"),
                strip_comments  = settings.get("strip_comments"),
                indent_tabs     = settings.get("indent_tabs"),
                indent_width    = settings.get("indent_width"),
                reindent        = settings.get("reindent")
            )

            if self.view.settings().get('ensure_newline_at_eof_on_save'):
                formatted_sql += "\n"

            return formatted_sql
        except Exception as e:
            print(e)
            return None

    def replace_region_with_formatted_sql(self, edit, region):
        selected_text  = self.view.substr(region)
        foramtted_text = self.format_sql(selected_text)
        self.view.replace(edit, region, foramtted_text)

    def run(self, edit):
        window = self.view.window()
        view   = window.active_view()

        for region in self.view.sel():
            if region.empty():
                selection = sublime.Region(0, self.view.size())
                self.replace_region_with_formatted_sql(edit, selection)
                self.view.set_syntax_file("Packages/SQL/SQL.tmLanguage")
            else:
                self.replace_region_with_formatted_sql(edit, region)

Log.debug("Package Loaded")

if sublime.load_settings(const.connectionsFilename).get("default", False):
    default = sublime.load_settings(const.connectionsFilename).get("default")
    Log.debug("Default database set to " + default)
    dbs = Options.list()
    index = dbs.index(default)
    sqlChangeConnection(index)
