__version__ = "v0.1.0"


class SizeException(Exception):
    pass


class NotFoundException(Exception):
    pass


class History:

    def __init__(self, maxSize=100):
        self.items = []
        self.maxSize = maxSize

    def add(self, query):
        if self.getSize() >= self.getMaxSize():
            self.items.pop(0)
        self.items.insert(0, query)

    def get(self, index):
        if index < 0 or index > (len(self.items) - 1):
            raise NotFoundException("No query selected")

        return self.items[index]

    def setMaxSize(self, size=100):
        if size < 1:
            raise SizeException("Size can't be lower than 1")

        self.maxSize = size
        return self.maxSize

    def getMaxSize(self):
        return self.maxSize

    def getSize(self):
        return len(self.items)

    def all(self):
        return self.items

    def clear(self):
        self.items = []
        return self.items
