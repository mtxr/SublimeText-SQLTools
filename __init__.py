
import sublime, sublime_plugin, tempfile, os, subprocess, threading, signal

from SQLTools import const
from SQLTools.connection import Connection
from SQLTools.command import Command
from SQLTools.general import Selection, Options, Log

connection          = None
history             = ['']

def sqlChangeConnection(index):
    global connection
    names = Options.list()
    options = Options(names[index])
    connection = Connection(options)
    sublime.status_message('ST: Connection switched to %s' % names[index])

def showTableRecords(index):
    global connection
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

Log.debug("Package Loaded")
