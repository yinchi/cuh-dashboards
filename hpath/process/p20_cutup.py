"""Cut-up processes.

**TODO**: incorporate effect of cut-up specialities?
"""

from typing import TYPE_CHECKING

from ..distributions import PERT
from ..specimens import Block, Priority, Specimen
from .__core import Batch, BatchingProcess, DeliveryProcess, Process

if TYPE_CHECKING:
    from ..model import Model


def register(env: 'Model') -> None:
    """Register processes to the simulation environment."""

    env.processes['cutup_start'] = Process(
        'cutup_start', env=env, in_type=Specimen, fn=cutup_start
    )

    # BMS cut-up
    env.processes['cutup_bms'] = Process(
        'cutup_bms', env=env, in_type=Specimen, fn=cutup_bms
    )
    env.processes['batcher.cutup_bms_to_processing'] = BatchingProcess(
        'batcher.cutup_bms_to_processing',
        env=env,
        batch_size=env.batch_sizes.deliver_cut_up_to_processing,
        out_type=Batch[Specimen],
        out_process='cutup_bms_to_processing'
    )
    env.processes['cutup_bms_to_processing'] = DeliveryProcess(
        'cutup_bms_to_processing',
        env=env,
        runner=env.resources.bms,
        out_duration=env.minutes(2),
        return_duration=env.minutes(2),
        out_process='processing_start'
    )

    # Pool cut-up
    env.processes['cutup_pool'] = Process(
        'cutup_pool', env=env, in_type=Specimen, fn=cutup_pool
    )
    env.processes['batcher.cutup_pool_to_processing'] = BatchingProcess(
        'batcher.cutup_pool_to_processing',
        env=env,
        batch_size=env.batch_sizes.deliver_cut_up_to_processing,
        out_type=Batch[Specimen],
        out_process='cutup_pool_to_processing'
    )
    env.processes['cutup_pool_to_processing'] = DeliveryProcess(
        'cutup_pool_to_processing',
        env=env,
        runner=env.resources.cut_up_assistant,
        out_duration=env.minutes(2),
        return_duration=env.minutes(2),
        out_process='processing_start'
    )

    # Large specimens cut-up
    env.processes['cutup_large'] = Process(
        'cutup_large', env=env, in_type=Specimen, fn=cutup_large
    )
    env.processes['batcher.cutup_large_to_processing'] = BatchingProcess(
        'batcher.cutup_large_to_processing',
        env=env,
        batch_size=env.batch_sizes.deliver_cut_up_to_processing,
        out_type=Batch[Specimen],
        out_process='cutup_large_to_processing'
    )
    env.processes['cutup_large_to_processing'] = DeliveryProcess(
        'cutup_large_to_processing',
        env=env,
        runner=env.resources.cut_up_assistant,
        out_duration=env.minutes(2),
        return_duration=env.minutes(2),
        out_process='processing_start'
    )


def cutup_start(self: Specimen) -> None:
    """Take specimens arriving at cut-up and sort to the correct cut-up queue."""
    env: Model = self.env
    env.wips.in_cut_up.value += 1
    self.data['cutup_start'] = env.now()

    r = env.u01()
    suffix = '_urgent' if self.prio == Priority.URGENT else ''
    if r < getattr(env.globals, 'prob_bms_cutup'+suffix):
        cutup_type, next_process = 'BMS', 'cutup_bms'
    elif r < (getattr(env.globals, 'prob_bms_cutup'+suffix) +
              getattr(env.globals, 'prob_pool_cutup'+suffix)):
        cutup_type, next_process = 'Pool', 'cutup_pool'
    else:
        cutup_type, next_process = 'Large specimens', 'cutup_large'

    self.data["cutup_type"] = cutup_type
    self.enter_sorted(env.processes[next_process].in_queue, self.prio)


def cutup_bms(self: Specimen) -> None:
    """BMS cut-up. Always produces 1 small surgical block."""
    env: Model = self.env

    self.request((env.resources.bms, 1, self.prio))
    self.hold(env.task_durations.cut_up_bms)
    block = Block(
        f'{self.name()}.',
        env=env,
        parent=self,
        block_type='small surgical'
    )
    self.blocks.append(block)
    self.data['num_blocks'] = 1

    self.release()
    env.wips.in_cut_up.value -= 1
    self.data['cutup_end'] = env.now()

    if self.prio == Priority.URGENT:
        self.enter(env.processes['cutup_bms_to_processing'].in_queue)
    else:
        self.enter(env.processes['batcher.cutup_bms_to_processing'].in_queue)


def cutup_pool(self: Specimen) -> None:
    """Pool cut-up. Always produces 1 large surgical block."""
    env: Model = self.env

    self.request((env.resources.cut_up_assistant, 1, self.prio))
    self.hold(env.task_durations.cut_up_pool)
    block = Block(
        f'{self.name()}.',
        env=env,
        parent=self,
        block_type='large surgical'
    )
    self.blocks.append(block)
    self.data['num_blocks'] = 1

    self.release()
    env.wips.in_cut_up.value -= 1
    self.data['cutup_end'] = env.now()

    if self.prio == Priority.URGENT:
        self.enter_sorted(env.processes['cutup_pool_to_processing'].in_queue, Priority.URGENT)
    else:
        self.enter(env.processes['batcher.cutup_pool_to_processing'].in_queue)


def cutup_large(self: Specimen) -> None:
    """Large cut-up. Produces a random number of mega or large surgical blocks."""
    env: Model = self.env

    self.request((env.resources.cut_up_assistant, 1, self.prio))
    self.hold(env.task_durations.cut_up_large_specimens)

    # Urgent cut-ups never produce megas. Other large surgical blocks produce
    # megas with a given probability.
    # Assume a discretized PERT distribution for the number of Blocks.
    if (self.prio == Priority.URGENT) or (env.u01() < env.globals.prob_mega_blocks):
        n_blocks = env.globals.num_blocks_mega()
        block_type = 'mega'
    else:
        n_blocks = env.globals.num_blocks_large_surgical()
        block_type = 'large surgical'

    for _ in range(n_blocks):
        block = Block(
            f'{self.name()}.',
            env=env,
            parent=self,
            block_type=block_type
        )
        self.blocks.append(block)

    self.data['num_blocks'] = n_blocks

    self.release()
    env.wips.in_cut_up.value -= 1
    self.data['cutup_end'] = env.now()

    if self.prio == Priority.URGENT:
        self.enter_sorted(env.processes['cutup_large_to_processing'].in_queue, Priority.URGENT)
    else:
        self.enter(env.processes['batcher.cutup_large_to_processing'].in_queue)
