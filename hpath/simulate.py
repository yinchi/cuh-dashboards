"""Simulation module for the REST server.  Due to Redis/RQ limitations,
we have made this its own module."""
import json
import sqlite3 as sql
from datetime import datetime

from .kpis import Report
from .model import Config, Model
from .util import serialiser

SQL_UPDATE_RESULT = """\
UPDATE scenarios
SET
    completed = ?,
    results = ?,
    done_reps = num_reps
WHERE
    scenario_id = ?
"""


def simulate(config: Config, scenario_id: int) -> None:
    """Runs the simulation and saves the result to the database as JSON.
    Also updates the database to show progress.

    **TODO**: Multiple simulation runs are not yet supported.

    Args:
        config (Config):
            The model configuration to run. Because RQ only works with pickle-able
            objects, we build the final :py:class:`~hpath.model.Model` within the
            RQ task.
        result_dir(os.PathLike): The output directory path.
    """

    # TODO: run simulation specified number of times, and prepare summary report from
    # the individual replication reports
    model = Model(config)
    model.run()
    result_str = json.dumps(Report.from_model(model), default=serialiser)
    completed = datetime.utcnow().timestamp()

    conn = sql.connect('backend.db')
    cur = conn.cursor()
    cur.execute(SQL_UPDATE_RESULT, (completed, result_str, scenario_id))
    conn.commit()
