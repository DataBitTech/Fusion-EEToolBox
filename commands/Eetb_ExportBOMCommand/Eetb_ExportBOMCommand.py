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

import os
import adsk.core

from ..CommandBase import CommandBase
from ..PartDataExportCommandBase import PartDataExportCommandBase
from ..Eetb_EditUserScriptCommand.Eetb_EditUserScriptCommand import Eetb_EditUserScriptCommand
from ... import config
from ... import controls as eetbControls
from ...lib import eetbUtils as eetbutil
from ...lib import fusionAddInUtils as futil

from .exporters.Eetb_BOMExporterBase import Eetb_BOMExporterBase
from .exporters.Eetb_LegacyBomExporter import Eetb_LegacyBomExporter
from .exporters.Eetb_LegacyGroupedBomExporter import Eetb_LegacyGroupedBomExporter
from .exporters.Eetb_JLCPCBBomExporter import Eetb_JLCPCBExporter
from .exporters.Eetb_EuroCircuitsBOMExporter import Eetb_EuroCircuitsBOMExporter
from .exporters.Eetb_MacrofabBOMExporter import Eetb_MacrofabBOMExporter


class Eetb_ExportBOMCommand(PartDataExportCommandBase):

    def __init__(self, edit_user_script_command: Eetb_EditUserScriptCommand):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_export_bom_command_id',
            command_name = 'Export BOM data',
            command_description = 'Export Bill of Material in manufacturer specific formats',
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'),
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources'))
        super().__init__(command_attributes, edit_user_script_command)

        self._schematic_warning_ftext = "<b>WARNING</b><br>If you are using modules in your schematic, you need to run this command from the layout editor!"
       
        # Instantiate all BOM exporters in the exporters directory
        self._legacy_exporter = Eetb_LegacyBomExporter(self)
        self._legacy_grouped_exporter = Eetb_LegacyGroupedBomExporter(self)
        self._exporters: list[Eetb_BOMExporterBase] = [
            self._legacy_exporter,
            self._legacy_grouped_exporter,
            Eetb_EuroCircuitsBOMExporter(self),
            Eetb_JLCPCBExporter(self),
            Eetb_MacrofabBOMExporter(self)
        ]

        for exporter in self._exporters:
            self.add_supported_format(exporter.format_name, exporter.output_attributes, self._do_export)
        

    def get_user_script_input_data(self, filtered_part_data: list[dict], output_format: str) -> list[list[str]]:
        """
        Retrieves user script input data for the specified output format.

        This method overriddes the base class function to provide
        custom input data processing for different export types (BOM/CPL).

        Args:
            filtered_part_data (list[dict]): The list of part data dictionaries
                                             that have been filtered for export.
            output_format (str): The name of the output format for which
                                the input data is required.

        Returns:
            list[list[str]]: A list of lists containing the input data
                            formatted according to the requirements of the
                            user script for the specified output format.
        """
        format_name = ''
        if output_format.endswith('values%'):
            if self._legacy_grouped_exporter:
                format_name = self._legacy_grouped_exporter.format_name  
        else: 
            if self._legacy_exporter:
                format_name = self._legacy_exporter.format_name
           
        return [] if not format_name else self._do_export(format_name, filtered_part_data)


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        eetbControls.add_command_to_panel(config.ELECTRON_SCHEMATIC_ENV_ID, eetbControls.SchematicPanel.EXPORT_PANEL, commandDefinition)
        eetbControls.add_command_to_panel(config.ELECTRON_LAYOUT_ENV_ID,    eetbControls.LayoutPanel.EXPORT_PANEL,    commandDefinition)


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

        format_name = self.format_selection_input.selectedItem.name
        if self._app.activeDocument.dataFile.fileExtension == 'fsch':
            self.warning_label.formattedText = self._schematic_warning_ftext
            self.warning_label.numRows = 3
            self.warning_label.isVisible = True
        
        # Notify the exporter that is selected
        for exporter in self._exporters:
            if format_name == exporter.format_name:
                exporter.notify_selected()
                break


    def on_command_created(self, args: adsk.core.CommandCreatedEventArgs):
        """
        Override the base class command creation event, to update the mapping help.
        For detailed information see the base class.
        """
        super().on_command_created(args)
        self.mapping_help.text = 'Select component attributes for format-specific columns in the output' 


    #####################
    # PRIVATE FUNCTIONS #
    #####################

    def _do_export(self, selected_format, filtered_part_data: list[dict]) -> list[list[str]]:
        # Find the exporter with the matching name and call its export function
        for exporter in self._exporters:
            if exporter.format_name == selected_format:
                selected_attributes = []
                for col_to_attr_map in exporter.output_attributes:
                    selected_attributes.append(self.get_selected_attribute(col_to_attr_map))
                return exporter.export(filtered_part_data, selected_attributes)
        # If the exporter is not found, return empty list
        return []