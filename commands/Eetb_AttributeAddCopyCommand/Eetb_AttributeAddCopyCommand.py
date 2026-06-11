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

import json
import os
import adsk.core
from enum import Enum

from ..CommandBase import CommandBase
from ..PaletteCommandBase import PaletteCommandBase
from ... import config
from ... import controls as eetbControls
from ...lib import eetbUtils as eetbutil
from ...lib import fusionAddInUtils as futil

class Eetb_AttributeAddCopyCommand(PaletteCommandBase):
    
    class CopyType(Enum):
        OVERWRITE_AND_DELETE = "overwrite-and-delete"
        OVERWRITE_AND_KEEP = "overwrite-and-keep"
        ONLY_ADD_NEW = "only-add-new"


    def __init__(self, is_copy_operation: bool):
        if is_copy_operation:
            command_description: str = 'Copy all attributes from a source part to one or more target parts'
        else:
            command_description: str = 'Add a new attribute to one or more parts'

        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_attribute_{'copy' if is_copy_operation else 'add'}_command_id',
            command_name = f'Bulk {'copy' if is_copy_operation else 'add'} attributes',
            command_description = command_description,
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'),
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'copy' if is_copy_operation else 'add'))
                
        palette_attributes = PaletteCommandBase.MandatoryPaletteCommandAttributes(
            basic_attributes = command_attributes,
            palette_id =  f'{config.ADDIN_NAME}_attribute_{'copy' if is_copy_operation else 'add'}_palette_id',
            palette_name = f'Bulk {'copy' if is_copy_operation else 'add'} attribute',
            palette_docking = adsk.core.PaletteDockingStates.PaletteDockStateFloating, # type: ignore
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'palette.html'))
        super().__init__(palette_attributes)

        self._script_export_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}.scr')
        self._is_copy_operation = is_copy_operation
        self.palette_show_close_button = False
        self.palette_is_persistent = False


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        eetbControls.add_command_to_panel(config.ELECTRON_SCHEMATIC_ENV_ID, eetbControls.SchematicPanel.ATTRIBUTES_PANEL, commandDefinition)
        eetbControls.add_command_to_panel(config.ELECTRON_LAYOUT_ENV_ID,    eetbControls.LayoutPanel.ATTRIBUTES_PANEL,    commandDefinition)


    def html_event_handler(self, palette: adsk.core.Palette, event_name: str, event_data = {}):
        """Handles events coming from the HTML palette specific to this command.

        This function is called when an event is triggered from the HTML side of the palette.
        It processes the event and performs the necessary actions based on the event name.
        It overrides the base class method as required by the base class


        Args:
            palette (adsk.core.Palette): The palette that triggered the event.
            event_name (str): The name of the event that was triggered.
            event_data (dict, optional): Additional data associated with the event. Defaults to {}.
        """
        if event_name == 'okButtonClicked':
            self._handle_operation(event_data)
            self.close_palette()


    def palette_ready_event_handler(self, palette: adsk.core.Palette):
        """Handles the palette ready event.

        This function is called when the palette is fully initialized and ready for interaction.
        It can be used to perform any setup or initialization tasks that require the palette to be active.
        It overrides the base class method as required by the base class

        Args:
            palette (adsk.core.Palette): The palette that triggered the event.
        """
        formParams: dict = {"isCopyOperation":  self._is_copy_operation,
                            "isLayoutDocument": self._app.activeDocument.dataFile.fileExtension == 'fbrd'}
        palette.sendInfoToHTML('setFormParams', json.dumps(formParams))
        palette_init_data = self.get_eagle_data([{'type': eetbutil.ExportDataType.PART_LIST.value, 'args': []}, 
                                                 {'type': eetbutil.ExportDataType.PART_SELECTION.value, 'args': []}])
        palette.sendInfoToHTML('setEagleData', json.dumps(palette_init_data))


    ###################
    # EVENT FUNCTIONS #
    ###################

    def on_command_execute(self, args: adsk.core.CommandEventArgs):
        """Executes the command when triggered.

        See the base class for details.

        Args:
            args (adsk.core.CommandEventArgs): The command execution arguments.
        """
        super().on_command_execute(args)
        palette: adsk.core.Palette = self.ui.palettes.itemById(self.palette_id)
        if palette:
            self.local_handlers.append(futil.add_handler(palette.navigatingURL, self.on_palette_navigatingURL))


    def on_palette_navigatingURL(self, args: adsk.core.NavigationEventArgs):
        """Handles navigation events from the palette's web view.

        This method is invoked when the user interacts with links or navigates within the HTML palette.
        It allows for custom handling of navigation events, such as intercepting clicks on buttons or links
        and performing actions based on the URL or event data.

        Args:
            args (adsk.core.NavigationEventArgs): The navigation event arguments containing information
                about the navigation action, such as the URL being navigated to.
        """
        args.launchExternally = True


    def on_command_destroy(self, args: adsk.core.CommandEventArgs):
        """
        Event handler for when the command is destroyed.

        See the base class method for full details.

        Args:
            args: CommandEventArgs
        """
        try:
            if os.path.exists(self._script_export_path):
                os.remove(self._script_export_path)
        except Exception as e:
            self.log_error_to_ui(f"Error deleting script file: {str(e)}")
        
        super().on_command_destroy(args)


    #####################
    # PRIVATE FUNCTIONS #
    #####################

    def _attribute_exists_in_part(self, part_data: dict, attribute_name: str) -> bool:
        """Check if an attribute exists in a part.

        Args:
            part_data (dict): Part data including attributes
            attribute_name (str): Name of the attribute to check

        Returns:
            bool: True if attribute exists, False otherwise
        """
        attributes = part_data.get('attributes', [])
        return any(attr.get('name', '').lower() == attribute_name.lower() for attr in attributes)


    def _get_display_type(self, display_name: bool, display_value: bool):
        """Determine the display type based on whether name and value should be shown.

        Args:
            display_name (bool): Whether to display the attribute name.
            display_value (bool): Whether to display the attribute value.

        Returns:
            str: The display type string indicating which parts to show.
        """
        if display_name and display_value:
            return "BOTH"
        elif display_name:
            return "NAME"
        elif display_value:
            return "VALUE"
        else:
            return "OFF"
        

    def _add_attribute(self, outfile, partName: str, attrName: str, attrValue: str, displayType: str, sheetNum: int):
        """Adds an attribute to a part in the script file.

        This function writes a command to the output file to add or update an attribute
        on a specified part within a Fusion 360 script.

        Args:
            outfile: The file object to write the command to.
            partName (str): The name of the part to add the attribute to.
            attrName (str): The name of the attribute to add.
            attrValue (str): The value of the attribute to add.
            displayType (str): The display type for the attribute (e.g., "BOTH", "NAME", "VALUE").
            sheetNum (int): The sheet number associated with the part.
        """
        # update the display type first
        if displayType != self._last_display_type:
            outfile.write(f"CHANGE DISPLAY {displayType};\n")                             
            self._last_display_type = displayType

        if self._last_sheet != sheetNum:
            outfile.write(f"EDIT .s{sheetNum};\n")
            self._last_sheet = sheetNum

        outfile.write(f"ATTRIBUTE {partName} {attrName.upper()} '{attrValue}';\n")


    def _delete_attribute(self, outfile, partName: str, attrName: str, sheetNum: int):
        """Deletes an attribute from a part in the script file.

        This function writes a command to the output file to delete an attribute
        from a specified part within a Fusion 360 script.

        Args:
            outfile: The file object to write the command to.
            partName (str): The name of the part to delete the attribute from.
            attrName (str): The name of the attribute to delete.
            sheetNum (int): The sheet number associated with the part.
        """
        # Ensure we are on the correct sheet
        if self._last_sheet != sheetNum:
            outfile.write(f"EDIT .s{sheetNum};\n")
            self._last_sheet = sheetNum

        # Delete the attribute from the part
        outfile.write(f"ATTRIBUTE {partName} {attrName.upper()} DELETE;\n")


    def _handle_operation(self, event_data: dict):
        """Handles the operation based on the event data received from the HTML palette.

        This method processes the event data to determine the source part, target parts,
        and the type of operation (copy or add). It then performs the necessary actions
        to copy or add attributes to the target parts.

        Args:
            event_data (dict): The data received from the HTML palette event.
        """
        try:
            # Get the attribute data
            add_attribute_name = event_data.get('attribute_name', '')
            add_attribute_value = event_data.get('attribute_value', '')
            source_part = event_data.get('source_part')
            target_parts = event_data.get('target_parts', [])
            add_type_overwrite = event_data.get('overwrite_existing', False)
            copy_type = event_data.get('copy_type', '')
            copy_value = event_data.get('copy_value', False)
            
            if self._is_copy_operation:
                if not source_part or not target_parts:
                    self.log_error_to_ui("Invalid operation data: missing source or target parts")
                    return
            else:
                if not add_attribute_name or not add_attribute_value or not target_parts:
                    self.log_error_to_ui("Invalid operation data: missing attribute name, value or target parts")
                    return
            
            # Query for part data for all affected parts
            affected_parts = target_parts
            if self._is_copy_operation:
                affected_parts += [source_part]
            exported_eagle_data = self.get_part_data(affected_parts)
            part_data = exported_eagle_data.get(eetbutil.ExportDataType.PART_DATA.value, [])
            
            source_part_info = next((part for part in part_data if part.get('name') == source_part), {})
            source_attributes = []
            if self._is_copy_operation:
                # First, get the source part attributes
                source_attributes = source_part_info.get('attributes', [])
                if not source_attributes:
                    self.log_error_to_ui(f"No attributes found in source part {source_part}")
                    return

            # Group target parts by sheet number to minimize sheet switching
            sheet_parts = {}
            for part_name in target_parts:
                target_part_info = next((part for part in part_data if part.get('name') == part_name), None)
                if not target_part_info:
                    continue  # Skip if part not found

                sheet_num = target_part_info['first_sheet']
                if sheet_num not in sheet_parts:
                    sheet_parts[sheet_num] = []
                sheet_parts[sheet_num].append(target_part_info)

            # Sort sheets numerically to ensure consistent order
            sorted_sheets = sorted(sheet_parts.keys(), key=lambda x: int(x))

            # Generate the script
            with open(self._script_export_path, 'w') as f:
                f.write("CHANGE DISPLAY OFF;\n")
                self._last_display_type = 'OFF'
                self._last_sheet = 0

                # Iterate through sheets and parts to minimize sheet switching
                for sheet_num in sorted_sheets:
                    for target_part_info in sheet_parts[sheet_num]:
                        if self._is_copy_operation:
                            # overwrite value from source part on request
                            if copy_value:
                                f.write(f"VALUE {target_part_info['name']} '{source_part_info['value']}';\n")

                            # Copy each attribute from source to target
                            for attr in source_attributes:
                                attr_name = attr.get('name', '')
                                attr_value = attr.get('value', '')

                                # Skip if attribute name is NAME or VALUE
                                if attr_name in ['NAME', 'VALUE']:
                                    continue

                                # add or overwrite existing attribute
                                if not self._attribute_exists_in_part(target_part_info, attr_name) or copy_type != self.CopyType.ONLY_ADD_NEW.value:
                                    display_type = self._get_display_type(attr['display_name'], attr['display_value'])
                                    self._add_attribute(f, target_part_info['name'], attr_name, attr_value, display_type, target_part_info['first_sheet'])

                            if copy_type == self.CopyType.OVERWRITE_AND_DELETE.value:
                                target_attributes = target_part_info.get('attributes', [])
                                source_attribute_names = [attr.get('name') for attr in source_attributes]  # Get all source attribute names
                                for attr in target_attributes:
                                    if attr['name'] in ['NAME', 'VALUE']:
                                        continue
                                    if attr['name'] not in source_attribute_names:
                                        self._delete_attribute(f, target_part_info['name'], attr['name'], target_part_info['first_sheet'])
                        
                        # handle add operation
                        elif add_type_overwrite or not self._attribute_exists_in_part(target_part_info, add_attribute_name):
                            self._add_attribute(f, target_part_info['name'], add_attribute_name, add_attribute_value, 'OFF', target_part_info['first_sheet'])
            
            # Execute the script
            self.log_to_console(f"Successfully generated add script at {self._script_export_path}")
            self.run_eagle_script(self._script_export_path)
            
        except Exception as e:
            self.log_to_console(f"Error in {'copy' if self._is_copy_operation else 'add'} operation:\n{self.get_error_reason()}")