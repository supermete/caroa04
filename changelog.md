# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## latest
### Fixed
- Read outputs at init to prevent overwriting outputs that are already active, #15


## [1.0.2] - 2024-04-27
### Changed
- Convert logging info to debug to avoid excessive logging, #13


## [1.0.1] - 2024-04-27
### Changed
- In start method, interface parameter is made optional, #11

### Fixed
- Fix code snippet in documentation , #10


## [1.0.0] - 2024-04-26
### Changed
- Use notifier from can library to allow sharing the bus with other bus users, #7
- Merge stop and shutdown methods, to only have a stop method to be called when stopping, #8

### Fixed
- Fix communication when bus is set before starting , #5


## [0.1.2] - 2024-04-15
### Changed
- Move CanMessage/CanSignal inherited classes in canmessage.py. Delete travis yml and create mkdocs, #3
- Rename class for more coherence, #1

