Program Architecture
====================

Docker services
---------------

The simulation backend server is implemented as a set of Docker containers:

- **docs**: Serves this documentation website.  Based on the ``httpd:alpine``
  `Docker image <https://hub.docker.com/_/httpd/>`_.
- **redis**: Provides a redis service for the `RQ <https://python-rq.org/docs/>`_ job queue.
  Based on the ``redis:alpine`` `Docker image <https://hub.docker.com/_/redis/>`_.
- **redis-worker**: Runs simulation jobs from the job queue.
- **server**: RESTful server for submitting simulation jobs and viewing their status/results.

.. image:: https://kroki.io/graphviz/svg/eNodjDEOwjAMAPe-wupeVAbYzMQvEEPAbmJh4sqJCAXxdyjTnW44kuhhTnCEdweQjRhO9-BRMo4wWa5FXozbPTShmnDc7KCkMDNe7AmlLso4iSoTrLiamqNKTDWaEmc3WljV2vl3dyYpMByg_9vQzG_s_VoK-4O9-3wBBlAyGQ==
    :width: 120
    :alt: Relationship between the Docker services of this application.

The relationship between the Docker services is shown above. Each service in the figure depends on
the services above.

Database structure
------------------

Scenario results and simulation statuses are stored in a SQLite database with the following schema:

.. image:: https://kroki.io/dbml/svg/eNp1kEkOwjAMRfc5hQ9AKesuOATqrkLINC6KSJwqSSUixN1xmRohWFn-fh6-WzxagtgTYzA-wlXBJzsYDYYTnShANwbjMGQ4U94Lg4w2RxMLRtQ-ECbSIMFCxz4BT9bOfO_daOldE4Endwg0xmVDiWvP9Ke8Ak0DTjY1sJnRQFGSCIkuSd2Uah-OnGjmaefHqV92pGtHQ7O8YV30bF-zSg3qGhxyrpKv5FKl7i1Hc0E=
    :width: 500
    :alt: Database schema diagram

In the above DBML diagram, the primary keys of each table are shown in bold text and are set to
``AUTOINCREMENT``. The ``(!)`` marker represents ``NOT NULL``. The ``created`` and ``completed``
fields are UNIX timestamps, while the ``results`` field is a JSON string.