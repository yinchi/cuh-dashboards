"""Compute KPIs for a model from simulation results."""
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypedDict

import numpy as np
import pandas as pd
import salabim as sim

from . import util
from .chart_datatypes import ChartData, MultiChartData

if TYPE_CHECKING:
    from .model import Model


def wip_hourly(wip: sim.Monitor) -> pd.DataFrame:
    """Return a dataframe showing the hourly mean WIP
    of a histopath stage."""
    df = pd.DataFrame(wip.tx())\
        .T\
        .rename(columns={0: 't', 1: wip.name()})\
        .set_index('t')
    df.index = pd.to_timedelta(df.index, 'h')

    df1 = df.resample('H').mean()
    df1.index /= pd.Timedelta(1, unit='h')

    # handle hour intervals with no WIP changes
    df2 = df.resample('H').ffill()
    df2.index /= pd.Timedelta(1, unit='h')
    return df1.fillna(df2)


def wip_hourlies(mdl: 'Model') -> pd.DataFrame:
    """Return a dataframe showing the hourly mean WIP
    for each stage in the histopathology process."""
    return pd.concat([wip_hourly(wip) for wip in util.dc_values(mdl.wips)], axis='columns')


def wip_summary(mdl: 'Model') -> pd.DataFrame:
    """Return a dataframe with the histopath stages as rows, and
    the mean WIP of each stage as its "mean" column."""
    df = pd.DataFrame({wip.name(): [wip.mean()] for wip in util.dc_values(mdl.wips)})
    df.index = ['mean']
    return df.T


def _timestamp_helper(mdl: 'Model') -> pd.DataFrame:
    # Actually contains more data than just timestamps but we will ignore those columns
    timestamps = pd.DataFrame.from_dict(
        {sp.name(): sp.data for sp in mdl.completed_specimens.as_list()},
        orient='index'
    )

    # specimen.123 -> 123
    timestamps.index = [int(idx.rsplit('.', 1)[1]) for idx in timestamps.index]
    return timestamps


def overall_tat(mdl: 'Model') -> pd.DataFrame:
    """Overall mean turnaround time."""
    timestamps = _timestamp_helper(mdl)
    # Extract TAT from data columns
    tat_total = timestamps['report_end'] - timestamps['reception_start']
    return tat_total.mean()


def overall_lab_tat(mdl: 'Model') -> pd.DataFrame:
    """Overall mean turnaround time."""
    timestamps = _timestamp_helper(mdl)
    # Extract TAT from data columns
    tat_lab = timestamps['qc_end'] - timestamps['reception_start']
    return tat_lab.mean()


def tat_by_stage(mdl: 'Model') -> pd.DataFrame:
    """Return a dataframe with the histopath stages as rows, and
    the mean turnaround time of each stage as its "mean (hours)" column."""
    timestamps = _timestamp_helper(mdl)

    stages = [x.rsplit('_end', 1)[0] for x in timestamps.columns if x.endswith('_end')]
    df = pd.concat([timestamps[f'{x}_end'] - timestamps[f'{x}_start']
                    for x in stages], axis='columns')
    df.columns = stages

    ret = pd.DataFrame({'mean (hours)': df.mean()})
    ret.index = [wip.name() for wip in util.dc_values(
        mdl.wips)][1:]  # Remove 'Total' to match ret data
    return ret


def tat_dist(mdl: 'Model', day_list: Iterable[int]) -> pd.DataFrame:
    """Return a dataframe showing the proportion of specimens
    completed in ``n`` days, for ``n`` in ``day_list``. Both
    overall and lab turnaround time are shown."""

    # Actually contains more data than just timestamps but we will ignore those columns
    timestamps = _timestamp_helper(mdl)

    # Extract TAT from data columns
    tat_total = timestamps['report_end'] - timestamps['reception_start']
    tat_lab = timestamps['qc_end'] - timestamps['reception_start']

    return pd.DataFrame([{
        'days': days,
        'TAT': np.mean(tat_total < days*24),
        'TAT_lab': np.mean(tat_lab < days*24)
    } for days in day_list]).set_index('days')


def utilisation_means(mdl: 'Model') -> pd.DataFrame:
    """Return a dataframe showing the mean utilisation of each resource."""
    ret = {r.name(): r.claimed_quantity.mean()/r.capacity.mean()
           for r in util.dc_values(mdl.resources)}
    return pd.DataFrame({'mean': ret})


def q_length_means(mdl: 'Model') -> pd.DataFrame:
    """Return a dataframe showing the mean queue length of each resource."""
    ret = {r.name(): r.requesters().length.mean()/r.capacity.mean()
           for r in util.dc_values(mdl.resources)}
    return pd.DataFrame({'mean': ret})


def allocation_timeseries(res: sim.Resource):
    """Return a dataframe showing the allocation level of a resource."""
    df = pd.DataFrame(res.capacity.tx())\
        .T\
        .rename(columns={0: 't', 1: res.name()})\
        .set_index('t')
    # Duplicates can happen as the final allocation change may be at the
    # simulation end time.  Remove these.
    return df.groupby('t').tail(1)


def utilisation_hourly(res: sim.Resource) -> pd.DataFrame:
    """Return a dataframe showing the hourly mean utilisation of a resource."""
    df = pd.DataFrame(res.claimed_quantity.tx())\
        .T\
        .rename(columns={0: 't', 1: res.name()})\
        .set_index('t')
    df.index = pd.to_timedelta(df.index, unit='h')
    df1 = df.resample('H').mean()
    df1.index /= pd.Timedelta(1, unit='h')

    # handle hour intervals with no utilisation changes
    df2 = df.resample('H').ffill()
    df2.index /= pd.Timedelta(1, unit='h')
    return df1.fillna(df2)


def utilisation_hourlies(mdl: 'Model') -> pd.DataFrame:
    """Return a dataframe showing the hourly mean utilisation of each resource."""
    return pd.concat(
        [utilisation_hourly(res) for res in util.dc_values(mdl.resources)],
        axis='columns'
    )


def q_length_hourly(res: sim.Resource) -> pd.DataFrame:
    """Return a dataframe showing the hourly mean queue length for a resource.
    Queue members can be specimen, block, slide, or batch tasks including delivery."""
    df = pd.DataFrame(res.requesters().length.tx())\
        .T\
        .rename(columns={0: 't', 1: res.name()})\
        .set_index('t')
    df.index = pd.to_timedelta(df.index, unit='h')
    df1 = df.resample('H').mean()
    df1.index /= pd.Timedelta(1, unit='h')

    # handle hour intervals with no queue changes
    df2 = df.resample('H').ffill()
    df2.index /= pd.Timedelta(1, unit='h')
    return df1.fillna(df2)


def q_length_hourlies(mdl: 'Model') -> pd.DataFrame:
    """Return a dataframe showing the hourly mean queue length of each resource.
    Queue members can be specimen, block, slide, or batch tasks including delivery."""
    return pd.concat(
        [utilisation_hourly(res) for res in util.dc_values(mdl.resources)],
        axis='columns'
    )


Progress = TypedDict('Progress', {
    '7': float,
    '10': float,
    '12': float,
    '21': float
})

LabProgress = TypedDict('LabProgress', {
    '3': float
})


@dataclass(kw_only=True)
class Report:
    """Dataclass for reporting a set of KPIs for passing to a frontend visualisation server.
    In the current implementation, this is https://github.com/lakeesiv/digital-twin"""
    overall_tat: float
    lab_tat: float
    progress: Progress
    lab_progress: Progress
    tat_by_stage: ChartData
    resource_allocation: dict[str, ChartData]  # ChartData for each resource
    wip_by_stage: dict[str, ChartData]  # ChartData for each stage
    utilization_by_resource: ChartData
    q_length_by_resource: ChartData
    hourly_utilization_by_resource: MultiChartData

    overall_tat_min: float | None = field(default=None)
    overall_tat_max: float | None = field(default=None)
    lab_tat_min: float | None = field(default=None)
    lab_tat_max: float | None = field(default=None)
    progress_min: Progress | None = field(default=None)
    progress_max: Progress | None = field(default=None)
    lab_progress_min: LabProgress | None = field(default=None)
    lab_progress_max: LabProgress | None = field(default=None)

    def fake_min_max(self) -> 'Report':
        """**Dev**: to create max/min values for faking multiple simulation replications"""
        ret = deepcopy(self)
        ret.overall_tat_min = 0.9 * ret.overall_tat
        ret.overall_tat_max = 1.1 * ret.overall_tat

        ret.lab_tat_min = 0.9 * ret.lab_tat
        ret.lab_tat_max = 1.1 * ret.lab_tat

        ret.progress_min = {k: 0.9 * v for k, v in ret.progress.items()}
        ret.progress_max = {k: min(1, 1.1 * v) for k, v in ret.progress.items()}

        ret.lab_progress_min = {k: 0.9 * v for k, v in ret.lab_progress.items()}
        ret.lab_progress_max = {k: min(1, 1.1 * v) for k, v in ret.lab_progress.items()}

        return ret

    @staticmethod
    def from_model(mdl: 'Model') -> 'Report':
        """Produce a single dataclass for passing simulation results to a frontend server."""
        return __class__(
            overall_tat=overall_tat(mdl),
            lab_tat=overall_lab_tat(mdl),
            progress=dict(zip(
                ['7', '10', '12', '21'],
                tat_dist(mdl, [7, 10, 12, 21]).TAT.tolist()
            )),
            lab_progress=dict(zip(['3'], tat_dist(mdl, [3]).TAT_lab.tolist())),
            tat_by_stage=ChartData.from_pandas(tat_by_stage(mdl)).fake_min_max(),
            resource_allocation={
                res.name(): ChartData.from_pandas(allocation_timeseries(res))
                for res in util.dc_values(mdl.resources)
            },
            wip_by_stage=MultiChartData.from_pandas(wip_hourlies(mdl)).fake_min_max(),
            utilization_by_resource=ChartData.from_pandas(utilisation_means(mdl)).fake_min_max(),
            q_length_by_resource=ChartData.from_pandas(q_length_means(mdl)).fake_min_max(),
            hourly_utilization_by_resource=MultiChartData.from_pandas(
                utilisation_hourlies(mdl))#  .fake_min_max()
        ).fake_min_max()
