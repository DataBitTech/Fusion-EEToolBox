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
 
import os, sys
import adsk.core
from .. import fusionAddInUtils as futil
from ... import config
from .extract_data import *
from .stackup_parser import *
from .config_manager import *
from .extract_data import *
from .wire_processing import *
from .length_units import *
from .themes import get_theme


def generate_js_enum() -> str:
    """Generates JavaScript enum definition from Python enum.

    Returns:
        str: The JavaScript enum definition as a string.
    """
    enum_dict = {member.name: member.value for member in ExportDataType}
    
    # Manually construct the JS object string to have unquoted keys
    js_object_items = []
    for key, value in enum_dict.items():
        js_object_items.append(f'    {key}: "{value}"')
    
    js_object_string = "{\n" + ",\n".join(js_object_items) + "\n}"
    return f"export const ExportDataType = {js_object_string};\n\n"


def generate_js_include() -> None:
    """Generates JavaScript include file with configuration data.

    Creates or updates a JavaScript file containing configuration data
    including enum definitions, theme information, and icon paths.

    Returns:
        None
    """
    try:
        app = adsk.core.Application.get()
        electron_icon_path = config.ELECTRON_COMMON_ICON_DIR.replace('\\', '/')

        # generate file content first
        js_content = "/* THIS FILE IS GENERATED AUTOMATICALLY. DO NOT EDIT! */\n"
        js_content += generate_js_enum()
        js_content += f'export let theme = "{get_theme()}";\n\n'
        js_content += f'export const icon_path = "{electron_icon_path}";\n'

        js_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'javascript', 'eetb_info_generated.js'))
        os.makedirs(os.path.dirname(js_path), exist_ok=True)

        write_file = True
        if os.path.exists(js_path):
            # If the file exists, check if content is different
            with open(js_path, 'r') as f:
                existing_content = f.read()
            if existing_content == js_content:
                write_file = False

        if write_file:
            with open(js_path, 'w') as f:
                f.write(js_content)
            futil.log(f"Successfully generated JavaScript file: {js_path}")

    except Exception as e:
        futil.log(f"Error generating JavaScript file: {e}")
