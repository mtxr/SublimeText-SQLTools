import os
import signal
import subprocess

from threading import Thread, Timer
from .Log import Log


class Command:
    timeout = 5000

    def __init__(self, args, callback, query=None, encoding='utf-8'):
        self.query = query
        self.process = None
        self.args = args
        self.encoding = encoding
        self.callback = callback
        Thread.__init__(self)

    def run(self):
        if not self.query:
            return

        self.args = map(str, self.args)
        si = None
        if os.name == 'nt':
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        self.process = subprocess.Popen(self.args,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        stdin=subprocess.PIPE,
                                        env=os.environ.copy(),
                                        startupinfo=si)

        results, errors = self.process.communicate(input=self.query.encode())

        resultString = ''

        if results:
            resultString += results.decode(self.encoding,
                                           'replace').replace('\r', '')

        if errors:
            resultString += errors.decode(self.encoding,
                                          'replace').replace('\r', '')

        self.callback(resultString)

    @staticmethod
    def createAndRun(args, query, callback):
        command = Command(args, callback, query)
        command.run()


class ThreadCommand(Command, Thread):
    def __init__(self, args, callback, query=None, encoding='utf-8',
                 timeout=Command.timeout):
        self.query = query
        self.process = None
        self.args = args
        self.encoding = encoding
        self.callback = callback
        self.timeout = timeout
        Thread.__init__(self)

    def stop(self):
        if not self.process:
            return

        try:
            os.kill(self.process.pid, signal.SIGKILL)
            self.process = None

            Log.debug("Your command is taking too long to run. Process killed")
        except Exception:
            pass

    @staticmethod
    def createAndRun(args, query, callback):
        command = ThreadCommand(args, callback, query)
        command.start()
        killTimeout = Timer(command.timeout, command.stop)
        killTimeout.start()
