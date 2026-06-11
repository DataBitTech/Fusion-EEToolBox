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

from copy import deepcopy
import adsk.core
import os
from ... import config
from ...lib import fusionAddInUtils as futil
from ...lib import eetbUtils as eetbutil
from ... import controls as eetbControls
from ..CommandBase import CommandBase
from ..Eetb_ScriptAndULPButtonCommand.Eetb_ScriptAndULPButtonCommand import Eetb_ScriptAndULPButtonCommand


class Eetb_DefineUserScriptAndULPButtonCommand(CommandBase):

    def __init__(self):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = "Eetb_DefineUserScriptAndULPButtonCommand",
            command_name = "Define user buttons",
            command_description = "Define buttons for running user scripts and ULPs.",
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources'),
            json_temp_path = os.path.join(config.TEMP_DIR, "userscript_buttons.json"))
        super().__init__(command_attributes)

        self._table: adsk.core.TableCommandInput
        self._add_button: adsk.core.BoolValueCommandInput
        self._remove_button: adsk.core.BoolValueCommandInput
        self._user_commands: list[Eetb_ScriptAndULPButtonCommand] = []


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        self._create_user_commands(config.ELECTRON_SCHEMATIC_ENV_ID,        commandDefinition)
        self._create_user_commands(config.ELECTRON_LAYOUT_ENV_ID,           commandDefinition)
        self._create_user_commands(config.ELECTRON_LIBRARY_DEVICE_ENV_ID,   commandDefinition)
        self._create_user_commands(config.ELECTRON_LIBRARY_FOOTPRINT_ENV_ID,commandDefinition)
        self._create_user_commands(config.ELECTRON_LIBRARY_SYMBOL_ENV_ID,   commandDefinition)


    def stop(self):
        """Stops the command and cleans up any resources."""
        for user_cmd in self._user_commands:
            user_cmd.stop()
        self._user_commands.clear()
        super().stop()


    def on_command_created(self, args: adsk.core.CommandCreatedEventArgs):
        """
        Event handler for when the command is created.

        See the base class method for full details.
        
        Args:
            args: CommandCreatedEventArgs
        """
        super().on_command_created(args)
        
        inputs = args.command.commandInputs

        icon_path_add = os.path.join(config.EETB_COMMON_ICON_DIR, 'Add')
        icon_path_remove = os.path.join(config.EETB_COMMON_ICON_DIR, 'Delete')

        label = inputs.addStringValueInput('user_script_desc', '', 'You can create buttons on the UI for legacy scripts and ULPs')
        label.isReadOnly = True
        label.isFullWidth = True

        self._table = inputs.addTableCommandInput("user_script_table", "User Scripts", 2, "2:3")
        self._table.hasGrid = True
        self._table.tablePresentationStyle = adsk.core.TablePresentationStyles.itemBorderTablePresentationStyle # type: ignore
        self._table.columnSpacing = 1
        self._table.rowSpacing = 1
        self._table.minimumVisibleRows = 3
        self._table.maximumVisibleRows = 8
        
        # Add headers as a non-removable row
        header_button_name = inputs.addStringValueInput("header_button_name", "Button name", "Button name")
        header_button_name.isReadOnly = True
        header_script = inputs.addStringValueInput("header_script", "Script/ULP to run", "Script/ULP to run")
        header_script.isReadOnly = True
        
        self._table.addCommandInput(header_button_name, 0, 0)
        self._table.addCommandInput(header_script, 0, 1)

        self._add_button = inputs.addBoolValueInput('add_script_row', 'Add', False, icon_path_add)
        self._remove_button = inputs.addBoolValueInput('remove_script_row', 'Remove', False, icon_path_remove)
        self._table.addToolbarCommandInput(self._add_button)
        self._table.addToolbarCommandInput(self._remove_button)

        self._load_workspace_settings(inputs)

        self.local_handlers.append(futil.add_handler(args.command.inputChanged, self.on_command_input_changed))
        self.local_handlers.append(futil.add_handler(args.command.validateInputs, self.on_validate_inputs))


    def on_command_input_changed(self, args: adsk.core.InputChangedEventArgs):
        """
        Event handler for when command inputs change.

        This method is called whenever a user interacts with any of the command's inputs.
        It handles the logic for adding and removing rows in the table, as well as
        updating the table contents based on user actions.

        Args:
            args: InputChangedEventArgs containing information about the changed input.
        """
        changed_input = args.input
        if changed_input == self._add_button:
            self._add_button.value = False
            self._add_row(args.inputs)

        elif changed_input == self._remove_button:
            self._remove_button.value = False
            if self._table.selectedRow > 0: # Do not remove header
                self._table.deleteRow(self._table.selectedRow)
            elif self._table.rowCount > 1:
                self._table.deleteRow(self._table.rowCount - 1)

        self._remove_button.isEnabled = self._table.rowCount > 1
        self._update_add_button_state()


    def on_validate_inputs(self, args: adsk.core.ValidateInputsEventArgs):
        """
        Event handler for validating the inputs of the command.

        This method is called to validate the user inputs before the command is executed.
        It ensures that all required fields are filled correctly and that the data is consistent.

        Args:
            args: ValidateInputsEventArgs containing information about the validation state.
        """
        self._update_add_button_state()
        args.areInputsValid = self._add_button.isEnabled   # False disables OK button


    def on_command_execute(self, args: adsk.core.CommandEventArgs):
        """
        Event handler for when the command is executed.

        See the base class method for full details.
        
        Args:
            args: CommandEventArgs
        """
        super().on_command_execute(args)
        self._save_workspace_settings()
        self._create_user_commands(self.ui.activeWorkspace.id, self.ui.commandDefinitions.itemById(self.command_id))


    def on_command_destroy(self, args: adsk.core.CommandEventArgs):
        """
        Event handler for when the command is destroyed.

        See the base class method for full details.
        
        Args:
            args: CommandEventArgs
        """
        super().on_command_destroy(args)


    def _add_row(self, inputs: adsk.core.CommandInputs, button_name: str = "", script_path: str = ""):
        """Adds a new row to the table with inputs for ULP/script configuration.

        This method creates and populates a new row in the table command input with
        fields for specifying whether the entry is for a ULP, a button name, and a script path.
        It also handles the initial state of the row's inputs.

        Args:
            inputs: The CommandInputs object to which the new row will be added.
            is_ulp: A boolean flag indicating if the entry is for a ULP (True) or a script (False).
            button_name: The name to be displayed on the button.
            script_path: The file path to the ULP or script to be executed.
        """
        row = self._table.rowCount
        name_input = inputs.addStringValueInput(f"button_name_{row}", "", button_name)
        script_input = inputs.addStringValueInput(f"script_path_{row}", "", script_path)

        self._table.addCommandInput(name_input, row, 0)
        self._table.addCommandInput(script_input, row, 1)
        
        self._remove_button.isEnabled = self._table.rowCount > 1
        self._update_add_button_state()


    def _update_add_button_state(self):
        """
        Updates the enabled state of the add button based on the current row count.

        This method ensures that the add button is only enabled when the last row 
        is properly filled out.
        """
        if not self._add_button:
            return
            
        if self._table.rowCount <= 1:
            self._add_button.isEnabled = True
            return

        # check each row for valid inputs
        for row in range(1, self._table.rowCount):
            button_name_input = self._table.getInputAtPosition(row, 0)
            script_path_input = self._table.getInputAtPosition(row, 1)

            if isinstance(button_name_input, adsk.core.StringValueCommandInput) and isinstance(script_path_input, adsk.core.StringValueCommandInput):
                is_filled = bool(button_name_input.value and script_path_input.value)
                is_extension_ok = False
                if script_path_input.value:
                    # Extract the first word (treat as a path)
                    first_word = script_path_input.value.strip().split()[0]
                    # Check if it has .scr or .ulp extension
                    _, ext = os.path.splitext(first_word)
                    is_extension_ok = ext.lower() in ['.scr', '.ulp']
                self._add_button.isEnabled = is_filled and is_extension_ok
            else:
                self._add_button.isEnabled = False
            if not self._add_button.isEnabled:
                return


    def _load_workspace_settings(self, inputs: adsk.core.CommandInputs):
        """Loads the workspace-specific settings from the user configuration file and populates the table.

        This method reads the user script button configurations from the user 
        configuration file and adds rows to the table based on the loaded data.
        If the JSON file does not exist or is invalid, it clears the table

        Args:
            inputs: The CommandInputs object used to manage the command's inputs.
        """
        settings = eetbutil.config_manager.get_global_option(self.command_id, "user_scripts")
        if settings:
            for script in settings:
                if script['workspace'] == self._get_workspace_id():
                    self._add_row(inputs, script.get('name', ''), script.get('path', ''))
        
        #if self._table.rowCount <= 1: # Only header exists
        #    self.add_row(inputs) # Add an empty row to start with
            
        self._remove_button.isEnabled = self._table.rowCount > 1
        self._update_add_button_state()


    def _save_workspace_settings(self):
        """
        Saves the current workspace settings to the user configuration file.

        This method collects the current table data, including whether each entry is a ULP or script,
        the button name, and the script path, and saves it to the user configuration file under
        the global 'user_scripts' key. It ensures that the settings are properly structured and saved
        for the current workspace.

        The saved data includes:
        - workspace: The ID of the current workspace
        - is_ulp: Boolean indicating if the entry is for a ULP
        - name: The button name
        - path: The script or ULP file path
        """
        settings = []
        # Start from 1 to skip header row
        for i in range(1, self._table.rowCount):
            button_name_input = self._table.getInputAtPosition(i, 0)
            script_path_input = self._table.getInputAtPosition(i, 1)

            if isinstance(button_name_input, adsk.core.StringValueCommandInput) and \
               isinstance(script_path_input, adsk.core.StringValueCommandInput):
                
                if button_name_input.value and script_path_input.value: #Only save non-empty rows
                    settings.append({
                        'workspace': self._get_workspace_id(),
                        'name': button_name_input.value,
                        'path': script_path_input.value
                    })
        stored_settings = eetbutil.config_manager.get_global_option(self.command_id, "user_scripts", [])
        if stored_settings is not None:
            for stored_script in stored_settings:
                if stored_script['workspace'] != self._get_workspace_id():
                    settings.append(stored_script) #Keep existing scripts from other workspaces

        eetbutil.config_manager.store_global_option(self.command_id, "user_scripts", settings)
        CommandBase.log_to_console(f"Saved {len(settings)} user scripts.")


    def _create_user_commands(self, workspace_id: str, command_definition: adsk.core.CommandDefinition):
        """
        Creates user-defined script/ULP commands for the specified workspace.

        This method iterates through the saved user script configurations and creates
        corresponding command buttons for the given workspace. It ensures that only
        commands relevant to the current workspace are created, and it manages the
        lifecycle of these commands.

        Args:
            workspace_id: The ID of the workspace for which to create commands.
            command_definition: The CommandDefinition object used to create the commands.
        """
        # first clean up the current ones if any
        user_cmds_copy = list.copy(self._user_commands)
        self._user_commands.clear()
        for user_cmd in user_cmds_copy:
            if user_cmd.workspace_id == workspace_id:
                user_cmd.stop()
            else:
                self._user_commands.append(user_cmd) # Keep commands from other workspaces

        # clean up UI
        if workspace_id == config.ELECTRON_SCHEMATIC_ENV_ID:
            panel = eetbControls.SchematicPanel.SCRIPT_PANEL
        elif workspace_id == config.ELECTRON_LAYOUT_ENV_ID:
            panel = eetbControls.LayoutPanel.SCRIPT_PANEL
        else:
            panel = eetbControls.LibraryPanel.SCRIPT_PANEL
        eetbControls.clear_panel(workspace_id, panel)
        eetbControls.add_command_to_panel(workspace_id, panel, command_definition, True)

        user_scripts = eetbutil.config_manager.get_global_option(self.command_id, "user_scripts", [])
        if user_scripts is None:
            return
        for script in user_scripts:
            if script['workspace'] == workspace_id:
                script_path = script.get('path', '')
                first_word = script_path.strip().split()[0]
                _, extension = os.path.splitext(first_word)
                if extension.lower() not in ['.scr', '.ulp']:
                    continue
                user_cmd = Eetb_ScriptAndULPButtonCommand(script.get('name', 'Unknown'), 
                                                          script_path, 
                                                          extension.lower() == '.ulp', 
                                                          workspace_id)
                self._user_commands.append(user_cmd)
                user_cmd.start()
  

    def _get_workspace_id(self) -> str:
        """
        Returns the ID of the current workspace.

        This method retrieves the ID of the currently active workspace in the Fusion 360 UI.
        It is used to determine which workspace-specific script buttons should be loaded or saved.

        Returns:
            str: The ID of the current workspace.
        """
        fusion_workspace = self.ui.activeWorkspace
        workspace = fusion_workspace.id if fusion_workspace else config.ELECTRON_SCHEMATIC_ENV_ID
        return workspace
