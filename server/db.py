import os
import logging
from contextlib import asynccontextmanager

import psycopg2
from psycopg2 import pool

logger = logging.getLogger(__name__)

_pool = None


def init_pool(database_url=None, min_conn=2, max_conn=10):
    global _pool
    if database_url is None:
        database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set")
    _pool = pool.ThreadedConnectionPool(min_conn, max_conn, database_url)
    logger.info("Database connection pool initialized (min=%d, max=%d)", min_conn, max_conn)


def get_pool():
    if _pool is None:
        raise RuntimeError("Connection pool not initialized. Call init_pool() first.")
    return _pool


def get_conn():
    return get_pool().getconn()


def put_conn(conn):
    get_pool().putconn(conn)


def close_pool():
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        logger.info("Database connection pool closed")


def check_health():
    try:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
            return True
        finally:
            put_conn(conn)
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        return False
