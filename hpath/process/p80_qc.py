"""Block/quality check processes."""

from typing import TYPE_CHECKING

from ..specimens import Specimen
from .__core import Process

if TYPE_CHECKING:
    from ..model import Model


def register(env: "Model"):
    """Register processes to the simulation environment."""
    env.processes['qc'] = Process('qc', env=env, in_type=Specimen, fn=qc)

    # Since slides are already scanned, no need to hand to histopathologist after QC,
    # therefore, batching and delivery are not part of this stage.


def qc(self: Specimen):
    """Label all slides of a specimen."""
    env: Model = self.env
    env.wips.in_qc.value += 1
    self.data['qc_start'] = env.now()

    self.request((env.resources.qc_staff, 1, self. prio))
    self.hold(env.task_durations.block_and_quality_check)
    self.release()

    env.wips.in_qc.value -= 1
    self.data['qc_end'] = env.now()

    self.enter(env.processes['assign_histopath'].in_queue)
