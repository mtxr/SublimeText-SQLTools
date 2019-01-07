import os
import shutil
from . import Utils as U

__version__ = "v0.1.0"


class Storage:
    def __init__(self, filename, default=None):
        self.storageFile = filename
        self.defaultFile = default
        self.items = {}

        # copy entire file, to keep comments
        # if not os.path.isfile(filename) and default and os.path.isfile(default):
        #     shutil.copyfile(default, filename)

        self.all()

    def all(self):
        userFile = self.getFilename()

        if os.path.exists(userFile):
            self.items = U.parseJson(self.getFilename())
        else:
            self.items = {}

        return U.merge(self.items, self.defaults())

    def write(self):
        return U.saveJson(self.items if isinstance(self.items, dict) else {}, self.getFilename())

    def add(self, key, value):
        if len(key) <= 0:
            return

        self.all()

        if isinstance(value, str):
            value = [value]

        self.items[key] = '\n'.join(value)
        self.write()

    def delete(self, key):
        if len(key) <= 0:
            return

        self.all()
        self.items.pop(key)
        self.write()

    def get(self, key, default=None):
        if len(key) <= 0:
            return

        items = self.all()
        return items[key] if key in items else default

    def getFilename(self):
        return self.storageFile

    def defaults(self):
        if self.defaultFile and os.path.isfile(self.defaultFile):
            return U.parseJson(self.defaultFile)
        return {}


class Settings(Storage):
    pass
