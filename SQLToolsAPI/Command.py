import os
import signal
import subprocess
import time

from threading import Thread, Timer
from .Log import Log


class Command(object):
    timeout = 15

    def __init__(self, args, callback, query=None, encoding='utf-8',
                 options=None, timeout=15, silenceErrors=False, stream=False):
        if options is None:
            options = {}

        self.stream = stream
        self.args = args
        self.callback = callback
        self.query = query
        self.encoding = encoding
        self.options = options
        self.timeout = timeout
        self.silenceErrors = silenceErrors
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

        # select appropriate file handle for stderr
        # usually we want to redirect stderr to stdout, so erros are shown
        # in the output in the right place (where they actually occurred)
        # only if silenceErrors=True, we separate stderr from stdout and discard it
        stderrHandle = subprocess.STDOUT
        if self.silenceErrors:
            stderrHandle = subprocess.PIPE

        self.process = subprocess.Popen(self.args,
                                        stdout=subprocess.PIPE,
                                        stderr=stderrHandle,
                                        stdin=subprocess.PIPE,
                                        env=os.environ.copy(),
                                        startupinfo=si)

        if self.stream:
            self.process.stdin.write(self.query.encode())
            self.process.stdin.close()
            for line in self.process.stdout:
                self.callback(line.decode(self.encoding,
                    'replace').replace('\r', ''))

            queryTimerEnd = time.time()
            # we are done with the output, terminate the process
            self.process.terminate()

            if 'show_query' in self.options and self.options['show_query']:
                resultInfo = "/*\n-- Executed querie(s) at {0} took {1:.3f}ms --".format(
                    str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(queryTimerStart))),
                    (queryTimerEnd - queryTimerStart))
                resultLine = "-" * (len(resultInfo) - 3)
                resultString = "{0}\n{1}\n{2}\n{3}\n*/".format(
                    resultInfo, resultLine, self.query, resultLine)
                return self.callback(resultString)

            return

        # regular mode is handled with more reliable Popen.communicate
        # which also terminates the process afterwards
        results, errors = self.process.communicate(input=self.query.encode())

        queryTimerEnd = time.time()

        resultString = ''

        if results:
            resultString += results.decode(self.encoding,
                                           'replace').replace('\r', '')

        if errors and not self.silenceErrors:
            resultString += errors.decode(self.encoding,
                                          'replace').replace('\r', '')

        if 'show_query' in self.options and self.options['show_query']:
            resultInfo = "/*\n-- Executed querie(s) at {0} took {1:.3f}ms --".format(
                str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(queryTimerStart))),
                (queryTimerEnd - queryTimerStart))
            resultLine = "-" * (len(resultInfo) - 3)
            resultString = "{0}\n{1}\n{2}\n{3}\n*/\n{4}".format(
                resultInfo, resultLine, self.query, resultLine, resultString)

        self.callback(resultString)

    @staticmethod
    def createAndRun(args, query, callback, options=None, timeout=15, silenceErrors=False, stream=False):
        if options is None:
            options = {}
        command = Command(args, callback, query, options=options,
                          timeout=timeout, silenceErrors=silenceErrors)
        command.run()


class ThreadCommand(Command, Thread):
    def __init__(self, args, callback, query=None, encoding='utf-8',
                 options=None, timeout=Command.timeout, silenceErrors=False, stream=False):
        if options is None:
            options = {}

        Command.__init__(self, args, callback, query=query,
                         encoding=encoding, options=options,
                         timeout=timeout, silenceErrors=silenceErrors,
                         stream=stream)
        Thread.__init__(self)

    def stop(self):
        if not self.process:
            return

        # if poll returns None - proc still running, otherwise returns process return code
        if self.process.poll() is not None:
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
    def createAndRun(args, query, callback, options=None,
                     timeout=Command.timeout, silenceErrors=False, stream=False):
        # Don't allow empty dicts or lists as defaults in method signature,
        # cfr http://nedbatchelder.com/blog/200806/pylint.html
        if options is None:
            options = {}
        command = ThreadCommand(args, callback, query, options=options,
                                timeout=timeout, silenceErrors=silenceErrors, stream=stream)
        command.start()
        killTimeout = Timer(command.timeout, command.stop)
        killTimeout.start()
