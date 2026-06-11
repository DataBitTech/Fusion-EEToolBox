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
import math, os
from pathlib import Path
import adsk.core

from ..CommandBase import CommandBase
from ..PartDataExportCommandBase import PartDataExportCommandBase
from ..Eetb_EditUserScriptCommand.Eetb_EditUserScriptCommand import Eetb_EditUserScriptCommand
from ... import config
from ... import controls as eetbControls
from ...lib import eetbUtils as eetbutil

from .exporters.Eetb_CPLExporterBase import Eetb_CPLExporterBase
from .exporters.Eetb_RawCPLExporter import Eetb_RawCPLExporter
from .exporters.Eetb_EuroCircuitsCPLExporter import Eetb_EuroCircuitsCPLExporter
from .exporters.Eetb_JLCPCBCPLExporter import Eetb_JLCPCBCPLExporter
from .exporters.Eetb_MacrofabCPLExporter import Eetb_MacrofabCPLExporter


class Eetb_ExportCPLDefaultOutputAttribute(Enum):
    ROTATION_FIX = 'Rotation fix'
    HORIZONTAL_FIX = 'Horizontal position fix'
    VERTICAL_FIX = 'Vertical position fix'


class Eetb_ExportCPLDataCommand(PartDataExportCommandBase):

    def __init__(self, edit_user_script_command: Eetb_EditUserScriptCommand):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_export_cpl_data_command_id',
            command_name = 'Export placement data',
            command_description = 'Export component placement data in manufacturer specific formats',
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'),
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources'))
        super().__init__(command_attributes, edit_user_script_command)

        # for now the query unit is always millimeter
        query_unit = eetbutil.LengthUnits.MILLIMETER

        self._default_attribute_mapping: list[tuple[str, bool]] = [
            # column to map to attribute                                optional?
            (Eetb_ExportCPLDefaultOutputAttribute.ROTATION_FIX.value,    True),
            (Eetb_ExportCPLDefaultOutputAttribute.HORIZONTAL_FIX.value,  True),
            (Eetb_ExportCPLDefaultOutputAttribute.VERTICAL_FIX.value,    True)
        ]

        # Instantiate all CPL exporters in the exporters directory
        self._raw_exporter = Eetb_RawCPLExporter(self, query_unit)
        self._exporters: list[Eetb_CPLExporterBase] = [
            self._raw_exporter,
            Eetb_EuroCircuitsCPLExporter(self, query_unit),
            Eetb_JLCPCBCPLExporter(self, query_unit),
            Eetb_MacrofabCPLExporter(self, query_unit)
        ]

        for exporter in self._exporters:
            self.add_supported_format(exporter.format_name,
                                      self._default_attribute_mapping + exporter.output_attributes, 
                                      self._do_export, exporter.output_file_extension)


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        eetbControls.add_command_to_panel(config.ELECTRON_LAYOUT_ENV_ID, eetbControls.LayoutPanel.EXPORT_PANEL, commandDefinition)


    def on_command_created(self, args: adsk.core.CommandCreatedEventArgs):
        """
        Override the base class command creation event, to update the mapping help.
        For detailed information see the base class.
        """
        super().on_command_created(args)
        self.mapping_help.text = "Fabhouses may define component centroid and null rotation different from the component library. Fix origin and rotation mismatch with component attributes. If an origin fix attribute value does not have a dimension, 'millimeters' is assumed" 
        self.mapping_help.numRows = 6
        self.mapping_table.minimumVisibleRows = 3


    def get_user_script_input_data(self, filtered_part_data: list[dict], output_format: str) -> list[list[str]]:
        return self._raw_exporter.export(filtered_part_data, {})


    def on_format_selection_input_changed(self, inputs: adsk.core.CommandInputs):
        """
        Handles the change event for the format selection input.

        This method is called when the user changes the selected export format
        in the palette. It calls the base class implementation to show or hide
        the appropriate attribute mapping controls based on the selected format.
        In addition, it handles the warning shown for some formats

        Args:
            inputs (adsk.core.CommandInputs): The command inputs object
                                             containing all UI elements.
        """
        super().on_format_selection_input_changed(inputs)
        
        self.open_file_on_ok_chkbox.isEnabled = True
        format_name = self.format_selection_input.selectedItem.name

        # Notify the exporter that is selected
        for exporter in self._exporters:
            if format_name == exporter.format_name:
                exporter.notify_selected()
                break


    #####################
    # PRIVATE FUNCTIONS #
    #####################

    def _get_selected_attribute(self, bom_column_name_def: tuple[str, bool]) -> str:
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
        (cpl_column_name, isOptional) = bom_column_name_def
        # Iterate through all rows in the mapping table
        for rowIdx in range(0, self.mapping_table.rowCount):
            # Get the label input (first column)
            label_input = self.mapping_table.getInputAtPosition(rowIdx, 0)
            if label_input is None or not isinstance(label_input, adsk.core.StringValueCommandInput):
               raise TypeError(f"Unexpected input type for the attribute mapping row {rowIdx}, column 0")

            if label_input.value == cpl_column_name:
                # Get the dropdown input (second column)
                dropdown_input = self.mapping_table.getInputAtPosition(rowIdx, 1)
                if dropdown_input is None or not isinstance(dropdown_input, adsk.core.DropDownCommandInput):
                    raise TypeError(f"Unexpected input type for the attribute mapping row {rowIdx}, column 1")
                return dropdown_input.selectedItem.name
        # If no matching row is found, return an empty string
        return ""
    

    def _do_export(self, selected_format, filtered_part_data: list[dict]) -> list[list[str]]:
        # Find the exporter with the matching name and call its export function
        for exporter in self._exporters:
            if exporter.format_name == selected_format:
                if exporter != self._raw_exporter:
                    selected_attributes = {}
                    for (column_name, isOptional) in self._default_attribute_mapping + exporter.output_attributes:
                        selected_attributes[column_name] = self.get_selected_attribute((column_name, isOptional))
                    return exporter.export(filtered_part_data, selected_attributes)
                else:
                    return exporter.export(filtered_part_data, {})
        # If the exporter is not found, return empty list
        return []