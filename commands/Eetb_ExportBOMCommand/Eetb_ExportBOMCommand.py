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

        self.attribute_map_col_names_EuroCircuits = [
            # column to map to attribute    optional?
            ('Manufacturer Part Number',    False),
            ('Description',                 False),
            ('Supplier part number',        False), 
            ('Supplier',                    False),
            ('URL',                         False)]
        self.attribute_map_col_names_JLCPCB = [('JLCPCB Part# (optional)', True)]
        self.attribute_map_col_names_Macrofab = [
            ('Populate',                    True),
            ('MPN',                         False),
            ('Manufacturer',                False)]
        
        self.add_supported_format('Raw',                        None,                                       self.export_raw_by_parts)
        self.add_supported_format('Raw (grouped by values)',    None,                                       self.export_raw_by_values)
        self.add_supported_format('EuroCircuits',               self.attribute_map_col_names_EuroCircuits,  self.export_EuroCircuits)
        self.add_supported_format('JLCPCB',                     self.attribute_map_col_names_JLCPCB,        self.export_JLCPCB)
        self.add_supported_format('Macrofab',                   self.attribute_map_col_names_Macrofab,      self.export_Macrofab)



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
        if output_format.endswith('values%'):
            return self.export_raw_by_values(output_format, filtered_part_data)
        else:
            return self.export_raw_by_parts(output_format, filtered_part_data)


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
            if format_name == 'EuroCircuits':
                self.warning_label.formattedText += "<br><br>The 'Mounting type' column (SMD or THT) in the output file needs to be filled out by hand! Run this command from the layout editor to automatically include that data"
                self.warning_label.numRows = 7
            


    def on_command_created(self, args: adsk.core.CommandCreatedEventArgs):
        """
        Override the base class command creation event, to update the mapping help.
        For detailed information see the base class.
        """
        super().on_command_created(args)
        self.mapping_help.text = 'Select component attributes for format-specific columns in the output' 


    ###########################
    # FAB SPECIFIC FORMATTING #
    ###########################

    def export_EuroCircuits(self, selected_format, filtered_part_data: list[dict]) -> list[list[str]]:
        """
        Exports the part data in the EuroCircuits format.

        This function takes the filtered part data and formats it according to the
        EuroCircuits specification. It ensures that the required columns are present
        and properly mapped to the corresponding part attributes.

        Args:
            selected_format (str): The name of the selected export format (unused in this function).
            filtered_part_data (list[dict]): A list of dictionaries containing the filtered
                                             part data to be exported.

        Returns:
            list[list[str]]: A list of lists where each inner list represents a row of
                            the exported data in EuroCircuits format.
        """
        significant_attributes = self._get_significant_attributes(self.attribute_map_col_names_EuroCircuits)
        filtered_part_data = self.group_by_parts(filtered_part_data, ['angle', 'locked', 'mirror', 'x', 'y'], False, significant_attributes)
        headers = ['Manufacturer Part Number', 'Description', 'Reference designators', 'Quantity', 'Supplier part number', 'Supplier', 'Package name', 'Mounting type', 'URL']
        bom_data = [headers]
        for component in filtered_part_data:
            attributes = component.get('attributes', [])
            isTHT = self._package_is_THT(component.get('package', '')) if self._app.activeDocument.dataFile.fileExtension == 'fbrd' else None
            if attributes:
                attr_values = self.get_mapped_attribute_values(self.attribute_map_col_names_EuroCircuits, attributes)
                
                # add to the output
                bom_data.append([attr_values[0], attr_values[1], component['name'], component['__quantity__'], attr_values[2], attr_values[3], component['package'], '' if isTHT is None else 'Thru-hole' if isTHT == True else 'SMD', attr_values[4]])
            else:
                bom_data.append(['', '', component['name'], component['__quantity__'], '', '', component['package'], '' if isTHT is None else 'Thru-hole' if isTHT == True else 'SMD', ''])
        return bom_data


    def export_JLCPCB(self, selected_format, filtered_part_data: list[dict]) -> list[list[str]]:
        """
        Exports the part data in the JLCPCB format.

        This function takes the filtered part data and formats it according to the
        JLCPCB specification. It ensures that the required columns are present
        and properly mapped to the corresponding part attributes.

        Args:
            selected_format (str): The name of the selected export format (unused in this function).
            filtered_part_data (list[dict]): A list of dictionaries containing the filtered
                                             part data to be exported.

        Returns:
            list[list[str]]: A list of lists where each inner list represents a row of
                            the exported data in JLCPCB format.
        """
        significant_attributes = self._get_significant_attributes(self.attribute_map_col_names_JLCPCB)
        filtered_part_data = self.group_by_parts(filtered_part_data, ['angle', 'locked', 'mirror', 'x', 'y'], False, significant_attributes)
        jlcpcb_part_num_used = self.get_selected_attribute(self.attribute_map_col_names_JLCPCB[0]) != 'None'
        headers = ['Comment', 'Designator', 'Footprint']
        if jlcpcb_part_num_used:
            (column_name, isOptional) = self.attribute_map_col_names_JLCPCB[0]
            headers.append(column_name)
        bom_data = [headers]
        for component in filtered_part_data:
            # add to the output
            if jlcpcb_part_num_used:
                jlcpcb_pn = ''
                attributes = component.get('attributes', [])
                if attributes:
                    jlcpcb_pn = self.get_mapped_attribute_values(self.attribute_map_col_names_JLCPCB, attributes)[0]
                bom_data.append([component['value'], component['name'], component['package'], jlcpcb_pn])
            else:
                bom_data.append([component['value'], component['name'], component['package']])
        return bom_data
    

    def export_Macrofab(self, selected_format, filtered_part_data: list[dict]) -> list[list[str]]:
        """
        Exports the part data in the Macrofab format.

        This function takes the filtered part data and formats it according to the
        Macrofab specification. It ensures that the required columns are present
        and properly mapped to the corresponding part attributes.

        Args:
            selected_format (str): The name of the selected export format (unused in this function).
            filtered_part_data (list[dict]): A list of dictionaries containing the filtered
                                             part data to be exported.

        Returns:
            list[list[str]]: A list of lists where each inner list represents a row of
                            the exported data in Macrofab format.
        """
        headers = ['Designator', 'Value', 'Footprint', 'Populate', 'MPN', 'Manufacturer']
        bom_data = [headers]
        for component in filtered_part_data:
            # add to the output
            macrofab_mpn = ''
            macrofab_manuf = ''
            populate = '1'
            attributes = component.get('attributes', [])
            if attributes:
                mapped_values = self.get_mapped_attribute_values(self.attribute_map_col_names_Macrofab, attributes)
                populate = mapped_values[0]
                macrofab_mpn = mapped_values[1]
                macrofab_manuf = mapped_values[2]
                if not populate or populate == '':
                    populate = '1'
            bom_data.append([component['name'], component['value'], component['package'], populate, macrofab_mpn, macrofab_manuf])
        return bom_data


    def export_raw_by_parts(self, selected_format, filtered_part_data: list[dict]) -> list[list[str]]:
        """
        Exports the part data in a raw format, one row for each component.

        This function takes the filtered part data and formats it into a raw
        tabular format where each row corresponds to a single part. It includes
        all relevant part information such as name, value, package, and all attributes.

        Args:
            selected_format (str): The name of the selected export format (unused in this function).
            filtered_part_data (list[dict]): A list of dictionaries containing the filtered
                                             part data to be exported.

        Returns:
            list[list[str]]: A list of lists where each inner list represents a row of
                            the exported data in raw format, one row for each component.
        """
        return self._export_raw(filtered_part_data, False)


    def export_raw_by_values(self, selected_format, filtered_part_data: list[dict]) -> list[list[str]]:
        """
        Exports the part data in a raw format, grouped by component values.

        This function takes the filtered part data and formats it into a raw
        tabular format where each row corresponds to a unique component value.
        It includes all relevant part information such as name, value, package,
        and all attributes, but groups multiple parts with the same value and 
        attribute values together.

        Args:
            selected_format (str): The name of the selected export format (unused in this function).
            filtered_part_data (list[dict]): A list of dictionaries containing the filtered
                                             part data to be exported.

        Returns:
            list[list[str]]: A list of lists where each inner list represents a row of
                            the exported data in raw format, grouped by identical component 
                            values and attributes.
        """
        return self._export_raw(filtered_part_data, True)


    #############################
    # PRIVATE UTILITY FUNCTIONS #
    #############################

    # emulate the bom.ulp output
    def _export_raw(self, filtered_part_data: list[dict], collect_by_value: bool) -> list[list[str]]:
        """
        Exports the part data in a raw tabular format.

        This function formats the filtered part data into a raw tabular format.
        If collect_by_value is True, it groups components by their value and attributes,
        otherwise it exports each component as a separate row. It provides identical outputs
        to the legacy 'bom.ulp' Eagle ULP

        Args:
            filtered_part_data (list[dict]): A list of dictionaries containing the filtered
                                             part data to be exported.
            collect_by_value (bool): If True, groups components by their value and attributes.
                                     If False, exports each component as a separate row.

        Returns:
            list[list[str]]: A list of lists where each inner list represents a row of
                            the exported data in raw format.
        """
        if collect_by_value:
            filtered_part_data = self.group_by_parts(filtered_part_data, ['angle', 'locked', 'mirror', 'x', 'y'], True)
            headers = ['Qty', 'Value', 'Footprint Name', 'Parts']
        else:
            headers = ['Part', 'Value', 'Footprint Name']
        if self._app.activeDocument.dataFile.fileExtension == 'fsch':
            headers.insert(2, 'Device')
            headers.append('Detailed Description')
        for attribute in self.attribute_list:
            headers.append(attribute)
        
        cpl_data = [headers]
        for component in filtered_part_data:
            if collect_by_value:
                row = [ component['__quantity__'],
                        component['value'],
                        component['package'],
                        component['name']]
            else:
                row = [ component['name'],
                        component['value'],
                        component['package']]
            if self._app.activeDocument.dataFile.fileExtension == 'fsch':
                row.insert(2, component['device'])
                row.append(component['headline'])
            component_attributes = component['attributes'] if component.get('attributes') else {}
            for attribute in self.attribute_list:
                attr_value = next((cattr['value'] for cattr in component_attributes if cattr.get('name') == attribute), '')
                row.append(attr_value)
            cpl_data.append(row)
        return cpl_data
    

    def _package_is_THT(self, package_name: str) -> bool | None:
        """
        Find the package provided as an input argument in the self.package_data
        and iterate through its 'contacts'. If any of them is 'type'=='pad' then return true, else false.

        Args:
            package_name (str): The name of the package to search for.

        Returns:
            bool: True if any contact is of type 'pad', False otherwise.
        """
        # Find the package in self.package_data
        package = next((pkg for pkg in self.package_data if pkg.get('name') == package_name), None)
        if not package:
            return None

        # Iterate through the contacts
        contacts = package.get('contacts', [])
        for contact in contacts:
            if contact.get('type') == 'pad':
                return True
        return False


    def _get_significant_attributes(self, attr_map_col_names: list[tuple[str, bool]]) -> list[str]:
        """
        Extracts the names of mapped attributes from the attribute mapping column names.

        This function retrieves the selected attribute names based on the attribute mapping column names 
        and returns a list of attribute names that need to be distuinguished

        Args:
            attr_map_col_names (list[tuple[str, bool]]): A list of tuples where each tuple
                                                        contains an attribute name (str) and
                                                        a boolean indicating if it's optional (True)
                                                        or required (False).

        Returns:
            list[str]: A list of attribute names that need to be distuinguished for value based grouping
        """
        significant_attributes = []
        for col_to_attr_map in attr_map_col_names:
            attr_name = self.get_selected_attribute(col_to_attr_map)
            if attr_name != 'None':
                significant_attributes.append(attr_name)
        return significant_attributes