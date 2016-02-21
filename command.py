import sublime, os, subprocess, threading, signal

from SQLTools import const
from SQLTools.general import Log

class Command(threading.Thread):
    def __init__(self, text, tempfile=None):
        self.text     = text
        self.tempfile = tempfile
        self.process  = None
        threading.Thread.__init__(self)

    def _display(self, panelName, text):
        if not sublime.load_settings(const.settingsFilename).get('show_result_on_window'):
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
        self.process = subprocess.Popen(self.text, stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True, preexec_fn=os.setsid)
        results, errors = self.process.communicate()

        if errors:
            return self._errors(errors.decode('utf-8', 'replace').replace('\r', ''))

        return results.decode('utf-8', 'replace').replace('\r', '')

    def run(self):
        results = self.execute()
        self.process = None

        if results:
            self._result(results)

        if self.tempfile and os.path.exists(self.tempfile):
            os.unlink(self.tempfile)
    def stop(self):
        if self.process:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process = None
            if self.tempfile:
                os.unlink(self.tempfile)
            sublime.message_dialog("Query is taking too long to execute. Try to run outside of sublime.")
            Log.debug("Query is taking too long to run. Killing process")
