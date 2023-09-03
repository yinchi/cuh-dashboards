"""Histopath reporting processes."""

from typing import TYPE_CHECKING

from ..specimens import Specimen
from .__core import Process

if TYPE_CHECKING:
    from ..model import Model


def register(env: "Model"):
    """Register processes to the simulation environment."""
    env.processes['assign_histopath'] = Process(
        'assign_histopath', env=env, in_type=Specimen, fn=assign_histopath)
    env.processes['report'] = Process('report', env=env, in_type=Specimen, fn=report)


def assign_histopath(self: Specimen):
    """Assign a histopathologist to the specimen."""
    env: Model = self.env

    self.request((env.resources.qc_staff, 1, self. prio))
    self.hold(env.task_durations.assign_histopathologist)
    self.release()

    self.enter(env.processes['report'].in_queue)


def report(self: Specimen):
    """Write the final histopathological report."""
    env: Model = self.env
    env.wips.in_reporting.value += 1
    self.data['report_start'] = env.now()

    self.request((env.resources.histopathologist, 1, self. prio))
    self.hold(env.task_durations.write_report)
    self.release()

    env.wips.in_reporting.value -= 1
    self.data['report_end'] = env.now()

    env.wips.total.value -= 1  # ALL DONE
    self.enter(env.completed_specimens)
