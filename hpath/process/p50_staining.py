"""Staining and cover-slip processes."""

from typing import TYPE_CHECKING

from ..specimens import Priority, Slide, Specimen
from .__core import (Batch, BatchingProcess, CollationProcess, DeliveryProcess,
                     Process)

if TYPE_CHECKING:
    from ..model import Model


def register(env: 'Model') -> None:
    """Register processes to the simulation environment."""

    env.processes['staining_start'] = Process(
        'staining_start', env=env, in_type=Specimen, fn=staining_start
    )

    # REGULAR SLIDES
    env.processes['batcher.staining_regular'] = BatchingProcess(
        'batcher.staining_regular',
        env=env,
        batch_size=env.batch_sizes.staining_regular,
        out_type=Batch[Slide],
        out_process='staining_regular'
    )
    env.processes['staining_regular'] = Process(
        'staining_regular', env=env, in_type=Batch[Slide], fn=staining_regular
    )

    # MEGA SLIDES
    env.processes['batcher.staining_megas'] = BatchingProcess(
        'batcher.staining_megas',
        env=env,
        batch_size=env.batch_sizes.staining_megas,
        out_type=Batch[Slide],
        out_process='staining_megas'
    )
    env.processes['staining_megas'] = Process(
        'staining_megas', env=env, in_type=Batch[Slide], fn=staining_megas
    )

    # COLLATION AND POST-STAINING
    env.processes['collate.staining.slides'] = CollationProcess(
        'collate.staining.slides', env=env,
        counter_name='num_slides', out_process='collate.staining.blocks'
    )
    env.processes['collate.staining.blocks'] = CollationProcess(
        'collate.staining.blocks', env=env,
        counter_name='num_blocks', out_process='post_staining'
    )
    env.processes['post_staining'] = Process(
        'post_staining', env=env, in_type=Specimen, fn=post_staining
    )

    # DELIVERY
    env.processes['batcher.staining_to_labelling'] = BatchingProcess(
        'batcher.staining_to_labelling',
        env=env,
        batch_size=env.batch_sizes.deliver_staining_to_labelling,
        out_type=Batch[Specimen],
        out_process='staining_to_labelling'
    )
    env.processes['staining_to_labelling'] = DeliveryProcess(
        'staining_to_labelling',
        env=env,
        runner=env.resources.staining_staff,
        out_duration=env.minutes(5),
        return_duration=env.minutes(5),
        out_process='labelling'
    )


def staining_start(self: Specimen) -> None:
    """Create a staining task for each individual slide."""
    env: Model = self.env
    env.wips.in_staining.value += 1
    self.data['staining_start'] = env.now()

    for block in self.blocks:
        for slide in block.slides:
            if slide.data['slide_type'] == 'megas':
                slide.enter_sorted(env.processes['batcher.staining_megas'].in_queue, self.prio)
            else:
                slide.enter_sorted(env.processes['batcher.staining_regular'].in_queue, self.prio)


def staining_regular(self: Batch[Slide]) -> None:
    """Stain and cover-slip a batch of regular-sized slides."""
    env: Model = self.env

    # LOAD
    self.request(env.resources.staining_staff, env.resources.staining_machine)
    self.hold(env.task_durations.load_staining_machine_regular)
    self.release(env.resources.staining_staff)

    # STAIN
    self.hold(env.task_durations.staining_regular)

    # TRANSFER TO COVERSLIP MACHINE
    self.request(env.resources.staining_staff)
    self.hold(env.task_durations.unload_staining_machine_regular)
    self.release()

    self.request(env.resources.staining_staff, env.resources.coverslip_machine)
    self.hold(env.task_durations.load_coverslip_machine_regular)
    self.release(env.resources.staining_staff)

    # COVERSLIP
    self.hold(env.task_durations.coverslip_regular)

    # UNLOAD COVERSLIP MACHINE
    self.request(env.resources.staining_staff)
    self.hold(env.task_durations.unload_coverslip_machine_regular)
    self.release()  # release all

    for slide in self.items:
        slide.enter(env.processes['collate.staining.slides'].in_queue)


def staining_megas(self: Batch[Slide]) -> None:
    """Stain and cover-slip a batch of mega slides."""
    env: Model = self.env

    # LOAD
    self.request(env.resources.staining_staff, env.resources.staining_machine)
    self.hold(env.task_durations.load_staining_machine_megas)
    self.release(env.resources.staining_staff)

    # STAIN
    self.hold(env.task_durations.staining_megas)

    # UNLOAD
    self.request(env.resources.staining_staff)
    self.hold(env.task_durations.unload_staining_machine_megas)
    self.release(env.resources.staining_machine)
    # Keep staining staff for coverslipping tasks

    for slide in self.items:
        # MANUAL COVERSLIPPING FOR MEGA SLIDES
        self.hold(env.task_durations.coverslip_megas)
        slide.enter(env.processes['collate.staining.slides'].in_queue)

    self.release()  # release all


def post_staining(self: Specimen) -> None:
    """Post-staining tasks."""
    env: Model = self.env

    env.wips.in_staining.value -= 1
    self.data['staining_end'] = env.now()

    if self.prio == Priority.URGENT:
        self.enter_sorted(env.processes['staining_to_labelling'].in_queue, Priority.URGENT)
    else:
        self.enter(env.processes['batcher.staining_to_labelling'].in_queue)
