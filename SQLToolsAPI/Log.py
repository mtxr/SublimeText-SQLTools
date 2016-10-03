VERSION = "v0.1.0"


class Logger:
    logging = False
    packageName = "SQLTools"
    packageVersion = VERSION

    @staticmethod
    def debug(message):
        if not Logger.isLogging():
            return

        print ("%s (%s): %s" % (Logger.packageName,
                                Logger.packageVersion,
                                message))

    @staticmethod
    def setLogging(param):
        Logger.logging = param
        Log('Logging is active')

    @staticmethod
    def isLogging():
        return Logger.logging

    @staticmethod
    def setPackageName(param):
        Logger.packageName = param

    @staticmethod
    def getPackageName():
        return Logger.packageName

    @staticmethod
    def setPackageVersion(param):
        Logger.packageVersion = param

    @staticmethod
    def getPackageVersion():
        return Logger.packageVersion


def Log(message):
    return Logger.debug(message)
