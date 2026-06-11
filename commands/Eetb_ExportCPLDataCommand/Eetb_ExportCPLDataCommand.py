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

import math, os
from pathlib import Path
import adsk.core

from ..CommandBase import CommandBase
from ..PartDataExportCommandBase import PartDataExportCommandBase
from ..Eetb_EditUserScriptCommand.Eetb_EditUserScriptCommand import Eetb_EditUserScriptCommand
from ... import config
from ... import controls as eetbControls
from ...lib import eetbUtils as eetbutil
from ...lib import fusionAddInUtils as futil

class Eetb_ExportCPLDataCommand(PartDataExportCommandBase):

    def __init__(self, edit_user_script_command: Eetb_EditUserScriptCommand):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_export_cpl_data_command_id',
            command_name = 'Export placement data',
            command_description = 'Export component placement data in manufacturer specific formats',
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'),
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources'))
        super().__init__(command_attributes, edit_user_script_command)
        
        self._rotation_attribute_selection_input: adsk.core.DropDownCommandInput
        self._horizontal_attribute_selection_input: adsk.core.DropDownCommandInput
        self._vertical_attribute_selection_input: adsk.core.DropDownCommandInput

        self.default_attribute_mapping = [
            # column to map to attribute    optional?
            ('Rotation fix',             True),
            ('Horizontal position fix',  True),
            ('Vertical position fix',    True)
        ]
        self.macrofab_attribute_mapping = self.default_attribute_mapping.copy()
        self.macrofab_attribute_mapping.append(('Populate',  True))
        self.macrofab_attribute_mapping.append(('MPN',       True))

        self.add_supported_format('Raw',            None,                               self.export_raw)
        self.add_supported_format('EuroCircuits',   self.default_attribute_mapping,     self.export_EuroCircuits)
        self.add_supported_format('JLCPCB',         self.default_attribute_mapping,     self.export_JLCPCB)
        self.add_supported_format('Macrofab',       self.macrofab_attribute_mapping,    self.export_Macrofab, PartDataExportCommandBase.FileExtensions.FILE_EXTENSION_CUSTOM)


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        eetbControls.add_command_to_panel(config.ELECTRON_LAYOUT_ENV_ID, eetbControls.LayoutPanel.EXPORT_PANEL, commandDefinition)


    def on_command_created(self, args: adsk.core.CommandCreatedEventArgs):
        """
        Override the base class command creation event, to update the mapping help.
        For detailed information see the base class.
        """
        super().on_command_created(args)
        self.mapping_help.text = 'Fix component origin/rotation mismatch with (potentially fabhouse specific) attributes' 


    def get_user_script_input_data(self, filtered_part_data: list[dict], output_format: str) -> list[list[str]]:
        """NOT IMPLEMENTED YET"""
        # we should define a standard output format first
        raise NotImplementedError('Not implemented yet')
      

    def _apply_corrections(self, component: dict) -> tuple [float, float, float]:
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
        rotation_fix_used = self.get_selected_attribute(self.default_attribute_mapping[0]) != 'None'
        horizontal_fix_used = self.get_selected_attribute(self.default_attribute_mapping[1]) != 'None'
        vertical_fix_used = self.get_selected_attribute(self.default_attribute_mapping[2]) != 'None'

        # now handle the position/rotation fix
        x = component['x']
        y = component['y']
        rot = component['angle']
        rotation_fix = 0.0

        attributes = component.get('attributes',[])
        fix_values = self.get_mapped_attribute_values(self.default_attribute_mapping, attributes)

        if horizontal_fix_used and fix_values[1]:
            x += float(fix_values[1]) * math.cos(rot / 180 * math.pi)
            y -= float(fix_values[1]) * math.sin(rot / 180 * math.pi)
        if vertical_fix_used and fix_values[2]:
            x -= float(fix_values[2]) * math.sin(rot / 180 * math.pi)
            y += float(fix_values[2]) * math.cos(rot / 180 * math.pi)
        if rotation_fix_used and fix_values[0]:
            rotation_fix = float(fix_values[0])
            if rotation_fix < 0:
                rotation_fix += 360.0
        
        rot += rotation_fix
        while (rot >= 360.0):
            rot -= 360.0

        return (x, y, rot)
    

    def _convert_mm_to_mil(self, mm: float) -> float:
        """
        Convert millimeters to mils (thousandths of an inch).

        Args:
            mm (float): Value in millimeters

        Returns:
            float: Value in mils
        """
        # 1 inch = 25.4 mm, 1 inch = 1000 mils
        # So 1 mm = 1000/25.4 mils
        mils_per_mm = 1000.0 / 25.4
        return mm * mils_per_mm


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


    def _get_package_bounding_box(self, package_name: str) -> tuple[float, float] | None:
        """
        Find the package in self.package_data and compute its bounding box size (width, height)
        based on the 'contacts' (pads and smds).

        Pads have 'x', 'y', 'diameter' properties (treated as circles).
        Smds have 'x', 'y', 'dx', 'dy', and optionally 'angle' properties (rectangles, possibly rotated).

        Args:
            package_name (str): The name of the package to search for.

        Returns:
            tuple[float, float]: Width and height of the bounding box in mm, or None if package not found.
        """
        # Find the package in self.package_data
        package = next((pkg for pkg in self.package_data if pkg.get('name') == package_name), None)
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


    ###########################
    # FAB SPECIFIC FORMATTING #
    ###########################

    def export_EuroCircuits(self, format_name: str, filtered_part_data: list[dict]) -> list[list[str]]:
        """Exports component placement data in EuroCircuits format.

        This function takes the filtered part data and formats it according to the EuroCircuits
        specification. It includes component reference, value, package, position (X, Y), rotation,
        and layer information. It also applies corrections to the output data, if the user specified
        the required attributes for that.

        Args:
            format_name (str): The name of the format being exported (used for logging).
            filtered_part_data (list[dict]): A list of dictionaries containing component data.

        Returns:
            list[list]: A list of lists representing the formatted data rows for EuroCircuits.
        """
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
            
            (x, y , rot) = self._apply_corrections(component)

            # add to the output
            cpl_data.append([component['name'], comment, 'Bottom' if component['mirror'] else 'Top', f'{x:.3f}', f'{y:.3f}', f'{rot:.2f}', description])
        return cpl_data


    def export_JLCPCB(self, format_name: str, filtered_part_data: list[dict]) -> list[list[str]]:
        """Exports component placement data in JLCPCB format.

        This function takes the filtered part data and formats it according to the JLCPCB
        specification. It includes component reference, value, package, position (X, Y), rotation,
        and layer information. It also applies corrections to the output data, if the user specified
        the required attributes for that.

        Args:
            format_name (str): The name of the format being exported (used for logging).
            filtered_part_data (list[dict]): A list of dictionaries containing component data.

        Returns:
            list[list]: A list of lists representing the formatted data rows for JLCPCB.
        """
        headers = ['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation']
        cpl_data = [headers]
        for component in filtered_part_data:
            (x, y , rot) = self._apply_corrections(component)
            top_side = component['mirror'] == False
            if not top_side:
                rot = (360 - rot)
                rot = rot + 180
                rot = rot % 360

            # add to the output
            cpl_data.append([component['name'], f'{x:.3f}mm', f'{y:.3f}mm', 'Top' if top_side else 'Bottom', f'{round(rot)}'])
        return cpl_data


    def export_Macrofab(self, format_name: str, filtered_part_data: list[dict]) -> list[list[str]]:
        """Exports component placement data in Macrofab format.

        This function takes the filtered part data and formats it according to the Macrofab
        specification. It includes component reference, value, package, position (X, Y), rotation,
        layer information, populate flag, and MPN. It also applies corrections to the output data,
        if the user specified the required attributes for that.

        Since it exports to a custom file type, it needs to handle the file encoding, writing, and
        configuration saving. 

        Args:
            format_name (str): The name of the format being exported (used for logging).
            filtered_part_data (list[dict]): A list of dictionaries containing component data.

        Returns:
            list[list]: an empty list, ignored by the caller.
        """
        headers = ['#Designator', 'X-Loc', 'Y-Loc', 'Rotation', 'Side', 'Type', 'X-Size', 'Y-Size', 'Value', 'Footprint', 'Populate', 'MPN']
        cpl_data = [headers]
        num_default_attributes = len(self.default_attribute_mapping)
        populated_used = self.get_selected_attribute(self.macrofab_attribute_mapping[num_default_attributes]) != 'None'
        mpn_used = self.get_selected_attribute(self.macrofab_attribute_mapping[num_default_attributes + 1]) != 'None'
        for component in filtered_part_data:
            populate = ''
            mpn = ''
            width = 0.0
            height = 0.0
            (x, y , rot) = self._apply_corrections(component)
            top_side = component['mirror'] == False
            attributes = component.get('attributes', [])
            isTHT = self._package_is_THT(component.get('package', ''))
            bounding_box = self._get_package_bounding_box(component.get('package', ''))
            if bounding_box is not None:
                (width, height) = bounding_box
            
            if attributes:
                mapped_values = self.get_mapped_attribute_values(self.macrofab_attribute_mapping, attributes)
                populate = mapped_values[0]
                mpn = mapped_values[1]
            # add to the output
            cpl_data.append([component['name'], f'{self._convert_mm_to_mil(x):.2f}', f'{self._convert_mm_to_mil(y):.2f}', f'{round(rot)}', 
                             'T' if top_side else 'B', '' if isTHT == None else '1' if isTHT == False else '2', 
                             f'{self._convert_mm_to_mil(width):.2f}' if bounding_box is not None else '', 
                             f'{self._convert_mm_to_mil(height):.2f}' if bounding_box is not None else '', 
                             component['value'], component['package'], populate if populated_used else '1', mpn if mpn_used else ''])

        # this format uses a custom file extension, so it is handled here
        extension_filter = "XYRS files (*.XYRS)"

        # Get the last used output file from ConfigManager
        user_selection: dict = eetbutil.config_manager.get_document_option(self.document_id, self.command_id, format_name, {}) # type: ignore
        
        # Create a file dialog for saving results
        fileDialog = self.ui.createFileDialog()
        fileDialog.isMultiSelectEnabled = False
        fileDialog.title = f"Save {format_name} Results"
        fileDialog.filter = extension_filter
        fileDialog.filterIndex = 0

        if user_selection and 'last_output_dir' in user_selection and os.path.exists(user_selection['last_output_dir']):
            fileDialog.initialDirectory = user_selection['last_output_dir'] if os.path.isdir(user_selection['last_output_dir']) else os.path.dirname(user_selection['last_output_dir'])
        else:
            fileDialog.initialDirectory = str(Path.home())
        
        dialogResult = fileDialog.showSave()
        
        if dialogResult == adsk.core.DialogResults.DialogOK:
            output_file = fileDialog.filename + ".XYRS"

            # Write the data to the file based on the format
            file_data = self.format_data_by_extension(cpl_data, PartDataExportCommandBase.FileExtensions.FILE_EXTENSION_TXT.value)
            try:
                with open(output_file, 'wb') as f:
                    f.write(file_data)

                self.log_to_console(f'Results saved to {output_file}')
                self.save_config(format_name, os.path.dirname(output_file))
            except IOError as e:
                self.ui.messageBox(f"Error writing to file {output_file}: {e}")
        
        return []


    def export_raw(self, format_name: str, filtered_part_data: list[dict]) -> list[list[str]]:
        """Exports component placement data in raw format.

        This function takes the filtered part data and formats it as a list of lists,
        where each inner list represents a row of data. The raw format includes
        component reference, value, package, position (X, Y), rotation, and mirror
        information. It does not apply any corrections to the output data

        Args:
            format_name (str): The name of the format being exported (used for logging).
            filtered_part_data (list[dict]): A list of dictionaries containing component data.

        Returns:
            list[list]: A list of lists representing the formatted data rows for raw export.
        """
        headers = ['Designator', 'Value', 'Footprint', 'Center X', 'Center Y', 'Rotation', 'Side']
        for attribute in self.attribute_list:
            headers.append(attribute)
        cpl_data = [headers]
        for component in filtered_part_data:
            row = [component['name'], 
                   component['value'], 
                   component['package'], 
                   f'{component['x']:.3f}', 
                   f'{component['y']:.3f}',
                   f'{component['x']:.2f}', 
                   'Bottom' if component['mirror'] else 'Top']
            for attribute in self.attribute_list:
                row.append(component.get(attribute, ''))
            cpl_data.append(row)
        return cpl_data
