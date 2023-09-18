Program Architecture
====================

This project implements digital tools for Cambridge University Hospitals NHS Trust.

Docker services
---------------

The digital hospitals server is implemented as a set of Docker containers:

- **docs**: Serves this documentation website.  Based on the ``httpd:alpine``
  `Docker image <https://hub.docker.com/_/httpd/>`_.
- **redis**: Provides a redis service for the `RQ <https://python-rq.org/docs/>`_ job queue.
  Based on the ``redis:alpine`` `Docker image <https://hub.docker.com/_/redis/>`_.
- **redis-worker**: Runs simulation jobs from the job queue.
- **backend**: RESTful server for submitting simulation jobs and viewing their status/results.
- **frontend**: React.js based frontend server for accessing the sensors and histopathology
  simulation dashboards.  (`GitHub link <https://github.com/lakeesiv/digital-twin>`_)

.. image:: _static/docker_compose.svg
    :width: 300
    :alt: Relationship between the Docker services of this application.

..
   https://niolesk.top/#https://kroki.io/graphviz/svg/eNpVjsEOgjAQRO98xYazGDTRi6kn_4J4KOxCG5YuaUkQDf8uhWDiaWfysjODtvG6N_CATwLgBAmKTvvGOpVDLW4I9k3qdIXR4mBUfrxAMLonVcoLwjAxqdoyE0I8lbB4xbYxQyOM5LzgRMwyPpd0T2gDZHdIV5WN4lvy6UJi98K1a1XQHd1Wi1KFVZS6asnhqmu_bNrMnPxQDN0JFNss1MEQHjrrmJw6xwH_vfFpj56_zMtW7w==

The relationship between the Docker services is shown above. Each service in the figure depends on
the services above.  The dashed line denotes that the frontend depends on the "server" service
but will still launch without a running backend server (albeit without the relevant
functionalities).

**TODO**: add sensor server to the docker bundle.

Database structure
------------------

Scenario results and simulation statuses are stored in a SQLite database with the following schema:

.. image:: _static/db_schema.svg
    :width: 500
    :alt: Database schema diagram

..
  https://niolesk.top/#https://kroki.io/dbml/svg/eNp1kEkOwjAMRfc5hQ9AKesuOATqrkLINC6KSJwqSSUixN1xmRohWFn-fh6-WzxagtgTYzA-wlXBJzsYDYYTnShANwbjMGQ4U94Lg4w2RxMLRtQ-ECbSIMFCxz4BT9bOfO_daOldE4Endwg0xmVDiWvP9Ke8Ak0DTjY1sJnRQFGSCIkuSd2Uah-OnGjmaefHqV92pGtHQ7O8YV30bF-zSg3qGhxyrpKv5FKl7i1Hc0E=

In the above DBML diagram, the primary keys of each table are shown in bold text and are set to
``AUTOINCREMENT``. The ``(!)`` marker represents ``NOT NULL``. The ``created`` and ``completed``
fields are UNIX timestamps, while the ``results`` field is a JSON string.