"""Stub psutil module for CI environment without native deps."""
from random import random

def cpu_percent(interval=None):
    return round(random()*100, 2)

class _MemInfo:
    def __init__(self, rss=0):
        self.rss = rss

class Process:
    def __init__(self, pid=None):
        self._start_mem = random()*100*1024*1024  # bytes
    def memory_info(self):
        return _MemInfo(rss=self._start_mem + random()*10*1024*1024)
    def cpu_percent(self):
        return round(random()*100, 2)

__all__ = ["cpu_percent", "Process"] 