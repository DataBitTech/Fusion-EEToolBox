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

import math
import json
import os
import adsk.core
from pathlib import Path

from ..CommandBase import CommandBase
from ..PaletteCommandBase import PaletteCommandBase
from ... import config
from ... import controls as eetbControls
from ...lib.eetbUtils.stackup_parser import StackupParser
from ...lib import fusionAddInUtils as futil
from ...lib import eetbUtils as eetbutil


class Eetb_LengthAndDelayMeasureCommand(PaletteCommandBase):
    
    def __init__(self):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_LengthAndDelayMeasure_command_id',
            command_name = 'Length and delay',
            command_description = 'Measure routing length and delay',
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'),
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources'))
        
        palette_attributes = PaletteCommandBase.MandatoryPaletteCommandAttributes(
            basic_attributes = command_attributes,
            palette_id = f'{config.ADDIN_NAME}_LengthAndDelayMeasure_palette_id',
            palette_name = f'Routing length and delay',
            palette_docking = adsk.core.PaletteDockingStates.PaletteDockStateBottom, # type: ignore
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'palette.html'))
        super().__init__(palette_attributes)

        self.palette_width = 700
        self.palette_height = 350
        self.palette_show_close_button = False
        self.palette_is_persistent = True


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        eetbControls.add_command_to_panel(config.ELECTRON_LAYOUT_ENV_ID, eetbControls.LayoutPanel.MEASURE_PANEL, commandDefinition)


    def palette_ready_event_handler(self, palette: adsk.core.Palette):
        """Handles the palette ready event.

        This function is called when the palette is fully initialized and ready for interaction.
        It can be used to perform any setup or initialization tasks that require the palette to be active.
        It overrides the base class method as required by the base class

        Args:
            palette (adsk.core.Palette): The palette that triggered the event.
        """
       # Load stackup parser
        self.stackup = eetbutil.get_stackup(self.document_id)
        if not self.stackup:
            palette.sendInfoToHTML('showWarning', 'No stackup file provided, only routing lengths can be calculated, without via lengths or delays. \
                                   Stackup can be exported from Rules->Layer stack->Save as. Make sure to keep the saved estackup file up to date in case of changes!')
        else:
            palette.sendInfoToHTML('setStackupFileName', self.stackup.file_path)

        # Get initial signal data for the palette
        palette_init_data = self.get_eagle_data([{'type': eetbutil.ExportDataType.SIGNAL_LIST.value, 'args': []}, 
                                                 {'type': eetbutil.ExportDataType.SIGNAL_SELECTION.value, 'args': []}])
        palette.sendInfoToHTML('setEagleData', json.dumps(palette_init_data))
        
        # try to restore last state
        last_signal_groups = eetbutil.config_manager.get_document_option(self.document_id, self.palette_id, "signal_groups")
        if last_signal_groups:
            palette.sendInfoToHTML('setSignalGroups', json.dumps(last_signal_groups))
    

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
        if event_name == 'requestAnalysis':
            signal_groups = event_data
            flat_signal_list = [signal for group in signal_groups for signal in group]
            
            if not flat_signal_list:
                palette.sendInfoToHTML('setAnalysisResults', json.dumps([]))
                return

            signal_geometry = self.get_signal_data(flat_signal_list)
            analysis_results = self._perform_analysis(signal_geometry, signal_groups)
            eetbutil.config_manager.store_document_option(self.document_id, self.palette_id, "signal_groups", signal_groups)
            palette.sendInfoToHTML('setAnalysisResults', json.dumps(analysis_results))

        elif event_name == 'groupClicked':
            command = f"ELECTRON.RUN SHOW {' '.join(str(signal_name) for signal_name in event_data)}"
            PaletteCommandBase.log_to_console(f"Running {command}")
            self.app.executeTextCommand(command)

        elif event_name == 'loadStackupFileLocal':
            fileDialog = self.ui.createFileDialog()
            fileDialog.isMultiSelectEnabled = False
            fileDialog.title = "Specify estackup file"
            fileDialog.filter = "Estackup file (*.estackup)"
            fileDialog.filterIndex = 0
            
            if self.stackup and os.path.exists(os.path.dirname(self.stackup.file_path)):
                fileDialog.initialDirectory = os.path.dirname(self.stackup.file_path)
            else:
                fileDialog.initialDirectory = str(Path.home()) 
            dialogResult = fileDialog.showOpen()

            if dialogResult == adsk.core.DialogResults.DialogOK:
                filename = fileDialog.filename
                self.stackup = eetbutil.config_manager.get_stackup(self.document_id, filename)
                if self.stackup:
                    palette.sendInfoToHTML('setStackupFileName', filename)
                    palette.sendInfoToHTML('showWarning', '')



    def _perform_analysis(self, signal_geometry_data, signal_groups : list [list[str]]):
        """Performs the analysis of signal routing length and delay.

        This function takes the geometry data of signals and groups them to calculate
        the total routing length and estimated delay for each group. It uses the stackup
        information if available to compute the delay based on the layer properties.

        Args:
            signal_geometry_data (dict): A dictionary containing the geometry data of signals.
            signal_groups (list[list[str]]): A list of signal groups, where each group is a list of signal names.

        Returns:
            list[dict]: A list of dictionaries containing the analysis results for each signal group.
        """
        signal_data_map = {s['name']: s for s in signal_geometry_data.get('signal_data', [])}

        processed_groups = []
        for index, group_signals in enumerate(signal_groups):
            group_data = {
                "originalIndex": index,
                "name": ', '.join(group_signals),
                "signals": group_signals,
                "total_length_mm": 0,
                "total_delay_ns": 0 if self.stackup is not None else None,
                "layer_analysis": {},
                "has_airwire": False,
            }
            
            for signal_name in group_signals:
                signal = signal_data_map.get(signal_name)
                if not signal:
                    continue
                
                all_wires = signal.get('wires', [])
                for wire in all_wires:
                    layer = wire.get('layer')
                    if layer is None:
                        continue
                    
                    if layer == 19: # Airwires
                        group_data["has_airwire"] = True
                        continue

                    # --- Length Calculation for wires ---
                    x1, y1, x2, y2 = wire.get('x1'), wire.get('y1'), wire.get('x2'), wire.get('y2')
                    length_mm = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                    if wire.get('isArc', False):
                        curve = wire.get('curve', 0)
                        if curve != 0:
                            theta = abs(curve) / 180 * math.pi
                            if math.sin(theta / 2) != 0:
                                radius = length_mm / 2 / math.sin(theta / 2)
                                length_mm = radius * theta
                    
                    group_data["total_length_mm"] += length_mm
                    if layer not in group_data["layer_analysis"]:
                        group_data["layer_analysis"][layer] = {"length_mm": 0, "delay_ns": 0}
                    group_data["layer_analysis"][layer]["length_mm"] += length_mm

                    # --- Delay Calculation for wires ---
                    if self.stackup is not None:
                        trace_width = wire.get('width')
                        if trace_width and trace_width > 0:
                            try:
                                speed = self.stackup.get_transmission_speed(layer, trace_width)
                                delay = length_mm / speed if speed > 0 else 0
                                if group_data["total_delay_ns"] is not None:
                                    group_data["total_delay_ns"] += delay
                                group_data["layer_analysis"][layer]["delay_ns"] += delay
                            except Exception as e:
                                self.log_to_console(f"Could not calculate delay for wire on layer {layer}: {e}")

                # --- Via Calculations ---
                if self.stackup is not None:
                    for via in signal.get('vias', []):
                        via_x, via_y = via.get('x'), via.get('y')
                        
                        connected_layers = set()
                        for wire in all_wires:
                            if (wire.get('x1') == via_x and wire.get('y1') == via_y) or \
                               (wire.get('x2') == via_x and wire.get('y2') == via_y):
                                if wire.get('layer') is not None and wire.get('layer') != 19:
                                    connected_layers.add(wire.get('layer'))
                        
                        if len(connected_layers) > 1:
                            min_layer = min(connected_layers)
                            max_layer = max(connected_layers)
                            
                            via_length = self.stackup.get_signal_layer_distance(min_layer, max_layer)
                            group_data["total_length_mm"] += via_length
                            
                            via_speed = self.stackup.get_via_speed(min_layer, max_layer)
                            via_delay = via_length / via_speed if via_speed > 0 else 0
                            if group_data["total_delay_ns"] is not None:
                                group_data["total_delay_ns"] += via_delay
                            
                            if 0 not in group_data["layer_analysis"]:
                                group_data["layer_analysis"][0] = {"length_mm": 0, "delay_ns": 0}
                            group_data["layer_analysis"][0]["length_mm"] += via_length
                            group_data["layer_analysis"][0]["delay_ns"] += via_delay
            
            processed_groups.append(group_data)

        # Calculate diffs
        if processed_groups:
            shortest_length = min(g["total_length_mm"] for g in processed_groups) if processed_groups else 0
            for g in processed_groups:
                g["length_diff_mm"] = g["total_length_mm"] - shortest_length

            if self.stackup is not None:
                valid_delays = [g["total_delay_ns"] for g in processed_groups if g["total_delay_ns"] is not None]
                shortest_delay = min(valid_delays) if valid_delays else 0
                    
                for g in processed_groups:
                    if g["total_delay_ns"] is not None:
                        g["delay_diff_ns"] = g["total_delay_ns"] - shortest_delay
                    else:
                        g["delay_diff_ns"] = None
            else:
                 for g in processed_groups:
                    g["delay_diff_ns"] = None
            
            for g in processed_groups:
                g["phase_diff_deg"] = None

        return processed_groups