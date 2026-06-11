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
import json

from ... import config, controls
from ..CommandBase import CommandBase
from ...lib import fusionAddInUtils as futil
from ...lib import eetbUtils as eetbutil

class Eetb_AppInfoCommand(CommandBase):

    def __init__(self):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_app_info_command_id',
            command_name = 'About',
            command_description = 'Information about the Electronics Extended Toolbox',
            
            # Paths
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources'),
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'))
        super().__init__(command_attributes)

        # Get version from manifest
        self._version = 'Unknown'
        try:
            # Get the path to the manifest file
            manifest_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'ElectronicsExtendedToolBox.manifest')
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
                self._version = manifest_data.get('version', 'Unknown')
        except Exception:
            pass

        # info text
        self._info_text = f"""
            <h2>Electronics Extended Toolbox</h2>
            <p><b>Version:</b> {self._version}</p>
            <p>This is an open-source Fusion 360 add-in designed to extend the capabilities of the Electronics workspace. It provides additional tools and utilities for electronic design and documentation.</p>
            
            <p>Contributions are welcome! You can find the source code and contribute at our <a href="https://github.com/databittech/fusion-eettb-addon">GitHub repository</a>.</p>

            <p>The project is licensed under the MIT License. See the LICENSE file in the repository for more details.</p>

            <p><h3>Privacy Policy</h3></p>
            <p>This application does not collect any personal data. All user configuration settings are stored locally on your device and are never transmitted to any external servers.</p>
            """


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        controls.add_command_to_panel(config.ELECTRON_SCHEMATIC_ENV_ID,         controls.SchematicPanel.COMMON_PANEL,  commandDefinition)
        controls.add_command_to_panel(config.ELECTRON_LAYOUT_ENV_ID,            controls.LayoutPanel.COMMON_PANEL,     commandDefinition)
        controls.add_command_to_panel(config.ELECTRON_LIBRARY_DEVICE_ENV_ID,    controls.LibraryPanel.ABOUT_PANEL,     commandDefinition)
        controls.add_command_to_panel(config.ELECTRON_LIBRARY_FOOTPRINT_ENV_ID, controls.LibraryPanel.ABOUT_PANEL,     commandDefinition)
        controls.add_command_to_panel(config.ELECTRON_LIBRARY_SYMBOL_ENV_ID,    controls.LibraryPanel.ABOUT_PANEL,     commandDefinition)


    def on_command_created(self, args: adsk.core.CommandCreatedEventArgs):
        """
        Event handler for when the command is created.

        See the base class method for full details.
        
        Args:
            args: CommandCreatedEventArgs
        """
        super().on_command_created(args)

        cmd = args.command
        inputs = cmd.commandInputs
        
        cmd.isOKButtonVisible = False
        cmd.cancelButtonText = 'Close'

        inputs.addTextBoxCommandInput('info_text', '', self._info_text, 24, True)
