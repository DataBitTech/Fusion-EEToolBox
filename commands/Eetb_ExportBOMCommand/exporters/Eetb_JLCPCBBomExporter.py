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


class Eetb_JLCPCBExporter(Eetb_BOMExporterBase):
    """JLCPCB BOM exporter implementation."""
    
    def __init__(self, exportBomCommand: PartDataExportCommandBase):
        super().__init__(exportBomCommand)
        self._column_names = [('JLCPCB Part# (optional)', True)]


    @property
    def output_attributes(self) -> list[tuple[str, bool]]:
        """See the base class for details"""
        return self._column_names
    

    @property
    def format_name(self) -> str:
        """See the base class for details"""
        return "JLCPCB"


    def notify_selected(self) -> None:
        """See the base class for details"""
        pass


    def export(self, filtered_part_data: list[dict], column_attributes: list[str]) -> list[list[str]]:
        """See the base class for details"""
        grouped_part_data = self.group_by_parts(filtered_part_data, column_attributes)
        jlcpcb_part_num_used = column_attributes[0] != 'None'
        headers = ['Comment', 'Designator', 'Footprint']
        if jlcpcb_part_num_used:
            (column_name, _) = self._column_names[0]
            headers.append(column_name)
        bom_data = [headers]
        for component in grouped_part_data:
            # add to the output
            if jlcpcb_part_num_used:
                jlcpcb_pn = ''
                attributes = component.get('attributes', [])
                if attributes:
                    jlcpcb_pn = next((attr['value'] for attr in attributes if attr['name'] == column_attributes[0]), '')
                bom_data.append([component['value'], component['name'], component['package'], jlcpcb_pn])
            else:
                bom_data.append([component['value'], component['name'], component['package']])
        return bom_data
    
 