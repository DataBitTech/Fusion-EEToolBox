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


class Eetb_LegacyGroupedBomExporter(Eetb_BOMExporterBase):
    
    def __init__(self, exportBomCommand: PartDataExportCommandBase):
        super().__init__(exportBomCommand)


    @property
    def output_attributes(self) -> list[tuple[str, bool]]:
        """See the base class for details"""
        return []
    

    @property
    def format_name(self) -> str:
        """See the base class for details"""
        return "Legacy grouped by values"


    def notify_selected(self) -> None:
        """See the base class for details"""
        pass


    def export(self, filtered_part_data: list[dict], column_attributes: list[str]) -> list[list[str]]:
        """See the base class for details"""
        grouped_part_data = self.group_by_parts(filtered_part_data, [])
        headers = ['Qty', 'Value', 'Footprint Name', 'Parts']
        isSchematic = self._exportBomCommand.app.activeDocument.dataFile.fileExtension == 'fsch'
        if isSchematic:
            headers.insert(2, 'Device')
            headers.append('Detailed Description')
        for attribute in self._exportBomCommand.attribute_list:
            headers.append(attribute)
        
        bom_data = [headers]
        for component in grouped_part_data:
            row = [ component['__quantity__'],
                    component['value'],
                    component['package'],
                    component['name']]
            if isSchematic:
                row.insert(2, component['device'])
                row.append(component['headline'])
            component_attributes = component['attributes'] if component.get('attributes') else {}
            for attribute in self._exportBomCommand.attribute_list:
                attr_value = next((cattr['value'] for cattr in component_attributes if cattr.get('name') == attribute), '')
                row.append(attr_value)
            bom_data.append(row)
        return bom_data
    