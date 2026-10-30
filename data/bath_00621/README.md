# Data Repository for Design Science Paper ``The emergent structures within digital engineering work: what can we learn from dynamic DSMs of near-identical systems design projects?''

Dr. J. A. Gopsill

This repository contains the underlying data used to generate the DSMs for cross-project comparison of three near-identical systems design projects. The data is stored in a SQlite database and a jupyter notebook is provided to demonstrate how to access the data.

The database contains a single table `metadata`, which has the following fields:

- `id` An anonymous file id
- `type` Whether the file is an assembly or part
- `subsystem` The subsystem the file belongs to
- `time_delta` A time delta with respect to the first edit made by the team
- `team` A letter designating which team the file belongs to (A, B, C)

The subsystems are coded as follows:

- `BR` Brake System
- `CA` Complete Assembly
- `EL` Electrical System
- `EN` Engine & Drivetrain
- `FR` Frame & Body
- `FS` Standard Parts
- `MS` Miscellaneous
- `ST` Steering
- `SU` Suspension
- `WT` Wheels & Tyres
