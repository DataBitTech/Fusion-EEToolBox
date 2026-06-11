# Electronics Extended Toolbox (EETB) for Fusion 360

An extension for Autodesk Fusion 360 that provides an extended set of tools for electronics design and PCB layout.

## Overview

The Electronics Extended Toolbox is a Fusion 360 add-in that provides enhanced tools and utilities for electrical and electronics design within Fusion 360's Electronics workspace. This plugin aims to extend the built-in electronics capabilities with additional functionality for PCB design, component management, and design automation. It aims to extend the electronics workspaces, adding long missing functionality and assembling scripts that users have been writing for themselves since the Eagle times. We hope to provide a platform to continue the tradition of sharing useful routines in a community driven way and modernized form.

## Features

The following commands are available in the Electronics Extended Toolbox plugin for Fusion 360:

### Schematics editor
- Export BOM in manufacturer specific formats, supporting
  - filtering out components using user defined Regex patterns
  - mapping attributes to BOM columns
  - exporting to CSV, Excel, and text files
  - calling external user scripts from Fusion for custom BOM processing processing
- Add UI buttons for any legacy ULP or SCR script
- Bulk add attribute to components
- Bulk delete an attribute from components
- Bulk rename attribute of components
- Bulk copy attributes between components
- ToDo list with links to schematic elements

### Layout editor
- Measure routing length and propagation delay, including vias
- Swap signal routing, with layer and via filtering
- Swap component placement with different orientation options
- Fix line connections for unconnected lines
- Generate via fencing for signals/line geometries with preview
- Export BOM in manufacturer specific formats, supporting THT/SMD flag in addition to the features of the schematics editor BOM exporter
- Export component placement data in manufacturer specific formats, supporting
  - rotation and translation fixes specific to the manufacturer
  - filtering out components using user defined Regex patterns
  - mapping attributes to BOM columns
  - exporting to CSV, Excel, and text files
  - calling external user scripts from Fusion for custom BOM processing processing
- Add UI buttons for any legacy ULP or SCR script
- Bulk add attribute to components
- Bulk delete an attribute from components
- Bulk rename attribute of components
- Bulk copy attributes between components
- ToDo list with links to schematic elements
- Production checklist with global checklist items and document specific completed states

### 3D package editor
- Snap 3D model to PCB surface
- Center 3D model feature to footprint feature
- Symmetric alignment of 3d features to footprint features

### Library editor
- Add UI buttons for any legacy ULP or SCR script

## Installation

The easiest way to install is using the installer ([Windows](https://marketplace.autodesk.com/apps/1ab36649-512f-4797-9bdc-68179270dac9?priceId=85abea3a-13a8-444f-a41c-9bd409506c40) and [MacOS](https://marketplace.autodesk.com/apps/7fa2b512-d2b1-4e0c-8076-def8fdc63ebc?priceId=b5001295-273e-437b-8271-46be2d927309)) from the Autodesk App Store 

If you prefer to install manually or want have the most up-to-date version, follow these steps:
1. Download the latest release from the [releases page](https://github.com/DataBitTech/Fusion-EEToolbox/releases) and extract or simply clone this repository to a path of your choosing. Fusion can be kept running in the background.
2. On the Utilities ribbon, find the Add-ins button. Use the Add button ('+' sign) on the top of the dialog, then 'Script or add-in from device'
3. Enjoy, share, contribute and give feedback!

## Tutorials

There are tutorials for the new commands on [YouTube](https://youtube.com/playlist?list=PLa4BUswmWtMA-BXwLmQtifTjxLAAvYVyo&si=Ub-zl5piD1LCWjOr). 

## Contributing

Contributions are most welcome! Please consult the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

This project uses 3rd party libraries -  see the [NOTICE](NOTICE) file for details.

Thank you for all the community contributors for sharing their knowledge and code snippets!
