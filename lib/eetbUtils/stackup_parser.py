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

import xml.etree.ElementTree as ET
import math
from .length_units import *
from .microstrip import Microstrip

class StackupParser:
    """Parses a .estackup file (XML format) and provides easy access to its data.

    This class handles parsing of stackup files and provides methods to access
    layer information, dielectric properties, and transmission speeds.
    """
    C_MM_PER_NS = 299.792458

    def __init__(self, file_path: str):
        """
        Initializes the parser with the path to the .estackup file.

        Args:
            file_path (str): The path to the .estackup file.
        """
        self._speed_cache_wires = {}
        self._speed_cache_vias = {}
        self.file_path = file_path
        self.data = self._parse()

        # update the bottom layer number - support for the 'new' Fusion numbering
        signal_layers = self.get_signal_layers()
        bottom_layer = signal_layers[-1].get('layer')
        self.SIGNAL_LAYER_TOP: int = 1
        self.SIGNAL_LAYER_BOTTOM: int = bottom_layer

    def _parse(self) -> dict:
        """
        Parses the XML file and returns its content as a dictionary.

        Returns:
            dict: A dictionary representing the content of the .estackup file.
                  Returns an empty dictionary if parsing fails.
        """
        try:
            tree = ET.parse(self.file_path)
            root = tree.getroot()
            
            layerstackup_el = root.find('layerstackup')
            if layerstackup_el is None:
                return {}

            stackup_data = {
                'attributes': layerstackup_el.attrib,
                'layers': [],
                'vias': []
            }
            
            for child in layerstackup_el:
                if child.tag == 'layerdef':
                    layer_data = {'attributes': child.attrib, 'material': {}}
                    material_el = child.find('material')
                    if material_el is not None:
                        layer_data['material'] = material_el.attrib
                    stackup_data['layers'].append(layer_data)
                elif child.tag == 'viadef':
                    stackup_data['vias'].append(child.attrib)
            
            return stackup_data
            
        except (ET.ParseError, FileNotFoundError) as e:
            print(f"Error reading or parsing file {self.file_path}: {e}")
            return {}


    def get_stackup_attributes(self) -> dict:
        """
        Returns the attributes of the root element.

        Returns:
            dict: A dictionary of attributes.
        """
        return self.data.get('attributes', {})


    def get_signal_layers(self) -> list:
        """
        Returns a list of 'Signal' layers with their number, name, and thickness.

        Returns:
            list: A list of dictionaries containing layer information.
        """
        signal_layers = []
        for layer in self.data.get('layers', []):
            attrs = layer.get('attributes', {})
            if attrs.get('type') == 'Signal':
                mat_attrs = layer.get('material', {})
                signal_layers.append({
                    'layer': int(attrs.get('layer', 0)),
                    'layer_name': attrs.get('name'),
                    'thickness': mat_attrs.get('thickness')
                })
        return signal_layers


    @staticmethod
    def _convert_to_mm(value: str) -> float:
        """
        Converts a string representation of a length value to millimeters.

        This function takes a string that may contain a numeric value with a unit
        (e.g., "1.5mm", "0.06in") and converts it to millimeters. It supports
        various units including mil, inch, mm, cm, and um.

        Args:
            value (str): The string representation of the length value with optional unit.

        Returns:
            float: The length value in millimeters.
        """
        dimension_tuple = parse_dimension_string(value)
        return convert_to_unit(dimension_tuple, LengthUnits.MILLIMETER)


    def _get_first_layer_index(self, signal_layers: list) -> int:
        """Finds the index of the first signal layer in the layer stack.

        Args:
            signal_layers: List of signal layer numbers to search for.

        Returns:
            int: The index of the first signal layer found, or -1 if not found.
        """
        all_layers = self.data.get('layers', [])
        start_index = -1
        for i, layer in enumerate(all_layers):
            attrs = layer.get('attributes', {})
            if attrs.get('type') == 'Signal' and int(attrs.get('layer', -1)) in signal_layers:
                start_index = i
                break
        return start_index


    def _get_dielectrics_next_to_signal_layer(self, signal_layer_number: int, aboveLayer: bool) -> list[dict]:
        """Returns dielectric layers adjacent to a signal layer.

        Retrieves dielectric layers found either above or below a given signal layer,
        up to the next signal layer.

        Args:
            signal_layer_number: The number of the signal layer to find adjacent dielectrics for.
            aboveLayer: If True, searches above the signal layer; if False, searches below.

        Returns:
            list[dict]: A list of dictionaries representing dielectric layers with their properties.
        """
        all_layers = self.data.get('layers', [])
        
        start_index = self._get_first_layer_index([signal_layer_number])
        if start_index == -1:
            return []

        dielectrics = []
        iter_range = range(start_index + 1, len(all_layers)) if not aboveLayer else range(start_index - 1, -1, -1)

        for i in iter_range:
            layer = all_layers[i]
            attrs = layer.get('attributes', {})
            layer_type = attrs.get('type')

            if layer_type in ['Prepreg', 'Core']:
                mat_attrs = layer.get('material', {})
                dielectrics.append({
                    'layer_type': layer_type,
                    'thickness': mat_attrs.get('thickness'),
                    'dielectric_constant': mat_attrs.get('dielectric_constant_1g'),
                    'dissipation_factor': mat_attrs.get('dissipation_factor_1g'),
                    'position_id': attrs.get('name')
                })
            elif layer_type == 'Signal':
                break
                
        return dielectrics


    def get_dielectrics_below_signal_layer(self, signal_layer_number: int) -> list[dict]:
        """Gets dielectric layers below a specified signal layer.

        Args:
            signal_layer_number: The number of the signal layer to find dielectrics below.

        Returns:
            list[dict]: A list of dictionaries representing dielectric layers below the signal layer.
        """
        return self._get_dielectrics_next_to_signal_layer(signal_layer_number, False)


    def get_dielectrics_above_signal_layer(self, signal_layer_number: int) -> list[dict]:
        """Gets dielectric layers above a specified signal layer.

        Args:
            signal_layer_number: The number of the signal layer to find dielectrics above.

        Returns:
            list[dict]: A list of dictionaries representing dielectric layers above the signal layer.
        """
        return self._get_dielectrics_next_to_signal_layer(signal_layer_number, True)


    def get_vias(self) -> list:
        """
        Returns a list of all vias, where each via is a dictionary of its attributes.
        """
        return self.data.get('vias', [])


    def _get_weighted_Er(self, dielectrics: list[dict]) -> float:
        """Calculates the weighted average dielectric constant.

        Computes the weighted average dielectric constant of dielectric layers
        based on their thickness.

        Args:
            dielectrics: A list of dictionaries representing dielectric layers,
                        each with 'thickness' and 'dielectric_constant' keys.

        Returns:
            float: The weighted average dielectric constant.
        """
        total_thickness = sum(StackupParser._convert_to_mm(layer.get('thickness', 0)) for layer in dielectrics)
        if total_thickness:
            weighted_sum = sum(StackupParser._convert_to_mm(layer.get('thickness', 0)) * float(layer.get('dielectric_constant', 0)) for layer in dielectrics)
            return weighted_sum / total_thickness
        else:
            return 1.0


    def get_transmission_speed(self, signal_layer: int, trace_width: float) -> float:
        """Calculates the transmission speed for a signal layer.

        Computes the transmission speed of signals on a given signal layer based on
        the dielectric properties and trace geometry.

        Args:
            signal_layer: The signal layer number.
            trace_width: The width of the trace in millimeters.

        Returns:
            float: The transmission speed in mm/ns.
        """
        if (signal_layer, trace_width) in self._speed_cache_wires:
            return self._speed_cache_wires[(signal_layer, trace_width)]

        dielectrics = []
        dielectrics.extend(self.get_dielectrics_above_signal_layer(signal_layer))
        dielectrics.extend(self.get_dielectrics_below_signal_layer(signal_layer))

        if signal_layer in [self.SIGNAL_LAYER_TOP, self.SIGNAL_LAYER_BOTTOM]:
            W = trace_width
            t = next((StackupParser._convert_to_mm(layer.get('thickness'))for layer in self.get_signal_layers() if layer['layer'] == signal_layer), 0)
            h = sum(StackupParser._convert_to_mm(layer.get('thickness'))for layer in dielectrics)
            Er = self._get_weighted_Er(dielectrics)
            ErEff = Microstrip(t=t, h=h, er=Er).effective_permittivity(W)
        else:
            ErEff = self._get_weighted_Er(dielectrics)

        speed = self.C_MM_PER_NS / math.sqrt(ErEff)
        self._speed_cache_wires[(signal_layer, trace_width)] = speed
        return speed


    def get_signal_layer_distance(self, layer_a: int, layer_b: int) -> float:
        """Calculates the distance between two signal layers.

        Determines the physical distance between two signal layers in the stackup
        by summing the thicknesses of layers between them.

        Args:
            layer_a: The first signal layer number.
            layer_b: The second signal layer number.

        Returns:
            float: The distance between the layers in millimeters.
        """
        all_layers = self.data.get('layers', [])
        start_index = self._get_first_layer_index([layer_a, layer_b])

        if start_index == -1:
            return 0.0

        distance = 0
        other_layer_found = False
        for i in range(start_index + 1, len(all_layers)):
            layer = all_layers[i]
            attrs = layer.get('attributes', {})
            material = layer.get('material', {})
            if attrs.get('type') == 'Signal' and int(attrs.get('layer', -1)) in [layer_a, layer_b]:
                other_layer_found = True
                break
            else:
                distance += StackupParser._convert_to_mm(material.get('thickness'))

        return distance if other_layer_found else 0.0


    def get_via_speed(self, layer_a: int, layer_b: int) -> float:
        """Calculates the transmission speed through vias between signal layers.

        Computes the transmission speed for signals traveling through vias between
        two signal layers based on the dielectric properties of the layers.

        Args:
            layer_a: The first signal layer number.
            layer_b: The second signal layer number.

        Returns:
            float: The transmission speed in mm/ns.
        """
        # check the cache first
        if (min(layer_a, layer_b), max(layer_a, layer_b)) in self._speed_cache_vias:
            return self._speed_cache_vias[(min(layer_a, layer_b), max(layer_a, layer_b))]

        signal_layers = self.get_signal_layers()
        first_layer_found = False
        dielectrics = []
        for layer_idx in range(0, len(signal_layers)):
            if int(signal_layers[layer_idx].get('layer')) == min(layer_a, layer_b):
                first_layer_found = True
            if int(signal_layers[layer_idx].get('layer')) == max(layer_a, layer_b):
                break
            if first_layer_found:
                dielectrics.extend(self.get_dielectrics_below_signal_layer(signal_layers[layer_idx].get('layer')))
        er_approximation = self._get_weighted_Er(dielectrics)
        speed = self.C_MM_PER_NS / math.sqrt(self._get_weighted_Er(dielectrics)) if er_approximation != 0.0 else 0.0
        self._speed_cache_vias[(min(layer_a, layer_b), max(layer_a, layer_b))] = speed
        return speed
