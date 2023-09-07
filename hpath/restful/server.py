"""The simulation server."""

import json
import sqlite3 as sql
from http import HTTPStatus
from typing import Any

import flask
import pandas as pd
from flask import Flask, Response, request
from flask_cors import CORS
from openpyxl import load_workbook
from werkzeug.exceptions import HTTPException

from ..config import Config
from ..simulate import simulate
from .redis import REDIS_QUEUE

app = Flask(__name__)
CORS(app)


SQL_CREATE_SCENARIOS = """\
CREATE TABLE scenarios(
    scenario_id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER,
    created REAL NOT NULL,
    completed REAL,
    num_reps INTEGER NOT NULL,
    done_reps INTEGER NOT NULL,
    results TEXT
)"""

SQL_INSERT_SCENARIOS = """\
INSERT INTO scenarios (analysis_id, created, num_reps, done_reps)
VALUES (?,?,?,?)"""

SQL_SELECT_SCENARIO = """\
SELECT scenario_id, analysis_id, CAST(done_reps AS REAL)/num_reps AS progress, created, completed
FROM scenarios
WHERE scenario_id = ?"""

SQL_LIST_SCENARIOS = """\
SELECT scenario_id, analysis_id, CAST(done_reps AS REAL)/num_reps AS progress, created, completed
FROM scenarios"""


@app.errorhandler(HTTPException)
def handle_exception(exc: HTTPException):
    """Return JSON instead of HTML (the default) for HTTP errors."""
    # start with the correct headers and status code from the error
    response = exc.get_response()
    # replace the body with JSON
    response.data = json.dumps({
        "code": exc.code,
        "name": exc.name,
        "description": exc.description,
    }, separators=(',', ':'))
    response.content_type = "application/json"
    return response


@app.route('/')
def hello_world() -> Response:
    """Return a simple HTML message, unless the request body is 'PING' (returns 'PONG' instead.)"""
    if request.get_data(as_text=True) == 'PING':
        return Response('PONG')
    return Response("<h1>Hello World!</h1>", status=HTTPStatus.OK)


def new_scenario(config: Config) -> dict[str, Any]:
    """Set up a new simulation task from an :py:class:`Config` and submit it to the RQ server.
    This :py:class:`Config` is created from an Excel file in :py:meth:`new_scenario_rest`."""
    conn = sql.connect('backend.db')
    cur = conn.cursor()
    cur.execute(
        SQL_INSERT_SCENARIOS,
        (config.analysis_id, config.created, config.num_reps, 0)
    )
    conn.commit()
    scenario_id = cur.lastrowid

    # Enqueue the simulation job
    REDIS_QUEUE.enqueue(simulate, config, scenario_id)

    ret = {
        'scenario_id': scenario_id,
        'created': config.created
    }
    if config.analysis_id is not None:
        ret['analysis_id'] = config.analysis_id
    return ret


@app.route('/scenarios/', methods=['POST'])
def new_scenario_rest() -> Response:
    """Process POST request for creating a new scenario.  The scenario configuration is contained
    in the request's ``files`` and ``form`` data.

    Invalid configuration files will lead to an ``HTTP 400 Bad Request`` error.
    """
    if 'config' not in request.files:
        flask.abort(HTTPStatus.BAD_REQUEST, 'Missing "config" in request.files.')
    file = request.files['config']  # Uploaded config file

    if 'num_reps' not in request.form:
        flask.abort(HTTPStatus.BAD_REQUEST, 'Missing "num_reps" in request.form.')
    num_reps = int(request.form['num_reps'])  # Number of simulation replications

    if 'sim_hours' not in request.form:
        flask.abort(HTTPStatus.BAD_REQUEST, 'Missing "sim_hours" in request.form.')
    sim_hours = float(request.form['sim_hours'])  # Simulation duration in hours

    # Parse and validate the input file. If error, return HTTP 400 Bad Request.
    try:
        config_bytes = file.stream
        wbook = load_workbook(config_bytes, data_only=True)
    except Exception as exc:
        flask.abort(HTTPStatus.BAD_REQUEST,
                    f'Reading the uploaded file as an Excel file produced the following'
                    f" <{type(exc).__name__}> error: '{str(exc)}'")

    try:
        config = Config.from_workbook(wbook, sim_hours, num_reps)
    except Exception as exc:
        flask.abort(HTTPStatus.BAD_REQUEST,
                    f'Parsing the uploaded Excel file produced the following'
                    f" <{type(exc).__name__}> error: {str(exc)}")  # openpyxl errors already quoted

    response = new_scenario(config)
    return flask.jsonify(response)


def status(scenario_id: int) -> dict[str, Any]:
    """Return the status of a scenario task."""
    conn = sql.connect('backend.db')
    cur = conn.cursor()
    cur.execute(SQL_SELECT_SCENARIO, (scenario_id, ))
    res = cur.fetchone()

    if res is None:
        return None
    else:
        _, analysis_id, progress, created, completed = res  # unpack tuple
        data = {
            'scenario_id': scenario_id,
            'progress': progress,
            'created': created,
        }
        if completed is not None:
            data['completed'] = completed
        if analysis_id is not None:
            data['analysis_id'] = analysis_id
        return data


@app.route('/scenarios/<scenario_id>/status/')
def status_rest(scenario_id) -> Response:
    """Process GET request for querying scenario task status."""
    not_found_text = f"Cannot find scenario with ID: '{scenario_id}'."

    # Ensure scenario_id is integer-compatible
    try:
        s_id = int(scenario_id)
    except ValueError:
        flask.abort(HTTPStatus.NOT_FOUND, description=not_found_text)

    # Fetch the scenario status
    res = status(s_id)
    if res is None:
        flask.abort(HTTPStatus.NOT_FOUND, description=not_found_text)
    return flask.jsonify(res)


@app.route('/scenarios/')
def list_scenarios() -> Response:
    """Return a list of scenarios on the server."""
    conn = sql.connect('backend.db')
    df = pd.read_sql(SQL_LIST_SCENARIOS, conn, index_col='scenario_id')
    return flask.jsonify(df.to_dict('index'))


def results(scenario_id: int) -> dict[str, Any]:
    """Return the results of a scenario task."""
    conn = sql.connect('backend.db')
    cur = conn.cursor()
    cur.execute("""SELECT results FROM scenarios WHERE scenario_id = ?""", (scenario_id, ))
    res = cur.fetchone()
    if res is None or res[0] is None:  # res == None or (None, )
        return None
    else:  # res == (results, )
        return res[0]


@app.route('/scenarios/<scenario_id>/results/')
def results_rest(scenario_id: int) -> Response:
    """Process GET request for reading a scenario simulation result."""
    not_found_text = f"Cannot find results for scenario with ID: '{scenario_id}'."

    # Ensure scenario_id is integer-compatible
    try:
        s_id = int(scenario_id)
    except ValueError:
        flask.abort(HTTPStatus.NOT_FOUND, description=not_found_text)

    # Fetch the scenario results
    res = results(s_id)
    if res is None:
        flask.abort(HTTPStatus.NOT_FOUND, description=not_found_text)

    return app.response_class(res, HTTPStatus.OK, mimetype='application/json')


def main() -> None:
    """Start up the Flask server."""

    # Get a SQLite cursor
    conn = sql.connect('backend.db')
    cur = conn.cursor()

    # Create the scenarios table if not exists
    res = cur.execute("SELECT name FROM sqlite_master")
    sql_res = res.fetchall()
    if not any('scenarios' in x for x in sql_res):
        cur.execute(SQL_CREATE_SCENARIOS)

    app.run(host='0.0.0.0', port=5000)


if __name__ == '__main__':
    main()
