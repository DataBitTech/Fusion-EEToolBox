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

import json, os
import adsk.core
from collections import defaultdict

from ..CommandBase import CommandBase
from ..PaletteCommandBase import PaletteCommandBase
from ... import config
from ... import controls as eetbControls
from ...lib import eetbUtils as eetbutil
from ...lib import treelib

class Eetb_ViaFenceCommand(PaletteCommandBase):

    def __init__(self):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_via_fence_command_id',
            command_name = 'Via fence',
            command_description = 'Create via fence for board geometry',
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'),
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources'))

        palette_attributes = PaletteCommandBase.MandatoryPaletteCommandAttributes(
            basic_attributes = command_attributes,
            palette_id =  f'{config.ADDIN_NAME}_via_fence_palette_id',
            palette_name = f'Via fence',
            palette_docking = adsk.core.PaletteDockingStates.PaletteDockStateFloating, # type: ignore
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'palette.html'))
        super().__init__(palette_attributes)

        self._script_export_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}.scr')
        self.palette_show_close_button = False
        self._stitching_points_cache = []


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        eetbControls.add_command_to_panel(config.ELECTRON_LAYOUT_ENV_ID, eetbControls.LayoutPanel.PATTERNS_PANEL, commandDefinition)

 
    def close_palette(self):
        """Handles command-specific cleanup and closes the palette.
        
        See the base class method for full details.
        """
        if self._stitching_points_cache:
            self._stitching_points_cache = []
            self.run_eagle_command('UNDO')
        try:
            if os.path.exists(self._script_export_path):
                os.remove(self._script_export_path)
        except Exception as e:
            self.log_error_to_ui(f"Error deleting script file: {str(e)}")
        
        super().close_palette()


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
                                                 {'type': eetbutil.ExportDataType.LAYER_DATA.value, 'args': []}],
                                                 True) # use grid units
        self._layer_data = palette_init_data.get(eetbutil.ExportDataType.LAYER_DATA.value, [])
        self._grid_unit = eetbutil.parse_length_unit(palette_init_data.get('unit', 'mm'))

        # Add a dummy layer with number 0 and name 'None' to the layer data
        layer_data = self._layer_data.copy()
        layer_data.insert(0, {'number': 0, 'name': 'None'})
        palette_init_data[eetbutil.ExportDataType.LAYER_DATA.value] = layer_data

        # send all info to the palette
        palette.sendInfoToHTML('setEagleData', json.dumps(palette_init_data))
        settings = self._load_config()
        palette.sendInfoToHTML('setParameters', json.dumps(settings))
        self._stitching_points_cache = []


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
        if event_name == 'cancelButtonClicked':
            self.close_palette()
        elif event_name in ['doShowPreview', 'okButtonClicked']:
            # do some sanity checks
            try:
                preview_layer = event_data.get('preview_layer', '0')
                preview_layer = int(preview_layer)
                spacing = event_data.get('spacing')
                (spacing, unit) = eetbutil.parse_dimension_string(spacing, self._grid_unit)
            except Exception as e:
                return
            
            if (preview_layer == 0 and event_name == 'doShowPreview') or spacing == 0.0:
                return

            # first get the signal data or layer geometry data
            geometry_type = event_data.get('geometry_type', 'signal')
            if geometry_type == 'signal':
                # Get signal data for the specified signal
                exported_eagle_data = self.get_signal_data([event_data.get("signal_name", "")], True)
            else:
                # Get layer geometry data for the specified layer
                layer_number = event_data.get("geometry_layer", 1)
                exported_eagle_data = self.get_geometry_data([layer_number], True)

            # Process the geometry data to create helper lines
            stitching_points = self._process_geometry_data(exported_eagle_data, event_data)

            if event_name == 'doShowPreview':
                self._write_preview_script(stitching_points, event_data)
                self._stitching_points_cache = stitching_points
            else:
                self._write_via_script(stitching_points, event_data)

            PaletteCommandBase.log_to_console(f"Running {self._script_export_path}")
            self.run_eagle_script(self._script_export_path)

            if event_name == 'okButtonClicked':
                self._save_config(event_data)
                self.close_palette()


    def _process_geometry_data(self, eagle_data: dict, event_data: dict) -> list[tuple[float, float]]:
        """Process the Eagle geometry data to create stitching lines based on offset settings.

        Args:
            eagle_data (dict): The data returned from Eagle containing geometry information
            event_data (dict): The data from the UI event including offset settings

        Returns:
            list: List of coordinates where vias shall be placed
        """
        # Get offset settings
        offset_string = event_data.get('offset', '0')
        offset_side = event_data.get('offset_side', 'side_a')
        geometry_type = event_data.get('geometry_type', 'signal')
        spacing_string = event_data.get('spacing', '1')
        initial_step_string = event_data.get('initial_step', '0')

        # Parse offset value
        try:
            offset = eetbutil.convert_to_unit(eetbutil.parse_dimension_string(offset_string, self._grid_unit), self._grid_unit)
            spacing = eetbutil.convert_to_unit(eetbutil.parse_dimension_string(spacing_string, self._grid_unit), self._grid_unit)
            initial_step = eetbutil.convert_to_unit(eetbutil.parse_dimension_string(initial_step_string, self._grid_unit), self._grid_unit)
        except ValueError:
            offset = 0.0
            initial_step = 0.0
            spacing = 1.0

        wires = []
        # Process based on geometry type
        if geometry_type == 'signal' and 'signal_data' in eagle_data:
            # Process signal data - extract wires from signal
            signal_data = eagle_data['signal_data']
            for signal in signal_data:
                if 'wires' in signal:
                    wires = signal['wires']
        elif geometry_type == 'lines' and 'geometry_data' in eagle_data:
            # Process layer geometry data - extract wires from geometry_data
            geometry_data = eagle_data['geometry_data']
            if 'wires' in geometry_data:
                wires = geometry_data['wires']
        
        # collect them into trees of connected wires
        wire_trees = self._build_wire_trees(wires)

        # re-root trees and re-orient wire segments 
        normalized_trees = self._normalize_wire_trees(wire_trees)

        # calculate trees along which stitching will be done
        stitching_trees = []
        for tree in normalized_trees:
            if offset_side in ['side_a', 'symmetrical']:
                stitching_trees.extend(self._compute_stitching_trees(tree, offset))
            if offset_side in ['side_b', 'symmetrical']:
                stitching_trees.extend(self._compute_stitching_trees(tree, -1.0 * offset))

        # now calculate the stitching points
        stitching_points = []
        for tree in stitching_trees:
            if False:
                script = f'CHANGE LAYER {event_data.get('preview_layer', 100)};\n'
                for node in tree.all_nodes():
                    wire = node.data
                    script += f"LINE ({wire['x1']} {wire['y1']}) ({wire['x2']} {wire['y2']});\n"

                # Write the script command to the temporary file
                with open(self._script_export_path, 'w') as f:
                    f.write(script)
                PaletteCommandBase.log_to_console(f"Running {self._script_export_path}")
                self.run_eagle_script(self._script_export_path)
            else:
                stitching_points.extend(self._get_stitching_points(tree, initial_step, spacing))
        return stitching_points


    def _build_wire_trees(self, wires: list) -> list:
        """Build connected component trees from wire segments using the treelib library.

        This method groups connected wire segments into treelib trees where each tree
        represents a connected component of wires. For each tree, the wire with the 
        most negative X coordinate endpoint is used as the root of the tree.

        Args:
            wires (list): List of wire dictionaries with x1, y1, x2, y2 coordinates

        Returns:
            list: List of treelib.Tree objects
        """
        if not wires:
            return []

        # Create a mapping of wire endpoints to wire indices
        endpoint_to_wires = {}
        for i, wire in enumerate(wires):
            p1 = (wire['x1'], wire['y1'])
            p2 = (wire['x2'], wire['y2'])
            for p in [p1, p2]:
                if p not in endpoint_to_wires:
                    endpoint_to_wires[p] = []
                endpoint_to_wires[p].append(i)

        visited = set()
        treelib_trees = []

        # Find connected components and build trees
        for i in range(len(wires)):
            if i in visited:
                continue

            # Identify all wires in this connected component (BFS to collect indices)
            component_indices = set()
            stack = [i]
            visited.add(i)
            while stack:
                curr_idx = stack.pop()
                component_indices.add(curr_idx)
                wire = wires[curr_idx]
                for p in [(wire['x1'], wire['y1']), (wire['x2'], wire['y2'])]:
                    for neighbor_idx in endpoint_to_wires.get(p, []):
                        if neighbor_idx not in visited:
                            visited.add(neighbor_idx)
                            stack.append(neighbor_idx)

            # Choose a random root - the tree will be re-rooted later anyway
            root_idx = min(component_indices)

            # Create the treelib tree
            tree = treelib.Tree()
            tree.create_node(tag=f"Wire {root_idx}", identifier=root_idx, data=wires[root_idx])

            # Build the tree structure using BFS from the root
            bfs_queue = [root_idx]
            added_to_tree = {root_idx}
            while bfs_queue:
                parent_idx = bfs_queue.pop(0)
                parent_wire = wires[parent_idx]
                # Check neighbors of the parent wire via its endpoints
                for p in [(parent_wire['x1'], parent_wire['y1']), (parent_wire['x2'], parent_wire['y2'])]:
                    for neighbor_idx in endpoint_to_wires.get(p, []):
                        if neighbor_idx in component_indices and neighbor_idx not in added_to_tree:
                            tree.create_node(tag=f"Wire {neighbor_idx}", 
                                           identifier=neighbor_idx, 
                                           parent=parent_idx, 
                                           data=wires[neighbor_idx])
                            added_to_tree.add(neighbor_idx)
                            bfs_queue.append(neighbor_idx)
            
            treelib_trees.append(tree)

        return treelib_trees


    def _normalize_wire_trees(self, trees: list[treelib.Tree]) -> list[treelib.Tree]:
        """Standardize wire trees by finding leaves and selecting the leftmost unconnected end as the new root.

        This method processes each tree to identify all leaf nodes (nodes with no children) and then
        selects the leaf with the leftmost (minimum x-coordinate) unconnected end to become the new root.
        This ensures a consistent starting point for processing each connected component, especially
        when dealing with complex wire geometries where the original root might not be ideal for
        subsequent operations like stitching or offsetting.

        Args:
            trees (list[treelib.Tree]): List of treelib.Tree objects representing connected wire components

        Returns:
            list[treelib.Tree]: List of normalized treelib.Tree objects with potentially new roots
        """
        def reroot_tree(old_tree: treelib.Tree, leaf_id: str):
            #self.log_to_console(old_tree.show(stdout=False)) # type: ignore
            
            # 1. Get path from leaf up to root: [leaf, ..., parent, root]
            path = list(old_tree.rsearch(leaf_id))
            new_tree = treelib.Tree()
            
            # 2. add the old leaf as the new root
            new_root_node = old_tree[leaf_id]
            new_tree.create_node(new_root_node.tag, new_root_node.identifier, parent=None, data=new_root_node.data)

            # 3. Add the rest of the path, using the PREVIOUSLY added node as the parent
            for i in range(len(path) - 1):
                child_id = path[i+1] # The node that will become a child in the new tree
                parent_id = path[i]  # The node we just added
                
                node_to_add = old_tree[child_id]
                new_tree.create_node(node_to_add.tag, node_to_add.identifier, parent=parent_id, data=node_to_add.data)
            
                # 4. Handle side-branches (neighbors not on the main path)
                for child in old_tree.children(child_id):
                    if child.identifier not in path:
                        # subtree() creates a copy of the branch
                        branch = old_tree.subtree(child.identifier)
                        new_tree.paste(child_id, branch)
                        
            return new_tree


        normalized_trees = []
        for tree in trees:
            if not tree:
                continue

            # Find all leaf nodes (nodes with no children)
            leaves = tree.leaves()
            root_id = tree.root
            if root_id and tree.children(root_id).count == 1:
                 leaves.append(tree.get_node(tree.root)) # type: ignore

            # Find the leaf with the leftmost unconnected end
            leftmost_leaf = None
            min_x = float('inf')
            for leaf in leaves:
                wire = leaf.data
                # Check both endpoints of the wire for the leaf
                x1, x2 = wire['x1'], wire['x2']
                leaf_x = min(x1, x2)
                if leaf_x < min_x:
                    min_x = leaf_x
                    leftmost_leaf = leaf

            # If we found a leftmost leaf, make it the new root
            if leftmost_leaf and leftmost_leaf.identifier != tree.root:
                # Create a new tree with the leftmost leaf as root
                normalized_trees.append(reroot_tree(tree, leftmost_leaf.identifier))
            else:
                # No change needed, keep the original tree
                normalized_trees.append(tree)
        return normalized_trees


    def _compute_stitching_trees(self, normalized_tree: treelib.Tree, offset_value: float) -> list[treelib.Tree]:
        """Compute new trees by translating wire segments perpendicular to themselves.

        This method takes a tree of connected wires and creates new trees where:
        1. The root wire segment is translate perpendicular to itself by offset_value
        2. The first child node below the current node inherits the translation vector, that
            is then rotated by the angle between the current node and first node below
        3. The child node wire and the parent node wire are prolonged until they intersect
        4. If a node has multiple children, the first node continues the new tree, the other children create new trees

        Args:
            tree (treelib.Tree): The tree of connected wires
            offset_value (float): The offset distance to apply

        Returns:
            list: New trees (lists of connected wires)
        """
        if not normalized_tree:
            return []

        stitching_tree_collection = []

        def process_node(node_id, parent_wire, tree_collection: list[treelib.Tree], stitching_tree: treelib.Tree):
            node = normalized_tree.get_node(node_id)
            wire = node.data.copy() # type: ignore
            
            # Orient wire: x1,y1 should be the connection point to parent
            if parent_wire:
                # If connection point to parent is at wire's x2,y2, flip it
                if eetbutil.connection_point_of_wires(parent_wire, wire) == (2, 2):
                    eetbutil.flip_wire(wire)

            # Translate current wire
            translated_wire = eetbutil.translate_wire(wire, offset_value)
            
            # If we have a previous wire in this path, intersect them to prolong until they meet
            if stitching_tree.size() > 0:
                parent_translated_node = stitching_tree.leaves()[0]
                parent_translated_wire = parent_translated_node.data
                ix, iy = eetbutil.intersect_lines(parent_translated_wire, translated_wire)
                if ix is not None:
                    parent_translated_wire['x2'] = ix
                    parent_translated_wire['y2'] = iy
                    translated_wire['x1'] = ix
                    translated_wire['y1'] = iy
                
                stitching_tree.create_node(tag=f"Wire {node_id}", identifier=node_id, parent=parent_translated_node, data=translated_wire)
            else:
                stitching_tree.create_node(tag=f"Wire {node_id}", identifier=node_id, data=translated_wire)
            
            children = normalized_tree.children(node_id)
            if children:
                # First child continues the current path
                process_node(children[0].identifier, wire, tree_collection, stitching_tree)
                
                # Other children start new trees
                for other_child in children[1:]:
                    stitching_tree = treelib.Tree()
                    process_node(other_child.identifier, wire, tree_collection, stitching_tree)
            else:
                tree_collection.append(stitching_tree)


        # Process the root node first to ensure correct orientation
        root_node = normalized_tree.get_node(normalized_tree.root)
        root_wire = root_node.data.copy() # type: ignore
        children = normalized_tree.children(normalized_tree.root) # type: ignore
        if children:
            first_child = children[0]
            child_wire = normalized_tree.get_node(first_child.identifier).data # type: ignore
            # Check if root wire's x1,y1 connects to first child (it shouldn't)
            if eetbutil.connection_point_of_wires(root_wire, child_wire) in [(1, 1), (1, 2)]:
                eetbutil.flip_wire(root_wire)
            # Update the root node's data with the potentially flipped wire
            root_node.data = root_wire # type: ignore

        # Start processing from the root node
        current_tree = treelib.Tree()
        process_node(normalized_tree.root, None, stitching_tree_collection, current_tree)
        return stitching_tree_collection
    

    def _get_stitching_points(self, tree: treelib.Tree, initial_step: float, spacing: float) -> list[tuple[float, float]]:
        """Generate a list of coordinate pairs along a tree path for via placement.

        Starting from the root, it takes an initial step along the path, then
        subsequent steps at fixed spacing intervals. The list of coordinate pairs
        is returned for via placement purposes. This function walks the tree from
        root to leaves, accumulating points along each path segment. It handles
        both tree and list inputs for compatibility with different data structures.

        Args:
            tree (treelib.Tree): The tree of wires to traverse
            initial_step (float): Distance for the first step from the root (default: 0.5)
            spacing (float): Distance between subsequent steps (default: 1.0)

        Returns:
            list: List of coordinate pairs (x, y) along the path
        """
        stithing_points = []
        # Get root node
        root = tree.get_node(tree.root)
        if root is None:
            return stithing_points
        # Start with root point
        wire = root.data
        distance_to_next_via = initial_step

        node = root
        while node is not None:
            wire = node.data # type: ignore
            # walk the wire segment
            last_point = (wire['x1'], wire['y1'])
            remaining_length = eetbutil.wire_length(wire)
            while distance_to_next_via < remaining_length:
                last_point = eetbutil.walk_along_wire(wire, last_point, distance_to_next_via)
                stithing_points.append(last_point)
                remaining_length -= distance_to_next_via
                distance_to_next_via = spacing

            distance_to_next_via -= remaining_length
            children = tree.children(node.identifier)
            node = children[0] if len(children) else None
        return stithing_points


    def _write_preview_script(self, stitching_points: list[tuple[float, float]], event_data: dict):
        """Write an Eagle script that draws circles on the preview layer for preview purposes.

        Args:
            stitching_points (list): List of coordinate pairs (x, y) where vias should be placed
            event_data (dict): The data from the UI event including offset settings
        """
        # Get the via diameter from event data or use a default
        via_drill_string = event_data.get('drill', '0.3 mm')
        annular_ring = eetbutil.convert_to_unit((0.15, eetbutil.LengthUnits.MILLIMETER), self._grid_unit)
        try:
            diameter_mm = eetbutil.convert_to_unit(eetbutil.parse_dimension_string(via_drill_string, self._grid_unit), self._grid_unit)
        except ValueError:
            diameter_mm = eetbutil.convert_to_unit((0.3, eetbutil.LengthUnits.MILLIMETER), self._grid_unit)
            
        # Create the Eagle script
        script = ''
        if self._stitching_points_cache:
            script += 'UNDO;\n'
            self._stitching_points_cache = []
        
        # we need to switch to the units used in the export data - in case of INCH or CM user grid, it
        # does not match, because the export data is currently only MM or MIL
        script += f'GRID {'10' if self._grid_unit == eetbutil.LengthUnits.MIL else '0.5'} {self._grid_unit.value};\n'
        script += f"CHANGE LAYER {event_data.get('preview_layer', '')};\n"
        
        # Draw circles at each stitching point
        for x, y in stitching_points:
            script += f"CIRCLE {annular_ring} ({x} {y}) ({x + diameter_mm/2 + annular_ring/2} {y});\n"
        script += "GRID LAST;\n"

        # Write the script command to the temporary file
        with open(self._script_export_path, 'w') as f:
            f.write(script)


    def _write_via_script(self, stitching_points: list[tuple[float, float]], event_data: dict):
        """Write an Eagle script that creates vias at specified stitching points.

        This function generates an Eagle ULP script that places vias on the appropriate
        layer based on the event data. The vias are placed at the coordinates provided
        in the stitching_points list.

        Args:
            stitching_points (list): List of coordinate pairs (x, y) where vias should be placed
            event_data (dict): The data from the UI event including via settings like drill size
        """
        # Get the via drill from event data or use a default
        via_drill_string = event_data.get('drill', '')
        try:
            drill = eetbutil.convert_to_unit(eetbutil.parse_dimension_string(via_drill_string, self._grid_unit), self._grid_unit)
        except ValueError:
            return

        # Create the Eagle script
        script = ''
        if self._stitching_points_cache:
            script += 'UNDO;\n'
            self._stitching_points_cache = []
        script += f'GRID {'10' if self._grid_unit == eetbutil.LengthUnits.MIL else '0.5'} {self._grid_unit.value};\n'
        script += f'CHANGE DRILL {drill};\n'
        
        # Add via at each stitching point
        for x, y in stitching_points:
            script += f"VIA '{event_data.get('via_net', '')}' ({x} {y});\n"
        script += "GRID LAST;\n"
        
        # Write the script command to the temporary file
        with open(self._script_export_path, 'w') as f:
            f.write(script)


    def _save_config(self, event_data: dict):
        """Save the current configuration to a file.

        This function takes the event data containing the configuration settings
        and saves them to a the user configuration file. The configuration includes
        settings like drill size, layer information, and other user preferences
        for the stitching process.

        Args:
            event_data (dict): The data from the UI event containing configuration settings
        """
        parameters_to_save = ['spacing', 'drill', 'via_net']
        for param_name in parameters_to_save:
            eetbutil.config_manager.store_document_option(self.document_id, self.command_id, param_name, event_data.get(param_name, ''))
        eetbutil.config_manager.store_global_option(self.command_id, 'preview_layer', event_data.get('preview_layer', ''))


    def _load_config(self) -> dict:
        """Load configuration settings from the user configuration and return them as a dictionary.

        This method retrieves previously saved configuration options for the command,
        including spacing, drill size, via net, and preview layer settings. It returns
        a dictionary containing these values, with defaults provided if settings are not found.

        Returns:
            dict: A dictionary containing the loaded configuration options
        """
        config = {}
        config['spacing'] = eetbutil.config_manager.get_document_option(self.document_id, self.command_id, 'spacing')
        config['drill'] = eetbutil.config_manager.get_document_option(self.document_id, self.command_id, 'drill')
        config['via_net'] = eetbutil.config_manager.get_document_option(self.document_id, self.command_id, 'via_net')
        config['preview_layer'] = eetbutil.config_manager.get_global_option(self.command_id, 'preview_layer')
        return config
