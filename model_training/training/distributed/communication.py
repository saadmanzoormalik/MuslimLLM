from contextlib import contextmanager
import time


@contextmanager
def communication_timer(metrics: dict, name: str):
    started = time.perf_counter()
    try: yield
    finally: metrics[name] = metrics.get(name, 0.0) + time.perf_counter() - started

