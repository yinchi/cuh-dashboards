"""Microtomy processes."""

from typing import TYPE_CHECKING

from ..distributions import PERT
from ..specimens import Priority, Slide, Specimen
from .__core import Batch, BatchingProcess, DeliveryProcess, Process

if TYPE_CHECKING:
    from ..model import Model


def register(env: 'Model') -> None:
    """Register processes to the simulation environment."""

    env.processes['microtomy'] = Process(
        'microtomy', env=env, in_type=Specimen, fn=microtomy
    )
    env.processes['batcher.microtomy_to_staining'] = BatchingProcess(
        'batcher.microtomy_to_staining',
        env=env,
        batch_size=env.batch_sizes.deliver_microtomy_to_staining,
        out_type=Batch[Specimen],
        out_process='microtomy_to_staining'
    )
    env.processes['microtomy_to_staining'] = DeliveryProcess(
        'microtomy_to_staining',
        env=env,
        runner=env.resources.microtomy_staff,
        out_duration=env.minutes(5),
        return_duration=env.minutes(5),
        out_process='staining_start'
    )


def microtomy(self: Specimen) -> None:
    """Generate all slides for a specimen."""
    env: Model = self.env
    env.wips.in_microtomy.value += 1
    self.data['microtomy_start'] = env.now()
    self.data['total_slides'] = 0  # running total

    for block in self.blocks:

        # Each block is its own separate task (request-release pair)
        self.request((env.resources.microtomy_staff, 1, self.prio))

        if block.data['block_type'] == 'small surgical':
            # Small surgical blocks produce "levels" or "serials" slides
            if env.u01() < env.globals.prob_microtomy_levels:
                slide_type = 'levels'
                self.hold(env.task_durations.microtomy_levels)
                num_slides = env.globals.num_slides_levels()
            else:
                slide_type = 'serials'
                self.hold(env.task_durations.microtomy_serials)
                num_slides = env.globals.num_slides_serials()
        elif block.data['block_type'] == 'large surgical':
            slide_type = 'larges'
            self.hold(env.task_durations.microtomy_larges)
            num_slides = env.globals.num_slides_larges()
        else:
            slide_type = 'megas'
            self.hold(env.task_durations.microtomy_megas)
            num_slides = env.globals.num_slides_megas()

        for _ in range(num_slides):
            slide = Slide(
                f'{block.name()}.',
                env=env,
                parent=block,
                slide_type=slide_type
            )
            block.slides.append(slide)
        block.data['num_slides'] = num_slides
        self.data['total_slides'] += num_slides

        self.release()

    env.wips.in_microtomy.value -= 1
    self.data['microtomy_end'] = env.now()

    if self.prio == Priority.URGENT:
        self.enter_sorted(env.processes['microtomy_to_staining'].in_queue, Priority.URGENT)
    else:
        self.enter(env.processes['batcher.microtomy_to_staining'].in_queue)
