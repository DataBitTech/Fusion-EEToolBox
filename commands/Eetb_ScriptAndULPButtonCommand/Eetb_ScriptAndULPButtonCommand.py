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


import adsk.core
import os

from ... import config, controls
from ..CommandBase import CommandBase
from ...lib import fusionAddInUtils as futil
from ...lib import eetbUtils as eetbutil

class Eetb_ScriptAndULPButtonCommand(CommandBase):
    # class variable to create unique IDs
    _running_idx = 0

    def __init__(self, button_name: str, script_path: str, isULP: bool, workspace_id: str):
        type_string = 'ULP' if isULP else 'script'
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_script_and_ulp_button_{Eetb_ScriptAndULPButtonCommand._running_idx}_command_id',
            command_name =  button_name if button_name else f'Execute user script/ULP "{script_path}"',
            command_description = f'Execute the legacy Eagle {type_string} "{script_path}" in Fusion',
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'),
            icon_folder = os.path.join(config.EETB_COMMON_ICON_DIR, 'Ulp' if isULP else 'Script'))
        super().__init__(command_attributes)
        
        self._isULP = isULP
        self._script_path = script_path
        self._workspace_id = workspace_id
        
        Eetb_ScriptAndULPButtonCommand._running_idx += 1


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        if self._workspace_id == config.ELECTRON_SCHEMATIC_ENV_ID:
            panel = controls.SchematicPanel.SCRIPT_PANEL
        elif self._workspace_id == config.ELECTRON_LAYOUT_ENV_ID:
            panel = controls.LayoutPanel.SCRIPT_PANEL
        else:
            panel = controls.LibraryPanel.SCRIPT_PANEL
        controls.add_command_to_panel(self._workspace_id, panel, commandDefinition, True)


    def on_command_created(self, args: adsk.core.CommandCreatedEventArgs):
        """
        Event handler for when the command is created.

        See the base class method for full details.
        
        Args:
            args: CommandCreatedEventArgs
        """
        super().on_command_created(args)
        self.log_to_console(f"Running Eagle {'ULP' if self._isULP else 'script'} from User defined button {self._command_name}")
        self.run_eagle_command(f"{'RUN' if self._isULP else 'SCRIPT'} '{self._script_path}'")


    ##############
    # PROPERTIES #
    ##############

    @property
    def workspace_id(self):
        """Get the workspace context for this command."""
        return self._workspace_id

