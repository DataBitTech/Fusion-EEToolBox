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



class Eetb_EuroCircuitsCPLExporter(Eetb_CPLExporterBase):
    """EuroCircuits CPL exporter."""

    def __init__(self, exportCplCommand: PartDataExportCommandBase, queryUnit: eetbutil.LengthUnits):
        super().__init__(exportCplCommand, queryUnit)


    @property
    def format_name(self) -> str:
        """See the base class for details"""
        return "EuroCircuits"


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
        pass


    def export(self, filtered_part_data: list[dict], column_attributes: dict[str, str]) -> list[list[str]]:
        """See the base class for details"""
        headers = ['Designator', 'Comment', 'Layer', 'Center-X(mm)', 'Center-Y(mm)', 'Rotation', 'Description']
        # retrieve the correction mapping
        cpl_data = [headers]
        for component in filtered_part_data:
            comment = component['value']
            description = ''
            for attribute in component.get('attributes',[]):
                if attribute['name'] in ['DESCRIPTION', 'DESC']:
                    description = attribute['value']
                    break
            (x, y , rot) = self.apply_corrections(component, column_attributes)

            # add to the output
            cpl_data.append([component['name'],
                             comment, 'Bottom' if component['mirror'] else 'Top',
                             f'{eetbutil.convert_to_unit((x, self._query_unit), eetbutil.LengthUnits.MILLIMETER):.3f}',
                             f'{eetbutil.convert_to_unit((y, self._query_unit), eetbutil.LengthUnits.MILLIMETER):.3f}',
                             f'{rot:.2f}',
                             description])
        return cpl_data