"""Module defining the simulation model."""
import json
import typing as ty

import pandas as pd
import pydantic as pyd

Probability = pyd.confloat(ge=0, le=1)


class ArrivalSchedule(pyd.BaseModel):
    """An arrival schedule for specimens."""
    rates: ty.Sequence[pyd.NonNegativeFloat]

    @staticmethod
    def from_pd(df: pd.DataFrame) -> 'ArrivalSchedule':
        """Construct an arrival schedule from a dataframe with the 24 hours the day as rows \
and the seven days of the week as columns (starting on Monday).  Each value is the \
arrival rate for one hour of the week."""
        return __class__(rates=df.to_numpy().flatten('F').tolist())


class ArrivalSchedules(pyd.BaseModel):
    """Dataclass for tracking the specimen arrival schedules of a model."""

    cancer: ArrivalSchedule =\
        pyd.Field(description='Arrival schedule for cancer pathway specimens.')
    noncancer: ArrivalSchedule =\
        pyd.Field(description='Arrival schedule for non-cancer pathway specimens.')


class ResourceSchedule(pyd.BaseModel):
    """A resource allocation schedule."""

    day_flags: ty.Sequence[bool] =\
        pyd.Field(description='True/1 if resource is scheduled for the day (MON to SUN), '
                  'False/0 otherwise.')

    allocation: ty.Sequence[pyd.NonNegativeInt] =\
        pyd.Field(description='Number of resource units allocated for the day '
                  '(in 30-min intervals), if the corresponding day flag is set to 1. '
                  'The list length is expected to be 48.')

    @pyd.field_validator('day_flags', mode='after')
    @classmethod
    def _is_length_7(cls, seq: ty.Sequence[bool]):
        """Enforce sequence length on  ``day_flags`` argument."""
        assert len(seq) == 7, 'Length of sequence must be 7.'

    @pyd.field_validator('allocation', mode='after')
    @classmethod
    def _is_length_48(cls, seq: ty.Sequence[bool]):
        """Enforce sequence length on  ``allocation`` argument."""
        assert len(seq) == 48, 'Length of sequence must be 48.'

    @staticmethod
    def from_pd(df: pd.DataFrame, row_name: str) -> 'ResourceSchedule':
        """Construct a resource schedule from a DataFrame row."""
        return __class__(
            day_flags=df.loc[row_name, 'MON':'SUN'].tolist(),
            allocation=df.loc[row_name, '00:00':'23:30'].tolist()
        )


class ResourceInfo(pyd.BaseModel):
    """Contains information about a resource."""
    name: str
    type: ty.Literal['staff', 'machine']
    schedule: ResourceSchedule


class ResourcesInfo(pyd.BaseModel):
    """Dataclass for tracking the staff resources of a model.

The fields in this dataclass **MUST** match the rows of the configuration \
Excel template ("Resources" tab), with all letters to lowercase, spaces to \
underscores, and other characters removed."""

    booking_in_staff: ResourceInfo =\
        pyd.Field(title='Booking-in staff',
                  json_schema_extra={'resource_type': 'staff'})
    bms: ResourceInfo =\
        pyd.Field(title='BMS',
                  json_schema_extra={'resource_type': 'staff'})
    cut_up_assistant: ResourceInfo =\
        pyd.Field(title='Cut-up assistant',
                  json_schema_extra={'resource_type': 'staff'})
    processing_room_staff: ResourceInfo =\
        pyd.Field(title='Processing room staff',
                  json_schema_extra={'resource_type': 'staff'})
    microtomy_staff: ResourceInfo =\
        pyd.Field(title='Microtomy staff',
                  json_schema_extra={'resource_type': 'staff'})
    staining_staff: ResourceInfo =\
        pyd.Field(title='Staining staff',
                  json_schema_extra={'resource_type': 'staff'})
    scanning_staff: ResourceInfo =\
        pyd.Field(title='Scanning staff',
                  json_schema_extra={'resource_type': 'staff'})
    qc_staff: ResourceInfo =\
        pyd.Field(title='QC staff',
                  json_schema_extra={'resource_type': 'staff'})
    histopathologist: ResourceInfo =\
        pyd.Field(title='Histopathologist',
                  json_schema_extra={'resource_type': 'staff'})
    bone_station: ResourceInfo =\
        pyd.Field(title='Bone station',
                  json_schema_extra={'resource_type': 'machine'})
    processing_machine: ResourceInfo =\
        pyd.Field(title='Processing machine',
                  json_schema_extra={'resource_type': 'machine'})
    staining_machine: ResourceInfo =\
        pyd.Field(title='Staining machine',
                  json_schema_extra={'resource_type': 'machine'})
    coverslip_machine: ResourceInfo =\
        pyd.Field(title='Coverslip machine',
                  json_schema_extra={'resource_type': 'machine'})
    scanning_machine_regular: ResourceInfo =\
        pyd.Field(title='Scanning machine (regular)',
                  json_schema_extra={'resource_type': 'machine'})
    scanning_machine_megas: ResourceInfo =\
        pyd.Field(title='Scanning machine (megas)',
                  json_schema_extra={'resource_type': 'machine'})

    @staticmethod
    def from_pd(df: pd.DataFrame) -> 'ResourcesInfo':
        """Constructor.

        Args:
            env (salabim.Environment):
                The environment the resources are to be attached to.
        """
        resources = {
            key: ResourceInfo(
                name=field.title,
                type=field.json_schema_extra['resource_type'],
                schedule=ResourceSchedule.from_pd(df, row_name=key)
            )
            for key, field in __class__.model_fields.items()
        }
        return __class__(**resources)


class DistributionInfo(pyd.BaseModel):
    """Information describing a three-point random distributions for task durations."""

    type: ty.Literal['Constant', 'Triangular', 'PERT']  # Supported distribution types
    low: pyd.NonNegativeFloat
    mode: pyd.NonNegativeFloat
    high: pyd.NonNegativeFloat
    time_unit: ty.Literal['s', 'm', 'h']

    @pyd.field_validator('time_unit', mode='before')
    @classmethod
    def _first_letter(cls, time_unit_str: str) -> str:
        """Take only the first letter from a time-unit string.

        For simplicity, only the first character of time-unit strings are checked, i.e.
        "hours", "hour", and "hxar" are identical.
        """
        assert time_unit_str[0] in ['s', 'm', 'h']
        return time_unit_str[0]

    @pyd.model_validator(mode='after')
    def _enforce_ordering(self) -> 'DistributionInfo':
        """Ensure that the the ``low``, ``mode`` and ``high`` parameters of the distribution
        are in non-decreasing order."""
        # Constant case
        if self.type == 'Constant':
            return __class__.model_construct(
                type='Constant', low=self.mode, mode=self.mode, high=self.mode)
        # Other cases
        assert self.mode >= self.low, 'Failed requirement: mode >= low'
        assert self.high >= self.mode, 'Failed requirement: high >= mode'
        return self


class TaskDurationsInfo(pyd.BaseModel):
    """Information for tracking task durations in a model.

The field titles in this class **MUST** match the rows of the Excel input file \
("Task Durations" tab)."""

    receive_and_sort: DistributionInfo =\
        pyd.Field(title='Receive and sort',
                  description='Time for reception to receive a new specimen and assign '
                  'a priority value.')
    pre_booking_in_investigation: DistributionInfo =\
        pyd.Field(title='Pre-booking-in investigation',
                  description='Time to conduct a pre-booking-in investigation, if required.')
    booking_in_internal: DistributionInfo =\
        pyd.Field(title='Booking-in (internal)',
                  description='Time to book in the specimen, if the specimen was received '
                  'internally, i.e. it already exists on the EPIC sytem.')
    booking_in_external: DistributionInfo =\
        pyd.Field(title='Booking-in (internal)',
                  description='Time to book in the specimen, if the specimen was received '
                  'externally, i.e. a new entry must be created on EPIC.')
    booking_in_investigation_internal_easy: DistributionInfo =\
        pyd.Field(title='Booking-in investigation (internal, easy)',
                  description='Time to conduct a booking-in investigation for an internal '
                  'specimen, if the investigation is classified as "easy".')
    booking_in_investigation_internal_hard: DistributionInfo =\
        pyd.Field(title='Booking-in investigation (internal, hard)',
                  description='Time to conduct a booking-in investigation for an internal '
                  'specimen, if the investigation is classified as "hard".')
    booking_in_investigation_external: DistributionInfo =\
        pyd.Field(title='Booking-in investigation (internal, easy)',
                  description='Time to conduct a booking-in investigation for an '
                  'external specimen.')
    cut_up_bms: DistributionInfo =\
        pyd.Field(title='Cut-up (BMS)', description='Time to conduct a BMS cut-up.')
    cut_up_pool: DistributionInfo =\
        pyd.Field(title='Cut-up (Pool)', description='Time to conduct a pool cut-up.')
    cut_up_large_specimens: DistributionInfo =\
        pyd.Field(title='Cut-up (large specimens)',
                  description='Time to conduct a large specimens cut-up.')
    load_bone_station: DistributionInfo =\
        pyd.Field(title='Load bone station',
                  description='Time to load a batch of blocks into a bone station.')
    decalc: DistributionInfo =\
        pyd.Field(title='Decalc', description='Time to decalcify a bony specimen.')
    unload_bone_station: DistributionInfo =\
        pyd.Field(title='Unload bone station',
                  description='Time to unload a batch of blocks into a bone station.')
    load_into_decalc_oven: DistributionInfo =\
        pyd.Field(title='Load bone station',
                  description='Time to load a single block into a bone station.')
    unload_from_decalc_oven: DistributionInfo =\
        pyd.Field(title='Load bone station',
                  description='Time to unload a single block into a bone station.')
    load_processing_machine: DistributionInfo =\
        pyd.Field(title='Load processing machine',
                  description='Time to load a batch of blocks into a processing machine.')
    unload_processing_machine: DistributionInfo =\
        pyd.Field(title='Unload processing machine',
                  description='Time to unload a batch of blocks from a processing machine.')
    processing_urgent: DistributionInfo =\
        pyd.Field(title='Processing machine (urgent)',
                  description='Programme length for the processing of urgent blocks.')
    processing_small_surgicals: DistributionInfo =\
        pyd.Field(title='Processing machine (small surgicals)',
                  description='Programme length for the processing of small surgical blocks.')
    processing_large_surgicals: DistributionInfo =\
        pyd.Field(title='Processing machine (large surgicals)',
                  description='Programme length for the processing of large surgical blocks.')
    processing_megas: DistributionInfo =\
        pyd.Field(title='Processing machine (megas)',
                  description='Programme length for the processing of mega blocks.')
    embedding: DistributionInfo =\
        pyd.Field(title='Embedding',
                  description='Time to embed a block in paraffin wax (staffed).')
    embedding_cooldown: DistributionInfo =\
        pyd.Field(title='Embedding (cooldown)',
                  description='Time for a wax block to cool (unstaffed).')
    block_trimming: DistributionInfo =\
        pyd.Field(title='Block trimming',
                  description='Time to trim excess wax from the edges of a block.')
    microtomy_serials: DistributionInfo =\
        pyd.Field(title='Microtomy (serials)',
                  description='Time to produce serial slides from a block.')
    microtomy_levels: DistributionInfo =\
        pyd.Field(title='Microtomy (levels)',
                  description='Time to produce level slides from a block.')
    microtomy_larges: DistributionInfo =\
        pyd.Field(title='Microtomy (larges)',
                  description='Time to produce large-section slides from a block. '
                  'These are regular-sized slides, but with larger tissue sections.')
    microtomy_megas: DistributionInfo =\
        pyd.Field(title='Microtomy (mega)',
                  description='Time to produce mega slides from a mega block.')
    load_staining_machine_regular: DistributionInfo =\
        pyd.Field(title='Load staining machine (regular)',
                  description='Time to load a batch of regular-sized slides into a '
                  'staining machine.')
    load_staining_machine_megas: DistributionInfo =\
        pyd.Field(title='Load staining machine (regular)',
                  description='Time to load a batch of mega slides into a staining machine.')
    staining_regular: DistributionInfo =\
        pyd.Field(title='Load staining machine (regular)',
                  description='Time to stain a batch of regular slides.')
    staining_megas: DistributionInfo =\
        pyd.Field(title='Load staining machine (regular)',
                  description='Time to stain a batch of mega slides.')
    unload_staining_machine_regular: DistributionInfo =\
        pyd.Field(title='Load staining machine (regular)',
                  description='Time to unload a batch of regular slides from a staining machine.')
    unload_staining_machine_megas: DistributionInfo =\
        pyd.Field(title='Load staining machine (regular)',
                  description='Time to unload a batch of mega slides from a staining machine.')
    load_coverslip_machine_regular: DistributionInfo =\
        pyd.Field(title='Load coverslip machine (regular)',
                  description='Time to load a batch of regular slides into a coverslip machine.')
    coverslip_regular: DistributionInfo =\
        pyd.Field(title='Coverslipping (regular)',
                  description='Time to affix coverslips to a batch of regular slides.')
    coverslip_megas: DistributionInfo =\
        pyd.Field(title='Load coverslip machine (regular)',
                  description='Time to affix a coverslip to a mega slide (manual task).')
    unload_coverslip_machine_regular: DistributionInfo =\
        pyd.Field(title='Load coverslip machine (regular)',
                  description='Time to unload a batch of regular slides into a coverslip machine.')
    labelling: DistributionInfo =\
        pyd.Field(title='Labelling', description='Time to label a slide.')
    load_scanning_machine_regular: DistributionInfo =\
        pyd.Field(title='Load scanning machine (regular)',
                  description='Time to load a batch of regular slides into a scanning machine.')
    load_scanning_machine_megas: DistributionInfo =\
        pyd.Field(title='Load scanning machine (megas)',
                  description='Time to load a batch of mega slides into a scanning machine. '
                  'There are dedicated scanning machines for mega slides.')
    scanning_regular: DistributionInfo =\
        pyd.Field(title='Scanning (regular)',
                  description='Time to scan a batch of regular slides.')
    scanning_megas: DistributionInfo =\
        pyd.Field(title='Scanning (regular)',
                  description='Time to scan a batch of mega slides.')
    unload_scanning_machine_regular: DistributionInfo =\
        pyd.Field(title='Unload scanning machine (regular)',
                  description='Time to unload a batch of regular slides from a scanning machine.')
    unload_scanning_machine_megas: DistributionInfo =\
        pyd.Field(title='Unload scanning machine (regular)',
                  description='Time to unload a batch of mega slides from a scanning machine.')
    block_and_quality_check: DistributionInfo =\
        pyd.Field(title='Block and quality check',
                  description='Time to perform the block and quality checks for a specimen.')
    assign_histopathologist: DistributionInfo =\
        pyd.Field(title='Assign histopathologist',
                  description='Time to assign a histopathologist to a specimen.')
    write_report: DistributionInfo =\
        pyd.Field(title='Write histopathological report',
                  description='Time to write the histopathological report for a specimen.')


class BatchSizes(pyd.BaseModel):
    """Information for tracking batch sizes in a model.  This is the number of \
specimens, blocks, or slides in a machine or delivery batch.  Batches in the model \
are homogeneous, i.e. all items in a batch are of the same type.\

The field titles in this class MUST match the rows of the Excel input file \
("Batch Sizes" tab)."""

    deliver_reception_to_cut_up: pyd.PositiveInt =\
        pyd.Field(title='Delivery (reception to cut-up)')
    deliver_cut_up_to_processing: pyd.PositiveInt =\
        pyd.Field(title='Delivery (cut-up to processing)')
    deliver_processing_to_microtomy: pyd.PositiveInt =\
        pyd.Field(title='Delivery (processing to microtomy)')
    deliver_microtomy_to_staining: pyd.PositiveInt =\
        pyd.Field(title='Delivery (microtomy to staining)')
    deliver_staining_to_labelling: pyd.PositiveInt =\
        pyd.Field(title='Delivery (staining to labelling)')
    deliver_labelling_to_scanning: pyd.PositiveInt =\
        pyd.Field(title='Delivery (labelling to scanning)')
    deliver_scanning_to_qc: pyd.PositiveInt = pyd.Field(title='Delivery (scanning to QC)')

    bone_station: pyd.PositiveInt = pyd.Field(title='Bone station (blocks)')
    processing_regular: pyd.PositiveInt = pyd.Field(title='Processing machine (regular blocks)')
    processing_megas: pyd.PositiveInt = pyd.Field(title='Processing machine (mega blocks)')
    staining_regular: pyd.PositiveInt = pyd.Field(title='Staining (regular slides)')
    staining_megas: pyd.PositiveInt = pyd.Field(title='Staining (mega slides)')
    digital_scanning_regular: pyd.PositiveInt = pyd.Field(title='Scanning (regular slides)')
    digital_scanning_megas: pyd.PositiveInt = pyd.Field(title='Scanning (mega slides)')


class IntDistributionInfo(pyd.BaseModel):
    """Information describing a discretised three-point random distribution."""

    type: ty.Literal['Constant', 'IntTriangular', 'IntPERT']  # Supported distribution types
    low: pyd.NonNegativeInt
    mode: pyd.NonNegativeInt
    high: pyd.NonNegativeInt

    @pyd.model_validator(mode='after')
    def _enforce_ordering(self) -> 'DistributionInfo':
        """Ensure that the the ``low``, ``mode`` and ``high`` parameters of the distribution
        are in non-decreasing order."""
        # Constant case
        if self.type == 'Constant':
            return __class__.model_construct(
                type='Constant', low=self.mode, mode=self.mode, high=self.mode)
        # Other cases
        assert self.mode >= self.low, 'Failed requirement: mode >= low'
        assert self.high >= self.mode, 'Failed requirement: high >= mode'
        return self


class Globals(pyd.BaseModel):
    """Stores the global variables of a model.

Field titles should match the corresponding named range in the Excel input file \
and therefore should not contain any spaces or symbols."""

    prob_internal: Probability =\
        pyd.Field(title='ProbInternal',
                  description='Probability that a specimen comes from an internal source, i.e. '
                  'one that uses the EPIC system.')

    prob_urgent_cancer: Probability =\
        pyd.Field(title='ProbInternal',
                  description='Probability that a cancer-pathway specimen has Urgent priority.')
    prob_urgent_non_cancer: Probability =\
        pyd.Field(title='ProbInternal',
                  description='Probability that a non-cancer-pathway specimen has Urgent priority.')
    prob_priority_cancer: Probability =\
        pyd.Field(title='ProbInternal',
                  description='Probability that a cancer-pathway specimen has Priority priority.')
    prob_priority_non_cancer: Probability =\
        pyd.Field(title='ProbInternal',
                  description='Probability that a non-cancer-pathway specimen has '
                  'Priority priority.')
    prob_routine_cancer: Probability =\
        pyd.Field(title='ProbInternal',
                  description='Probability that a cancer-pathway specimen has '
                  'Routine/Cancer priority.')
    prob_routine_non_cancer: Probability =\
        pyd.Field(title='ProbInternal',
                  description='Probability that a non-cancer-pathway specimen has '
                  'Routine priority.')

    prob_prebook: Probability =\
        pyd.Field(title='ProbInternal',
                  description='Probability that a specimen requires pre-booking-in investigation.')
    prob_invest_easy: Probability =\
        pyd.Field(title='ProbInternal',
                  description='Probability that an internal specimen requires '
                  'booking-in investigation, and the investigation is classified as "easy".')
    prob_invest_hard: Probability =\
        pyd.Field(title='ProbInternal',
                  description='Probability that an internal specimen requires '
                  'booking-in investigation, and the investigation is classified as "hard".')
    prob_invest_external: Probability =\
        pyd.Field(title='ProbInternal',
                  description='Probability that an external specimen requires '
                  'booking-in investigation.')

    prob_bms_cutup: Probability =\
        pyd.Field(title='ProbBMSCutup',
                  description='Probability that a non-urgent specimen goes to BMS cut-up.')
    prob_bms_cutup_urgent: Probability =\
        pyd.Field(title='ProbBMSCutup',
                  description='Probability that an urgent specimen goes to BMS cut-up.')
    prob_large_cutup: Probability =\
        pyd.Field(title='ProbBMSCutup',
                  description='Probability that a non-urgent specimen goes to '
                  'large specimens cut-up.')
    prob_large_cutup_urgent: Probability =\
        pyd.Field(title='ProbBMSCutup',
                  description='Probability that an urgent specimen goes to '
                  'large specimens cut-up.')
    prob_pool_cutup: Probability =\
        pyd.Field(title='ProbBMSCutup',
                  description='Probability that a non-urgent specimen goes to Pool cut-up.')
    prob_pool_cutup_urgent: Probability =\
        pyd.Field(title='ProbBMSCutup',
                  description='Probability that an urgent specimen goes to Pool cut-up.')

    prob_mega_blocks: Probability =\
        pyd.Field(title='ProbMegaBlocks',
                  description='Probability that a large specimen cut-up produces mega blocks. '
                  'With the remaining probability, large surgical blocks are produced instead.')

    prob_decalc_bone: Probability =\
        pyd.Field(title='ProbDecalcBone',
                  description='Probability that an specimen requires decalcification at a '
                  'bone station.')
    prob_decalc_oven: Probability =\
        pyd.Field(title='ProbDecalcOven',
                  description='Probability that an specimen requires decalcification in a '
                  'decalc oven.')

    prob_microtomy_levels: Probability =\
        pyd.Field(title='ProbMicrotomyLevels',
                  description='Probability that a small surgical block produces a "levels" '
                  'microtomy task. With remaining probability, a "serials" microtomy task '
                  'is produced.')

    num_blocks_large_surgical: IntDistributionInfo =\
        pyd.Field(title='NumBlocksLargeSurgical',
                  description='Parameters for the number of large surgical blocks produced in a '
                  'cut-up that produces such blocks.')
    num_blocks_mega: IntDistributionInfo =\
        pyd.Field(title='NumBlocksMega',
                  description='Parameters for the number of mega blocks produced in a '
                  'cut-up that produces such blocks.')
    num_slides_larges: IntDistributionInfo =\
        pyd.Field(title='NumSlidesLarges',
                  description='Parameters for the number of slides produced for a '
                  'large surgical microtomy task.')
    num_slides_levels: IntDistributionInfo =\
        pyd.Field(title='NumSlidesLarges',
                  description='Parameters for the number of slides produced for a '
                  'levels microtomy task.')
    num_slides_megas: IntDistributionInfo =\
        pyd.Field(title='NumSlidesLarges',
                  description='Parameters for the number of slides produced for a '
                  'megas microtomy task.')
    num_slides_serials: IntDistributionInfo =\
        pyd.Field(title='NumSlidesLarges',
                  description='Parameters for the number of slides produced for a '
                  'serials microtomy task.')


class Config(pyd.BaseModel):
    """Configuration settings for the histopathlogy department model."""

    arrival_schedules: ArrivalSchedules
    resources_info: ResourcesInfo
    task_durations_info: TaskDurationsInfo
    batch_sizes: BatchSizes
    global_vars: Globals


if __name__ == '__main__':
    print(json.dumps(Config.model_json_schema(), indent=2))
