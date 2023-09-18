Processing
==========

The possible processing programmes are:

- Urgent blocks
- Small surgical blocks
- Large surgical blocks
- Mega blocks

The duration of each programme can be set in the configuration input Excel file and should include
any idle machine time (delayed programme start).

**TODO**

- Add signals to program logic -- wait for time-of-day based signal to start processing
  machine?
- Model embedding machine, paraffin (wax) trimmer resources

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
    :**WIP**\nProcessing += 1;

    partition Decalcification (per block) {
        switch (Decalc?)
        case (Bone station)
            #orchid:**Seize**\nBMS,\nBone staton<
            #palegreen:**Delay**\n(Load bone\nstation);
            #orchid:**Release**\nBMS>
            #palegreen:**Delay**\n(Decalc);
            #orchid:**Seize**\nBMS<
            #palegreen:**Delay**\n(Unload bone\nstation);
            #orchid:**Release**\nBMS,\nBone station>
        case (Oven)
            #orchid:**Seize**\nBMS<
            #palegreen:**Delay**\n(Place in oven);
            #orchid:**Release**\nBMS>
            #palegreen:**Delay**\n(Decalc);
            #orchid:**Seize**\nBMS<
            #palegreen:**Delay**\n(Take from oven);
            #orchid:**Release**\nBMS>
        case (None)
        endswitch
    }

    #Lightskyblue:**Batch** blocks by\nprocessing programme;

    partition Processing machine (per batch of blocks) {
        #CornflowerBlue:**Seize**\nProcessing room staff,\nProcessing machine<
        note right: URGENT or default priority
        #palegreen:**Delay**\n(Load processing machine);
        #CornflowerBlue:**Release**\nProcessing room staff>
        #palegreen:**Delay**\n(Processing);
        note right: Duration depends on\nselected programme
        #CornflowerBlue:**Seize**\nProcessing room staff<
        note right: URGENT or default priority
        #palegreen:**Delay**\n(Unload processing machine);
        #CornflowerBlue:**Release**\nProcessing room staff,\nProcessing machine>
    }

    #Lightskyblue:**Unbatch** blocks;

    partition Embed and trim (per block) {
        #Plum:**Seize**\nProcessing room staff<
        #palegreen:**Delay**\n(Embed wax block);
        #Plum:**Release**\nProcessing room staff>
        #palegreen:**Delay**\n(Cool-down);
        #Plum:**Seize**\nProcessing room staff<
        #palegreen:**Delay**\n(Trim excess wax);
        #Plum:**Release**\nProcessing room staff>
    }

    #Lightskyblue:**Collate** blocks by specimen;
    :**WIP**\nProcessing -= 1;

    partition Batch and deliver {
        if (Urgent specimen?) then (yes)
        else (no)
            #Lightskyblue:**Batch** specimens;
        endif
        #orchid:**Seize**\nProcessing room staff<
        #Lightskyblue:**Deliver**\nto cut-up\n (& return trip);
        #orchid:**Release**\nBMS or\nCut-up assistant>
    }
    stop
    @enduml
