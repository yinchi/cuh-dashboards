"""Labelling processes."""

from typing import TYPE_CHECKING

from ..specimens import Priority, Specimen
from .__core import Batch, BatchingProcess, DeliveryProcess, Process

if TYPE_CHECKING:
    from ..model import Model


def register(env: "Model") -> None:
    """Register processes to the simulation environment."""

    # Labelling is done in the "main lab", i.e. microtomy
    env.processes['labelling'] = Process('labelling', env=env, in_type=Specimen, fn=labelling)
    env.processes['batcher.labelling_to_scanning'] = BatchingProcess(
        'batcher.labelling_to_scanning',
        env=env,
        batch_size=env.batch_sizes.deliver_labelling_to_scanning,
        out_type=Batch[Specimen],
        out_process='labelling_to_scanning'
    )
    env.processes['labelling_to_scanning'] = DeliveryProcess(
        'labelling_to_scanning',
        env=env,
        runner=env.resources.microtomy_staff,
        out_duration=env.minutes(5),
        return_duration=env.minutes(5),
        out_process='scanning_start'
    )


def labelling(self: Specimen) -> None:
    """Label all slides of a specimen."""
    env: Model = self.env
    env.wips.in_labelling.value += 1
    self.data['labelling_start'] = env.now()

    self.request((env.resources.microtomy_staff, 1, self. prio))
    for block in self.blocks:
        for _ in block.slides:
            self.hold(env.task_durations.labelling)
    self.release()

    env.wips.in_labelling.value -= 1
    self.data['labelling_end'] = env.now()

    if self.prio == Priority.URGENT:
        self.enter_sorted(env.processes['labelling_to_scanning'].in_queue, Priority.URGENT)
    else:
        self.enter(env.processes['batcher.labelling_to_scanning'].in_queue)
