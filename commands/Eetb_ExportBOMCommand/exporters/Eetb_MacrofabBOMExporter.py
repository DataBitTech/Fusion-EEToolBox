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


class Eetb_MacrofabBOMExporter(Eetb_BOMExporterBase):
    """Macrofab BOM exporter implementation."""

    def __init__(self, exportBomCommand: PartDataExportCommandBase):
        super().__init__(exportBomCommand)
        self._column_names = [
            ('Populate',                    True),
            ('MPN',                         False),
            ('Manufacturer',                False)]


    @property
    def output_attributes(self) -> list[tuple[str, bool]]:
        """See the base class for details"""
        return self._column_names
    

    @property
    def format_name(self) -> str:
        """See the base class for details"""
        return "Macrofab"
    
    
    def notify_selected(self) -> None:
        """See the base class for details"""
        pass
    

    def export(self, filtered_part_data: list[dict], column_attributes: list[str]) -> list[list[str]]:
        """See the base class for details"""
        col_headers = []
        for (name, _) in self._column_names:
            col_headers.append(name)
        headers = ['Designator', 'Value', 'Footprint']
        headers.extend(col_headers)
        bom_data = [headers]
        # Filter out 'None' string elements from column_attributes
        filtered_column_attributes = [attr for attr in column_attributes if attr != 'None']
        grouped_part_data = self.group_by_parts(filtered_part_data, filtered_column_attributes)
        for component in grouped_part_data:
            # add to the output
            populate = '1'
            attr_values = [''] * len(self._column_names)
            attributes = component.get('attributes', [])
            if attributes:
                for i in range(len(column_attributes)):
                    if column_attributes[i] == 'None':
                        value = ''
                    else:
                        # Find this attribute name and return its value
                        value = next((attr['value'] for attr in attributes if attr['name'] == column_attributes[i]), '')
                    attr_values[i] = value
                populate = attr_values[0]
                if populate == '':
                    populate = '1'
            bom_data.append([component['name'], component['value'], component['package'], populate, attr_values[1], attr_values[2]])
        return bom_data