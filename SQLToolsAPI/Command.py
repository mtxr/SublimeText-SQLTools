import os
import signal
import subprocess
import time

from threading import Thread, Timer
from .Log import Log


class Command:
    timeout = 15

    def __init__(self, args, callback, query=None, encoding='utf-8',
                 options=None, timeout=15):
        if options is None:
            options = {}

        self.args = args
        self.callback = callback
        self.query = query
        self.encoding = encoding
        self.options = options
        self.timeout = timeout
        self.process = None

    def run(self):
        if not self.query:
            return

        queryTimerStart = time.time()

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

        queryTimerEnd = time.time()

        resultString = ''

        if results:
            resultString += results.decode(self.encoding,
                                           'replace').replace('\r', '')

        if errors:
            resultString += errors.decode(self.encoding,
                                          'replace').replace('\r', '')

        if 'show_query' in self.options and self.options['show_query']:
            resultInfo = "/*\n-- Executed querie(s) at {0} took {1}ms --".format(
                str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(queryTimerStart))),
                str(queryTimerEnd - queryTimerStart))
            resultLine = "-" * (len(resultInfo) - 3)
            resultString = "{0}\n{1}\n{2}\n{3}\n*/\n{4}".format(
                resultInfo, resultLine, self.query, resultLine, resultString)

        self.callback(resultString)

    @staticmethod
    def createAndRun(args, query, callback, options=None):
        # Don't allow empty dicts or lists as defaults in method signature,
        # cfr http://nedbatchelder.com/blog/200806/pylint.html
        if options is None:
            options = {}
        command = Command(args, callback, query, options=options)
        command.run()


class ThreadCommand(Command, Thread):
    def __init__(self, args, callback, query=None, encoding='utf-8',
                 options=None, timeout=Command.timeout):
        if options is None:
            options = {}

        self.args = args
        self.callback = callback
        self.query = query
        self.encoding = encoding
        self.options = options
        self.timeout = timeout
        self.process = None
        Thread.__init__(self)

    def stop(self):
        if not self.process:
            return

        try:
            # Windows does not provide SIGKILL, go with SIGTERM
            sig = getattr(signal, 'SIGKILL', signal.SIGTERM)
            os.kill(self.process.pid, sig)
            self.process = None

            Log("Your command is taking too long to run. Process killed")
            self.callback("Command execution time exceeded 'thread_timeout'.\nProcess killed!\n\n")
        except Exception:
            pass

    @staticmethod
    def createAndRun(args, query, callback, options=None, timeout=Command.timeout):
        # Don't allow empty dicts or lists as defaults in method signature,
        # cfr http://nedbatchelder.com/blog/200806/pylint.html
        if options is None:
            options = {}
        command = ThreadCommand(args, callback, query, options=options, timeout=timeout)
        command.start()
        killTimeout = Timer(command.timeout, command.stop)
        killTimeout.start()
