"""Tissue processing processes.

**TODO**:
    - Incorporate signals as gates for processing start times
    - Handle weekends as special cases
    - Reduced batch size for urgents?
"""

from typing import TYPE_CHECKING

from ..specimens import Block, Priority, Specimen
from .__core import (Batch, BatchingProcess, CollationProcess, DeliveryProcess,
                     Process)

if TYPE_CHECKING:
    from ..model import Model


def register(env: 'Model') -> None:
    """Register processes to the simulation environment."""

    env.processes['processing_start'] = Process(
        'processing_start', env=env, in_type=Specimen, fn=processing_start
    )

    # DECALC
    env.processes['batcher.decalc_bone_station'] = BatchingProcess(
        'batcher.decalc_bone_station',
        env=env,
        batch_size=env.batch_sizes.bone_station,
        out_type=Batch[Block],
        out_process='decalc_bone_station'
    )
    env.processes['decalc_bone_station'] = Process(
        'decalc_bone_station', env=env, in_type=Batch[Block], fn=decalc_bone_station
    )
    env.processes['decalc_oven'] = Process(
        'decalc_oven', env=env, in_type=Block, fn=decalc_oven
    )

    # ASSIGN PROCESSING MACHINE QUEUE
    env.processes['processing_assign_queue'] = Process(
        'processing_assign_queue', env=env, in_type=Block, fn=processing_assign_queue
    )

    # PROCESSING (URGENTS)
    env.processes['batcher.processing_urgents'] = BatchingProcess(
        'batcher.processing_urgents',
        env=env,
        batch_size=env.batch_sizes.processing_regular,
        out_type=Batch[Block],
        out_process='processing_urgents'
    )
    env.processes['processing_urgents'] = Process(
        'processing_urgents', env=env, in_type=Batch[Block], fn=processing_urgents
    )

    # PROCESSING (SMALLS)
    env.processes['batcher.processing_smalls'] = BatchingProcess(
        'batcher.processing_smalls',
        env=env,
        batch_size=env.batch_sizes.processing_regular,
        out_type=Batch[Block],
        out_process='processing_smalls'
    )
    env.processes['processing_smalls'] = Process(
        'processing_smalls', env=env, in_type=Batch[Block], fn=processing_smalls
    )

    # PROCESSING (LARGES)
    env.processes['batcher.processing_larges'] = BatchingProcess(
        'batcher.processing_larges',
        env=env,
        batch_size=env.batch_sizes.processing_regular,
        out_type=Batch[Block],
        out_process='processing_larges'
    )
    env.processes['processing_larges'] = Process(
        'processing_larges', env=env, in_type=Batch[Block], fn=processing_larges
    )

    # PROCESSING (MEGA BLOCKS)
    env.processes['batcher.processing_megas'] = BatchingProcess(
        'batcher.processing_megas',
        env=env,
        batch_size=env.batch_sizes.processing_megas,
        out_type=Batch[Block],
        out_process='processing_megas'
    )
    env.processes['processing_megas'] = Process(
        'processing_megas', env=env, in_type=Batch[Block], fn=processing_megas
    )

    # EMBEDDING AND TRIMMING
    env.processes['embed_and_trim'] = Process(
        'embed_and_trim', env=env, in_type=Block, fn=embed_and_trim
    )

    # COLLATION AND STATS(POST-PROCESSING)
    env.processes['collate.processing'] = CollationProcess(
        'collate.processing', env=env,
        counter_name='num_blocks', out_process='post_processing'
    )
    env.processes['post_processing'] = Process(
        'post_processing', env=env, in_type=Specimen, fn=post_processing
    )

    # DELIVERY
    env.processes['batcher.processing_to_microtomy'] = BatchingProcess(
        'batcher.processing_to_microtomy',
        env=env,
        batch_size=env.batch_sizes.deliver_processing_to_microtomy,
        out_type=Batch[Specimen],
        out_process='processing_to_microtomy'
    )
    env.processes['processing_to_microtomy'] = DeliveryProcess(
        'processing_to_microtomy',
        env=env,
        runner=env.resources.processing_room_staff,
        out_duration=env.minutes(2),
        return_duration=env.minutes(2),
        out_process='microtomy'
    )


def processing_start(self: Specimen) -> None:
    """Take specimens arriving a processing and send to decalc if necessary.
    Else, send to queue assignment."""
    env: Model = self.env
    env.wips.in_processing.value += 1
    self.data['processing_start'] = env.now()

    r = env.u01()
    if r < env.globals.prob_decalc_bone:
        self.data['decalc_type'] = 'bone station'
        out_queue = env.processes['batcher.decalc_bone_station'].in_queue
    elif r < env.globals.prob_decalc_bone + env.globals.prob_decalc_oven:
        self.data['decalc_type'] = 'decalc oven'
        out_queue = env.processes['decalc_oven'].in_queue
    else:
        out_queue = env.processes['processing_assign_queue'].in_queue

    for block in self.blocks:
        block.enter_sorted(out_queue, self.prio)


def decalc_bone_station(self: Batch[Block]) -> None:
    """Decalc a batch of blocks in a bone station."""
    env: Model = self.env

    # LOAD
    self.request((env.resources.bms, 1), (env.resources.bone_station, 1))
    self.hold(env.task_durations.load_bone_station)
    self.release(env.resources.bms)  # release staff only

    # DECALC
    self.hold(env.task_durations.decalc)  # machine-only task

    # UNLOAD
    self.request((env.resources.bms, 1))  # request staff again
    self.hold(env.task_durations.unload_bone_station)
    self.release()  # release all

    for block in self.items:
        block.enter_sorted(env.processes['processing_assign_queue'].in_queue, block.prio)


def decalc_oven(self: Block) -> None:
    """Decalc a block in an oven.

    **NOTE**: It is assumed that the decalc oven is not a capacity bottleneck
    and is thus not modelled as an limited resource.
    """
    env: Model = self.env

    # LOAD
    self.request((env.resources.bms, 1))
    self.hold(env.task_durations.load_into_decalc_oven)
    self.release(env.resources.bms)  # release staff

    # DECALC
    self.hold(env.task_durations.decalc)

    # UNLOAD
    self.request((env.resources.bms, 1))  # request staff again
    self.hold(env.task_durations.unload_from_decalc_oven)
    self.release()  # release all

    self.enter_sorted(env.processes['processing_assign_queue'].in_queue, self.prio)


def processing_assign_queue(self: Block) -> None:
    """Assign incoming blocks to the correct :py:class:`~histopath.process.BatchingProcess`,
    according to type."""
    env: Model = self.env

    if self.prio == Priority.URGENT:
        out_queue = env.processes["batcher.processing_urgents"].in_queue
    if self.data["block_type"] == "small surgical":
        out_queue = env.processes["batcher.processing_smalls"].in_queue
    if self.data["block_type"] == "large surgical":
        out_queue = env.processes["batcher.processing_larges"].in_queue
    else:
        out_queue = env.processes["batcher.processing_megas"].in_queue

    self.enter_sorted(out_queue, self.prio)


def processing_urgents(self: Batch[Block]) -> None:
    """Processing machine program for urgent blocks."""
    env: Model = self.env

    # LOAD
    self.request(
        (env.resources.processing_room_staff, 1, Priority.URGENT),
        (env.resources.processing_machine, 1, Priority.URGENT),
    )
    self.hold(env.task_durations.load_processing_machine)
    self.release(env.resources.processing_room_staff)

    # PROCESSING
    self.hold(env.task_durations.processing_urgent)

    # UNLOAD
    self.request((env.resources.processing_room_staff, 1, Priority.URGENT))
    self.hold(env.task_durations.unload_processing_machine)
    self.release()  # release all

    for block in self.items:
        block.enter_sorted(env.processes["embed_and_trim"].in_queue, block.prio)


def processing_smalls(self: Batch[Block]) -> None:
    """Processing machine program for small surgical blocks."""
    env: Model = self.env

    # LOAD
    self.request(env.resources.processing_room_staff, env.resources.processing_machine)
    self.hold(env.task_durations.load_processing_machine)
    self.release(env.resources.processing_room_staff)

    # PROCESSING
    self.hold(env.task_durations.processing_small_surgicals)

    # UNLOAD
    self.request(env.resources.processing_room_staff)
    self.hold(env.task_durations.unload_processing_machine)
    self.release()  # release all

    for block in self.items:
        block.enter_sorted(env.processes["embed_and_trim"].in_queue, block.prio)


def processing_larges(self: Batch[Block]) -> None:
    """Processing machine program for large surgical blocks."""
    env: Model = self.env

    # LOAD
    self.request(env.resources.processing_room_staff, env.resources.processing_machine)
    self.hold(env.task_durations.load_processing_machine)
    self.release(env.resources.processing_room_staff)

    # PROCESSING
    self.hold(env.task_durations.processing_large_surgicals)

    # UNLOAD
    self.request(env.resources.processing_room_staff)
    self.hold(env.task_durations.unload_processing_machine)
    self.release()  # release all

    for block in self.items:
        block.enter_sorted(env.processes["embed_and_trim"].in_queue, block.prio)


def processing_megas(self: Batch[Block]) -> None:
    """Processing machine program for mega blocks."""
    env: Model = self.env

    # LOAD
    self.request(env.resources.processing_room_staff, env.resources.processing_machine)
    self.hold(env.task_durations.load_processing_machine)
    self.release(env.resources.processing_room_staff)

    # PROCESSING
    self.hold(env.task_durations.processing_megas)

    # UNLOAD
    self.request(env.resources.processing_room_staff)
    self.hold(env.task_durations.unload_processing_machine)
    self.release()  # release all

    for block in self.items:
        block.enter_sorted(env.processes["embed_and_trim"].in_queue, block.prio)


def embed_and_trim(self: Block) -> None:
    """Embed a block in wax and trim the excess."""
    env: Model = self.env

    # EMBED
    self.request(env.resources.processing_room_staff)
    self.hold(env.task_durations.embedding)
    self.release()

    # COOLDOWN (no resources tracked)
    self.hold(env.task_durations.embedding_cooldown)

    # TRIM
    self.request(env.resources.processing_room_staff)
    self.hold(env.task_durations.block_trimming)
    self.release()

    self.enter_sorted(env.processes["collate.processing"].in_queue, self.prio)


def post_processing(self: Specimen) -> None:
    """Post-processing tasks."""
    env: Model = self.env

    env.wips.in_processing.value -= 1
    self.data['processing_end'] = env.now()

    if self.prio == Priority.URGENT:
        self.enter_sorted(env.processes['processing_to_microtomy'].in_queue, Priority.URGENT)
    else:
        self.enter(env.processes['batcher.processing_to_microtomy'].in_queue)
