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

import os
import json
import adsk.core
from enum import Enum
from .. import fusionAddInUtils as futil
from ... import config

EXTRACT_DATA_ULP: str = os.path.join(config.ULP_DIR, 'extract_data.ulp')

# these tags are used both in communication between Python and Javascript,
# and in the JSON file returned by the extract_data.ulp
class ExportDataType(Enum):
    GRID_UNIT = 'unit'
    SIGNAL_LIST = 'signal_list'
    SIGNAL_SELECTION = 'signal_selection'
    SIGNAL_DATA = 'signal_data'
    PART_LIST = 'part_list'
    PART_SELECTION = 'part_selection'
    PART_DATA = 'part_data'
    ATTRIBUTE_LIST = 'attribute_list'
    LAYER_DATA = 'layer_data'
    GEOMETRY_DATA = 'geometry_data'
    PACKAGE_DATA = 'package_data'
    

def get_eagle_data(json_output_path: str, requests: list[dict], use_grid_unit = False) -> dict:
    """
    Extracts various data types from the schematics/layout and combines them into a single JSON file.

    Args:
        json_output_path (str): The path to write the output JSON file to.
        requests (list[dict]): A list of requests, where each request is a dictionary
                               with 'type' (a string from ExportDataType values) and 'args' (list[str]).
                               For examples look at the shorthand functions in CommandBase.py 

    Returns:
        dict: A dictionary containing the extracted data.
    """
    if not json_output_path or not requests:
        return {}

    # Mapping from enum members to ULP arguments
    output_type_map = {
        ExportDataType.SIGNAL_LIST:     '-siglist',
        ExportDataType.SIGNAL_DATA:     '-sigdata',
        ExportDataType.SIGNAL_SELECTION:'-sigsel',
        ExportDataType.PART_LIST:       '-partlist',
        ExportDataType.PART_DATA:       '-partdata',
        ExportDataType.PART_SELECTION:  '-partsel',
        ExportDataType.LAYER_DATA:      '-lyrdata',
        ExportDataType.ATTRIBUTE_LIST:  '-attrlist',
        ExportDataType.GEOMETRY_DATA:   '-geodata',
        ExportDataType.PACKAGE_DATA:    '-packagedata'
    }

    # Reverse mapping from string value to enum member
    value_to_enum_map = {member.value: member for member in ExportDataType}

    ulp_args = []
    for request in requests:
        out_type_str = request.get('type', '')
        out_type = value_to_enum_map.get(out_type_str)
        
        if not out_type:
            futil.log(f'Warning: Unknown output type "{out_type_str}" requested.')
            continue

        args = request.get('args')

        arg_template = output_type_map.get(out_type)
        if not arg_template:
            # This case should ideally not be reached if the maps are in sync
            futil.log(f'Warning: No ULP argument found for output type "{out_type}".')
            continue

        if out_type in [ExportDataType.SIGNAL_DATA, ExportDataType.PART_DATA, ExportDataType.GEOMETRY_DATA] :
            if args:
                arg_list_str = " ".join(str(arg) for arg in args)
                ulp_args.append(f"{arg_template} {arg_list_str}")
            else:
                futil.log('Warning: "SIGNAL_DATA", "PART_DATA" or "GEOMETRY_DATA" requested but no arguments provided.')
        else:
            ulp_args.append(arg_template)

        if use_grid_unit:
            ulp_args.append('-userunit')

    if not ulp_args:
        futil.log('No valid output types to process.')
        return {}

    command_args = " ".join(ulp_args)
    
    app = adsk.core.Application.get()
    
    command = f'ELECTRON.RUN RUN "\'{EXTRACT_DATA_ULP}\' -o \'{json_output_path}\' {command_args}"'
    
    futil.log(f'RUNNING: {command}')
    app.executeTextCommand(command)

    if not os.path.isfile(json_output_path):
        futil.log(f'Failed to find extracted JSON file "{json_output_path}"')
        return {}
    
    try:
        with open(json_output_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        futil.log(f'Error decoding JSON from {json_output_path}: {e}')
        return {}
    
    return data