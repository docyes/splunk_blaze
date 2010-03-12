#!/usr/bin/env python

def contextual_class_name(obj):
    """Takes an object reference and derives a css class name. Used primarily for deriving a contextual css selector per handler."""
    return obj.__class__.__name__.lower().replace("handler", "")

class BufferedWriter(object):
    """Convenience object to write and maintain ordering of rendered strings. Useful when dealing with multiple async requests and buffering responses."""
    def __init__(self, length, callback):
        self.buffer = [None for i in xrange(length)]
        self.count = 0
        self.length = length
        self.callback = callback

    def write(self, index, data):
        """Writes to the buffer at the specified indices. Note: Indices that are out of bounds will throw a ValueError."""
        if index<0 or index+1>self.length: 
            raise ValueError
        self.buffer[index] = data
        if self.buffer.count(None)==0:
            string = "".join(self.buffer)
            self.callback(string)