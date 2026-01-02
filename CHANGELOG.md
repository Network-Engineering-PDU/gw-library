# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Node diagnosis feature
- Test examples
- Multiple relays and DACs capability

### Changed

- Output layer messages structure
- Events are generated with correct units

## [1.12.2] - 2024-11-20

### Changed

- AWS boto3 and pylink as optional requirements
- Update package versions for Kirkstone

## [1.12.1] - 2024-09-26

### Added

- Hardware self-test module

### Fixed

- Remove node from whitelist when configuration timeouts
- Remove handlers from event handler when stopping the gateway
- Ensure modules are off after stop

## [1.12.0] - 2024-05-24

### Added

- Handshake in passthrough mode
- CM v2 board
- Gateway ID to passthrough config

### Changed

- Output models include automation feature

## [1.11.0] - 2023-12-20

### Added

- Passthrough mode
- Node whitelist
- UART disconnection event
- nRF52 hard reset feature

## [1.10.1] - 2023-11-10

### Added

- Add CM platform

### Changed

- Update cryptography version
- Simplify OpenOCD calls

## [1.10.0] - 2023-06-09

### Added

- Opcode to change node tasks without deleting them
- Bi-directional ping
- Node task configuration based on ChangeTask and config mode
- JLink and OpenOCD programmer classes
- Fw version and lib version in gateway status
- Store node tasks in memory

### Changed

- Reduce max number of nodes being configured a the same time to 10
- Reschedule tasks without modifying task order

## [1.9.0] - 2023-02-03

### Added

- Relay support in radio OTA
- Srote radio OTA status
- Output (relay & DAC) model
- Sensor calibration feature
- Sensor config (heater & repeatability) feature
- Blinking led tasks
- New Rhea and Thor boards
- Low priority queue in tx manager

### Changed

- Adapt power meter dataframes to new structure

### Removed

- Power meter alerts

## [1.8.0] - 2022-08-12

## Added

- Replay cache
- Pylint config
- Stress test
- Node configuration timeout
- Power meter nodes
- FW 1.3.0 compatibility

## Changed

- Rework event parser module
- Rework of database module for better compatibility with SQLite
- If port if given, DK fw not checked
- Max 20 concurrent node configuration
- Better Prometeo configuration

## Fixed

- REQ\_DATETIME task intitial time
- Remove replay cache entry when node is removed

## [1.7.0]

### Added

- Add last node contacted checking before changing DEVKEY and DST_ADDR
- Update and fix listener mode
- Add transport layer for communications between gateways
- Remove sequence number and version from mesh database
- Add tast timeout max retries
- Add provisioner mode
- Add manual platform/board selection
- Add config object

### Fixed

- Fix model send message LOCK only at model scope
- Fix has_c02 for unknown nodes
- Mesh TTL set to max (127)
- Listener mode

### Changed

- Move sequence number to its own file

## [1.6.1]

### Added

- Add new boards (Iris v5 & Prometeo v4)
- Add new board (Soter v2)

### Fixed

- Fix dependency versions

## [1.6.0]

### Added

- This changelog

[Unreleased]: https://bitbucket.org/tychetools/gw-library/branches/compare/devel..master
[1.12.2]: https://bitbucket.org/tychetools/gw-library/branches/compare/1.12.2..1.12.1
[1.12.1]: https://bitbucket.org/tychetools/gw-library/branches/compare/1.12.1..1.12.0
[1.12.0]: https://bitbucket.org/tychetools/gw-library/branches/compare/1.12.0..1.11.0
[1.11.0]: https://bitbucket.org/tychetools/gw-library/branches/compare/1.11.0..1.10.1
[1.10.1]: https://bitbucket.org/tychetools/gw-library/branches/compare/1.10.1..1.10.0
[1.10.0]: https://bitbucket.org/tychetools/gw-library/branches/compare/1.10.0..1.9.0
[1.9.0]: https://bitbucket.org/tychetools/gw-library/branches/compare/1.9.0..1.8.0
[1.8.0]: https://bitbucket.org/tychetools/gw-library/branches/compare/1.8.0..1.7.0
[1.7.0]: https://bitbucket.org/tychetools/gw-library/branches/compare/1.7.0..1.6.1
[1.6.1]: https://bitbucket.org/tychetools/gw-library/branches/compare/1.6.1..1.6.0
[1.6.0]: https://bitbucket.org/tychetools/gw-library/branches/compare/1.6.0..1.5.1
