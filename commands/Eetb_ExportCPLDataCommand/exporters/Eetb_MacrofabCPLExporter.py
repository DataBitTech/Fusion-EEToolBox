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

import math
import os
from enum import Enum
from pathlib import Path
import subprocess
import adsk.core
from .Eetb_CPLExporterBase import Eetb_CPLExporterBase
from ...PartDataExportCommandBase import PartDataExportCommandBase
from ....lib import eetbUtils as eetbutil

class Eetb_MacrofabCPLExporter(Eetb_CPLExporterBase):
    """Macrofab CPL exporter."""

    class OutputAttribute(Enum):
        POPULATE = 'Populate'
        MPN = 'MPN'


    def __init__(self, exportCplCommand: PartDataExportCommandBase, queryUnit: eetbutil.LengthUnits):
        super().__init__(exportCplCommand, queryUnit)
        
        self._attribute_mapping = [
            (self.OutputAttribute.POPULATE.value,  True),
            (self.OutputAttribute.MPN.value,       True)
        ]


    @property
    def format_name(self) -> str:
        """See the base class for details"""
        return "Macrofab"


    @property
    def output_attributes(self) -> list[tuple[str, bool]]:
        """See the base class for details"""
        return self._attribute_mapping


    @property
    def output_file_extension(self) -> PartDataExportCommandBase.FileExtensions:
        """See the base class for details"""
        return PartDataExportCommandBase.FileExtensions.FILE_EXTENSION_CUSTOM


    def notify_selected(self) -> None:
        """See the base class for details"""
        self._export_cpl_command.open_file_on_ok_chkbox.value = False 
        self._export_cpl_command.open_file_on_ok_chkbox.isEnabled = False 

    
    def export(self, filtered_part_data: list[dict], column_attributes: dict[str, str]) -> list[list[str]]:
        """Exports component placement data in Macrofab format.
        
        Since it exports to a custom file type, it needs to handle the file encoding, writing, and
        configuration saving. 
        """
        headers = ['#Designator', 'X-Loc', 'Y-Loc', 'Rotation', 'Side', 'Type', 'X-Size', 'Y-Size', 'Value', 'Footprint', 'Populate', 'MPN']
        cpl_data = [headers]

        populated_attribute = column_attributes.get(self.OutputAttribute.POPULATE.value, 'None')
        populated_used = populated_attribute != 'None'
        
        mpn_attribute = column_attributes.get(self.OutputAttribute.MPN.value, 'None')
        mpn_used = mpn_attribute != 'None'
        
        for component in filtered_part_data:
            populated_value = []
            mpn_value = []
            width = 0.0
            height = 0.0
            (x, y , rot) = self.apply_corrections(component, column_attributes)
            top_side = component['mirror'] == False
            attributes = component.get('attributes', [])
            isTHT = self._package_is_THT(component.get('package', ''))
            bounding_box = self._get_package_bounding_box(component.get('package', ''))
            if bounding_box is not None:
                (width, height) = bounding_box
            
            if attributes:
                populated_value = [attribute for attribute in attributes if attribute.get('name') == populated_attribute]
                mpn_value = [attribute for attribute in attributes if attribute.get('name') == mpn_attribute]
            # add to the output
            cpl_data.append([component['name'], f'{eetbutil.convert_to_unit((x, self._query_unit), eetbutil.LengthUnits.MIL):.2f}', 
                             f'{eetbutil.convert_to_unit((y, self._query_unit), eetbutil.LengthUnits.MIL):.2f}', 
                             f'{round(rot)}', 
                             'T' if top_side else 'B', 
                             '' if isTHT == None else '1' if isTHT == False else '2', 
                             f'{eetbutil.convert_to_unit((width, self._query_unit), eetbutil.LengthUnits.MIL):.2f}' if bounding_box is not None else '', 
                             f'{eetbutil.convert_to_unit((height, self._query_unit), eetbutil.LengthUnits.MIL):.2f}' if bounding_box is not None else '', 
                             component['value'], component['package'], 
                             populated_value[0] if populated_used and populated_value else '1', 
                             mpn_value[0] if mpn_used and mpn_value else ''])

        # this format uses a custom file extension, so it is handled here
        extension_filter = "XYRS files (*.XYRS)"

        # Get the last used output file from ConfigManager
        user_selection: dict = eetbutil.config_manager.get_document_option(self._export_cpl_command.document_id, self._export_cpl_command.command_id, self.format_name, {}) # type: ignore
        
        # Create a file dialog for saving results
        fileDialog = self._export_cpl_command.ui.createFileDialog()
        fileDialog.isMultiSelectEnabled = False
        fileDialog.title = f"Save {self.format_name} Results"
        fileDialog.filter = extension_filter
        fileDialog.filterIndex = 0

        if user_selection and 'last_output_dir' in user_selection and os.path.exists(user_selection['last_output_dir']):
            fileDialog.initialDirectory = user_selection['last_output_dir'] if os.path.isdir(user_selection['last_output_dir']) else os.path.dirname(user_selection['last_output_dir'])
        else:
            fileDialog.initialDirectory = str(Path.home())
        
        dialogResult = fileDialog.showSave()
        
        if dialogResult == adsk.core.DialogResults.DialogOK:
            output_file = fileDialog.filename
            root, ext = os.path.splitext(output_file)
            if ext != ".XYRS":
                output_file += ".XYRS"

            # Write the data to the file based on the format
            file_data = self._export_cpl_command.format_data_by_extension(cpl_data, PartDataExportCommandBase.FileExtensions.FILE_EXTENSION_TXT.value)
            try:
                with open(output_file, 'wb') as f:
                    f.write(file_data)

                self._export_cpl_command.log_to_console(f'Results saved to {output_file}')
                self._export_cpl_command.save_config(self.format_name, os.path.dirname(output_file))
            except IOError as e:
                self._export_cpl_command.ui.messageBox(f"Error writing to file {output_file}: {e}")
        
        return []
    

    ####################
    # HELPER FUNCTIONS #
    ####################

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
        package = next((pkg for pkg in self._export_cpl_command.package_data if pkg.get('name') == package_name), None)
        if not package:
            return None

        # Iterate through the contacts
        contacts = package.get('contacts', [])
        for contact in contacts:
            if contact.get('type') == 'pad':
                return True
        return False


    def _get_package_bounding_box(self, package_name: str) -> tuple[float, float] | None:
        """
        Find the package in self.package_data and compute its bounding box size (width, height)
        based on the 'contacts' (pads and smds).

        Pads have 'x', 'y', 'diameter' properties (treated as circles).
        Smds have 'x', 'y', 'dx', 'dy', and optionally 'angle' properties (rectangles, possibly rotated).

        Args:
            package_name (str): The name of the package to search for.

        Returns:
            tuple[float, float]: Width and height of the bounding box in self._query_unit, or None if package not found.
        """
        # Find the package in self.package_data
        package = next((pkg for pkg in self._export_cpl_command.package_data if pkg.get('name') == package_name), None)
        if not package:
            return None

        contacts = package.get('contacts', [])
        if not contacts:
            return None

        min_x = float('inf')
        max_x = float('-inf')
        min_y = float('inf')
        max_y = float('-inf')

        for contact in contacts:
            contact_type = contact.get('type')
            x = contact.get('x', 0.0)
            y = contact.get('y', 0.0)

            if contact_type == 'pad':
                # Treat as circle with diameter
                diameter = contact.get('diameter', 0.0)
                radius = diameter / 2.0
                # Add the radius to all directions to get the bounding box
                min_x = min(min_x, x - radius)
                max_x = max(max_x, x + radius)
                min_y = min(min_y, y - radius)
                max_y = max(max_y, y + radius)
            elif contact_type == 'smd':
                # Treat as rectangle with dx, dy, and optional angle
                dx = contact.get('dx', 0.0)
                dy = contact.get('dy', 0.0)
                angle = contact.get('angle', 0.0)  # in degrees

                # Calculate the half dimensions
                half_dx = dx / 2.0
                half_dy = dy / 2.0

                # If no rotation, simple case
                if angle == 0.0:
                    min_x = min(min_x, x - half_dx)
                    max_x = max(max_x, x + half_dx)
                    min_y = min(min_y, y - half_dy)
                    max_y = max(max_y, y + half_dy)
                else:
                    # Rotate the rectangle corners to find the bounding box
                    # Convert angle to radians
                    angle_rad = math.radians(angle)
                    cos_a = math.cos(angle_rad)
                    sin_a = math.sin(angle_rad)

                    # Rectangle corners in local coordinates (centered at origin)
                    corners = [
                        (-half_dx, -half_dy),  # bottom-left
                        (half_dx, -half_dy),   # bottom-right
                        (half_dx, half_dy),    # top-right
                        (-half_dx, half_dy)    # top-left
                    ]

                    # Rotate and translate to global coordinates
                    for cx, cy in corners:
                        # Rotate
                        rx = cx * cos_a - cy * sin_a
                        ry = cx * sin_a + cy * cos_a
                        # Translate to global position
                        rx += x
                        ry += y
                        # Update bounding box
                        min_x = min(min_x, rx)
                        max_x = max(max_x, rx)
                        min_y = min(min_y, ry)
                        max_y = max(max_y, ry)

        # Calculate width and height
        width = max_x - min_x
        height = max_y - min_y

        return (width, height)