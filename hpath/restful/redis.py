"""Redis queue and worker.

See:
    https://python-rq.org/docs/
"""
import redis
from rq import Queue, Worker

from ..conf import REDIS_HOST, REDIS_PORT


REDIS_CONN = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT  # default
)
"""Provides an connection to the redis server at ``redis://<REDIS_HOST>:<REDIS_PORT>``."""

REDIS_QUEUE = Queue(connection=REDIS_CONN, default_timeout=3600)
"""Set up the default RQ queue for the redis server."""


def main() -> None:
    """Start an RQ worker on the default queue."""
    worker = Worker([REDIS_QUEUE], connection=REDIS_CONN)
    worker.work()


if __name__ == '__main__':
    main()
