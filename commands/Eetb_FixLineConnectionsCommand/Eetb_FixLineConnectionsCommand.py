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
from ...lib import treelib

SELECT_GEOMETRY_ULP: str = os.path.join(config.ULP_DIR, 'select_geometry.ulp')

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
        self._grid_unit = eetbutil.parse_length_unit(geo_data.get('unit', 'mm'))

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

            self.local_handlers.append(futil.add_handler(cmd.validateInputs, self.on_validate_inputs))
            
        except Exception as e:
            self.log_error_to_ui(f"Error creating command: {self.get_error_reason()}")


    def on_validate_inputs(self, eventArgs: adsk.core.ValidateInputsEventArgs):
        """Validates the inputs for the command.

        This method is called whenever the command's inputs are changed or validated.
        It performs validation checks on the command's UI elements to ensure that
        all required fields are properly filled and that the values are acceptable
        for the export operation. It updates the UI state and disables the OK button
        if validation fails.

        Args:
            eventArgs: ValidateInputsEventArgs containing the validation event arguments

        Returns:
            None: This method does not return a value.
        """
        if not isinstance(eventArgs.firingEvent.sender, adsk.core.Command):
            raise TypeError("Event sender is not a Command object")

        eventArgs.areInputsValid = self._epsilon_value_input.isValid   # False disables OK button


    def on_command_execute(self, args: adsk.core.CommandEventArgs):
        """
        Event handler for when the command is executed.

        See the base class method for full details.
        
        Args:
            args: CommandEventArgs
        """
        try:  
            epsilon = eetbutil.convert_to_unit((self._epsilon_value_input.value, eetbutil.LengthUnits.CENTIMETER), self._grid_unit)
            layer_number = int(self._layer_selection_input.selectedItem.name.split(' ')[0])

            wires_on_layer = []
            for wire in self._layer_geometry['wires']:
                if wire['layer'] == layer_number:
                    wires_on_layer.append(wire)

            if not wires_on_layer:
                self.log_to_console(f'No wires found on the selected layer.')
                return

            # collect them into trees of connected wires
            wire_trees = eetbutil.build_wire_trees(wires_on_layer)

            # identify the wires to be moved
            wires_to_move = self._find_close_wire_endpoints(wire_trees, epsilon)
            
            if wires_to_move:
                self._write_move_script(wires_to_move)
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


    def _find_close_wire_endpoints(self, wire_trees: list[treelib.Tree], epsilon: float) -> list[dict]:
        """
        Find and fix connections between wires from different trees.
        
        This function identifies potential connections between leaves of different wire trees
        and returns a list of (original_wire, moved_wire) tuples for fixing.
        
        Args:
            wire_trees (list): List of treelib.Tree objects representing connected wire components
            epsilon (float): The epsilon value for connection detection, must be the same unit as the exported data
            
        Returns:
            list[tuple]: List of wires to be moved
        """
        moved_wires_list = []

        # Process each tree
        for tree in wire_trees:
            if not tree:
                continue
                
            # Process each node in the tree
            for node in tree.all_nodes():
                # Only check leaf nodes and the root node
                if not node.is_leaf() and not node.is_root():
                    continue
                
                # get the endpoints that could be moved at all
                free_endpoints = self._get_unconnected_endpoints(tree, node)             
                wire = node.data

                # If no endpoints can be moved, skip to the next leaf
                if not free_endpoints:
                    continue

                # Check against all other endpoints in all trees
                for other_tree in wire_trees:
                    for other_node in other_tree.all_nodes():
                        other_wire = other_node.data
                        if other_wire == wire:
                            continue
                        
                        # now check closeness of the endpoints
                        (wire_close_endpoint, other_wire_close_endpoint) = eetbutil.are_wire_endpoints_near(wire, other_wire, epsilon)
                        
                        if wire_close_endpoint in free_endpoints and wire.get(f'x{wire_close_endpoint}_moved') is None:
                            # Check if the other wire has been moved already
                            if other_wire.get(f'x{other_wire_close_endpoint}_moved') is not None:
                                # If it has, we check if it is moved to our coordinate
                                if other_wire[f'x{other_wire_close_endpoint}_moved'] != wire[f'x{wire_close_endpoint}'] or \
                                   other_wire[f'y{other_wire_close_endpoint}_moved'] != wire[f'y{wire_close_endpoint}']:
                                    # note the new coordinates
                                    wire[f'x{wire_close_endpoint}_moved'] = other_wire[f'x{other_wire_close_endpoint}_moved']
                                    wire[f'y{wire_close_endpoint}_moved'] = other_wire[f'y{other_wire_close_endpoint}_moved']
                                    break
                                else:
                                    continue
                            else:
                                # note the new coordinates
                                wire[f'x{wire_close_endpoint}_moved'] = other_wire[f'x{other_wire_close_endpoint}']
                                wire[f'y{wire_close_endpoint}_moved'] = other_wire[f'y{other_wire_close_endpoint}']
                                break
                if wire.get('x1_moved') is not None or wire.get('x2_moved') is not None:
                    # Add the wire to the list of wires that need to be moved
                    moved_wires_list.append(wire)
        return moved_wires_list
    

    def _get_unconnected_endpoints(self, tree: treelib.Tree, node: treelib.Node) -> list[str]:
        """
        Determine which endpoints of a wire node are unconnected to other wires in the tree.

        This function checks the endpoints of a given node in a wire tree and identifies
        which ones are not connected to any other wire in the same tree. These endpoints
        are considered "unconnected" and may be candidates for adjustment or connection.

        Args:
            tree (treelib.Tree): The tree containing the node
            node (treelib.Node): The node whose endpoints are to be checked

        Returns:
            list[str]: A list of endpoint identifiers ('x1y1' or 'x2y2') that are unconnected
        """
        wire = node.data
        unconnected_endpoints = []
        p1_connected = False
        p2_connected = False

        # Get the two endpoints of this leaf wire
        p1 = (wire['x1'], wire['y1'])
        p2 = (wire['x2'], wire['y2'])
        
        # Check parent
        parent = tree.parent(node.identifier)
        if parent:
            parent_wire = parent.data
            (leaf_coincident_endpoint, parent_coincident_endpoint) = eetbutil.are_wires_connecting(wire, parent_wire)
            if leaf_coincident_endpoint == 1:
                p1_connected = True
            if leaf_coincident_endpoint == 2:
                p2_connected = True
        # Check children
        children = tree.children(node.identifier)
        for child in children:
            child_wire = child.data
            (leaf_coincident_endpoint, child_coincident_endpoint) = eetbutil.are_wires_connecting(wire, child_wire)
            if leaf_coincident_endpoint == 1:
                p1_connected = True
            if leaf_coincident_endpoint == 2:
                p2_connected = True

        # Add endpoints to unconnected list if they are not connected
        if not p1_connected:
            unconnected_endpoints.append(1)
        if not p2_connected:
            unconnected_endpoints.append(2)

        return unconnected_endpoints
    

    def _write_move_script(self, wires_to_move: list[dict]):
        with open(self._script_export_path, 'w') as f:
            # f.write(f'DISPLAY NONE {layer_number};\n')
            # f.write(f'CHANGE LAYER {layer_number};\n')
            f.write(f'GRID 1 {self._grid_unit.value};\n')
            
            # first select the wires that will be moved
            f.write(f'run {SELECT_GEOMETRY_ULP} -u {self._grid_unit.value}')
            for wire in wires_to_move:
                f.write(f' -w {wire['layer']} {wire['x1']} {wire['y1']} {wire['x2']} {wire['y2']}')
            f.write(';\n')
            
            # now delete them
            f.write('DELETE (> 0 0);\n')

            # now draw the moved wires
            last_layer = 0
            for wire in wires_to_move:
                if wire['layer'] != last_layer:
                    f.write(f'CHANGE LAYER {wire['layer']};\n')
                    last_layer = wire['layer']
                f.write(f'LINE {wire['width']} ')
                if wire.get('x1_moved') is not None:
                    f.write(f'({wire['x1_moved']} {wire['y1_moved']}) ')
                else:
                    f.write(f'({wire['x1']} {wire['y1']}) ')
                f.write(f'{wire['curve']:+} ')
                if wire.get('x2_moved') is not None:
                    f.write(f'({wire['x2_moved']} {wire['y2_moved']});\n')
                else:
                    f.write(f'({wire['x2']} {wire['y2']});\n')

            f.write(f'GRID LAST;\n')