"""Scanning processes."""

from typing import TYPE_CHECKING

from ..specimens import Slide, Specimen
from .__core import (Batch, BatchingProcess, CollationProcess, DeliveryProcess,
                     Process)

if TYPE_CHECKING:
    from ..model import Model


def register(env: "Model") -> None:
    """Register processes to the simulation environment."""
    env.processes['scanning_start'] = Process(
        'scanning_start', env=env, in_type=Specimen, fn=scanning_start
    )

    # REGULAR SLIDES
    env.processes['batcher.scanning_regular'] = BatchingProcess(
        'batcher.scanning_regular',
        env=env,
        batch_size=env.batch_sizes.digital_scanning_regular,
        out_type=Batch[Slide],
        out_process='scanning_regular'
    )
    env.processes['scanning_regular'] = Process(
        'scanning_regular', env=env, in_type=Batch[Slide], fn=scanning_regular
    )

    # MEGA SLIDES
    env.processes['batcher.scanning_megas'] = BatchingProcess(
        'batcher.scanning_megas',
        env=env,
        batch_size=env.batch_sizes.digital_scanning_megas,
        out_type=Batch[Slide],
        out_process='scanning_megas'
    )
    env.processes['scanning_megas'] = Process(
        'scanning_megas', env=env, in_type=Batch[Slide], fn=scanning_megas
    )

    # COLLATION AND POST-STAINING
    env.processes['collate.scanning.slides'] = CollationProcess(
        'collate.scanning.slides', env=env,
        counter_name='num_slides', out_process='collate.scanning.blocks'
    )
    env.processes['collate.scanning.blocks'] = CollationProcess(
        'collate.scanning.blocks', env=env,
        counter_name='num_blocks', out_process='post_scanning'
    )
    env.processes['post_scanning'] = Process(
        'post_scanning', env=env, in_type=Specimen, fn=post_scanning
    )

    # DELIVERY
    env.processes['batcher.scanning_to_qc'] = BatchingProcess(
        'batcher.scanning_to_qc',
        env=env,
        batch_size=env.batch_sizes.deliver_scanning_to_qc,
        out_type=Batch[Specimen],
        out_process='scanning_to_qc'
    )
    env.processes['scanning_to_qc'] = DeliveryProcess(
        'scanning_to_qc',
        env=env,
        runner=env.resources.scanning_staff,
        out_duration=env.minutes(2),
        return_duration=env.minutes(2),
        out_process='qc'
    )


def scanning_start(self: Specimen) -> None:
    """Entry point for scanning."""
    env: Model = self.env
    env.wips.in_scanning.value += 1
    self.data['scanning_start'] = env.now()

    for block in self.blocks:
        for slide in block.slides:
            if slide.data['slide_type'] == 'megas':
                slide.enter(env.processes['batcher.scanning_megas'].in_queue)
            else:
                slide.enter(env.processes['batcher.scanning_regular'].in_queue)


def scanning_regular(self: Batch[Slide]) -> None:
    """Scan a batch of regular slides."""
    env: Model = self.env

    # LOAD
    self.request(env.resources.scanning_staff, env.resources.scanning_machine_regular)
    self.hold(env.task_durations.load_scanning_machine_regular)
    self.release(env.resources.scanning_staff)

    # SCAN
    self.hold(env.task_durations.scanning_regular)

    # UNLOAD
    self.request(env.resources.scanning_staff)
    self.hold(env.task_durations.unload_scanning_machine_regular)
    self.release()

    for slide in self.items:
        slide.enter(env.processes['collate.scanning.slides'].in_queue)


def scanning_megas(self: Batch[Slide]) -> None:
    """Scan a batch of mega slides."""
    env: Model = self.env

    # LOAD
    self.request(env.resources.scanning_staff, env.resources.scanning_machine_megas)
    self.hold(env.task_durations.load_scanning_machine_megas)
    self.release(env.resources.scanning_staff)

    # SCAN
    self.hold(env.task_durations.scanning_megas)

    # UNLOAD
    self.request(env.resources.scanning_staff)
    self.hold(env.task_durations.unload_scanning_machine_megas)
    self.release()

    for slide in self.items:
        slide.enter(env.processes['collate.scanning.slides'].in_queue)


def post_scanning(self: Specimen) -> None:
    """Post-scanning tasks."""
    env: Model = self.env
    env.wips.in_scanning.value -= 1
    self.data['scanning_end'] = env.now()
    self.enter_sorted(env.processes['batcher.scanning_to_qc'].in_queue, self.prio)
