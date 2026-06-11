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


from .Eetb_CPLExporterBase import Eetb_CPLExporterBase
from ...PartDataExportCommandBase import PartDataExportCommandBase
from ....lib import eetbUtils as eetbutil

class Eetb_RawCPLExporter(Eetb_CPLExporterBase):
    """Raw CPL exporter."""

    def __init__(self, exportCplCommand: PartDataExportCommandBase, queryUnit: eetbutil.LengthUnits):
        super().__init__(exportCplCommand, queryUnit)

    @property
    def format_name(self) -> str:
        """See the base class for details"""
        return "Raw"


    @property
    def output_attributes(self) -> list[tuple[str, bool]]:
        """See the base class for details"""
        return []


    @property
    def output_file_extension(self) -> PartDataExportCommandBase.FileExtensions:
        """See the base class for details"""
        return PartDataExportCommandBase.FileExtensions.FILE_EXTENSION_XLSX
    

    def notify_selected(self) -> None:
        """See the base class for details"""
        self._export_cpl_command.mapping_group.isVisible = False


    def export(self, filtered_part_data: list[dict], column_attributes: dict[str, str]) -> list[list[str]]:
        """Exports component placement data in raw format, including all attributes. See the base class for details"""
        headers = ['Designator', 'Value', 'Footprint', 'Center X', 'Center Y', 'Rotation', 'Side']
        for attribute in self._export_cpl_command.attribute_list:
            headers.append(attribute)
        cpl_data = [headers]
        for component in filtered_part_data:
            row = [component['name'], 
                   component['value'], 
                   component['package'], 
                   f'{eetbutil.convert_to_unit((component['x'], self._query_unit), eetbutil.LengthUnits.MILLIMETER):.3f}mm', 
                   f'{eetbutil.convert_to_unit((component['y'], self._query_unit), eetbutil.LengthUnits.MILLIMETER):.3f}mm',
                   f'{component['angle']:.2f}mm', 
                   'Bottom' if component['mirror'] else 'Top']
            attributes = component.get('attributes', [])
            for attribute in self._export_cpl_command.attribute_list:
                match = next((d for d in attributes if d.get('name', '') == attribute), None)
                row.append(match['value'] if match is not None else '')
                
            cpl_data.append(row)
        return cpl_data