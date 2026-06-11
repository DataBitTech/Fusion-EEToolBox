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
from abc import ABC, abstractmethod

from ...PartDataExportCommandBase import PartDataExportCommandBase
from ....lib import eetbUtils as eetbutil


class Eetb_CPLExporterBase(ABC):
    """Abstract base class for all CPL exporters."""

    def __init__(self, exportCplCommand: PartDataExportCommandBase, queryUnit: eetbutil.LengthUnits):
        self._export_cpl_command = exportCplCommand
        self._query_unit = queryUnit


    @abstractmethod
    def export(self, filtered_part_data: list[dict], column_attributes: dict[str, str]) -> list[list[str]]:
        """Export part data in the specific format.
        
        Args:
            filtered_part_data: List of part dictionaries to export
            column_attributes: List of attribute names to include as columns in the export

        Returns:
            List of lists representing the exported data rows
        """
        raise NotImplementedError("Subclasses must implement this method") 


    @abstractmethod
    def notify_selected(self) -> None:
        """Notify that this export format was selected in the UI."""
        raise NotImplementedError("Subclasses must implement this method") 


    ##############
    # PROPERTIES #
    ##############

    @property
    @abstractmethod
    def output_attributes(self) -> list[tuple[str, bool]]:
        """Returns a list of tuples representing the column attributes to be exported. Each tuple contains
        (attribute_name, is_visible). This property defines which columns are to be mapped to attributes 
        and whether they are mandatory to be mapped to one."""
        raise NotImplementedError("Subclasses must implement this property")


    @property
    @abstractmethod
    def format_name(self) -> str:
        """Returns the display name of the export format. This string is used on the UI to represent the 
        selected export option to the user."""
        raise NotImplementedError("Subclasses must implement this property")
    

    @property
    @abstractmethod
    def output_file_extension(self) -> PartDataExportCommandBase.FileExtensions:
        """Returns the default file extension for the exported file. If set to 'FILE_EXTENSION_CUSTOM', the
        child exporter class is responsible for the file writing in the appropriate format.
        """
        raise NotImplementedError("Subclasses must implement this property")


    ##################
    # IMPLEMENTATION #
    ##################

    def apply_corrections(self, component: dict, column_attributes: dict[str, str]) -> tuple [float, float, float]:
        """Applies corrections to the component's rotation, horizontal, and vertical position.

        This function takes a component dictionary and applies any necessary corrections
        to its rotation, horizontal, and vertical position values. It returns a tuple
        containing the corrected values. This correction is only visible in the output
        file, the electronics data is unchanged!

        Args:
            component (dict): A dictionary representing a component with rotation,
                              horizontal, and vertical position data.

        Returns:
            tuple[float, float, float]: A tuple containing the corrected rotation,
                                         horizontal position, and vertical position.
        """
        from ..Eetb_ExportCPLDataCommand import Eetb_ExportCPLDefaultOutputAttribute
        attributes = component.get('attributes',[])

        rotation_fix_attribute = column_attributes.get(Eetb_ExportCPLDefaultOutputAttribute.ROTATION_FIX.value, 'None')
        rotation_fix_used = rotation_fix_attribute != 'None'
        rotation_fix_value = [attribute.get('value', 0.0) for attribute in attributes if attribute.get('name') == rotation_fix_attribute]

        horizontal_fix_attribute = column_attributes.get(Eetb_ExportCPLDefaultOutputAttribute.HORIZONTAL_FIX.value, 'None')
        horizontal_fix_used = horizontal_fix_attribute != 'None'
        horizontal_fix_value = [attribute.get('value', 0.0) for attribute in attributes if attribute.get('name') == horizontal_fix_attribute]

        vertical_fix_attribute = column_attributes.get(Eetb_ExportCPLDefaultOutputAttribute.VERTICAL_FIX.value, 'None')
        vertical_fix_used = vertical_fix_attribute != 'None'
        vertical_fix_value = [attribute.get('value', 0.0) for attribute in attributes if attribute.get('name') == vertical_fix_attribute]

        # now handle the position/rotation fix
        x = component['x']
        y = component['y']
        rot = component['angle']
        top_side = not component.get('mirror', False)
        rotation_fix = 0.0


        if horizontal_fix_used and horizontal_fix_value:
            try:
                # First convert it to the units of the query
                (value, unit) = eetbutil.parse_dimension_string(horizontal_fix_value[0])
                dx = eetbutil.convert_to_unit((value, unit), self._query_unit)

                # Horizontal correction should be applied in the direction of the component's rotation
                # But since we're correcting the centroid position, we need to account for rotation
                # The offset should be applied in the component's local coordinate system
                offset_x = float(dx) * math.cos(rot / 180 * math.pi)
                offset_y = float(dx) * math.sin(rot / 180 * math.pi)
                y += offset_y
                if top_side:
                    x += offset_x
                else:
                    x -= offset_x # the board is mirrored, so compensate in the negative direction
            except:
                self._export_cpl_command.ui.messageBox(f'{component['name']} has a horizontal fix defined in its "{horizontal_fix_attribute}" attribute, but it is not a valid length! It is ignored and no horizontal correction is applied!',
                                   'Horizontal fix parsing error', adsk.core.MessageBoxButtonTypes.OKButtonType, adsk.core.MessageBoxIconTypes.WarningIconType) # type: ignore


        if vertical_fix_used and vertical_fix_value:
            try:
                # First convert it to the units of the query
                (value, unit) = eetbutil.parse_dimension_string(vertical_fix_value[0])
                dy = eetbutil.convert_to_unit((value, unit), self._query_unit)

                # Vertical correction should be applied perpendicular to the component's rotation
                # In component's local coordinate system, this is 90 degrees from rotation
                offset_x = dy * math.sin(rot / 180 * math.pi)
                offset_y = dy * math.cos(rot / 180 * math.pi)
                y += offset_y
                if top_side:
                    x -= offset_x  # Note: minus sign because we're going in the opposite direction
                else:
                    x += offset_x # the board is mirrored, so compensate in the positive direction
            except:
                self._export_cpl_command.ui.messageBox(f'{component['name']} has a vertical fix defined in its "{vertical_fix_attribute}" attribute, but it is not a valid length! It is ignored and no vertical correction is applied!',
                                   'Vertical fix parsing error', adsk.core.MessageBoxButtonTypes.OKButtonType, adsk.core.MessageBoxIconTypes.WarningIconType) # type: ignore


        if rotation_fix_used and rotation_fix_value:
            rotation_fix = float(rotation_fix_value[0])
            if rotation_fix < 0:
                rotation_fix += 360.0
        
        rot += rotation_fix
        while (rot >= 360.0):
            rot -= 360.0

        return (x, y, rot)