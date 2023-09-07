"""Redis queue and worker.

See:
    https://python-rq.org/docs/
"""
import redis
from rq import Queue, Worker


REDIS_CONN = redis.Redis(
    host='redis',
    port=6379  # default
)
"""Provides an connection to the redis server at ``redis://redis:6379``."""

REDIS_QUEUE = Queue(connection=REDIS_CONN, default_timeout=3600)
"""Set up the default RQ queue for the redis server."""


def main() -> None:
    """Start an RQ worker on the default queue."""
    worker = Worker([REDIS_QUEUE], connection=REDIS_CONN)
    worker.work()


if __name__ == '__main__':
    main()
