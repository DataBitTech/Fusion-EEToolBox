# Application Global Variables
# This module serves as a way to share variables across different
# modules (global variables).

import os
import tempfile
import adsk.core

# Flag that indicates to run in Debug mode or not. When running in Debug mode
# more information is written to the Text Command window. Generally, it's useful
# to set this to True while developing an add-in and set it to False when you
# are ready to distribute it.
DEBUG: bool = True

# Flag that indicates to run in Develop mode or not. When running in Develop mode
# some additional buttons become available on the UI to aid in the development of
# headless commands
DEVELOPER_MODE: bool = True

# Gets the name of the add-in from the name of the folder the py file is in.
# This is used when defining unique internal names for various UI elements 
# that need a unique name. It's also recommended to use a company name as 
# part of the ID to better ensure the ID is unique.
ADDIN_NAME: str = 'eetb'

#ulActiveWorkSpaceIdList = ['ElectronEmptyLbrEnvironment', 'SchEditorEnvironement', 'BoardLayoutEnvironement']

ELECTRON_SCHEMATIC_ENV_ID: str = 'SchEditorEnvironement'
ELECTRON_LAYOUT_ENV_ID: str = 'BoardLayoutEnvironement'
ELECTRON_LIBRARY_FOOTPRINT_ENV_ID: str = 'ElectronFootprintEnvironment'
ELECTRON_LIBRARY_SYMBOL_ENV_ID: str = 'ElectronSymbolEnvironment'
ELECTRON_LIBRARY_DEVICE_ENV_ID: str = 'ElectronDeviceEnvironment'
FUSION_PACKAGE_ENV_ID: str = 'Package3DEnvironment'
FUSION_SOLID_ENV_ID: str = 'FusionSolidEnvironment'

# Specify the full path to the csv file used to transfer BOM data from EAGLE to this add-in
TEMP_DIR: str = tempfile.gettempdir()
ULP_DIR: str = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'eetbUtils', 'ulp'))
EETB_COMMON_ICON_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'eetbUtils', 'icons'))
ELECTRON_COMMON_ICON_DIR = os.path.join(adsk.core.Application.get().applicationFolders.rootPath, 'Electron', 'UI', 'Resources', 'Icons')
FUSION_COMMON_ICON_DIR = os.path.join(adsk.core.Application.get().applicationFolders.rootPath, 'Fusion', 'UI', 'FusionUI', 'Resources')