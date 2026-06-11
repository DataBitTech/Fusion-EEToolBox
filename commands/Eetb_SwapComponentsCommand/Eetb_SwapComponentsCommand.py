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

import json
import os
import adsk.core
from ..CommandBase import CommandBase
from ..PaletteCommandBase import PaletteCommandBase
from ... import config
from ... import controls as eetbControls
from ...lib import eetbUtils as eetbutil

class Eetb_SwapComponentsCommand(PaletteCommandBase):

    def __init__(self):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_swap_components_command_id',
            command_name = 'Swap components',
            command_description = 'Swap component placement',
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'),
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources'))

        palette_attributes = PaletteCommandBase.MandatoryPaletteCommandAttributes(
            basic_attributes = command_attributes,
            palette_id =  f'{config.ADDIN_NAME}_swap_components_palette_id',
            palette_name = f'Swap component placement',
            palette_docking = adsk.core.PaletteDockingStates.PaletteDockStateFloating, # type: ignore
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'palette.html'))
        super().__init__(palette_attributes)

        self.palette_show_close_button = False
        self._script_export_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}.scr')


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        eetbControls.add_command_to_panel(config.ELECTRON_LAYOUT_ENV_ID, eetbControls.LayoutPanel.REWORK_PANEL, commandDefinition)


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
            # first get the signal data
            exported_eagle_data = self.get_eagle_data([ {'type': eetbutil.ExportDataType.PART_DATA.value, 'args': event_data.get("parts_to_swap", [])} ])
            errorMsg = self._generate_eagle_script(exported_eagle_data, event_data.get("part_rotation_option", str), event_data.get("part_mirroring_option", str))
            if errorMsg != '':
                self.log_error_to_ui(errorMsg)
            else:
                PaletteCommandBase.log_to_console(f"Running {self._script_export_path}")
                self.run_eagle_script(self._script_export_path)
            self.close_palette()


    def palette_ready_event_handler(self, palette: adsk.core.Palette):
        """Handles the palette ready event.

        This function is called when the palette is fully initialized and ready for interaction.
        It can be used to perform any setup or initialization tasks that require the palette to be active.
        It overrides the base class method as required by the base class

        Args:
            palette (adsk.core.Palette): The palette that triggered the event.
        """
        palette_init_data = self.get_eagle_data([{'type': eetbutil.ExportDataType.PART_LIST.value, 'args': []}, 
                                                 {'type': eetbutil.ExportDataType.PART_SELECTION.value, 'args': []}])
        palette.sendInfoToHTML('setEagleData', json.dumps(palette_init_data))


    def _generate_eagle_script(self, exported_eagle_data: dict, part_rotation_option: str, part_mirroring_option: str) -> str:
        """Generates an Eagle script to swap component placements based on the provided data and options.

        This function takes exported Eagle data and applies the specified rotation and mirroring options
        to generate a script that can be executed in Eagle to perform the component swaps.

        Args:
            exported_eagle_data (dict): The data exported from Eagle containing component information.
            part_rotation_option (str): The rotation option to apply to the components.
            part_mirroring_option (str): The mirroring option to apply to the components.

        Returns:
            str: An error message if the script generation fails, otherwise an empty string.
        """
        try:
            part_data = exported_eagle_data.get(eetbutil.ExportDataType.PART_DATA.value, [])

            part_a = part_data[0]
            part_b = part_data[1]

            signal_a_name = part_a["name"]
            signal_b_name = part_b["name"]

            with open(self._script_export_path, 'w') as f:
                f.write("GRID 0.1 mm;\n")

                f.write(f'MOVE {signal_a_name} ({part_b["x"]} {part_b["y"]});\n')
                f.write(f'MOVE {signal_b_name} ({part_a["x"]} {part_a["y"]});\n')
                if part_rotation_option != 'none':
                    rotate_a = float(part_b["angle"])
                    rotate_b = float(part_a["angle"])
                    part_a_mirror_str = '' 
                    part_b_mirror_str = ''
                    if part_rotation_option == 'antisymmetric':
                         rotate_a = (rotate_a + 180) % 360
                         rotate_b = (rotate_b + 180) % 360
                    if part_mirroring_option == 'transfer':
                        part_a_mirror_str = 'M' if part_b["mirror"] else '' 
                        part_b_mirror_str = 'M' if part_a["mirror"] else ''
                    elif part_mirroring_option == 'keep':
                        part_a_mirror_str = 'M' if part_a["mirror"] else '' 
                        part_b_mirror_str = 'M' if part_b["mirror"] else ''
                    elif part_mirroring_option == 'antisymmetric':
                        part_a_mirror_str = 'M' if not part_b["mirror"] else '' 
                        part_b_mirror_str = 'M' if not part_a["mirror"] else ''
                    f.write(f"ROTATE ={part_a_mirror_str}R{rotate_a} '{signal_a_name}';\n")
                    f.write(f"ROTATE ={part_b_mirror_str}R{rotate_b} '{signal_b_name}';\n")
                f.write("\nGRID LAST;\n")

            PaletteCommandBase.log_to_console(f'Successfully generated script at {self._script_export_path}')

        except FileNotFoundError:
            return f"Error: temporary file not found"
        except Exception as e:
            return f"An error occurred: {e}"
        
        return ''
    

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
