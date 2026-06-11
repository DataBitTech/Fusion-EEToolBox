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


from copy import deepcopy
import adsk.core
import traceback
import os
import math

from ... import config, controls
from ..CommandBase import CommandBase
from ..Eetb_ExecuteEagleScriptCommand.Eetb_ExecuteEagleScriptCommand import Eetb_ExecuteEagleScriptCommand
from ...lib import fusionAddInUtils as futil
from ...lib import eetbUtils as eetbutil

class Eetb_FixLineConnectionsCommand(CommandBase):

    def __init__(self, execute_script_command: Eetb_ExecuteEagleScriptCommand):
        
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_fix_line_connections_command_id',
            command_name = 'Fix line connections',
            command_description = 'Connected neighbouring line endings ',
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources'),
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'))
        super().__init__(command_attributes)

        self._script_export_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}.scr')
        self._execute_script_command = execute_script_command

        self._epsilon_value_input: adsk.core.DistanceValueCommandInput
        self._layer_selection_input: adsk.core.DropDownCommandInput
        self._layer_geometry: dict


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        controls.add_command_to_panel(config.ELECTRON_LAYOUT_ENV_ID, controls.LayoutPanel.REWORK_PANEL, commandDefinition)


    def _create_UI(self, command, inputs):
            """
            Create the face selection input for the command.
            This should be called when setting up the command UI.
            
            Args:
                command: The Command object
                inputs: The CommandInputs collection
            
            Returns:
                The face selection input
            """
            # Create a selection input for faces
            self._epsilon_value_input = inputs.addDistanceValueCommandInput('epsilon', 'Effect radius', adsk.core.ValueInput.createByReal(0.001))
            self._layer_selection_input = inputs.addDropDownCommandInput('layer_selection', 'On layer', adsk.core.DropDownStyles.TextListDropDownStyle)


    def _initialize_UI(self):
        """Initialize the UI elements for the command.

        This method sets up the dropdown list for layer selection
        and prepares the UI for user interaction.
        """
        layer_data = self.get_layer_data()
        layers_to_query = []
        for layer in layer_data.get('layer_data', []):
            layer_num = int(layer.get('number'))
            # Dimension layer and used layers upwards from Milling
            if  layer_num == 20 or (layer_num >= 46 and layer_num < 256):
                self._layer_selection_input.listItems.add(f'{layer_num} - {layer.get('name')}', False, '')
                layers_to_query.append(layer_num)
        geo_data = self.get_geometry_data(layers_to_query)
        self._layer_geometry = geo_data.get('geometry_data', {})

        if self._layer_selection_input.listItems.count:
            self._layer_selection_input.listItems[0].isSelected = True            


    def on_command_created(self, args: adsk.core.CommandCreatedEventArgs):
        """
        Event handler for when the command is created.

        See the base class method for full details.
        
        Args:
            args: CommandCreatedEventArgs
        """
        super().on_command_created(args)
        try:
            cmd = args.command
            inputs = cmd.commandInputs
            
            # Create face selection input
            self._create_UI(cmd, inputs)
            self._initialize_UI()

            # Set command properties
            cmd.isRepeatable = False
            cmd.isExecutedWhenPreEmpted = False
            
        except Exception as e:
            self.log_error_to_ui(f"Error creating command: {self.get_error_reason()}")


    def on_command_execute(self, args: adsk.core.CommandEventArgs):
        """
        Event handler for when the command is executed.

        See the base class method for full details.
        
        Args:
            args: CommandEventArgs
        """
        if not self._epsilon_value_input.isValid:
            self.log_error_to_ui('Please set a valid effect radius')
            return
        
        try:  
            epsilon_mm = float(self._epsilon_value_input.value)  * 10
            layer_number = int(self._layer_selection_input.selectedItem.name.split(' ')[0])

            wires_on_layer = []
            for wire in self._layer_geometry['wires']:
                if wire['layer'] == layer_number:
                    wires_on_layer.append(wire)

            if not wires_on_layer:
                self.log_to_console(f'No wires found on the selected layer.')
                return

            checked_wires = []
            moved_wires: list[tuple] = []
            for wire in wires_on_layer:
                
                for checked_wire in checked_wires:
                    if  (checked_wire['x1'] == wire['x1'] and checked_wire['y1'] == wire['y1']) or \
                        (checked_wire['x2'] == wire['x2'] and checked_wire['y2'] == wire['y2']) or \
                        (checked_wire['x1'] == wire['x2'] and checked_wire['y1'] == wire['y2']) or \
                        (checked_wire['x2'] == wire['x1'] and checked_wire['y2'] == wire['y1']):
                        continue
                        
                    checked_p1 = (checked_wire['x1'], checked_wire['y1'])
                    checked_p2 = (checked_wire['x2'], checked_wire['y2'])
                    wire_p1 = (wire['x1'], wire['y1'])
                    wire_p2 = (wire['x2'], wire['y2'])

                    if math.dist(checked_p1, wire_p1) < epsilon_mm:
                        moved_wire = deepcopy(wire)
                        moved_wire['x1'] = checked_wire['x1']
                        moved_wire['y1'] = checked_wire['y1']
                        moved_wires.append((wire, moved_wire))
                    elif math.dist(checked_p2, wire_p1) < epsilon_mm:
                        moved_wire = deepcopy(wire)
                        moved_wire['x1'] = checked_wire['x2']
                        moved_wire['y1'] = checked_wire['y2']
                        moved_wires.append((wire, moved_wire))
                    elif math.dist(checked_p1, wire_p2) < epsilon_mm:
                        moved_wire = deepcopy(wire)
                        moved_wire['x2'] = checked_wire['x1']
                        moved_wire['y2'] = checked_wire['y1']
                        moved_wires.append((wire, moved_wire))
                    elif math.dist(checked_p2, wire_p2)  < epsilon_mm:
                        moved_wire = deepcopy(wire)
                        moved_wire['x2'] = checked_wire['x2']
                        moved_wire['y2'] = checked_wire['y2']
                        moved_wires.append((wire, moved_wire))
                
                checked_wires.append(wire)
            
            if moved_wires:
                # # Group copied wires into contiguous lines
                # contiguous_lines: list[list[dict]] = []
                # for wire in copied_wires:
                #     added_to_line = False
                #     for line_segments in contiguous_lines:
                #         if wire['x1'] == line_segments[-1]['x2'] and wire['y1'] == line_segments[-1]['y2']:
                #             line_segments.append(wire)
                #             added_to_line = True
                #             break
                #         elif wire['x2'] == line_segments[0]['x1'] and wire['y2'] == line_segments[0]['y1']:
                #             line_segments.insert(0, wire)
                #             added_to_line = True
                #             break
                #     if not added_to_line:
                #         contiguous_lines.append([wire])

                # first remove all on this layer - the easiest way is to redraw the entire layer
                with open(self._script_export_path, 'w') as f:
                    f.write(f'DISPLAY NONE {layer_number};\n')
                    f.write(f'CHANGE LAYER {layer_number};\n')

                    for (original_wire, moved_wire) in moved_wires:
                        if original_wire['x1'] != moved_wire['x1'] or original_wire['y1'] != moved_wire['y1']:
                            f.write(f'DELETE ({original_wire['x1']} {original_wire['y1']});\n')
                        else:
                            f.write(f'DELETE ({original_wire['x2']} {original_wire['y2']});\n')
                        f.write(f'LINE {moved_wire['width']} ({moved_wire['x1']} {moved_wire['y1']}) {moved_wire['curve']:+} ({moved_wire['x2']} {moved_wire['y2']});\n')
                
                self.log_to_console(f'Successfully generated script at {self._script_export_path}')
                self._execute_script_command.run_script(self._script_export_path)
        except:
            self.log_error_to_ui(CommandBase.get_error_reason())


    def stop(self) -> None:
        """Stops the command and performs any necessary cleanup."""
        try:
            if os.path.exists(self._script_export_path):
                os.remove(self._script_export_path)
        except Exception as e:
            self.log_error_to_ui(f"Error deleting script file: {str(e)}")
        
        super().stop()