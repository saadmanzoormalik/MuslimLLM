import os
from contextlib import contextmanager

import psycopg
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://muslim_llm:muslim_llm@localhost:5432/muslim_llm")
_POOL: ConnectionPool | None = None


def connection_pool() -> ConnectionPool:
    global _POOL
    if _POOL is None:
        _POOL = ConnectionPool(
            conninfo=DATABASE_URL,
            min_size=int(os.getenv("DB_POOL_MIN_SIZE", "1")),
            max_size=int(os.getenv("DB_POOL_MAX_SIZE", "10")),
            kwargs={"row_factory": dict_row},
            open=True,
        )
    return _POOL


@contextmanager
def get_conn():
    with connection_pool().connection() as conn:
        yield conn


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in values) + "]"
