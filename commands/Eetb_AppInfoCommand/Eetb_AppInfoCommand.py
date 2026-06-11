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
import urllib.request
import urllib.error

from ... import config, controls
from ..CommandBase import CommandBase
from ...lib import fusionAddInUtils as futil
from ...lib import eetbUtils as eetbutil

class Eetb_AppInfoCommand(CommandBase):

    def __init__(self, isUpdateAvailable: bool):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_app_info_command_id',
            command_name = f'About{' - new version available!' if isUpdateAvailable else ''}',
            command_description = 'Information about the Electronics Extended Toolbox',
            
            # Paths
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'updateable' if isUpdateAvailable else 'latest'),
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'))
        super().__init__(command_attributes)

        self._isUpdateAvailable = isUpdateAvailable
        
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

        # construct the version text
        rel_notes_link = self._get_release_notes_link()
        self._version_text = f'<h2>Electronics Extended Toolbox</h2><p><h3>Version: {self._version}'
        if isUpdateAvailable:
            self._version_text += f'  <a href={config.APP_STORE_LINK_WIN64 if os.name == 'nt' else config.APP_STORE_LINK_MAC}>New version available!</a>'
        elif rel_notes_link:
            self._version_text += f'  <a href={rel_notes_link}>Release notes</a>'
        self._version_text += '</h3></p>'


        # info text
        self._info_text = """
            <p>This is an open-source Fusion 360 add-in designed to extend the capabilities of the Electronics workspace. It provides additional tools and utilities for electronic design and documentation.</p>
            
            <p>Contributions are welcome! You can find the source code and contribute at our <a href="https://github.com/DataBitTech/Fusion-EEToolBox">GitHub repository</a>.</p>

            <p>The project is licensed under the MIT License. See the LICENSE file in the repository for more details.</p>

            <p>There are video tutorials available on <a href="https://youtube.com/playlist?list=PLa4BUswmWtMA-BXwLmQtifTjxLAAvYVyo&si=h_H7UBg1845v0NrX">YouTube</a></p>

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

        checkUpdateOnStartup = eetbutil.config_manager.get_global_option('add-in', 'checkUpdateOnStartup', True)
        if checkUpdateOnStartup is None:
            checkUpdateOnStartup = True

        inputs.addTextBoxCommandInput('txtbx_versionText', '', self._version_text, 3, True)
            
        self._checkUpdateChkbx = inputs.addBoolValueInput('chkbx_checkUpdateOnStartup', '   Check for updates on startup', True, '', checkUpdateOnStartup)
        inputs.addTextBoxCommandInput('txtbx_infoText', '', self._info_text, 17, True)


    def on_command_destroy(self, args: adsk.core.CommandEventArgs) -> None:
        """
        Event handler for when the command is destroyed.

        This method is called when the command is closed or destroyed.

        Args:
            args: CommandEventArgs - The event arguments for the command destruction.
        """
        eetbutil.config_manager.store_global_option('add-in', 'checkUpdateOnStartup', self._checkUpdateChkbx.value)
        return super().on_command_destroy(args)
    

    def _get_release_notes_link(self) -> str:
        """
        Retrieves the release notes link for the current version of the add-in.

        Returns:
            str: The URL to the release notes page.
        """
        # Construct the release notes URL
        url = f'https://github.com/DataBitTech/Fusion-EEToolBox/releases/tag/APP_STORE_RELEASE_{self._version.replace(".", "_")}'

        try:
            # Attempt to fetch the URL to check if it exists
            response = urllib.request.urlopen(url)
            if response.getcode() == 200:
                return url
            else:
                return ''
        except urllib.error.HTTPError:
            return ''
        except Exception:
            return ''
