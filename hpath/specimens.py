"""Defines specimens, blocks, and slides."""
import enum
from abc import ABC
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar

import salabim as sim

if TYPE_CHECKING:
    from model import Model


class Priority(enum.IntEnum):
    """Specimen priority. Lower value = higher priority."""
    ROUTINE = 0
    CANCER = -1
    PRIORITY = -2
    URGENT = -3


class Component(sim.Component, ABC):
    """A salabim component with additional fields.

    Attribute:
        prio (Priority): Priority of the component (Urgent, Priority, Cancer, or Routine).
        parent (Component): The parent component, if it exists.
        data (dict[str, Any]): Properites of the component.
    """
    prio: Priority
    parent: Self | None
    data: dict[str, Any]


C = TypeVar('C', bound=Component)


class Specimen(Component):
    """A tissue specimen."""

    def setup(self, **kwargs) -> None:
        """Set up the `Specimen`. Salabim encourages use of a ``setup()`` method
        rather than overriding ``__init__()``. The method is called automatically
        immediately after initialisation."""
        env: Model = self.env

        self.data = kwargs
        self.blocks: list[Block] = []

        dist = 'cancer' if self.data['cancer'] else 'non_cancer'
        cdf = sim.CumPdf((
            Priority.URGENT,
            getattr(env.globals, 'prob_urgent_' + dist),

            Priority.PRIORITY,
            getattr(env.globals, 'prob_urgent_' + dist) +
            getattr(env.globals, 'prob_priority_' + dist),

            (Priority.CANCER if dist == "cancer" else Priority.ROUTINE),
            1
        ))
        self.prio: Priority = cdf.sample()
        self.data['priority'] = self.prio.name

    def process(self) -> None:
        """Insert specimen into the `in_queue` of its first process."""
        env: Model = self.env
        self.enter(env.processes['arrive_reception'].in_queue)


class Block(Component):
    """A wax block."""

    def setup(self, *, parent: Specimen, **kwargs) -> None:  # pylint: disable=arguments-differ
        """Set up the `Block`. Salabim encourages use of a ``setup()`` method
        rather than overriding ``__init__()``. The method is called automatically
        immediately after initialisation."""
        self.parent: Specimen = parent
        self.prio = self.parent.prio
        self.slides: list[Slide] = []
        self.data = kwargs


class Slide(Component):
    """A glass slide."""

    def setup(self, *, parent: Block, **kwargs) -> None:  # pylint: disable=arguments-differ
        """Set up the `Slide`. Salabim encourages use of a ``setup()`` method
        rather than overriding ``__init__()``. The method is called automatically
        immediately after initialisation."""
        self.parent: Block = parent
        self.prio = self.parent.prio
        self.data = kwargs


class Batch(Component, Generic[C]):
    """A Batch of :py:class:`Component` objects."""

    def setup(self, **kwargs) -> None:
        self.data = kwargs
        self.items: list[C] = []
