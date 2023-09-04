"""Reception processes."""

from typing import TYPE_CHECKING

import salabim as sim

from ..specimens import Priority, Specimen
from .__core import Batch, BatchingProcess, DeliveryProcess, Process

if TYPE_CHECKING:
    from ..model import Model


def register(env: 'Model') -> None:
    """Register processes to the simulation environment."""
    env.processes['arrive_reception'] = Process(
        'arrive_reception', env=env, in_type=Specimen, fn=arrive_reception
    )
    env.processes['booking_in'] = Process(
        'booking_in', env=env, in_type=Specimen, fn=booking_in
    )
    env.processes['batcher.reception_to_cutup'] = BatchingProcess(
        'batcher.reception_to_cutup',
        env=env,
        batch_size=env.batch_sizes.deliver_reception_to_cut_up,
        out_type=Batch[Specimen],
        out_process='reception_to_cutup'
    )
    env.processes['reception_to_cutup'] = DeliveryProcess(
        'reception_to_cutup',
        env=env,
        runner=env.resources.booking_in_staff,
        out_duration=env.minutes(2),
        return_duration=env.minutes(2),
        out_process='cutup_start'
    )


def arrive_reception(self: Specimen) -> None:
    """Called for each new specimen arrival."""
    env: Model = self.env

    env.wips.total.value += 1
    env.wips.in_reception.value += 1

    self.data['reception_start'] = env.now()
    self.data['source'] = sim.CumPdf(
        (
            "Internal", env.globals.prob_internal,
            "External", 1
        ),
        env=env
    ).sample()

    # For booking-in staff, receiving new specimens always takes priority
    # over all non-urgent booking-in tasks
    self.request((env.resources.booking_in_staff, 1, Priority.URGENT))
    self.hold(env.task_durations.receive_and_sort)
    self.release()
    self.enter_sorted(env.processes['booking_in'].in_queue, self.prio)


def booking_in(self: Specimen) -> None:
    """Book a specimen into the system."""
    env: Model = self.env

    self.request((env.resources.booking_in_staff, 1, self.prio))

    # Pre-booking-in investigation
    if env.u01() < env.globals.prob_prebook:
        self.hold(env.task_durations.pre_booking_in_investigation)

    # Booking-in
    if self.data['source'] == 'Internal':
        self.hold(env.task_durations.booking_in_internal)
    else:
        self.hold(env.task_durations.booking_in_external)

    # Additional investigation
    if self.data['source'] == 'Internal':
        r = env.u01()

        if r < env.globals.prob_invest_easy:
            self.hold(env.task_durations.booking_in_investigation_internal_easy)
        elif r < env.globals.prob_invest_easy + env.globals.prob_invest_hard:
            self.hold(env.task_durations.booking_in_investigation_internal_hard)

    elif env.u01() < env.globals.prob_invest_external:
        self.hold(env.task_durations.booking_in_investigation_external)

    # Booking-in complete
    self.release()
    self.data['reception_end'] = env.now()
    env.wips.in_reception.value -= 1

    # Deliver to next stage: individually for Urgents, batched otherwise.
    if self.prio == Priority.URGENT:
        self.enter_sorted(env.processes['reception_to_cutup'].in_queue, Priority.URGENT)
    else:
        self.enter(env.processes['batcher.reception_to_cutup'].in_queue)
