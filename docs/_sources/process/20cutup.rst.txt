Cut-up
======

For simplicity, some effects of cut-up specialities are ignored, e.g. room and time-slot assignment.

The possible cut-up types are:

- **BMS**: Typically simple biopsies, always produces 1 small surgical block.
- **Pool**: Always produces 1 large surgical block.
- **Large specimens**: Produces a random number of mega or large surgical blocks.

The probability of each cut-up type depends on whether or not the specimen is marked as urgent
and can be set in the configuration input Excel file, as can the number of blocks produced
by large specimen cut-ups.  Additionally, urgent cut-ups never produce mega blocks.

.. kroki::
    :type: plantuml

    @startuml
    skinparam ActivityDiamondBackgroundColor business
    skinparam ActivityDiamondFontSize 12
    skinparam NoteBackgroundColor motivation
    skinparam DefaultTextAlignment center
    skinparam NoteTextAlignment left
    skinparam DefaultFontSize 12

    start
    :**WIP**\nCut-up += 1;
    switch (Cut-up type)
    case (BMS)
        #orchid:**Seize**\nBMS;
    case (other)
        #orchid:**Seize**\nCut-up assistant;
        note right: Specimen-based priority
    endswitch
    #palegreen:**Delay**\n(Cut-up);
    note right: Duration depends on cut-up type
    #orchid:**Release**\nBMS or\nCut-up assistant;
    :**WIP**\nCut-up -= 1;
    partition Batch and deliver {
    if (Urgent specimen?) then (yes)
    else (no)
        #Lightskyblue:**Batch** specimens;
    endif
    switch (Cut-up type)
    case (BMS)
        #orchid:**Seize**\nBMS;
    case (other)
        #orchid:**Seize**\nCut-up assistant;
        note right: URGENT if specimen is URGENT,\nROUTINE priority otherwise
    endswitch
    #Lightskyblue:**Deliver**\nto processing\n (& return trip);
    #orchid:**Release**\nBMS or\nCut-up assistant;
    }
    stop
    @enduml
