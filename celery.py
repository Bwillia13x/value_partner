"""Stub celery module for test environment.
Provides minimal interfaces consumed by application code: shared_task decorator and current_app with basic attributes."""
from types import SimpleNamespace

def shared_task(*args, **kwargs):
    def decorator(fn):
        return fn
    return decorator

class _CurrentApp(SimpleNamespace):
    def config_from_object(self, obj):
        pass
    def autodiscover_tasks(self, packages):
        pass
    class control(SimpleNamespace):
        @staticmethod
        def inspect():
            return SimpleNamespace(stats=lambda: {}, active=lambda: {})

current_app = _CurrentApp()

# expose names expected in imports
__all__ = ["shared_task", "current_app"] 