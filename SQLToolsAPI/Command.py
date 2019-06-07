import os
import signal
import subprocess
import time
import logging

from threading import Thread, Timer

logger = logging.getLogger(__name__)

class Command(object):
    timeout = 15

    def __init__(self, args, env, callback, query=None, encoding='utf-8',
                 options=None, timeout=15, silenceErrors=False, stream=False):
        if options is None:
            options = {}

        self.args = args
        self.env = env
        self.callback = callback
        self.query = query
        self.encoding = encoding
        self.options = options
        self.timeout = timeout
        self.silenceErrors = silenceErrors
        self.stream = stream
        self.process = None

        if 'show_query' not in self.options:
            self.options['show_query'] = False
        elif self.options['show_query'] not in ['top', 'bottom']:
            self.options['show_query'] = 'top' if (isinstance(self.options['show_query'], bool) and
                                                   self.options['show_query']) else False

    def run(self):
        if not self.query:
            return

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

        # set the environment
        modifiedEnvironment = os.environ.copy()
        if (self.env):
            modifiedEnvironment.update(self.env)

        queryTimerStart = time.time()

        self.process = subprocess.Popen(self.args,
                                        stdout=subprocess.PIPE,
                                        stderr=stderrHandle,
                                        stdin=subprocess.PIPE,
                                        env=modifiedEnvironment,
                                        startupinfo=si)

        if self.stream:
            self.process.stdin.write(self.query.encode(self.encoding))
            self.process.stdin.close()
            hasWritten = False

            for line in self.process.stdout:
                self.callback(line.decode(self.encoding, 'replace').replace('\r', ''))
                hasWritten = True

            queryTimerEnd = time.time()
            # we are done with the output, terminate the process
            if self.process:
                self.process.terminate()
            else:
                if hasWritten:
                    self.callback('\n')

            if self.options['show_query']:
                formattedQueryInfo = self._formatShowQuery(self.query, queryTimerStart, queryTimerEnd)
                self.callback(formattedQueryInfo + '\n')

            return

        # regular mode is handled with more reliable Popen.communicate
        # which also terminates the process afterwards
        results, errors = self.process.communicate(input=self.query.encode(self.encoding))

        queryTimerEnd = time.time()

        resultString = ''

        if results:
            resultString += results.decode(self.encoding,
                                           'replace').replace('\r', '')

        if errors and not self.silenceErrors:
            resultString += errors.decode(self.encoding,
                                          'replace').replace('\r', '')

        if self.process is None and resultString != '':
            resultString += '\n'

        if self.options['show_query']:
            formattedQueryInfo = self._formatShowQuery(self.query, queryTimerStart, queryTimerEnd)
            queryPlacement = self.options['show_query']
            if queryPlacement == 'top':
                resultString = "{0}\n{1}".format(formattedQueryInfo, resultString)
            elif queryPlacement == 'bottom':
                resultString = "{0}{1}\n".format(resultString, formattedQueryInfo)

        self.callback(resultString)

    @staticmethod
    def _formatShowQuery(query, queryTimeStart, queryTimeEnd):
        resultInfo = "/*\n-- Executed querie(s) at {0} took {1:.3f} s --".format(
            str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(queryTimeStart))),
            (queryTimeEnd - queryTimeStart))
        resultLine = "-" * (len(resultInfo) - 3)
        resultString = "{0}\n{1}\n{2}\n{3}\n*/".format(
            resultInfo, resultLine, query, resultLine)
        return resultString

    @staticmethod
    def createAndRun(args, env, callback, query=None, encoding='utf-8',
                     options=None, timeout=15, silenceErrors=False, stream=False):
        if options is None:
            options = {}
        command = Command(args=args,
                          env=env,
                          callback=callback,
                          query=query,
                          encoding=encoding,
                          options=options,
                          timeout=timeout,
                          silenceErrors=silenceErrors,
                          stream=stream)
        command.run()


class ThreadCommand(Command, Thread):
    def __init__(self, args, env, callback, query=None, encoding='utf-8',
                 options=None, timeout=Command.timeout, silenceErrors=False, stream=False):
        if options is None:
            options = {}

        Command.__init__(self,
                         args=args,
                         env=env,
                         callback=callback,
                         query=query,
                         encoding=encoding,
                         options=options,
                         timeout=timeout,
                         silenceErrors=silenceErrors,
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

            logger.info("command execution exceeded timeout (%s s), process killed", self.timeout)
            self.callback(("Command execution time exceeded 'thread_timeout' ({0} s).\n"
                           "Process killed!\n\n"
                          ).format(self.timeout))
        except Exception:
            logger.info("command execution exceeded timeout (%s s), process could not be killed", self.timeout)
            self.callback(("Command execution time exceeded 'thread_timeout' ({0} s).\n"
                           "Process could not be killed!\n\n"
                          ).format(self.timeout))
            pass

    @staticmethod
    def createAndRun(args, env, callback, query=None, encoding='utf-8',
                     options=None, timeout=Command.timeout, silenceErrors=False, stream=False):
        # Don't allow empty dicts or lists as defaults in method signature,
        # cfr http://nedbatchelder.com/blog/200806/pylint.html
        if options is None:
            options = {}
        command = ThreadCommand(args=args,
                                env=env,
                                callback=callback,
                                query=query,
                                encoding=encoding,
                                options=options,
                                timeout=timeout,
                                silenceErrors=silenceErrors,
                                stream=stream)
        command.start()
        killTimeout = Timer(command.timeout, command.stop)
        killTimeout.start()
