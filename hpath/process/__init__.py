"""Definitions for Histopathology processes.

Processes are implemented as salabim :doc:`salabim:Component` instances
with a ``process()`` member.  This function is automatically triggered
upon instantiation of the process.

Each process takes entities from an input queue (implemented as an :py:class:`salabim.Store`),
performs work on these entities, and places the transformed entities onto an output queue.

    - The :py:class:`Process` class provides a link to a member function
      of some entity type in the model.  This function is triggered for
      each entity received from the input queue.  In fact, the constructor for
      the :py:class:`Process` class takes a function as its ``fn`` parameter and
      **makes** it a member function of the specified :doc:`salabim:Component` subtype.
    - The :py:class:`BatchingProcess` class takes multiple entities from the input queue
      and produces a single entity of the specified output type.
    - The :py:class:`CollationProcess` class searches for entities with the same parent
      and pushes the parent entity to the output queue when all sibling entities are
      found.
    - The :py:class:`DeliveryProcess` class represents deliveries of entities or batches.
      Batches are automatically unpacked when arriving at the output queue.

This module also defines the :py:class:`ArrivalGenerator` and :py:class:`ResourceScheduler` classes.
"""
from . import (p10_reception, p20_cutup, p30_processing, p40_microtomy,
               p50_staining, p60_labelling, p70_scanning, p80_qc, p90_reporting)
from .__core import (ArrivalGenerator, BatchingProcess, CollationProcess,
                     DeliveryProcess, Process, ProcessType, ResourceScheduler)

__all__ = [
    'ArrivalGenerator', 'BatchingProcess', 'CollationProcess', 'DeliveryProcess', 'Process',
    'ProcessType', 'ResourceScheduler',
    'p10_reception', 'p20_cutup', 'p30_processing', 'p40_microtomy', 'p50_staining',
    'p60_labelling', 'p70_scanning', 'p80_qc', 'p90_reporting'
]
