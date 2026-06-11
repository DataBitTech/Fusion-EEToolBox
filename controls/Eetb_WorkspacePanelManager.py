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


from enum import Enum
import traceback
import adsk.core, adsk.fusion
from typing import List, Dict, Optional
from .. import config

class Eetb_WorkspacePanelManager:
    """
    A common class to manage toolbar panels and command controls for different Fusion360 workspaces.
    """
    
    def __init__(self, workspace_id: str, tab_id: str, tab_name: str, 
                 panel_config: Enum):
        """
        Initialize the panel manager for a specific workspace.
        
        Args:
            workspace_id: The Fusion360 workspace ID
            tab_id: The toolbar tab ID
            tab_name: The toolbar tab name
            panel_config: Dictionary mapping panel IDs to panel names
        """
        self._tab_id = tab_id
        self._tab_name = tab_name
        self._panel_config = panel_config
        
        self._local_controls: List[adsk.core.CommandControl] = []
        self._local_panels: List[adsk.core.ToolbarPanel] = []
        
        self._app = adsk.core.Application.get()
        self._ui: adsk.core.UserInterface = self._app.userInterface
        self._workspace_id = workspace_id
        

    def start(self):
        """Initialize the workspace panels and controls."""
        try:
            workspace = self._ui.workspaces.itemById(self._workspace_id)
            eetb_tab = workspace.toolbarTabs.itemById(self._tab_id)

            if eetb_tab is None:
                eetb_tab = workspace.toolbarTabs.add(self._tab_id, self._tab_name)
            
            # Create all panels defined in panel_config
            for panel in self._panel_config:
                #first check if this is a built-in panel
                if eetb_tab.toolbarPanels.itemById(panel.value) is not None:
                    panel_id = panel.value
                else:
                    panel_id = self._get_panel_ID(panel)
                panel_var = eetb_tab.toolbarPanels.itemById(panel_id)
                if panel_var is None:
                    panel_var = eetb_tab.toolbarPanels.add(panel_id, panel.value)
                    self._local_panels.append(panel_var)
                    
        except Exception as e:
            if self._ui:
                self._ui.messageBox(f'Failed to start workspace panels:\n{traceback.format_exc()}')
    

    def stop(self):
        """Clean up all created controls and panels."""
        try:
            workspace = self._ui.workspaces.itemById(self._workspace_id)
            eetb_tab = workspace.toolbarTabs.itemById(self._tab_id)
            
            for cmd_ctrl in self._local_controls:
                cmd_ctrl.deleteMe()
            for panel in self._local_panels:
                if panel.controls.count == 0:
                    panel.deleteMe()
            if eetb_tab and eetb_tab.toolbarPanels.count == 0:
                eetb_tab.deleteMe()
                
        except Exception as e:
            if self._ui:
                self._ui.messageBox(f'Failed to stop workspace panels:\n{traceback.format_exc()}')


    def clear_panel(self, panel: Enum):
        """Clear all commands from a specific panel."""
        try:
            workspace = self._ui.workspaces.itemById(self._workspace_id)
            eetb_tab = workspace.toolbarTabs.itemById(self._tab_id)

            #first check if this is a built-in panel
            if eetb_tab.toolbarPanels.itemById(panel.value) is not None:
                panel_id = panel.value
            else:
                panel_id = self._get_panel_ID(panel)
                
            panel_var = eetb_tab.toolbarPanels.itemById(panel_id)
            if panel_var:
                # Delete all controls from the panel
                controls_to_delete = []
                for i in range(panel_var.controls.count):
                    controls_to_delete.append(panel_var.controls.item(i))
                
                for ctrl in controls_to_delete:
                    ctrl.deleteMe()
                    # Remove from local controls list
                    if ctrl in self._local_controls:
                        self._local_controls.remove(ctrl)
                    
        except Exception as e:
            if self._ui:
                self._ui.messageBox(f'Failed to clear panel:\n{traceback.format_exc()}')
        
    
    def add_command_to_panel(self, panel: Enum, command_def: adsk.core.CommandDefinition, 
                           is_promoted: bool = False) -> Optional[adsk.core.CommandControl]:
        """Add a command to a specific panel."""
        workspace = self._ui.workspaces.itemById(self._workspace_id)
        eetb_tab = workspace.toolbarTabs.itemById(self._tab_id)

        # first check if this is a built-in panel
        if eetb_tab.toolbarPanels.itemById(panel.value) is not None:
            panel_id = panel.value
        else:
            panel_id = self._get_panel_ID(panel)
            if not panel_id:
                return None
        
        try:
            panel_var = eetb_tab.toolbarPanels.itemById(panel_id)
            command_ctrl = panel_var.controls.addCommand(command_def)
            command_ctrl.isPromoted = is_promoted
            command_ctrl.isEnabled = True
            self._local_controls.append(command_ctrl)
            return command_ctrl
        except Exception as e:
            if self._ui:
                self._ui.messageBox(f'Failed to add command to panel:\n{traceback.format_exc()}')
            return None


    def _get_panel_ID(self, panel: Enum) -> Optional[adsk.core.ToolbarPanel]:
        """Get a specific panel by ID."""
        if panel not in self._panel_config:
            return None

        # construct panel name
        return 'Eetb_' + self._workspace_id.replace(' ', '_') + '_'  + panel.value.replace(' ', '_') + '_PanelID'
