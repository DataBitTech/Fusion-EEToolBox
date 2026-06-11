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

from abc import abstractmethod
import subprocess
import csv
import os
import re
import sys
import io
import shlex
from pathlib import Path
from typing import List, Optional, TypedDict, Callable, Tuple
import adsk.core
from enum import Enum

from .CommandBase import CommandBase
from .Eetb_EditUserScriptCommand.Eetb_EditUserScriptCommand import Eetb_EditUserScriptCommand
from .. import config
from .. import controls as eetbControls
from ..lib import eetbUtils as eetbutil
from ..lib import fusionAddInUtils as futil
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))
import openpyxl

class PartDataExportCommandBase(CommandBase):
    """Base class for part data export commands in the Electronics Extended ToolBox Fusion add-in.

    This abstract base class provides common functionality and structure for commands
    that export part data from Fusion 360 to various formats such as CSV, Excel, or
    other data exchange formats. It handles common operations like data extraction,
    formatting, and file generation while leaving specific export logic to derived classes.

    The class inherits from CommandBase and implements common methods for part data
    handling within the Electronics workspace of Fusion 360. It provides a foundation
    for creating specialized export commands for different data formats and use cases.
    """

    class FilterTypes(Enum):
        FILTER_TYPE_HAS_ATTRIBUTE = 'Has attribute'
        FILTER_TYPE_PART_NAME     = 'Part name'
        FILTER_TYPE_PART_VALUE    = 'Part value'
        FILTER_TYPE_PACKAGE_NAME  = 'Package name'

    class FileExtensions(Enum):
        FILE_EXTENSION_XLSX = 'Excel files (*.xlsx)'
        FILE_EXTENSION_CSV = 'CSV files (*.csv)'
        FILE_EXTENSION_TXT = 'TXT files (*.txt)'
        FILE_EXTENSION_CUSTOM = 'Custom'

    class FormatInfo(TypedDict):
        format_name: str
        built_in: bool
        syncronous: bool
        attribute_mapping: Optional[List[Tuple[str, bool]]]
        function: Callable
        script: str
        default_extension: 'PartDataExportCommandBase.FileExtensions'


    _filter_running_idx: int = 0


    ##############
    # PROPERTIES #
    ##############

    @property
    def supported_formats(self):
        return self._supported_formats

    @property
    def part_data(self):
        return self._part_data
    
    @property
    def package_data(self):
        return self._package_data
    
    @property
    def attribute_list(self):
        return self._attribute_list
    

    ####################
    # PUBLIC INTERFACE #
    ####################

    def __init__(self, command_attributes: CommandBase.MandatoryCommandAttributes, edit_user_script_command: Eetb_EditUserScriptCommand):
        super().__init__(command_attributes)
        self._edit_user_script_command = edit_user_script_command
        self._user_script_temp_input_file_base = os.path.join(config.TEMP_DIR, f'fusion360_{self.command_id}_user_script_input')
        self._supported_formats = []
        self._part_data = []
        self._attribute_list = []
        self._package_data = []

        self.format_selection_input: adsk.core.DropDownCommandInput
        self.filetype_selection_input: adsk.core.DropDownCommandInput
        self.mapping_group: adsk.core.GroupCommandInput
        self.mapping_table: adsk.core.TableCommandInput
        self.warning_label: adsk.core.TextBoxCommandInput
        
        self._add_format_button_input: adsk.core.BoolValueCommandInput
        self._edit_format_button_input: adsk.core.BoolValueCommandInput
        self._remove_format_button_input: adsk.core.BoolValueCommandInput
        self._file_type_sel_label: adsk.core.StringValueCommandInput
        
        self._filter_table: adsk.core.TableCommandInput
        self._add_filter_button_input: adsk.core.BoolValueCommandInput
        self._remove_filter_button_input: adsk.core.BoolValueCommandInput


    def save_config(self, format_name: str, output_dir: str) -> None:
        """Save the current configuration for a specific format to a file.

        This method serializes the configuration data for a given format name
        and saves it to the user configuration file. It includes information 
        about the format, its attributes, filters, and any associated scripts or functions.

        Args:
            format_name (str): The name of the format configuration to save.
            output_dir (str): The directory path where the last export was made.

        Returns:
            None: This method does not return a value.
        """
        eetbutil.config_manager.store_document_option(self.document_id, self.command_id, "last_format", format_name)
        filters = self._collect_filters()
        filters_formatted = [{'filter_type': filter_type, 'regex': regex} for filter_type, regex in filters]
        attribute_mapping = []
        for rowIdx in range (0, self.mapping_table.rowCount):
            output_column_stringinput = self.mapping_table.getInputAtPosition(rowIdx, 0)
            attribute_name_dropdown = self.mapping_table.getInputAtPosition(rowIdx, 1)

            if  not isinstance(output_column_stringinput, adsk.core.StringValueCommandInput) or\
                not isinstance(attribute_name_dropdown, adsk.core.DropDownCommandInput):
                raise TypeError("Unexpected input type in mapping table")

            attribute_mapping.append({'output_column': output_column_stringinput.value, 'attribute': attribute_name_dropdown.selectedItem.name})
        user_selection = {'last_output_dir': output_dir, 'filters': filters_formatted, 'attributes': attribute_mapping}
        eetbutil.config_manager.store_document_option(self.document_id, self.command_id, format_name, user_selection)


    def group_by_parts(self, part_data: list[dict], keys_to_ignore: list[str] = [], consider_all_attributes = False, significant_attributes: list[str] = []) -> list[dict]:
        """
        Groups part data by part number, aggregating attributes from multiple entries.

        This method takes a list of part data dictionaries and groups them by the 'part_number' key.
        For each unique part number, it creates a single dictionary that contains all attributes
        from the original entries, with duplicate attributes merged into lists. Attributes specified
        in `keys_to_ignore` are ignored during the grouping process. The method ensures that
        part data is consolidated for easier processing and export, especially when dealing with
        multiple instances of the same part in a design.
        Args:
            part_data (list[dict]): A list of dictionaries, where each dictionary represents
                                    a part with its attributes as key-value pairs. Each dictionary
                                    must contain a 'part_number' key for grouping.
            keys_to_ignore (list[str], optional): A list of attribute names to exclude from
                                                 the grouping process. Defaults to an empty list.

        Returns:
            list[dict]: A list of dictionaries, where each dictionary represents a unique part
                        with its attributes consolidated. Attributes that appear multiple times
                        are stored as lists, while unique attributes are stored as single values.
        """
        group_dict: dict[str, tuple[str, int, dict]] = {}
        # extend the keys to ignore
        keys_to_ignore.append('name')
        for part in part_data:
            designator = part.get("name", "")
            serialData = self._serialize_part_data(part, keys_to_ignore, consider_all_attributes, significant_attributes)
            if serialData not in group_dict.keys():
                group_dict[serialData] = (designator, 1, part)
            else:
                (part_list, count, part_dict) = group_dict[serialData]
                part_list += ', ' + designator
                count += 1
                group_dict[serialData] = (part_list, count, part_dict)

        grouped_data = []
        for (part_list, count, part_dict) in group_dict.values():
            part_dict['name'] = part_list
            part_dict['__quantity__'] = count
            grouped_data.append(part_dict)
        return grouped_data


    def add_supported_format(self, format_name: str, attributeMappings: Optional[list[tuple[str, bool]]], 
                             function: Callable, default_extension: FileExtensions = FileExtensions.FILE_EXTENSION_XLSX) -> None:
        """Add a new supported format to the export command.

        This method registers a new export format with the command, specifying
        the format name, attribute mappings, the function to handle the export,
        and the default file extension for the format.

        Args:
            format_name (str): The name of the format to be added.
            attributeMappings (list[tuple[str, bool]]): A list of tuples where each
                tuple contains an attribute name and a boolean indicating if it's required.
            function (Callable): The function that will be called to perform the export.
            default_extension (FileExtensions, optional): The default file extension
                for this format. Defaults to FILE_EXTENSION_XLSX.
        """
        format_info: PartDataExportCommandBase.FormatInfo = {
            'format_name': format_name,
            'built_in': True,
            'syncronous': True,
            'attribute_mapping': attributeMappings,
            'function': function,
            'script': '',
            'default_extension': default_extension
        }
        self._supported_formats.append(format_info)


    @abstractmethod
    def get_user_script_input_data(self, filtered_part_data: list[dict], output_format: str) -> list[list[str]]:
        """Retrieve input data for user scripts based on filtered part data and output format.

        This method prepares the input data that will be passed to user-defined scripts
        during the export process. It processes the filtered part data and formats it
        according to the specified output format, ensuring that the data is structured
        in a way that user scripts can easily consume and manipulate. This method must be 
        implemented by derived classes to provide output type (BOM, CPL, etc) specific handling
        of the part data for user scripts.

        Args:
            filtered_part_data (list[dict]): A list of dictionaries containing part data
                                             that has already been filtered based on
                                             the configured filter criteria.
            output_format (str): The name of the output format for which the data is
                                being prepared. This determines how the data should be
                                structured for the user script.

        Returns:
            list[list[str]]: A list of lists, where each inner list represents a row
                            of data to be passed to the user script. Each inner list
                            contains string values corresponding to the columns of data
                            required by the script for the specified output format.
        """
        raise NotImplementedError("Subclasses must implement get_user_script_input_data method")


    def stop(self) -> None:
        """Clean up temporary files here in case of async calls were used

        This method is overrides tha base class' function, for more info see the base class

        Returns:
            None: This method does not return a value.
        """
        # Clean up temporary user script input file if it exists
        temp_output_files = [f"{self._user_script_temp_input_file_base}.csv", f"{self._user_script_temp_input_file_base}.txt"]
        for temp_file in temp_output_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError as e:
                    # Log the error if needed, but don't stop execution
                    pass
        
        super().stop()


    ##################
    # EVENT HANDLERS #
    ##################

    def on_command_created(self, args: adsk.core.CommandCreatedEventArgs):
        """
        Event handler for when the command is created.
        Initializes the UI elements and sets up the command interface for part data export.

        This method is called when the command is first created in Fusion 360. It sets up
        the user interface elements including dropdowns for format selection, file type
        selection, mapping tables for attribute mapping, filter tables, and buttons for
        managing formats and filters. It also reads the part and package data structures
        (note that they can't be read in later event handlers) and sets up the initial 
        state of the command interface.
        Args:
            args: CommandCreatedEventArgs containing the command creation arguments
        """
        super().on_command_created(args)
        if self._supported_formats.count == 0:
            raise NotImplementedError("No supported formats are configured for this command.")

        try:
            cmd = args.command
            inputs = cmd.commandInputs

            # retrieve some data
            eagleData = self.get_eagle_data([{'type': eetbutil.ExportDataType.ATTRIBUTE_LIST.value, 'args': []}, 
                                             {'type': eetbutil.ExportDataType.PART_LIST.value, 'args': []}])
            self._attribute_list = [attr for attr in eagleData['attribute_list'] if attr not in ['NAME', 'VALUE']]
            part_list = eagleData.get(eetbutil.ExportDataType.PART_LIST.value, [])
            eagleData = self.get_eagle_data([{'type': eetbutil.ExportDataType.PART_DATA.value, 'args': part_list}, 
                                             {'type': eetbutil.ExportDataType.PACKAGE_DATA.value, 'args': []}])
            self._part_data = eagleData.get(eetbutil.ExportDataType.PART_DATA.value, [])
            self._package_data = eagleData.get(eetbutil.ExportDataType.PACKAGE_DATA.value, [])

            # create UI
            self._create_UI(cmd, inputs)

            # Set command properties
            cmd.isRepeatable = False
            cmd.isExecutedWhenPreEmpted = False

            self.local_handlers.append(futil.add_handler(cmd.inputChanged, self.on_command_input_changed))
            self.local_handlers.append(futil.add_handler(cmd.validateInputs, self.on_validate_inputs))
            
        except Exception as e:
            self.log_error_to_ui(f"Error creating command: {self.get_error_reason()}")


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

        inputsOK = True
        for input in inputs:
            if isinstance(input, adsk.core.StringValueCommandInput):
                if 'regex' in input.id:
                    try:
                        re.compile(input.value)
                        input.isValueError = False
                    except re.error as e:
                        inputsOK = False
                        input.isValueError = True

        eventArgs.areInputsValid = inputsOK   # False disables OK button


    def on_format_selection_input_changed(self, inputs: adsk.core.CommandInputs):
        """Handles changes to the format selection input.

        This method is triggered when the user selects a different export format
        from the dropdown menu. It updates the UI to reflect the selected format's
        properties, such as the default file extension, and refreshes the attribute
        mapping table to show the appropriate columns and available attributes for
        the selected format. It also loads the last used mapping and filters from
        the user configuration file, if possible

        Args:
            inputs (adsk.core.CommandInputs): The command inputs object containing
                                            all UI elements for the command.

        Returns:
            None: This method does not return a value.
        """
        format_index = self.get_selected_format_index()
        default_extension = self._supported_formats[format_index]['default_extension']
        is_user_script = self._supported_formats[format_index]['built_in'] == False
        is_custom_format = default_extension == PartDataExportCommandBase.FileExtensions.FILE_EXTENSION_CUSTOM.value
        self._remove_format_button_input.isEnabled = is_user_script
        self._edit_format_button_input.isEnabled = is_user_script
        self.filetype_selection_input.isVisible = not is_user_script and not is_custom_format
        self._file_type_sel_label.isVisible = not is_user_script and not is_custom_format
        self.mapping_group.isVisible = not is_user_script and self._supported_formats[format_index]['attribute_mapping'] is not None
        self.warning_label.isVisible = False
        
        # Find and select the default format item
        if not is_user_script and not is_custom_format:
            for item in self.filetype_selection_input.listItems:
                if item.name == default_extension:
                    item.isSelected = True
                    break
        
        # set up filters
        self._filter_table.clear()
        # check if we can restore some previously used options
        selected_format = self.format_selection_input.selectedItem.name
        user_selection = eetbutil.config_manager.get_document_option(self.document_id, self.command_id, selected_format)
         # Reverse mapping from string value to enum member
        filter_type_map = {member.value: member for member in PartDataExportCommandBase.FilterTypes}
        if user_selection and 'filters' in user_selection:
            for filter in user_selection.get('filters', []):
                if filter['filter_type'] in filter_type_map:
                    self._add_new_filter(inputs, filter_type_map[filter['filter_type']], filter['regex'])
        self._remove_filter_button_input.isEnabled = self._filter_table.rowCount > 0

        # set up attribute mapping
        self.mapping_table.clear()

        attribute_mapped_column_names = self._supported_formats[format_index]['attribute_mapping']
        if attribute_mapped_column_names is not None:
            for (column_name, isOptional) in attribute_mapped_column_names:
                self._add_attribute_mapping(inputs, column_name, isOptional)

        # try to restore the attribute mapping
        if user_selection and 'attributes' in user_selection:
            attribute_mapping = user_selection['attributes']
            for mapping in attribute_mapping:
                # Find the row with the matching bom_column
                for rowIdx in range(0, self.mapping_table.rowCount):
                    label_input = self.mapping_table.getInputAtPosition(rowIdx, 0)
                    if label_input is None or not isinstance(label_input, adsk.core.StringValueCommandInput):
                        raise TypeError("Unexpected input type for label_input")  # This should never happen
                        
                    if label_input and label_input.value == mapping['output_column']:
                        # Check if the attribute exists in our attribute_list
                        if mapping['attribute'] in self.attribute_list:
                            dropdown_input = self.mapping_table.getInputAtPosition(rowIdx, 1)
                            if dropdown_input is None or not isinstance(dropdown_input, adsk.core.DropDownCommandInput):
                                raise TypeError("Unexpected input type for dropdown_input")  # This should never happen
                            
                            # Set the dropdown to the stored attribute
                            for i in range(dropdown_input.listItems.count):
                                if dropdown_input.listItems[i].name == mapping['attribute']:
                                    dropdown_input.listItems[i].isSelected = True
                                    break
                        break


    def on_command_input_changed(self, args: adsk.core.InputChangedEventArgs):
        """
        Event handler for when a command input changes.

        This method handles changes to various UI elements in the command, such as
        format selection, filter additions/removals, and user script management.
        It updates the UI state and handles the logic for different input types.

        Args:
            args (adsk.core.InputChangedEventArgs): The event arguments containing
                information about the input that changed.
        """
        built_in_format_count = self._built_in_format_count()
        format_index = self.get_selected_format_index()
        
        # format selection dropdown
        if args.input == self.format_selection_input:
            self.on_format_selection_input_changed(args.inputs)
        
        # add filter button
        elif args.input == self._add_filter_button_input and self._add_filter_button_input.value:
            self._add_filter_button_input.value = False
            self._add_new_filter(args.inputs)
            self._remove_filter_button_input.isEnabled = True

        #remove filter button
        elif args.input == self._remove_filter_button_input and self._remove_filter_button_input.value:
            self._remove_filter_button_input.value = False
            if self._filter_table.selectedRow >= 0:
                self._filter_table.deleteRow(self._filter_table.selectedRow)
            else:
                self._filter_table.deleteRow(self._filter_table.rowCount - 1)
            self._remove_filter_button_input.isEnabled = self._filter_table.rowCount > 0

        # add user script as format
        elif args.input == self._add_format_button_input and self._add_format_button_input.value:
            self._add_format_button_input.value = False
            self._edit_user_script_command.show_user_format_editor(self.command_id, -1, [format_cfg['format_name'] for format_cfg in self._supported_formats])
        
        # edit user script
        elif args.input == self._edit_format_button_input and self._edit_format_button_input.value:
            self._edit_format_button_input.value = False
            script_index = format_index - built_in_format_count
            selected_format = self.format_selection_input.selectedItem.name
            # clear the non-built-in formats, they will be added again on the next on_command_create()
            self._supported_formats = self._supported_formats[:built_in_format_count]
            self._edit_user_script_command.show_user_format_editor(self.command_id, 
                                                                   script_index, 
                                                                   [format_cfg['format_name'] for format_cfg in self._supported_formats if format_cfg['format_name'] != selected_format])

        # remove user script
        elif args.input == self._remove_format_button_input and self._remove_format_button_input.value:
            self._remove_format_button_input.value = False
            script_index = format_index - built_in_format_count
            if script_index >= 0:
                user_scripts = self._get_user_scripts()
                user_scripts.pop(script_index)
                self._save_user_scripts(user_scripts)

                self._supported_formats.pop(format_index)
                self._populate_format_dropdown()



    def on_command_execute(self, args: adsk.core.CommandEventArgs):
        """
        Event handler for when the command is executed.

        This method is called when the user clicks the OK button in the command dialog.
        It orchestrates the entire export process, including:
        - Collecting the selected format and file type
        - Applying filters to the part data
        - Gathering user script input data
        - Executing the appropriate export function for the selected format
        - Saving the configuration for future use

        Args:
            args (adsk.core.CommandEventArgs): The event arguments containing information
                about the command execution, including the command object itself.
        """
        super().on_command_execute(args)
        try:
            # get the selected format
            format_index = self.get_selected_format_index()

            # first filter the parts
            filtered_part_data = self._filter_components(self.part_data)

            # then get it in a tabulated format
            fabhouse_data = self._supported_formats[format_index]['function'](self.format_selection_input.selectedItem.name, filtered_part_data)

            # for user scripts and custom file extensions nothing more to do
            if self._supported_formats[format_index]['built_in'] and self._supported_formats[format_index]['default_extension'] != PartDataExportCommandBase.FileExtensions.FILE_EXTENSION_CUSTOM:
                self._save_results_to_file(fabhouse_data)
            
        except Exception as e:
            self.log_error_to_ui(f"Error creating command: {self.get_error_reason()}")


    #####################
    # ATTRIBUTE MAPPING #
    #####################

    def get_mapped_attribute_values(self, column_names: list[tuple[str, bool]], component_attributes: list[dict]) -> list[str]:
        """Retrieve attribute values for a list of column names from component attributes.

        This method takes a list of column names (which may include optional flags) and a list
        of component attributes, and returns a list of attribute values corresponding to those
        column names. For optional columns where 'None' is selected by the user, it returns an
        empty string. For required columns, it also returns an empty string if no matching
        attribute is found.

        Args:
            column_names (list[tuple[str, bool]]): A list of tuples where each tuple contains
                a column name (str) and a boolean indicating if it's optional (True) or required (False).
            component_attributes (list[dict]): A list of dictionaries representing the attributes
                of a specific component, where each dictionary contains attribute names as keys and their
                corresponding values.

        Returns:
            list[str]: A list of attribute values corresponding to the column names. If a column
                is required and no matching attribute is found, or if a column is optional and
                'None' is selected by the user, an empty string is returned for that column.
        """
        attr_values = [''] * len(column_names)
        for attr in component_attributes:
            for i in range(len(column_names)):
                (column_name, isOptional) = column_names[i]
                selected_attribute_name = self.get_selected_attribute(column_names[i])
                if not (isOptional and selected_attribute_name == 'None') and attr['name'] == selected_attribute_name:
                    attr_values[i] = attr['value']
        return attr_values


    def get_selected_attribute(self, bom_column_name_def: tuple[str, bool]) -> str:
        """Retrieve the name of the selected attribute mapping for a given BOM column.

        This method looks up the name of the attribute selected by the user in the
        attribute mapping area for a given output column.

        Args:
            bom_column_name_def (tuple[str, bool]): A tuple where the first element
                is the column name (str) and the second element is a boolean flag
                indicating if the column is optional (True) or required (False).

        Returns:
            str: The attribute name selected by the user for the output column
        """
        (bom_column_name, isOptional) = bom_column_name_def
        # Iterate through all rows in the mapping table
        for rowIdx in range(0, self.mapping_table.rowCount):
            # Get the label input (first column)
            label_input = self.mapping_table.getInputAtPosition(rowIdx, 0)
            if label_input is None or not isinstance(label_input, adsk.core.StringValueCommandInput):
               raise TypeError(f"Unexpected input type for the attribute mapping row {rowIdx}, column 0")

            if label_input.value == bom_column_name:
                # Get the dropdown input (second column)
                dropdown_input = self.mapping_table.getInputAtPosition(rowIdx, 1)
                if dropdown_input is None or not isinstance(dropdown_input, adsk.core.DropDownCommandInput):
                    raise TypeError(f"Unexpected input type for the attribute mapping row {rowIdx}, column 1")
                return dropdown_input.selectedItem.name
        # If no matching row is found, return an empty string
        return ""


    ###############################################################################################
    #                          P R I V A T E   F U N C T I O N S                                  #
    ###############################################################################################

    ###############
    # UI HANDLING #
    ###############

    def _populate_format_dropdown(self):
        """Populates the format selection dropdown with supported formats.

        This private method clears the existing items in the format selection dropdown
        and adds all currently supported formats. It ensures that built-in formats are
        added first, followed by any user-defined formats that have been added via the
        user script editor. The method also sets the first item in the dropdown as the
        selected item if the dropdown is empty.

        Returns:
            None: This method does not return a value.
        """
        self.format_selection_input.listItems.clear()
        for format in self._supported_formats:
            self.format_selection_input.listItems.add(format['format_name'], False)
        self.format_selection_input.listItems[0].isSelected = True


    def _create_UI(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs) -> None:
        """Create the user interface elements for the part data export command.

        This private method sets up all the UI elements for the command, including:
        - Format selection dropdown
        - File type selection dropdown
        - Attribute mapping table
        - Filter table
        - Buttons for managing formats and filters
        - Warning label

        The method also initializes the UI with either default values or last used 
        values saved in the user configuration and sets up the necessary event handlers
        for the UI elements.

        Args:
            command (adsk.core.Command): The Fusion 360 command object for which
                the UI is being created.
            inputs (adsk.core.CommandInputs): The command inputs collection where
                the UI elements will be added.

        Returns:
            None: This method does not return a value.
        """
        icon_path_add = os.path.join(config.EETB_COMMON_ICON_DIR, 'Add')
        icon_path_edit = os.path.join(config.ELECTRON_COMMON_ICON_DIR, 'EditShortcut')
        icon_path_remove = os.path.join(config.ELECTRON_COMMON_ICON_DIR, 'Delete')
        
        format_label = inputs.addStringValueInput('format_label', '', 'Select output format')
        format_label.isReadOnly = True
        format_label.isFullWidth = True
        format_table = inputs.addTableCommandInput('format_selection_table', 'Format', 5, '5:10:1:1:1')
        format_table.maximumVisibleRows = 2
        format_table.tablePresentationStyle = adsk.core.TablePresentationStyles.transparentBackgroundTablePresentationStyle # type: ignore
        
        # create labels
        format_sel_label = inputs.addStringValueInput('format_selection_label', '', 'Format type')
        format_sel_label.isReadOnly = True
        self._file_type_sel_label = inputs.addStringValueInput('filetype_selection_label', '', 'File type')
        self._file_type_sel_label.isReadOnly = True
        # Create selection inputs
        self.format_selection_input = inputs.addDropDownCommandInput('format_selection','Format',adsk.core.DropDownStyles.TextListDropDownStyle) # type: ignore
        self.format_selection_input.tooltip = 'Select an output format'
        self.filetype_selection_input = inputs.addDropDownCommandInput('filetype_selection','File type',adsk.core.DropDownStyles.TextListDropDownStyle) # type: ignore
        self.filetype_selection_input.tooltip = 'Select a file format'
        for filetype in PartDataExportCommandBase.FileExtensions:
            if filetype != PartDataExportCommandBase.FileExtensions.FILE_EXTENSION_CUSTOM:
                self.filetype_selection_input.listItems.add(filetype.value, False)
        self.filetype_selection_input.listItems[0].isSelected = True

        # create the image buttons
        self._add_format_button_input = inputs.addBoolValueInput('add_format_img', '', False, icon_path_add)
        self._add_format_button_input.tooltip = 'Add a user scripted format'
        self._edit_format_button_input = inputs.addBoolValueInput('edit_format_img', '', False, icon_path_edit)
        self._edit_format_button_input.tooltip = 'Edit user scripted format'
        self._edit_format_button_input.isEnabled = False
        self._remove_format_button_input = inputs.addBoolValueInput('remove_format_img', '', False, icon_path_remove)
        self._remove_format_button_input.tooltip = 'Remove user scripted format'
        self._remove_format_button_input.isEnabled = False
        format_table.addCommandInput(format_sel_label, 0, 0)
        format_table.addCommandInput(self.format_selection_input, 0, 1)
        format_table.addCommandInput(self._add_format_button_input, 0, 2)
        format_table.addCommandInput(self._edit_format_button_input, 0, 3)
        format_table.addCommandInput(self._remove_format_button_input, 0, 4)
        format_table.addCommandInput(self._file_type_sel_label, 1, 0)
        format_table.addCommandInput(self.filetype_selection_input, 1, 1, 0, 3)

        # add all predefined and any user-defined formats
        user_scripts = self._get_user_scripts()
        if user_scripts:
            for script in user_scripts:
                new_format : PartDataExportCommandBase.FormatInfo = {
                    'format_name': script['name'],
                    'built_in': False, 
                    'syncronous': script['synchronous'],
                    'attribute_mapping': None,
                    'function': self._execute_user_script, 
                    'script': script['cmd'],
                    'default_extension': self.FileExtensions.FILE_EXTENSION_CSV
                }
                if new_format not in self._supported_formats:
                    self._supported_formats.append(new_format)
        self._populate_format_dropdown()

        # add an optional warning label - hidden by default
        self.warning_label = inputs.addTextBoxCommandInput('warning_label', '', '<b>Bold</b>', 1, True)
        self.warning_label.isVisible = False

        # present a table to be able to map some attributes
        self.mapping_group = inputs.addGroupCommandInput('mapping_group', 'Attribute mapping')
        self.mapping_help = self.mapping_group.children.addTextBoxCommandInput('mapping_help', '', '', 2, True)
        self.mapping_help.isFullWidth = True
        self.mapping_table = self.mapping_group.children.addTableCommandInput('mapping_table', 'Attribute mapping table', 2, '2:3')
        # this table is filled out dynamically in the subclasses

        # add a group for the component filter options
        filter_group = inputs.addGroupCommandInput('filter_group', 'Component filter')
        filter_group.tooltip = 'Filter out components from the output'
        self._filter_help = filter_group.children.addTextBoxCommandInput('filter_help', '', 'Exclude components from the output matching any of the filters', 2, True)
        self._filter_help.isFullWidth = True

        self._filter_table = filter_group.children.addTableCommandInput('filter_table', 'Component filter table', 3, '3:1:7')
        self._filter_table.minimumVisibleRows = 3
        self._filter_table.maximumVisibleRows = 6
        self._filter_table.columnSpacing = 1
        self._filter_table.rowSpacing = 1
        self._filter_table.tablePresentationStyle = adsk.core.TablePresentationStyles.itemBorderTablePresentationStyle # type: ignore
        self._filter_table.hasGrid = False

        self._add_filter_button_input = inputs.addBoolValueInput('add_filter_row', 'Add filter', False, icon_path_add, False)
        self._remove_filter_button_input = inputs.addBoolValueInput('remove_filter_row', 'Remove filter', False, icon_path_remove, False)
        self._filter_table.addToolbarCommandInput(self._add_filter_button_input)
        self._filter_table.addToolbarCommandInput(self._remove_filter_button_input)

        # try to restore the last used format and its options
        last_format = eetbutil.config_manager.get_document_option(self.document_id, self.command_id, "last_format")
        if last_format and any(format['format_name'] == last_format for format in self._supported_formats):
            selected_format_item = next((item for item in self.format_selection_input.listItems if item.name == last_format), None)
            if selected_format_item:
                selected_format_item.isSelected = True
        self.on_format_selection_input_changed(inputs)


    #############
    # FILTERING #
    #############

    def _add_new_filter(self, inputs: adsk.core.CommandInputs, type: FilterTypes = FilterTypes.FILTER_TYPE_HAS_ATTRIBUTE, regex = '') -> None:
        """Add a new filter row to the filter table.

        This private method creates a new row in the filter table with the specified
        filter type and regular expression. It adds the row to the table and sets up
        the necessary UI elements for the filter, including a dropdown for the filter
        type and a string input for the regular expression.

        Args:
            inputs (adsk.core.CommandInputs): The command inputs collection where
                the filter table is located.
            type (FilterTypes, optional): The type of filter to add. Defaults to
                FILTER_TYPE_HAS_ATTRIBUTE.
            regex (str, optional): The regular expression to use for the filter.
                Defaults to an empty string.

        Returns:
            None: This method does not return a value.
        """
        num_filters = self._filter_table.rowCount
        filter_type_values = [member.value for member in PartDataExportCommandBase.FilterTypes]
        type_dropdown = inputs.addDropDownCommandInput(f'filter_type_{num_filters}', '', adsk.core.DropDownStyles.TextListDropDownStyle) # type: ignore
        for filter_type in filter_type_values:
            type_dropdown.listItems.add(filter_type, filter_type == PartDataExportCommandBase.FilterTypes.FILTER_TYPE_HAS_ATTRIBUTE.value)
        selected_filter_type_item = next((item for item in type_dropdown.listItems if item.name == type.value), None)
        if selected_filter_type_item:
            selected_filter_type_item.isSelected = True
        regex_input = inputs.addStringValueInput(f'regex_input_{self._filter_running_idx}', '', regex)
        regex_picture = inputs.addImageCommandInput(f'regex_image', '', os.path.join(config.EETB_COMMON_ICON_DIR, 'RegEx', 'regex_small.png'))
        self._filter_running_idx += 1

        self._filter_table.addCommandInput(type_dropdown, num_filters, 0)
        self._filter_table.addCommandInput(regex_picture, num_filters, 1)
        self._filter_table.addCommandInput(regex_input, num_filters, 2)
        

    def _collect_filters(self) -> list[tuple[str, str]]:
        """
        Collects the filters defined in the UI.

        This private method iterates through all rows in the filter table and collects
        the filter type and regular expression for each row. It returns a list of tuples,
        where each tuple contains the filter type (as a string) and the regular expression
        (as a string) for a single filter.

        Returns:
            list[tuple[str, str]]: A list of tuples, where each tuple contains the filter
                type (str) and the regular expression (str) for a filter defined in the UI.
        """
        filters = []
        for filter_row in range(self._filter_table.rowCount):
            filter_type = self._filter_table.getInputAtPosition(filter_row, 0)
            regex = self._filter_table.getInputAtPosition(filter_row, 2)
            if isinstance(filter_type, adsk.core.DropDownCommandInput) and isinstance(regex, adsk.core.StringValueCommandInput):
                filters.append((filter_type.selectedItem.name, regex.value))
        return filters


    def _filter_components(self, unfiltered_cpl: list[dict]) -> list[dict]:
        """
        Filters the unfiltered component data based on the filters defined in the UI.

        Args:
            unfiltered_cpl (list[dict]): The unfiltered component data.

        Returns:
            list[dict]: The filtered component data.
        """
        filters = self._collect_filters()

        filtered_cpl = unfiltered_cpl.copy()
        for component in unfiltered_cpl:
            exclude_component = False
            for filter_type, regex in filters:
                if filter_type == PartDataExportCommandBase.FilterTypes.FILTER_TYPE_HAS_ATTRIBUTE.value:
                    for attribute in component.get('attributes', []):
                        if attribute['name'] not in ['NAME', 'VALUE'] and re.match(regex, attribute['name']):
                            exclude_component = True
                            break
                elif filter_type == PartDataExportCommandBase.FilterTypes.FILTER_TYPE_PART_NAME.value:
                    if re.match(regex, component['name']):
                        exclude_component = True
                        break
                elif filter_type == PartDataExportCommandBase.FilterTypes.FILTER_TYPE_PART_VALUE.value:
                    if re.match(regex, component['value']):
                        exclude_component = True
                        break
                elif filter_type == PartDataExportCommandBase.FilterTypes.FILTER_TYPE_PACKAGE_NAME.value:
                    if re.match(regex, component['package']):
                        exclude_component = True
                        break

            if exclude_component:
                filtered_cpl.remove(component)

        return filtered_cpl
    

    #####################
    # OUTPUT GENERATION #
    #####################

    def format_data_by_extension(self, data: list[list[str]], extension_filter) -> bytes:
        """Format the provided data according to the specified file extension filter.

        This method takes a list of dictionaries representing data and formats it
        into bytes based on the provided file extension filter. It supports various
        output formats such as CSV, Excel, and JSON, and returns the formatted data
        as a bytes object suitable for writing to a file.

        Args:
            data (list[dict]): A list of dictionaries containing the data to be formatted.
            extension_filter (str): The file extension filter that determines the output format.
                                    Supported extensions include '.csv', '.xlsx', and '.json'.

        Returns:
            bytes: The formatted data as a bytes object.
        """
        if PartDataExportCommandBase.FileExtensions.FILE_EXTENSION_CSV.value == extension_filter:
            output = io.StringIO()
            writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_ALL)
            for row in data:
                writer.writerow(row)
            return output.getvalue().encode('utf-8')
        elif PartDataExportCommandBase.FileExtensions.FILE_EXTENSION_TXT.value == extension_filter: 
            max_len = [max(len(str(item[i])) for item in data) for i in range(len(data[0]))]
            formatted_data = [] 
            for item in data: 
                formatted_item = [str(item[i]).ljust(max_len[i]) for i in range(len(item))] 
                formatted_data.append('\t'.join(formatted_item)) 
            return '\n'.join(formatted_data).encode('utf-8')
        elif PartDataExportCommandBase.FileExtensions.FILE_EXTENSION_XLSX.value == extension_filter:
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            if sheet is not None:
                for row in data:
                    sheet.append(row)
            with io.BytesIO() as output:
                workbook.save(output)
                return output.getvalue()
        else:
            raise ValueError(f"Unsupported file extension: {extension_filter}")


    def _save_results_to_file(self, data: list[list[str]]):
        """Save the formatted data to a file.

        This private method takes the formatted data and saves it to a file using the
        selected file type and format. It prompts the user to select a file location
        and name, and then writes the data to the specified file using the appropriate
        file extension and encoding.

        Args:
            data (list[list]): The formatted data to be saved to a file.

        Returns:
            None: This method does not return a value.
        """
        format_index = self.get_selected_format_index()
        format_name = self._supported_formats[format_index]['format_name']
        extension_filter = self.filetype_selection_input.selectedItem.name

        # Get the last used output file from ConfigManager
        user_selection = eetbutil.config_manager.get_document_option(self.document_id, self.command_id, format_name)
        
        # Create a file dialog for saving results
        fileDialog = self.ui.createFileDialog()
        fileDialog.isMultiSelectEnabled = False
        fileDialog.title = f"Save {format_name} Results"
        fileDialog.filter = extension_filter
        fileDialog.filterIndex = 0

        if user_selection and 'last_output_dir' in user_selection and os.path.exists(user_selection['last_output_dir']):
            fileDialog.initialDirectory = user_selection['last_output_dir'] if os.path.isdir(user_selection['last_output_dir']) else os.path.dirname(user_selection['last_output_dir'])
        else:
            fileDialog.initialDirectory = str(Path.home())
        
        dialogResult = fileDialog.showSave()
        
        if dialogResult == adsk.core.DialogResults.DialogOK:
            output_file = fileDialog.filename

            # Write the data to the file based on the format
            file_data = self.format_data_by_extension(data, extension_filter)
            try:
                with open(output_file, 'wb') as f:
                    f.write(file_data)

                self.log_to_console(f'Results saved to {output_file}')
                self.save_config(format_name, os.path.dirname(output_file))
            except IOError as e:
                self.ui.messageBox(f"Error writing to file {output_file}: {e}")


    #####################
    # UTILITY FUNCTIONS #
    #####################

    def _serialize_part_data(self, part: dict, keys_to_ignore: list[str] = [], consider_all_attributes = False, significant_attributes: list[str] = []) -> str:
        """Serializes part data into a string representation.

        This method takes a dictionary representing a part and converts it into a
        string representation. It allows for filtering out specific keys, considering
        all attributes, or focusing on significant attributes. The serialized string
        is formatted as a tab-separated list of key-value pairs.

        Args:
            part (dict): A dictionary representing the part data, where keys are
                attribute names and values are attribute values.
            keys_to_ignore (list[str], optional): A list of keys to exclude from
                the serialization. Defaults to an empty list.
            consider_all_attributes (bool, optional): If True, includes all
                attributes in the serialization. If False, only includes attributes
                specified in `significant_attributes`. Defaults to False.
            significant_attributes (list[str], optional): A list of attribute names
                to include in the serialization when `consider_all_attributes` is False.
                Defaults to an empty list.

        Returns:
            str: A tab-separated string representation of the part data, with each
                key-value pair separated by a tab character.
        """
        serialized_data = ''
        for key, value in part.items():
            if key not in keys_to_ignore:
                if key == "attributes" and isinstance(value, list):
                    filtered_attrs = value
                    if not consider_all_attributes:
                        # Only include attributes that are in significant_attributes
                        filtered_attrs = [attr for attr in value if attr.get("name") in significant_attributes]
                    # Sort the filtered attributes by name to ensure consistent ordering
                    filtered_attrs = sorted(filtered_attrs, key=lambda attr: attr.get("name", ""))
                    serialized_data += ",".join([f"{attr['name']}={attr['value']}" for attr in filtered_attrs])
                else:
                    serialized_data += f"{key}={value},"
        # Remove the trailing comma
        if serialized_data.endswith(","):
            serialized_data = serialized_data[:-1]
        return serialized_data


    def get_selected_format_index(self) -> int:
        """Returns the index of the currently selected format in the format selection dropdown.

        This method retrieves the currently selected item from the format selection dropdown
        and returns its index within the list of supported formats. It is used to determine
        which format is currently selected by the user for export.

        Returns:
            int: The index of the currently selected format in the format selection dropdown.
        """
        # get its index in self._supported_formats
        return next((i for i, fmt in enumerate(self._supported_formats) if fmt['format_name'] == self.format_selection_input.selectedItem.name), -1)


    def _built_in_format_count(self) -> int:
        """
        Returns the count of built-in formats in the supported formats list.

        This method iterates through the `_supported_formats` list and counts how many
        formats have the `built_in` attribute set to `True`. This is useful for
        distinguishing between built-in formats and user-defined formats when managing
        the format selection dropdown and related UI elements.

        Returns:
            int: The number of built-in formats in the `_supported_formats` list.
        """
        return sum(1 for fmt in self._supported_formats if fmt['built_in'])
        return sum(1 for fmt in self._supported_formats if fmt['built_in'])
    

    def _add_attribute_mapping(self, inputs: adsk.core.CommandInputs, output_column_name: str, isOptional: bool = False) -> None:
        """Add a new attribute mapping row to the mapping table.

        This private method creates a new row in the attribute mapping table with the
        specified output column name and optional flag. It adds the row to the table
        and sets up the necessary UI elements for the mapping, including a label for
        the output column and a dropdown for selecting the input attribute.

        Args:
            inputs (adsk.core.CommandInputs): The command inputs collection where
                the mapping table is located.
            output_column_name (str): The name of the output column to be mapped.
            isOptional (bool, optional): A flag indicating whether the mapping is
                optional. Defaults to False.

        Returns:
            None: This method does not return a value.
        """
        rowIndex = self.mapping_table.rowCount
        label = inputs.addStringValueInput(f'mapping_bom_label_{rowIndex}', '', output_column_name)
        label.isReadOnly = True
        dropdown = inputs.addDropDownCommandInput(f'mapping_bom_attr_{rowIndex}', '', adsk.core.DropDownStyles.TextListDropDownStyle) # type: ignore
        if isOptional:
            dropdown.listItems.add('None', True)
        for attribute in self.attribute_list:
            dropdown.listItems.add(attribute, False)
        if dropdown.listItems.count > 0 and not isOptional:
            dropdown.listItems[0].isSelected = True
        self.mapping_table.addCommandInput(label, rowIndex, 0)
        self.mapping_table.addCommandInput(dropdown, rowIndex, 1)
        self.mapping_table.minimumVisibleRows = 2
        self.mapping_table.maximumVisibleRows = rowIndex + 1 if rowIndex > 3 else 4
        self.mapping_table.minimumVisibleRows = self.mapping_table.maximumVisibleRows
    

    ################
    # USER SCRIPTS #
    ################

    def _split_user_command(self, user_cmd: str) -> list[str]:
        """Splits a user command string into a list of command parts.

        This method takes a user command string and splits it into individual command
        parts, handling quoted strings properly. It is used to parse user-defined
        commands for execution.

        Args:
            user_cmd (str): The user command string to be split.

        Returns:
            list[str]: A list of command parts, with quotes removed from quoted strings.
        """
        try:
            # Use shlex.split to properly handle quoted strings
            return shlex.split(user_cmd)
        except ValueError as e:
            # If shlex fails, fall back to a simple split
            # This is a basic fallback and may not handle all edge cases
            self.log_to_console(f"Warning: Failed to parse user command with shlex: {e}")
            return user_cmd.split()



    def _get_user_scripts(self) -> list[dict]:
        """Retrieves the list of user-defined scripts from the configuration.

        This private method fetches the user-defined scripts from the configuration
        manager. It returns a list of dictionaries, where each dictionary represents
        a user script with its name, command, and synchronous flag.

        Returns:
            list[dict[str, str, bool]]: A list of dictionaries representing user scripts.
                Each dictionary contains the keys 'name', 'cmd', and 'synchronous'.
        """
        user_scripts = eetbutil.config_manager.get_global_option(self.command_id, "user_scripts")
        return user_scripts if user_scripts is not None else []
    

    def _save_user_scripts(self, user_scripts: list[dict]) -> None:
        """Save the list of user-defined scripts to the configuration.

        This private method takes a list of user-defined scripts and saves it to the
        configuration manager. It updates the global configuration for the command with
        the provided list of user scripts.

        Args:
            user_scripts (list[dict[str, str, bool]]): A list of dictionaries representing
                user scripts. Each dictionary contains the keys 'name', 'cmd', and 'synchronous'.

        Returns:
            None: This method does not return a value.
        """
        eetbutil.config_manager.store_global_option(self.command_id, "user_scripts", user_scripts)


    def _execute_user_script(self, format: str, filtered_part_data: list[dict]):
        """
        Executes a user-defined script to process part data.

        This method takes a format string and a list of filtered part data, and executes
        a user-defined script to process the data. The script is expected to be a command
        that can be executed in a shell environment, and it should accept the part data
        as input and produce the formatted output.

        Args:
            format (str): The name of the format to be used for processing the part data.
            filtered_part_data (list[dict]): A list of dictionaries representing the
                filtered part data to be processed by the user script.

        Returns:
            list[list[str]]: The processed part data as a list of lists of strings.
        """
        # first find the user command details
        user_script_entry = next((entry for entry in self._supported_formats if entry['format_name'] == format), None)
        if not user_script_entry:
            return
        cmd = user_script_entry['script']
        synchronous = user_script_entry['syncronous']

        # now get the output format
        pattern = re.compile('%[^\\s%]+%')
        matches = pattern.findall(cmd)
        output_format = matches[0]

        # now get the tabulated data
        tabulated_data = self.get_user_script_input_data(filtered_part_data, output_format)
        if not tabulated_data:
            return

        # format the tabulated data as per the user's request
        output_file = self._user_script_temp_input_file_base
        if output_format.startswith('%csv_'):
            file_data = self.format_data_by_extension(tabulated_data, 'CSV files (*.csv)')
            output_file += '.csv'
        else:
            file_data = self.format_data_by_extension(tabulated_data, 'TXT files (*.txt)')
            output_file += '.txt'


        try:
            with open(output_file, 'wb') as f:
                f.write(file_data)
            self.log_to_console(f'User script input written to {output_file}')

            # now compile and call the final command
            output_file = '"' + output_file + '"'
            pattern = re.compile(r'%[^\s%]+%')
            final_cmd = re.sub(pattern, lambda _: output_file, cmd)

            self.save_config(format, '')

            # Split the command into arguments, handling quoted strings properly
            cmd_args = self._split_user_command(final_cmd)
            
            if synchronous:
                # Run the command
                subprocess.run(cmd_args)
            else:
                subprocess.Popen(cmd_args)
        except IOError as e:
            self.ui.messageBox(f"Error writing to file {output_file}: {e}")
        except Exception as e:
            self.ui.messageBox(f"An exception occured: {e}")
