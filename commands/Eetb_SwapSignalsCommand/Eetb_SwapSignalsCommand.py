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

import json, os
import adsk.core
from collections import defaultdict

from ..CommandBase import CommandBase
from ..PaletteCommandBase import PaletteCommandBase
from ... import config
from ... import controls as eetbControls
from ...lib import eetbUtils as eetbutil

class Eetb_SwapSignalsCommand(PaletteCommandBase):

    def __init__(self):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_swap_signals_command_id',
            command_name = 'Swap signals',
            command_description = 'Swap signal routing',
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'),
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources'))

        palette_attributes = PaletteCommandBase.MandatoryPaletteCommandAttributes(
            basic_attributes = command_attributes,
            palette_id =  f'{config.ADDIN_NAME}_swap_signals_palette_id',
            palette_name = f'Swap signal routing',
            palette_docking = adsk.core.PaletteDockingStates.PaletteDockStateFloating, # type: ignore
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'palette.html'))
        super().__init__(palette_attributes)

        self._script_export_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}.scr')
        self.palette_show_close_button = False


    # add button to the UI
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
            exported_eagle_data = self.get_eagle_data(  [ {'type': eetbutil.ExportDataType.SIGNAL_DATA.value, 'args': event_data.get("signals_to_swap", [])}, 
                                                          {'type': eetbutil.ExportDataType.LAYER_DATA.value, 'args': []} 
                                                        ])
            errorMsg = self._generate_eagle_script(exported_eagle_data, event_data.get("selected_layers", []), event_data.get("via_swap_option", str))
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
        palette_init_data = self.get_eagle_data([{'type': eetbutil.ExportDataType.SIGNAL_LIST.value, 'args': []}, 
                                                 {'type': eetbutil.ExportDataType.SIGNAL_SELECTION.value, 'args': []},
                                                 {'type': eetbutil.ExportDataType.LAYER_DATA.value, 'args': []}])
        palette.sendInfoToHTML('setEagleData', json.dumps(palette_init_data))


    def _generate_eagle_script(self, exported_eagle_data: dict, layers_to_swap: list[int], via_swap_option: str) -> str:
        """Generates an Eagle script to swap signals on specified layers.

        This function takes exported Eagle data, the layers to swap signals on, and a via swap option
        to create an Eagle script that performs the signal swapping operation.

        Args:
            exported_eagle_data (dict): The data exported from Eagle containing signal and layer information.
            layers_to_swap (list[int]): A list of layer numbers to perform the signal swap on.
            via_swap_option (str): The option for handling via swapping during the signal swap.

        Returns:
            str: An error message if the script generation fails, otherwise an empty string.
        """
        try:
            signal_data = exported_eagle_data.get(eetbutil.ExportDataType.SIGNAL_DATA.value, [])
            layer_data = exported_eagle_data.get(eetbutil.ExportDataType.LAYER_DATA.value, [])

            visible_layers = []
            # layer setup - save visible layers, restore them in the end -> speeds up the script
            for layer in layer_data:
                if layer["visible"]:
                    layer_number = int(layer["number"])
                    # HACK: filter layer 23 and 24 from the visible list (tOrigins, bOrigins), because it cannot be accessed in Fusion
                    if layer_number != 23 and layer_number != 24:
                        visible_layers.append(layer_number)

            # signal setup
            if len(signal_data) < 2:
                return "Error: one of the signals was not found"

            signal_a = signal_data[0]
            signal_b = signal_data[1]

            signal_a_name = signal_a["name"]
            signal_b_name = signal_b["name"]

            # Collect all wires grouped by layer -> speeds up the script
            wires_by_layer = defaultdict(list)
            swap_endpoints = set()

            # Process the first two signals
            for signal in [signal_a, signal_b]:
                original_signal_name = signal["name"]
                
                for wire in signal.get("wires", []):
                    wire_layer = wire["layer"]
                    
                    if wire_layer > 16 and wire_layer <= 256:
                        continue
                    wires_by_layer[wire_layer].append((wire, original_signal_name))
                   
                    if wire_layer in layers_to_swap and via_swap_option == 'connected':
                        swap_endpoints.add((wire['x1'], wire['y1']))
                        swap_endpoints.add((wire['x2'], wire['y2']))
            
            # Collect all vias grouped by drill -> speeds up the script
            vias_by_drill = defaultdict(list)

            for signal in [signal_a, signal_b]:
                original_signal_name = signal["name"]
                
                for via in signal.get("vias", []):
                    x, y = via['x'], via['y']
                    if (via_swap_option == 'connected' and (x, y) in swap_endpoints) or via_swap_option == 'all':
                        if original_signal_name == signal_b_name:
                            signal_name = signal_a_name
                        else:
                            signal_name = signal_b_name
                    else:
                        signal_name = original_signal_name
                    vias_by_drill[via['drill']].append((via, signal_name))

            # Write to file, minimizing layer switches, drill switches, displayed layers
            with open(self._script_export_path, 'w') as f:
                f.write("GRID 0.1 mm;\n")
                f.write(f"RIPUP '{signal_a_name}';\n")
                f.write(f"RIPUP '{signal_b_name}';\n")

                for layer in wires_by_layer:
                    f.write("DISPLAY NONE;\n");
                    f.write(f"LAYER {layer};\n")
                    for wire, original_signal_name in wires_by_layer[layer]:
                        if layer in layers_to_swap:
                            if original_signal_name == signal_b_name:
                                signal_name = signal_a_name
                            else:
                                signal_name = signal_b_name
                        else:
                            signal_name = original_signal_name
                        f.write(f"LINE '{signal_name}' {wire['width']} ({wire['x1']} {wire['y1']}) {wire['curve']:+f} ({wire['x2']} {wire['y2']})\n")

                for drill in vias_by_drill:
                    f.write(f"CHANGE DRILL {drill};\n")
                    for via, signal_name in vias_by_drill[drill]:
                        f.write(f"VIA '{signal_name}' {via['start']}-{via['end']} ({via['x']} {via['y']});\n")
            
                # restore settings
                f.write("DISPLAY NONE");
                for layer in visible_layers:
                    f.write(f" {layer}")
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