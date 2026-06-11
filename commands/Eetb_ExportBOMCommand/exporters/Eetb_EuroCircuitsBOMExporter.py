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


from .Eetb_BOMExporterBase import Eetb_BOMExporterBase
from ...PartDataExportCommandBase import PartDataExportCommandBase


class Eetb_EuroCircuitsBOMExporter(Eetb_BOMExporterBase):
    """EuroCircuits BOM exporter implementation."""
    
    def __init__(self, exportBomCommand: PartDataExportCommandBase):
        super().__init__(exportBomCommand)
        self._column_names = [
            # column to map to attribute    optional?
            ('Manufacturer Part Number',    False),
            ('Description',                 False),
            ('Supplier part number',        False), 
            ('Supplier',                    False),
            ('URL',                         False)]


    @property
    def output_attributes(self) -> list[tuple[str, bool]]:
        """See the base class for details"""
        return self._column_names
    

    @property
    def format_name(self) -> str:
        """See the base class for details"""
        return "EuroCircuits"


    def notify_selected(self) -> None:
        """See the base class for details"""
        if self._exportBomCommand.app.activeDocument.dataFile.fileExtension == 'fsch':
            self._exportBomCommand.warning_label.formattedText += "<br><br>The 'Mounting type' column (SMD or THT) in the output file needs to be filled out by hand! Run this command from the layout editor to automatically include that data"
            self._exportBomCommand.warning_label.numRows += 4


    def export(self, filtered_part_data: list[dict], column_attributes: list[str]) -> list[list[str]]:
        """See the base class for details"""
        col_headers = []
        for (name, _) in self._column_names:
            col_headers.append(name)
        headers = [col_headers[0], col_headers[1], 'Reference designators', 'Quantity', col_headers[2], col_headers[3], 'Package name', 'Mounting type', col_headers[4]]
        bom_data = [headers]
        grouped_part_data = self.group_by_parts(filtered_part_data, column_attributes if column_attributes[0] != 'None' else [])
        for component in grouped_part_data:
            attributes = component.get('attributes', [])
            isTHT = self._package_is_THT(component.get('package', '')) if self._exportBomCommand.app.activeDocument.dataFile.fileExtension == 'fbrd' else None
            if attributes:
                attr_values = []
                for col_attr_name in column_attributes:
                    # Find this attribute name and return its value
                    value = next((attr['value'] for attr in attributes if attr['name'] == col_attr_name), '')
                    attr_values.append(value)
                
                # add to the output
                bom_data.append([attr_values[0], attr_values[1], component['name'], component['__quantity__'], attr_values[2], attr_values[3], component['package'], '' if isTHT is None else 'Thru-hole' if isTHT == True else 'SMD', attr_values[4]])
            else:
                bom_data.append(['', '', component['name'], component['__quantity__'], '', '', component['package'], '' if isTHT is None else 'Thru-hole' if isTHT == True else 'SMD', ''])
        return bom_data
    

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
        package = next((pkg for pkg in self._exportBomCommand.package_data if pkg.get('name') == package_name), None)
        if not package:
            return None

        # Iterate through the contacts
        contacts = package.get('contacts', [])
        for contact in contacts:
            if contact.get('type') == 'pad':
                return True
        return False
