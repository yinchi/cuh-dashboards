"""Common definitions for salabim processes.
These definitions are exported to the top level of histopath.process
using the ``__all__`` keyword."""

import itertools
from typing import TYPE_CHECKING, Type, Union, Callable

import salabim as sim
from salabim import Environment

from ..specimens import Batch, Component, Priority, Specimen
from ..util import ARR_RATE_INTERVAL_HOURS, RESOURCE_ALLOCATION_INTERVAL_HOURS

if TYPE_CHECKING:
    from ..model import Model
    from ..config import ArrivalSchedule, ResourceSchedule


class ArrivalGenerator(Component):
    """:py:class:`~histopath.specimens.Specimen` arrival generator process.

    Attributes:
        iterator (itertools.cycle):
            Iterator yielding the arrival rate for each hourly period.
        cls_args (dict[str, typing.Any]):
            Arguments passed to the :py:class:`~histopath.specimens.Specimen` constructor.
    """

    def __init__(
            self, *args,
            schedule: 'ArrivalSchedule',
            env: 'Model',
            **kwargs) -> None:
        """Constructor.

        Args:
            args (dict[str, typing.Any]):
                Positional arguments passed to the :py:class:`super() <salabim.Component>`
                constructor.
            schedule (ArrivalSchedule): The arrival schedule as a dataclass instance.
            env (Model): The simulation model this arrival generator is attached to.
            kwargs (dict[str, typing.Any]):
                Additional keyword arguments. Arguments not consumed by the
                :py:class:`super() <salabim.Component>` constructor become ``self.cls_args``.
        """
        # super().__init__ consumes args and a bunch of kwargs and passes the rest to setup()
        super().__init__(*args, **kwargs, env=env, rates=schedule.rates)

    def setup(self, *, rates: list[float], **kwargs) -> None:  # pylint: disable=arguments-differ
        """Set up the `ArrivalGenerator`. Salabim encourages use of a ``setup()`` method
        rather than overriding ``__init__()``. The method is called automatically
        immediately after initialisation."""
        super().setup()
        self.iterator = itertools.cycle(rates)
        self.cls_args = kwargs

    def process(self) -> None:
        """The generator process. Creates a sub-generator for
        each hour with the specified rate."""
        for rate in self.iterator:
            if rate > 0:
                sim.ComponentGenerator(
                    Specimen,
                    generator_name=self.name(),
                    duration=self.env.hours(1),
                    iat=sim.Exponential(rate=rate, time_unit="hours", env=self.env),
                    env=self.env,
                    **self.cls_args
                )
            self.hold(duration=self.env.hours(ARR_RATE_INTERVAL_HOURS))


class ResourceScheduler(Component):
    """:py:class:`~salabim.Resource` scheduler process.  The resource level is set every
    half-hour. The resource level is set to 0 if the day entry in the
    `ResourceSchedule` is 0.

    Attributes:
        resource (salabim.Resource): The resource to control the allocation of.
        schedule (ResourceSchedule): The resource schedule in dataclass form.
        env (Model): The simulation model this arrival generator is attached to.
    """

    def __init__(self, *args,
                 resource: sim.Resource,
                 schedule: 'ResourceSchedule',
                 env: 'Model',
                 **kwargs) -> None:
        """Constructor.

        Args:
            args (dict[str, typing.Any]):
                Positional arguments passed to the :py:class:`super() <salabim.Component>`
                constructor.
            resource (salabim.Resource)
            schedule (ResourceSchedule)
            env (Model)
            kwargs (dict[str, typing.Any]):
                Additional keyword arguments passed to the :py:class:`super() <salabim.Component>`
                constructor.
        """
        # super().__init__ consumes args and a bunch of kwargs and passes the rest to setup()
        super().__init__(*args, **kwargs, env=env, resource=resource, schedule=schedule)

    def setup(self, *,  # pylint: disable=arguments-differ
              resource: sim.Resource,
              schedule: 'ResourceSchedule') -> None:
        """Set up the `ResourceScheduler`. Salabim encourages use of a ``setup()`` method
        rather than overriding ``__init__()``. The method is called automatically
        immediately after initialisation."""
        super().setup()
        self.resource = resource
        self.schedule = schedule

    def process(self) -> None:
        """Change the resource capacity based on the schedule.
        Capacities are given in 30-min intervals."""
        for day_flag in itertools.cycle(self.schedule.day_flags):
            if day_flag == 0:
                self.resource.set_capacity(0)
                self.hold(self.env.days(1))
            else:
                for allocation in self.schedule.allocation:
                    if allocation != self.resource.capacity() or self.env.now() == 0:
                        self.resource.set_capacity(allocation)
                    self.hold(self.env.hours(RESOURCE_ALLOCATION_INTERVAL_HOURS))


class Process(sim.Component):
    """A looped processed that takes one entity from its in-queue at a time
    and activates it.

    For example, ``Process(name='do_this', Specimen, do_this)`` creates
    ``Specimen.do_this = do_this`` and calls it for every arriving
    :py:class:`~histopath.specimens.Specimen`.

    Attributes:
        in_queue (salabim.Store): The in-queue of the process from which entities are taken.
        in_type (typing.Type): The type of the entities to be processed.
        fn (typing.Callable): The function to be activated by each new arrival to the process.
        env (Model): The simulation model this arrival generator is attached to.
    """

    def __init__(self, *args,
                 in_type: Type, fn: Callable, env: Environment = None, **kwargs) -> None:
        """Constructor.

        Args:
            args (dict[str, typing.Any]):
                Positional arguments passed to the :py:class:`super() <salabim.Component>`
                constructor.
            in_type (typing.Type)
            fn (typing.Callable)
            env (Model)
            kwargs (dict[str, typing.Any]):
                Additional keyword arguments passed to the :py:class:`super() <salabim.Component>`
                constructor.
        """
        # super().__init__ consumes args and a bunch of kwargs and passes the rest to setup()
        super().__init__(*args, **kwargs, env=env, in_type=in_type, fn=fn)

    def setup(  # pylint: disable=arguments-differ
            self, in_type: Type[Component], fn: Callable) -> None:
        """Set up the `Process`. Salabim encourages use of a ``setup()`` method
        rather than overriding ``__init__()``. The method is called automatically
        immediately after initialisation."""
        super().setup()

        # point <in_type>.<name> to fn, where <name> is the process name
        self.in_type = in_type
        setattr(self.in_type, self.name(), fn)

        # Create the in_queue and name it after the process name
        self.in_queue = sim.Store(name=f'{self.name()}.in_queue', env=self.env)

    def process(self) -> None:
        """The process loop."""
        while True:
            self.from_store(self.in_queue)
            entity: Component = self.from_store_item()
            entity.activate(process=self.name())  # trigger entity.<name>()


class BatchingProcess(Component):
    """Takes ``batch_size`` entites from ``in_queue`` and inserts a single
    instance of ``out_type`` to ``env.processes[out_process].in_queue``.

    Attributes:
        batch_size (int | typing.Callable[[], int]):
            The batch size or its distribution.  Can take `salabim` distributions or any
            other type with ``__call__`` implemented.
        in_queue (salabim.Store): The in-queue of the process from which entities are taken.
        out_type (typing.Type[Batch]):
            The output type of the batching process.
            Must contain an attribute ``items`` (a list).
        out_process (str): The name of the process receiving the batch.
        env (Model): The simulation model this arrival generator is attached to.
    """

    def __init__(self, *args,
                 batch_size: int | Callable[[], int],
                 out_type: Type['Batch'],
                 out_process: str,
                 env: Environment = None,
                 **kwargs) -> None:
        """Constructor.

        Args:
            args (dict[str, typing.Any]):
                Positional arguments passed to the :py:class:`super() <salabim.Component>`
                constructor.
            batch_size (int | typing.Callable[[], int])
            out_type (typing.Type[Batch])
            out_process (str)
            env (Model)
            kwargs (dict[str, typing.Any]):
                Additional keyword arguments passed to the :py:class:`super() <salabim.Component>`
                constructor.
        """
        # super().__init__ consumes args and a bunch of kwargs and passes the rest to setup()
        super().__init__(*args, **kwargs, env=env, batch_size=batch_size,
                         out_type=out_type, out_process=out_process)

    def setup(self,  # pylint: disable=arguments-differ
              batch_size: int | Callable[[], int],
              out_type: Type['Batch'],
              out_process: str,
              **kwargs) -> None:
        """Set up the `BatchingProcess`. Salabim encourages use of a ``setup()`` method
        rather than overriding ``__init__()``. The method is called automatically
        immediately after initialisation."""
        self.batch_size = batch_size
        self.in_queue = sim.Store(name=f'{self.name()}.in_queue', env=self.env)
        self.out_type = out_type
        self.out_process = out_process
        self.batch_args = kwargs

    def process(self) -> None:
        """The batching loop."""
        env: Model = self.env
        while True:
            batch_size = self.batch_size() if callable(self.batch_size) else self.batch_size
            batch = self.out_type(**self.batch_args)
            for _ in range(batch_size):
                self.from_store(self.in_queue)
                item = self.from_store_item()
                item.register(batch.items)
            batch.enter(env.processes[self.out_process].in_queue)


class CollationProcess(Component):
    """Takes entities from ``in_queue`` and places them into a pool.
    Once all entities with the same parent are found (based on comparing
    with a counter), the parent is inserted into
    ``env.processes[out_process].in_queue``.

    Attributes:
        counter_name (str):
            The name of the counter in the parent entity defining
            the number of child entities.
        in_queue (salabim.Store): The in-queue of the process from which entities are taken.
        out_process (str):
            The name of the process receiving the reconstituted parent entity.
        env (Model): The simulation model this arrival generator is attached to.
    """

    def __init__(self, *args,
                 counter_name: str,
                 out_process: str,
                 env: Environment = None,
                 **kwargs) -> None:
        """Constructor.

        Args:
            args (dict[str, typing.Any]):
                Positional arguments passed to the :py:class:`super() <salabim.Component>`
                constructor.
            counter_name (str)
            out_process (str)
            env (Model)
            kwargs (dict[str, typing.Any]):
                Additional keyword arguments passed to the :py:class:`super() <salabim.Component>`
                constructor.
        """
        # super().__init__ consumes args and a bunch of kwargs and passes the rest to setup()
        super().__init__(*args, **kwargs,
                         env=env, counter_name=counter_name, out_process=out_process)

    def setup(  # pylint: disable=arguments-differ
            self, counter_name: str, out_process: str) -> None:
        """Set up the `CollationProcess`. Salabim encourages use of a ``setup()`` method
        rather than overriding ``__init__()``. The method is called automatically
        immediately after initialisation."""
        self.counter_name = counter_name
        self.in_queue = sim.Store(name=f'{self.name()}.in_queue', env=self.env)
        self.out_process = out_process
        self.dict: dict[str, list[Component]] = {}

    def process(self) -> None:
        """The collation loop."""
        env: Model = self.env
        while True:
            self.from_store(self.in_queue)
            item: Component = self.from_store_item()
            key = item.parent.name()
            if key not in self.dict:
                self.dict[key] = []
            self.dict[key].append(item)

            # Check counter to see if we have all items in the group
            if len(self.dict[key]) ==\
                    item.parent.data[self.counter_name]:
                item.parent.enter_sorted(env.processes[self.out_process].in_queue, item.parent)
                del self.dict[key]


class DeliveryProcess(Component):
    """Takes entities/batches from the `in_queue` and places them
    in `env.processes[out_process].in_queue`, after some delay.
    A resource is required to move the entity/batch and requires
    time to travel between the locations associated with the two
    processes.  Batches are unbatched upon arrival.

    Attributes:
        runner (salabim.Resource):
            The resource (e.g. staff) responsible for the delivery.
        out_duration (float | typing.Callable[[], float]):
            The time required for the runner to collect and drop off the delivery.
            Acceptable types are those accepted by :py:meth:`salabim.Component.hold`.
        return_duration (float | typing.Callable[[], float]):
            The time required for the runner to return to its home location after delivery.
            Acceptable types are those accepted by :py:meth:`salabim.Component.hold`.
        out_process (str):
            The name of the process receiving the delivery.
        env (Model): The simulation model this arrival generator is attached to.
    """

    # NOTE: Add additional delivery resources, e.g. a trolley, in the future?

    def __init__(self, *args,
                 runner: sim.Resource,
                 out_duration: float | Callable[[], float],
                 return_duration: float | Callable[[], float],
                 out_process: str,
                 env: 'Model',
                 **kwargs) -> None:
        """Constructor.

        Args:
            args (dict[str, typing.Any]):
                Positional arguments passed to the :py:class:`super() <salabim.Component>`
                constructor.
            runner (sim.Resource)
            out_duration (float | Callable[[], float])
            return_duration (float | Callable[[], float])
            out_process (str)
            env (Model)
            kwargs (dict[str, typing.Any]):
                Additional keyword arguments passed to the :py:class:`super() <salabim.Component>`
                constructor.
        """
        # super().__init__ consumes args and a bunch of kwargs and passes the rest to setup()
        super().__init__(*args, **kwargs, env=env, runner=runner, out_duration=out_duration,
                         return_duration=return_duration, out_process=out_process)

    def setup(  # pylint: disable=arguments-differ
        self,
        runner: sim.Resource,
        out_duration: float | sim.Distribution,
        return_duration: float | sim.Distribution,
        out_process: str
    ) -> None:
        """Set up the `DeliveryProcess`. Salabim encourages use of a ``setup()`` method
        rather than overriding ``__init__()``. The method is called automatically
        immediately after initialisation."""
        self.in_queue = sim.Store(name=f'{self.name()}.in_queue', env=self.env)
        self.runner = runner
        self.out_duration = out_duration
        self.return_duration = return_duration
        self.out_process = out_process

    def process(self) -> None:
        """The delivery loop."""
        env: Model = self.env
        out_queue = env.processes[self.out_process].in_queue

        while True:
            self.from_store(self.in_queue)
            entity: Component = self.from_store_item()

            # Deliveries of single items are given the priority of that item (expected to be URGENT)
            delivery_prio = (entity.prio if not isinstance(entity, Batch)
                             else Priority.ROUTINE)

            self.request((self.runner, 1, delivery_prio))
            self.hold(self.out_duration)

            # Unload delivery items
            if isinstance(entity, Batch):
                item: Component
                for item in entity.items:
                    item.enter_sorted(
                        out_queue,
                        priority=item.prio)
            else:
                entity.enter_sorted(
                    out_queue,
                    priority=entity.prio)

            # return runner to origin station
            self.hold(self.return_duration)
            self.release()


ProcessType = Union[Process, BatchingProcess, CollationProcess]
