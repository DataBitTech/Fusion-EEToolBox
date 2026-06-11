#======================================================
# This software is released under the MIT license:
#
# MIT License
# 
# Copyright (c) 2025 Pal Szabo
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#======================================================


from typing import Literal
import adsk.core, adsk.fusion
from enum import Enum
from .. import config
from .Eetb_WorkspacePanelManager import Eetb_WorkspacePanelManager

app = adsk.core.Application.get()
ui = app.userInterface

controls: list[Eetb_WorkspacePanelManager] = []

class SchematicPanel(Enum):
    SWITCH_PANEL = 'Switch'
    EXPORT_PANEL = 'Export'
    SCRIPT_PANEL = 'User scripts'
    COMMON_PANEL = 'Manage'
    # ADD MORE PANELS HERE


class LayoutPanel(Enum):
    SWITCH_PANEL   = 'Switch'
    MEASURE_PANEL  = 'Measure'
    REWORK_PANEL   = 'Rework'
    PATTERNS_PANEL = 'Patterns'
    EXPORT_PANEL   = 'Export'
    SCRIPT_PANEL   = 'User scripts'
    COMMON_PANEL   = 'Manage'
    # ADD MORE PANELS HERE


class PackagePanel(Enum):
    PACKAGE_PANEL = 'Package3DPanel' # this is a built-in panel


class LibraryPanel(Enum):
    SCRIPT_PANEL = 'User scripts'
    ABOUT_PANEL = 'About'
    # ADD MORE PANELS HERE


workspace_tabs_and_panels = [
    {'workspace': config.ELECTRON_SCHEMATIC_ENV_ID,          'tab_id': 'EetbSchTab',        'tab_name': 'Extended Toolbox', 'panels': SchematicPanel},
    {'workspace': config.ELECTRON_LAYOUT_ENV_ID,             'tab_id': 'EetbLyoTab',        'tab_name': 'Extended Toolbox', 'panels': LayoutPanel}, 
    {'workspace': config.FUSION_PACKAGE_ENV_ID,              'tab_id': 'Package3DTab',      'tab_name': 'Package',          'panels': PackagePanel},      
    {'workspace': config.ELECTRON_LIBRARY_FOOTPRINT_ENV_ID,  'tab_id': 'EetbLibFootprintTab','tab_name':'Extended Toolbox', 'panels': LibraryPanel},
    {'workspace': config.ELECTRON_LIBRARY_SYMBOL_ENV_ID,     'tab_id': 'EetbLibSymbolTab',  'tab_name': 'Extended Toolbox', 'panels': LibraryPanel},
    {'workspace': config.ELECTRON_LIBRARY_DEVICE_ENV_ID,     'tab_id': 'EetbLibDeviceTab',  'tab_name': 'Extended Toolbox', 'panels': LibraryPanel},
]

def start():
    global controls
    controls = []

    for setup in workspace_tabs_and_panels:
        control = Eetb_WorkspacePanelManager(setup['workspace'], setup['tab_id'], setup['tab_name'], setup['panels'])
        controls.append(control)
    
    # Start all the controls
    for control in controls:
        control.start()

    # add some default buttons
    add_command_to_panel(config.ELECTRON_SCHEMATIC_ENV_ID, SchematicPanel.SWITCH_PANEL, ui.commandDefinitions.itemById('SwitchPcbDocCmd'))
    add_command_to_panel(config.ELECTRON_LAYOUT_ENV_ID, LayoutPanel.SWITCH_PANEL, ui.commandDefinitions.itemById('SwitchSchDocCmd'))
    add_command_to_panel(config.ELECTRON_LAYOUT_ENV_ID, LayoutPanel.SWITCH_PANEL, ui.commandDefinitions.itemById('Switch3dPcbDocCmd'))
    add_command_to_panel(config.ELECTRON_LAYOUT_ENV_ID, LayoutPanel.SWITCH_PANEL, ui.commandDefinitions.itemById('RemovePCB3DLinkCmd'), False)


def stop():
    global controls
    for control in controls:
        control.stop()


def add_command_to_panel(workspace_id: str, panel_id: Enum, command_def: adsk.core.CommandDefinition, is_promoted=True):
    # Get the array index of the workspace_id from workspace_tabs_and_panels
    ctrl_idx = next((i for i, setup in enumerate(workspace_tabs_and_panels) if setup['workspace'] == workspace_id), None)
    if ctrl_idx is None:
        raise ValueError(f"Workspace {workspace_id} not found in workspace_tabs_and_panels")

    # Add the command to the panel
    control = controls[ctrl_idx].add_command_to_panel(panel_id, command_def, is_promoted)


def clear_panel(workspace_id: str, panel_id: Enum):
    """
    Clear all controls from specified panels in a workspace.
    """
    # Get the array index of the workspace_id from workspace_tabs_and_panels
    ctrl_idx = next((i for i, setup in enumerate(workspace_tabs_and_panels) if setup['workspace'] == workspace_id), None)
    if ctrl_idx is None:
        raise ValueError(f"Workspace {workspace_id} not found in workspace_tabs_and_panels")
    
    # Get the control for this workspace
    control = controls[ctrl_idx].clear_panel(panel_id)
