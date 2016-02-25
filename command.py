import sublime, os, subprocess, threading, signal, sys, shlex, tempfile

from . import const
from .general import Log

class Command(threading.Thread):
    def __init__(self, text, query=None):
        self.text     = text
        self.query = query
        self.process  = None
        threading.Thread.__init__(self)

    def _display(self, panelName, text):
        if not sublime.load_settings(const.
            settingsFilename).get('show_result_on_window'):
            panel = sublime.active_window().create_output_panel(panelName)
            sublime.active_window().run_command("show_panel", {"panel": "output." + panelName})
        else:
            panel = sublime.active_window().new_file()

        panel.set_read_only(False)
        panel.set_syntax_file('Packages/SQL/SQL.tmLanguage')
        panel.run_command('append', {'characters': text})
        panel.set_read_only(True)

    def _result(self, text):
        self._display('ST', text)

    def _errors(self, text):
        self._display('ST.errors', text)
        Log.debug("Query error: " + text)

    def execute(self):
        sublime.status_message(' ST: running SQL command')
        args = shlex.split(self.text)
        self.tmp = tempfile.NamedTemporaryFile(mode = 'w', delete = False, suffix='.sql')
        self.tmp.write(self.query)
        self.tmp.close()

        self.process = subprocess.Popen(args, stdout=subprocess.PIPE,stderr=subprocess.PIPE, stdin=open(self.tmp.name))

        results, errors = self.process.communicate(input=self.query.encode('utf-8'))

        if errors:
            Log.debug(errors.decode('utf-8', 'replace').replace('\r', ''))
            return self._errors(errors.decode('utf-8', 'replace').replace('\r', ''))

        return results.decode('utf-8', 'replace').replace('\r', '')

    def run(self):
        results = self.execute()
        self.process = None

        if results:
            self._result(results)

    def stop(self):
        if self.process:
            os.kill(self.process.pid, signal.SIGKILL)
            self.process = None
            if self.tmp and os.path.exists(self.tmp.name):
                os.unlink(self.tmp.name)

            sublime.message_dialog("Your command is taking too long to execute. Try to run outside of sublime.")
            Log.debug("Your command is taking too long to run. Killing process")
