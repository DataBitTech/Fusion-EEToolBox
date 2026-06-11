#======================================================
# This software is released under the MIT license:
#
# MIT License
# 
# Copyright (c) 2026 Pal Szabo
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

import os
import adsk.core
import adsk.fusion
import re
from enum import Enum

from ..CommandBase import CommandBase
from ..Eetb_ExecuteEagleScriptCommand.Eetb_ExecuteEagleScriptCommand import Eetb_ExecuteEagleScriptCommand
from ... import config
from ... import controls as eetbControls
from ...lib import eetbUtils as eetbutil
from ...lib import fusionAddInUtils as futil

class Eetb_AttributeRenameDeleteCommand(CommandBase):

    NUM_MAX_DISPLAYED_PARTNAMES: int = 10

    def __init__(self, execute_script_command: Eetb_ExecuteEagleScriptCommand, isRenameCommand: bool):
        if isRenameCommand:
            command_attributes = CommandBase.MandatoryCommandAttributes(
                command_id = f'{config.ADDIN_NAME}_attribute_rename_command_id',
                command_name = 'Bulk rename attributes',
                command_description = 'Rename all occurences of a specific attribute for either the selected or all components',
                json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'),
                icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'rename'))
        else:
            command_attributes = CommandBase.MandatoryCommandAttributes(
                command_id = f'{config.ADDIN_NAME}_attribute_delete_command_id',
                command_name = 'Bulk delete attributes',
                command_description = 'Delete all occurences of a specific attribute for either the selected or all components',
                json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'),
                icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'delete'))
        super().__init__(command_attributes)

        self._script_export_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}.scr')
        self._execute_script_command = execute_script_command
        self._is_rename_command = isRenameCommand
        self._warning_text_rename = '<b>WARNING</b><br>If the attribute is defined in the schematic context, it will fail '\
            'to delete but the new attribute name will be added anyway and it will only be visible in the layout context. In this case '\
            'run this command from the schematics instead.'
        self._warning_text_delete = '<b>WARNING<b><br>Running this command from the layout context can only delete attributes defined '\
            'in this context. If you want to delete attributes defined in the schematic context, run this command from the schematics'


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        eetbControls.add_command_to_panel(config.ELECTRON_SCHEMATIC_ENV_ID, eetbControls.SchematicPanel.ATTRIBUTES_PANEL, commandDefinition)
        eetbControls.add_command_to_panel(config.ELECTRON_LAYOUT_ENV_ID,    eetbControls.LayoutPanel.ATTRIBUTES_PANEL,    commandDefinition)


    ###################
    # EVENT FUNCTIONS #
    ###################

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
        
        # Create face selection input
        self._create_UI(cmd, inputs)
        self._initialize_UI()
        
         # Set command properties
        cmd.isRepeatable = False
        cmd.isExecutedWhenPreEmpted = False

        self.local_handlers.append(futil.add_handler(cmd.inputChanged, self.on_command_input_changed))
        if self._is_rename_command:
            self.local_handlers.append(futil.add_handler(cmd.validateInputs, self.on_validate_inputs))


    def on_command_input_changed(self, args: adsk.core.InputChangedEventArgs):
        """
        Event handler for when a command input changes.

        This method handles changes to various UI elements in the command, such as
        attribute selection and affected component selection

        Args:
            args (adsk.core.InputChangedEventArgs): The event arguments containing
                information about the input that changed.
        """
        if args.input == self._attribute_selector_input or args.input == self._in_selection_input:
            self._update_affected_part_list()


    def on_validate_inputs(self, eventArgs: adsk.core.ValidateInputsEventArgs):
        """Validates the inputs for the command.

        This method is called whenever the command's inputs are changed or validated.
        It performs validation checks on the command's UI elements to ensure that
        all required fields are properly filled and that the values are acceptable
        for the export operation. It updates the UI state and disables the OK button
        if validation fails.

        Args:
            eventArgs: ValidateInputsEventArgs containing the validation event arguments

        Returns:
            None: This method does not return a value.
        """
        if not isinstance(eventArgs.firingEvent.sender, adsk.core.Command):
            raise TypeError("Event sender is not a Command object")
        inputs = eventArgs.firingEvent.sender.commandInputs
        newName = self._new_attribute_input.value
        # 1. It must not be an empty string
        # 2. It may consist of any letters, digits, '_', '#' and '-' and may have any length;
        #    the first character must not be '-'.
        isValidAttributeName = bool(re.match(r'^[a-zA-Z0-9_#][a-zA-Z0-9_#-]*$', newName)) and len(newName) > 0
        self._new_attribute_input.isValueError = not isValidAttributeName
        eventArgs.areInputsValid = isValidAttributeName


    def on_command_execute(self, args: adsk.core.CommandEventArgs):
        """
        Event handler for when the command is executed.

        See the base class method for full details.
        
        Args:
            args: CommandEventArgs
        """

        class DisplayCombination(Enum):
            NONE = "OFF"
            VALUE = "VALUE"
            NAME = "NAME"
            BOTH = "BOTH"

        # Filter the parts in self._parts_data and keep only the ones that have the attribute with the name self._attribute_selector_input.value
        if not self._attribute_selector_input.selectedItem.name:
            return
        selected_attribute = self._attribute_selector_input.selectedItem.name

        new_attribute: str = ''
        if self._is_rename_command:
            new_attribute = self._new_attribute_input.value
        
        filtered_parts = []
        for part in self._parts_data:
            part_attributes = part.get('attributes', [])
            # Check if any of the dicts in part_attributes has a 'name' field equal to the selected attribute name
            if any(attr.get('name') == selected_attribute for attr in part_attributes):
                filtered_parts.append(part)

        # If no parts have the selected attribute, return early
        if not filtered_parts:
            return

        # Sort the filtered parts into sets based on the "first_sheet" field
        parts_by_sheet = {}
        for part in filtered_parts:
            sheet = part.get('first_sheet')
            if sheet not in parts_by_sheet:
                parts_by_sheet[sheet] = []
            parts_by_sheet[sheet].append(part)

        try:
            with open(self._script_export_path, 'w') as f: 
                lastDisplay = DisplayCombination.NONE
                if self._is_rename_command:
                    f.write(f"CHANGE DISPLAY {DisplayCombination.NONE.value};\n")
                
                # Iterate through the parts by sheet
                for sheet, parts in parts_by_sheet.items():
                    f.write(f"EDIT .s{sheet};\n")
                    # Process each part in the sheet
                    for part in parts:
                        part_name = part['name']
                        part_attributes = part.get('attributes', [])

                        f.write(f"ATTRIBUTE {part_name} {selected_attribute} DELETE;\n")
                        
                        if self._is_rename_command:
                            attribute_value = next((attr.get('value') for attr in part_attributes if attr.get('name') == selected_attribute), None)
                            display_name = next((attr.get('display_name') for attr in part_attributes if attr.get('name') == selected_attribute), None)
                            display_value = next((attr.get('display_value') for attr in part_attributes if attr.get('name') == selected_attribute), None)
                            
                            # Determine the display combination based on the presence of display_name and display_value
                            display = DisplayCombination.NONE
                            if display_name and display_value:
                                display = DisplayCombination.BOTH
                            elif display_name:
                                display = DisplayCombination.NAME
                            elif display_value:
                                display = DisplayCombination.VALUE

                            if display != lastDisplay:
                                f.write(f"CHANGE DISPLAY {display.value};\n")
                                lastDisplay = display

                            f.write(f"ATTRIBUTE {part_name} {new_attribute.upper()} '{attribute_value}';\n")
            
            self.log_to_console(f'Successfully generated script at {self._script_export_path}')
            self._execute_script_command.run_script(self._script_export_path)
        except:
            self.log_error_to_ui(CommandBase.get_error_reason())


    def stop(self) -> None:
        """Stops the command and performs any necessary cleanup."""
        try:
            if os.path.exists(self._script_export_path):
                os.remove(self._script_export_path)
        except Exception as e:
            self.log_error_to_ui(f"Error deleting script file: {str(e)}")
        
        super().stop()


    ####################
    # HELPER FUNCTIONS #
    ####################

    def _create_UI(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs):
        """
        Create the face selection input for the command.
        This should be called when setting up the command UI.
        
        Args:
            command: The Command object
            inputs: The CommandInputs collection
        
        Returns:
            The face selection input
        """
        self._attribute_selector_input = inputs.addDropDownCommandInput('dropdown_attribute_to_change', 'Attribute', adsk.core.DropDownStyles.TextListDropDownStyle) # type: ignore
        if self._is_rename_command:
            self._new_attribute_input = inputs.addStringValueInput('strinput_new_attribute_name', 'New name', '')
            self._new_attribute_input.isValueError = True
        self._in_selection_input = inputs.addBoolValueInput('chkbox_selected_only', 'In selection', True, '', False)
        self._affected_components_output = inputs.addTextBoxCommandInput("txtbox_affected_comps", 'Affected parts', '', 3, True)
        warning_text = self._warning_text_rename if self._is_rename_command else self._warning_text_delete
        self._warning_label = inputs.addTextBoxCommandInput('txtbox_warning_label', '', warning_text, 6, True)


    def _initialize_UI(self):
        """Initialize the UI elements for the command.

        This method sets up the dropdown list for layer selection
        and prepares the UI for user interaction.
        """
        if self._app.activeDocument.dataFile.fileExtension == 'fsch':
            self._warning_label.isVisible = False
        requests = [{'type': eetbutil.ExportDataType.ATTRIBUTE_LIST.value, 'args': []},
                    {'type': eetbutil.ExportDataType.PART_LIST.value, 'args': []},
                    {'type': eetbutil.ExportDataType.PART_SELECTION.value, 'args': []}]
        eagleData = self.get_eagle_data(requests)
        self._selected_parts = eagleData[eetbutil.ExportDataType.PART_SELECTION.value]
        self._attribute_list = [attr for attr in eagleData[eetbutil.ExportDataType.ATTRIBUTE_LIST.value] if attr not in ['NAME', 'VALUE']]
        partsData = self.get_part_data(eagleData.get(eetbutil.ExportDataType.PART_LIST.value, []))
        self._parts_data = partsData.get(eetbutil.ExportDataType.PART_DATA.value, [])
        
        if not self._selected_parts:
            self._in_selection_input.isVisible = False
        for attribute in self._attribute_list:
            self._attribute_selector_input.listItems.add(attribute, False)
        if self._attribute_selector_input.listItems.count > 0:
            self._attribute_selector_input.listItems[0].isSelected = True
            self._update_affected_part_list()


    def _update_affected_part_list(self):
        """
        Updates the list of affected parts based on the selected attribute and
        whether the operation should be applied to selected parts only.

        This method is triggered when the attribute selection or the "selected parts only"
        checkbox is changed. It determines which parts will be affected by the
        rename/delete operation and updates the UI text box accordingly.
        """
        # list the affected components
        selected_attribute = self._attribute_selector_input.selectedItem.name
        affected_parts = []
        for part in self._parts_data:
            if self._in_selection_input.value and part['name'] not in self._selected_parts:
                continue
            for attr in part.get('attributes', []):
                if attr.get('name') == selected_attribute:
                    affected_parts.append(part['name'])
                    break  # No need to check further attributes for this part
        
        # Create a string of affected parts
        if len(affected_parts) > Eetb_AttributeRenameDeleteCommand.NUM_MAX_DISPLAYED_PARTNAMES:
            parts_string = ', '.join(affected_parts[:Eetb_AttributeRenameDeleteCommand.NUM_MAX_DISPLAYED_PARTNAMES]) + f' ... +{len(affected_parts) - Eetb_AttributeRenameDeleteCommand.NUM_MAX_DISPLAYED_PARTNAMES} more'
        else:
            parts_string = ', '.join(affected_parts)
        self._affected_components_output.text = parts_string