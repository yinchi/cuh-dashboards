"""The histopathology simulation model."""
import dataclasses
from dataclasses import dataclass, field
import json
from typing import Literal

import dacite
import salabim as sim

from . import process, kpis, util
from .config import Config, DistributionInfo, IntDistributionInfo, ResourceInfo
from .distributions import PERT, Constant, Distribution, IntPERT, Tri
from .process import ArrivalGenerator, ProcessType, ResourceScheduler
from .util import dc_items


@dataclass(kw_only=True, eq=False)
class Resources:
    """Dataclass for tracking the resources of a :py:class:`Model`.

    See also:
        :py:class:`hpath.config.ResourcesInfo`
    """

    # We use metadata here so that the allocation schedule of each resource can be looked up
    # in the Excel file.
    booking_in_staff: sim.Resource = field(
        default_factory=sim.Resource, metadata={'name': 'Booking-in staff'})
    bms: sim.Resource = field(
        default_factory=sim.Resource, metadata={'name': 'BMS'})
    cut_up_assistant: sim.Resource = field(
        default_factory=sim.Resource, metadata={'name': 'Cut-up assistant'})
    processing_room_staff: sim.Resource = field(
        default_factory=sim.Resource, metadata={'name': 'Processing room staff'})
    microtomy_staff: sim.Resource = field(
        default_factory=sim.Resource, metadata={'name': 'Microtomy staff'})
    staining_staff: sim.Resource = field(
        default_factory=sim.Resource, metadata={'name': 'Staining staff'})
    scanning_staff: sim.Resource = field(
        default_factory=sim.Resource, metadata={'name': 'Scanning staff'})
    qc_staff: sim.Resource = field(
        default_factory=sim.Resource, metadata={'name': 'QC staff'})
    histopathologist: sim.Resource = field(
        default_factory=sim.Resource, metadata={'name': 'Histopathologist'})
    bone_station: sim.Resource = field(
        default_factory=sim.Resource, metadata={'name': 'Bone station'})
    processing_machine: sim.Resource = field(
        default_factory=sim.Resource, metadata={'name': 'Processing machine'})
    staining_machine: sim.Resource = field(
        default_factory=sim.Resource, metadata={'name': 'Staining machine'})
    coverslip_machine: sim.Resource = field(
        default_factory=sim.Resource, metadata={'name': 'Coverslip machine'})
    scanning_machine_regular: sim.Resource = field(
        default_factory=sim.Resource, metadata={'name': 'Scanning machine (regular)'})
    scanning_machine_megas: sim.Resource = field(
        default_factory=sim.Resource, metadata={'name': 'Scanning machine (megas)'})

    def __init__(self, env: 'Model') -> None:
        for _field in dataclasses.fields(__class__):
            self.__setattr__(_field.name, sim.Resource(
                name=_field.metadata['name'],
                env=env
            ))


@dataclass(kw_only=True, eq=False)
class TaskDurations:
    """Dataclass for tracking task durations in a :py:class:`Model`.

    See also:
        :py:class:`hpath.config.TaskDurationsInfo`
    """
    receive_and_sort: Distribution
    pre_booking_in_investigation: Distribution
    booking_in_internal: Distribution
    booking_in_external: Distribution
    booking_in_investigation_internal_easy: Distribution
    booking_in_investigation_internal_hard: Distribution
    booking_in_investigation_external: Distribution
    cut_up_bms: Distribution
    cut_up_pool: Distribution
    cut_up_large_specimens:  Distribution
    load_bone_station: Distribution
    decalc: Distribution
    unload_bone_station: Distribution
    load_into_decalc_oven: Distribution
    unload_from_decalc_oven: Distribution
    load_processing_machine: Distribution
    unload_processing_machine: Distribution
    processing_urgent: Distribution
    processing_small_surgicals: Distribution
    processing_large_surgicals: Distribution
    processing_megas: Distribution
    embedding: Distribution
    embedding_cooldown: Distribution
    block_trimming: Distribution
    microtomy_serials: Distribution
    microtomy_levels: Distribution
    microtomy_larges: Distribution
    microtomy_megas: Distribution
    load_staining_machine_regular: Distribution
    load_staining_machine_megas: Distribution
    staining_regular: Distribution
    staining_megas: Distribution
    unload_staining_machine_regular: Distribution
    unload_staining_machine_megas: Distribution
    load_coverslip_machine_regular: Distribution
    coverslip_regular: Distribution
    coverslip_megas: Distribution
    unload_coverslip_machine_regular: Distribution
    labelling: Distribution
    load_scanning_machine_regular: Distribution
    load_scanning_machine_megas: Distribution
    scanning_regular: Distribution
    scanning_megas: Distribution
    unload_scanning_machine_regular: Distribution
    unload_scanning_machine_megas: Distribution
    block_and_quality_check: Distribution
    assign_histopathologist: Distribution
    write_report: Distribution


@dataclass(kw_only=True)
class Wips:
    """Dataclass for tracking work-in-progress counters for the :py:class:`Model` simulation."""
    total: sim.Monitor
    in_reception: sim.Monitor
    in_cut_up: sim.Monitor
    in_processing: sim.Monitor
    in_microtomy: sim.Monitor
    in_staining: sim.Monitor
    in_labelling: sim.Monitor
    in_scanning: sim.Monitor
    in_qc: sim.Monitor
    in_reporting: sim.Monitor

    def __init__(self, env: sim.Environment) -> None:
        self.total = sim.Monitor('Total WIP', level=True, type="uint32", env=env)
        self.in_reception = sim.Monitor('Reception', level=True, type="uint32", env=env)
        self.in_cut_up = sim.Monitor('Cut-up', level=True, type="uint32", env=env)
        self.in_processing = sim.Monitor('Processing', level=True, type="uint32", env=env)
        self.in_microtomy = sim.Monitor('Microtomy', level=True, type="uint32", env=env)
        self.in_staining = sim.Monitor('Staining', level=True, type="uint32", env=env)
        self.in_labelling = sim.Monitor('Labelling', level=True, type="uint32", env=env)
        self.in_scanning = sim.Monitor('Scanning', level=True, type="uint32", env=env)
        self.in_qc = sim.Monitor('QC', level=True, type="uint32", env=env)
        self.in_reporting = sim.Monitor('Reporting stage', level=True, type="uint32", env=env)


class Model(sim.Environment):
    """The simulation model."""

    def __init__(self, config: Config, **kwargs) -> None:
        """Constructor.

        Args:
            config (hpath.config.Config):
                Configuration settings for the simulation model.
            kwargs:
                Additional parameters absorbed by the super() constructor.
        """

        # Change super() defaults
        kwargs['time_unit'] = kwargs.get('time_unit', 'hours')
        kwargs['random_seed'] = kwargs.get('random_seed', '*')

        super().__init__(**kwargs, config=config)

    def setup(self, config: Config) -> None:  # pylint: disable=arguments-differ
        """Set up the salabim :py:class:`~salabim.Environment`. Triggered as the last step in
        object initialisation."""
        super().setup()

        self.num_reps = config.num_reps
        self.sim_length = self.env.hours(config.sim_hours)
        self.created = config.created
        self.analysis_id = config.analysis_id

        # ARRIVALS
        ArrivalGenerator(
            'Arrival Generator (cancer)',
            schedule=config.arrival_schedules.cancer,
            env=self,
            # cls_args:
            cancer=True
        )

        ArrivalGenerator(
            'Arrival Generator (non-cancer)',
            schedule=config.arrival_schedules.noncancer,
            env=self,
            # cls_args:
            cancer=True
        )

        # RESOURCES AND RESOURCE SCHEDULERS
        self.resources = Resources(self)
        for name, resource in dc_items(self.resources):
            resource: sim.Resource
            resource_info: ResourceInfo = getattr(config.resources_info, name)

            assert resource.name() == resource_info.name

            ResourceScheduler(
                f'Scheduler [{resource.name()}]',
                resource=resource,
                schedule=resource_info.schedule,
                env=self
            )

        def time_unit_full(abbr: Literal['s', 'm', 'h']):
            return "seconds" if abbr == 's' else "minutes" if abbr == 'm' else "hours"

        # TASK DURATIONS
        task_durations = {}
        for key1, val1 in iter(config.task_durations_info):
            val1: DistributionInfo
            task_durations[key1] = (
                PERT(val1.low, val1.mode, val1.high, time_unit_full(val1.time_unit), env=self)
                if val1.type == 'PERT' else
                Tri(val1.low, val1.mode, val1.high, time_unit_full(val1.time_unit), env=self)
                if val1.type == 'Triangular' else
                Constant(val1.mode, time_unit_full(val1.time_unit), env=self)
            )
        self.task_durations = dacite.from_dict(TaskDurations, task_durations)

        self.batch_sizes = config.batch_sizes
        self.globals = config.global_vars

        for key2, val2 in iter(self.globals):
            if isinstance(val2, IntDistributionInfo):
                if val2.type == 'IntPERT':
                    setattr(self.globals, key2, IntPERT(val2.low, val2.mode, val2.high, env=self))
                else:
                    raise ValueError(f'Distribution type {val2.type} not (yet) supported.')

        # DATA STORE FOR COMPLETED SPECIMENS
        self.completed_specimens = sim.Store(
            name='Completed specimens',
            env=self
        )

        # WORK-IN-PROGRESS COUNTERS
        self.wips = Wips(self)

        # REGISTER PROCESSES
        self.processes: dict[str, ProcessType] = {}
        process.p10_reception.register(self)
        process.p20_cutup.register(self)
        process.p30_processing.register(self)
        process.p40_microtomy.register(self)
        process.p50_staining.register(self)
        process.p60_labelling.register(self)
        process.p70_scanning.register(self)
        process.p80_qc.register(self)
        process.p90_reporting.register(self)

        # FREQUENTLY USED DISTRIBUTIONS
        self.u01 = sim.Uniform(0, 1, time_unit=None, env=self)

    def run(self) -> None:  # pylint: disable=arguments-differ
        super().run(duration=self.sim_length)


if __name__ == '__main__':
    model = Model(Config.from_excel('config.xlsx', 6*7*24, 10, None))
    model.run()
    print(json.dumps(kpis.Report.from_model(model), default=util.serialiser))
