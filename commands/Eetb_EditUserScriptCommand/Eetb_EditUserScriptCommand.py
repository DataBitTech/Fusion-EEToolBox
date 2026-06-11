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


import re
from typing import TypedDict
import adsk.core
import os

from ... import config
from ..CommandBase import CommandBase
from ...lib import fusionAddInUtils as futil
from ...lib import eetbUtils as eetbutil

class Eetb_EditUserScriptCommand(CommandBase):
    
    class UserScriptConfig(TypedDict):
        name: str
        cmd: str
        synchronous: bool

    def __init__(self):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_edit_user_script_command_id',
            command_name = 'Edit User Script',
            command_description = 'Edit a user defined script call',
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources'),
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'))
        super().__init__(command_attributes)

        self._caller_command_id: str
        self._displayNameInput: adsk.core.StringValueCommandInput
        self._commandLineInput: adsk.core.StringValueCommandInput
        self._synchronousCallInput: adsk.core.BoolValueCommandInput


    def show_user_format_editor(self, callerCmdId: str, userScriptIdx: int, invalidNames: list[str]) -> None:
        """
        Displays the user script editor dialog for modifying a user-defined script.

        This method is responsible for showing the UI dialog that allows users to
        edit the properties of a user script, including its display name, command line,
        and whether it should be called synchronously or asynchronously.

        Args:
            callerCmdId (str): The ID of the command that is calling this editor.
            userScriptIdx (int): The index of the user script in the collection to be edited.
            invalidNames (list[str]): A list of names that are already in use and should not be
                                      allowed for the script's display name.
        """
        self._caller_command_id = callerCmdId
        self._user_script_idx = userScriptIdx
        self._invalid_names = invalidNames
        
        command_definition: adsk.core.CommandDefinition = self.ui.commandDefinitions.itemById(self.command_id)
        if command_definition:
            command_definition.execute()


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """No visible button for this command.
        
        See the base class method for full details.
        """
        pass


    def on_command_execute(self, args: adsk.core.CommandEventArgs):
        """
        Event handler for when the command is executed.

        See the base class method for full details.
        
        Args:
            args: CommandEventArgs
        """
        super().on_command_execute(args)
        displayName = self._displayNameInput.value
        commandLine = self._commandLineInput.value
        isSynchCall = self._synchronousCallInput.value

        user_scripts = self._get_user_scripts()
        if self._user_script_idx < 0: # this is a new user script
            user_scripts.append({'name': displayName, 'cmd': commandLine, 'synchronous': isSynchCall})
        else:
            user_scripts[self._user_script_idx]['name'] = displayName
            user_scripts[self._user_script_idx]['cmd'] = commandLine
            user_scripts[self._user_script_idx]['synchronous'] = isSynchCall
        self._save_user_scripts(user_scripts)
        
        # now display the caller again
        command_definition: adsk.core.CommandDefinition = self.ui.commandDefinitions.itemById(self._caller_command_id)
        if command_definition:
            command_definition.execute()


    def on_command_created(self, args: adsk.core.CommandCreatedEventArgs):
        """
        Event handler for when the command is created.

        See the base class method for full details.
        
        Args:
            args: CommandCreatedEventArgs
        """
        super().on_command_created(args)
        try:
            cmd = args.command
            inputs = cmd.commandInputs
            
            # Create face selection input
            self._create_UI(cmd, inputs)
            self._initialize_UI()

            self.local_handlers.append(futil.add_handler(cmd.validateInputs, self.on_validate_inputs))
            
            # Set command properties
            cmd.isRepeatable = False
            cmd.isExecutedWhenPreEmpted = False
        except Exception as e:
            self.log_error_to_ui(f"Error creating command: {self.get_error_reason()}")


    def on_validate_inputs(self, args: adsk.core.ValidateInputsEventHandler):
        """
        Validates the inputs provided by the user in the command UI.

        This function checks whether the display name and command line inputs
        meet the required criteria. It ensures that the display name is not
        empty and not already in use, and that the command line is not empty.

        Args:
            args: ValidateInputsEventHandler - The event arguments containing
              the command inputs to validate.
        """
        eventArgs = adsk.core.ValidateInputsEventArgs.cast(args)
        inputsValid = True

        # format name must be unique
        if self._displayNameInput.value in self._invalid_names:
            inputsValid = False

        # Find all occurrences of the pattern
        pattern = r'%\b(csv|text)_(parts|values)\b%'
        matches = re.findall(pattern, self._commandLineInput.value)
        if len(matches) != 1:
            inputsValid = False

        eventArgs.areInputsValid = inputsValid   # False disables OK button


    def _create_UI(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs):
        """
        Creates the user interface elements for the script editor dialog.

        This method sets up the input fields for the user script editor, including:
        - A text input for the display name of the script
        - A text input for the command line to be executed
        - A checkbox for specifying if the script should be called synchronously
        - An information text box explaining how to use user scripts

        Args:
            command (adsk.core.Command): The command object to which the UI elements will be added.
            inputs (adsk.core.CommandInputs): The collection of command inputs to which the UI elements will be added.
        """
        self._displayNameInput = inputs.addStringValueInput('display_name_id', 'Display Name')
        self._commandLineInput = inputs.addStringValueInput('command_line_input_id', 'Command line')
        self._synchronousCallInput = inputs.addBoolValueInput('synchronous_call_id', 'Wait until finished', True, "", True)
        explanation_text = "Define how to call your existing script here.<br />" \
                            "<b><i>Display Name</i></b> a unique name that will be added to the list of available formats<br />" \
                            "<b><i>Command line</i></b> the external program/script when you select this format.<br /><br />" \
                            "The raw component data (including all attributes) will be saved to a temporary file that you must pass to your script. For compatibility, it can be formatted in a number of " \
                            "ways that was supported by the bom.ulp in Eagle.<br />" \
                            "<pre>%csv_parts% semicolon separated CSV format, one part per line<br />" \
                            "%csv_values% semicolon separated CSV format, same value parts are grouped into one line<br />" \
                            "%text_parts% tabulated (padded) text format, one part per line<br />" \
                            "%text_values% tabulated (padded) text format, same value parts are grouped into one line<br /></pre>" \
                            "<br />Example:<br />   <i>Display Name</i>: My Script<br />   <i>Command line</i>: C:\\path\\to\\script.exe -input %csv_parts% -output 'C:\\path\\to\\output\\file\\my special format output.xml" \
                            "<br /><br /><b><i>Note</i></b><br />This is an open-source project. If your output format is <b>NOT</b> proprietary, please consider contributing this fabhouse format, so that others can also use it"
        explanation = inputs.addTextBoxCommandInput('explanation_id', '', explanation_text, 23, True)


    def _initialize_UI(self):
        """
        Initializes the user interface elements for the script editor dialog.

        This method sets the initial values for the display name, command line,
        and synchronous call inputs based on the existing user script data.

        Note:
            This method assumes that the UI elements have already been created
            by the `_create_UI` method and that the `_user_script_idx` and
            `_invalid_names` attributes are properly set.
        """
        if self._user_script_idx >= 0:
            user_scripts = self._get_user_scripts()
            if self._user_script_idx < len(user_scripts):
                self._displayNameInput.value = user_scripts[self._user_script_idx]['name']
                self._commandLineInput.value =  user_scripts[self._user_script_idx]['cmd']
                self._synchronousCallInput.value = user_scripts[self._user_script_idx]['synchronous']

    

    def _get_user_scripts(self) -> list[UserScriptConfig]:
        """
        Retrieves the list of user-defined scripts from a JSON file.

        This function reads the user scripts from the user configuration file.

        Returns:
            list[UserScriptConfig]: A list of dictionaries, each representing
              a user script with keys 'name', 'cmd', and 'synchronous'.
        """
        user_scripts = eetbutil.config_manager.get_global_option(self._caller_command_id, "user_scripts")
        return user_scripts if user_scripts is not None else []
    

    def _save_user_scripts(self, user_scripts: list[UserScriptConfig]) -> None:
        """
        Saves the list of user-defined scripts to the user configuration file.
        This function writes the provided list of user scripts to the user
        configuration file, overwriting any existing data.

        Args:
            user_scripts (list[UserScriptConfig]): A list of dictionaries,
              each representing a user script with keys 'name', 'cmd', and
              'synchronous'.
        """
        eetbutil.config_manager.store_global_option(self._caller_command_id, "user_scripts", user_scripts)
