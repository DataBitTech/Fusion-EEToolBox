# Electronics Extended Toolbox (EETB) Developer Guide

This document provides detailed information for developers working with the Electronics Extended Toolbox Fusion 360 add-in.

## Project Overview

The Electronics Extended Toolbox is a Fusion 360 add-in designed to extend the built-in electronics capabilities with additional functionality for PCB design, component management, and design automation.

## Project Structure

```
ElectronicsExtendedToolBox/
├── commands/                       # New Fusion commands (Python backends with potential HTML/CSS/JS frontends)
├── controls/                       # UI binding and controls
├── lib/                            # Library files
│   ├── eetbUtils/                  # Project-specific utilities (custom functionality)
│   │   ├── CSS/                    # Common CSS styles
|   |   ├── icons/                  # Common non-Fusion icons used by multiple commands/palettes
│   │   ├── javascript/             # Common JavaScript utilities
│   │   ├── *.py                    # Common Python utility functions
│   │   └── ulp/                    # Eagle ULP scripts
│   ├── fusionAddInUtils/           # External Fusion utilities (do not modify)
|   ├── et_xmlfile/                 # XML handling python library (do not modify)
|   └── openpyxl/                   # Excel format handling python library (do not modify)
├── ElectronicsExtendedToolBox.py   # Main plugin files
├── DEFAULT_CONFIG.json             # Default configuration file, used only once after installation
├── CONFIG.json                     # User configuration file, stores user preferences
└── AddInIcon.svg                   # Add-in icon
```

## Command Structure

Each command follows a consistent pattern:
1. Python backend in `/commands` directory, inherited from 
2. HTML/CSS/JavaScript frontend in the command's `resources` subfolder (if palette type)
3. Files named `commandName.py` for Python backend and `palette.html` for frontend (if exists)

The `CommandBase` class implements a common base for all commands. New commands should inherit from `CommandBase` if they only use built-in UI elements.
If functionality not supported by the Fusion API is needed (e.g. autocomplete, advanced tables, etc.), commands should inherit from `PaletteCommandBase` instead, and use HTML/JavaScript. For basic UI elements, common CSS is provided in the `/lib/CSS` directory, imitating both Fusion themes.

## Data access

Fusion currently has no built-in support for accessing electronics data via an API. So electronics data is accessed via legacy ULP calls (see `/lib/eetbUtils/extract_data.py`), that export the requested data to a JSON file, which is then read by the commands. Due to the event handling mechanism in Fusion, ULP and SCR calls cannot be executed any time, only in the context of command creation. There are guarding mechanisms in place in `CommandBase` to prevent execution outside of command creation context, and thus crashing Fusion. If a script is needed to run as an output of command execution, there is a deferrred execution mechanism implemented, see `Eetb_ExecuteScriptCommand.py`.

Alternatively, one can use 'palettes' that communicate via messages between the backend (Python) and the frontend (HTML/JavaScript). The event handling of these messages seem to run in another context that allows the execution of both ULPs and SCR scripts. In `PaletteCommandBase` there is support to either emulate a regular command, that does not dock and auto-cancels when another command is started, or to create a palette that can be docked and persists until explicitly closed. 

## UI/Controls Structure

UI binding is managed by the class in the `/controls` directory. This separation is recommended/required by the Fusion API. It also allows the same command to be added to different workspaces.

## Shared Utilities

### eetbUtils Library
The `/lib/eetbUtils` directory contains backend utilities that can be shared across multiple commands:

- **CSS/**: Common CSS styles used throughout the add-in
- **javascript/**: Common JavaScript utility functions
- **Python files**: Shared Python utility functions
- **ulp/**: Eagle ULP scripts that integrate with the add-in

### fusionAddInUtils
The `/lib/fusionAddInUtils` directory contains external Fusion utilities that should NOT be modified. These provide base functionality for Fusion add-in development. This is provided by Autodesk.

## Development Guidelines

### Python Coding Standards
- Follow PEP 8 style guidelines
- Use descriptive variable and function names
- Include docstrings for functions and classes
- Use proper error handling and logging

### JavaScript Coding Standards
- Use ES6+ features and best practices
- Follow consistent naming conventions
- Minimize global variables
- Ensure DOM operations are efficient

### HTML/CSS Coding Standards
- Use semantic HTML elements
- Follow consistent CSS class naming conventions, reusing existing styling when possible
- Keep styles modular and reusable
- Ensure responsive design

## API Integration

All Fusion 360 API calls should reference the official documentation:
- [Fusion 360 API Reference manual](https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-7B5A90C8-E94C-48DA-B16B-430729B734DC)

## Debugging

Autodesk has a guide on how to create and debug Fusion 360 add-ins and there is a forum thread on how to enable HTML debugging: 
- [Debugging Fusion 360 Add-ins](https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-9701BBA7-EC0E-4016-A9C8-964AA4838954)
- [Python specific issues](https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-743C88FB-CA3F-44B0-B0B9-FCC378D0D782)
- [Forum thread on how to debug palettes (HTML/Javascript)](https://forums.autodesk.com/t5/fusion-api-and-scripts-forum/bug-no-devtools-when-right-click-on-a-palette-with/m-p/10243219/highlight/true#M13080)

## Testing

When developing new features:
1. Verify compatibility with existing commands
2. Test edge cases and error conditions
3. Ensure UI components function correctly

## Contributing

Please refer to [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing to this project.
