Reception
=========

Specimens are classified as internal if they already exist on the EPIC system prior to booking-in.
Currently, these include specimens from Addenbrooke's Hospital and Royal Papworth Hospital.
All other specimens are marked as external.

Branching probabiliities in the flowchart below are implemented as global variables and
can be set in the configuration input Excel file.  The time a specimen spends in the Reception
stage is measured between the two matching WIP labels.

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
    :**WIP**\ntotal += 1;
    :**WIP**\nReception += 1;
    partition Receive and Sort {
    #orchid:**Seize**\nbooking-in staff;
    note right: highest (URGENT) priority
    #palegreen:**Delay**\n(Receive and sort);
    #orchid:**Release**\nbooking-in staff;
    }
    partition Booking-in {
    #orchid:**Seize**\nbooking-in staff;
    note right: Specimen-based priority
    if (Pre-booking-in\ninvestigation?) then (yes)
        #palegreen:**Delay**\n(Pre-booking-in\ninvestigation);
    else (no)
    endif
    switch (Specimen source?)
    case (Internal)
        #palegreen:**Delay**\n(Booking-in,\ninternal);
        switch (Additional\ninvestigation?)
        case (Easy)
            #palegreen:**Delay**\n(Investigation,\n int. easy);
        case (Hard)
            #palegreen:**Delay**\n(Investigation,\n int. hard);
        case (None)
        endswitch
    case (External)
        #palegreen:**Delay**\n(Booking-in,\nexternal);
        switch (Additional\ninvestigation?)
        case (Yes)
            #palegreen:**Delay**\n(Investigation,\n external);
        case (No)
        endswitch
    endswitch
    #orchid:**Release**\nbooking-in staff;
    }
    :**WIP**\nReception -= 1;
    partition Batch and deliver {
    if (Urgent specimen?) then (yes)
    else (no)
        #Lightskyblue:**Batch** specimens;
    endif
    #orchid:**Seize**\nbooking-in staff;
    note right: URGENT if specimen is URGENT,\nROUTINE priority otherwise
    #Lightskyblue:**Deliver**\nto cut-up\n (& return trip);
    #orchid:**Release**\nbooking-in staff;
    }
    stop
    @enduml

