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

# Description:
# This module provides a simple interface to a configuration file 'CONFIG.JSON'
# located in the root directory of the add-in. It uses the 'json'
# library to read and write configuration settings.
#
# The configuration file is read only once when the module is first imported.
# Any subsequent calls to storage functions will write the changes directly
# to the file, ensuring that the configuration is always up-to-date.

import copy
from enum import Enum
import json
import os
import time
from typing import Optional, Any
from .stackup_parser import StackupParser
import adsk.core

class ConfigParamScope(Enum):
    GLOBAL = 'global'
    DOCUMENT = 'documents'

# Determine the root directory of the add-in to locate CONFIG.JSON
_ADDIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_CONFIG_FILE = os.path.join(_ADDIN_ROOT, 'CONFIG.JSON')
_DEFAULT_CONFIG_FILE = os.path.join(_ADDIN_ROOT, 'DEFAULT_CONFIG.JSON')

def _load_config() -> None:
    """Loads the configuration from the JSON file into the global _config dict.

    Reads the configuration from CONFIG.JSON or DEFAULT_CONFIG.JSON and
    loads it into the global configuration dictionary.

    Returns:
        None
    """
    global _config
    if os.path.exists(_CONFIG_FILE):
        with open(_CONFIG_FILE, 'r') as f:
            try:
                _config = json.load(f)
            except json.JSONDecodeError:
                # If file is corrupted or empty, start with a fresh config
                _config = {}
    elif os.path.exists(_DEFAULT_CONFIG_FILE):
        # If CONFIG.JSON doesn't exist, load from DEFAULT_CONFIG.JSON
        with open(_DEFAULT_CONFIG_FILE, 'r') as f:
            try:
                _config = json.load(f)
                # Save the default config as CONFIG.JSON for future use
                _save_config()
            except json.JSONDecodeError:
                # If default file is corrupted, start with a fresh config
                _config = {}
    else:
        # If neither file exists, start with a fresh config
        _config = {}


def _save_config() -> None:
    """Saves the current _config dictionary to the JSON file.

    Writes the global configuration dictionary to the CONFIG.JSON file.

    Returns:
        None
    """
    with open(_CONFIG_FILE, 'w') as f:
        json.dump(_config, f, indent=4)


def _store_option(scope_dict: dict, section: str, option: str, value: Any) -> None:
    """Stores an option in the specified scope dictionary and saves to file.

    Args:
        scope_dict: The dictionary to store the option in.
        section: The section name (top-level key).
        option: The option name (second-level key).
        value: The value to store.

    Returns:
        None
    """
    if scope_dict.get(section) is None:
        scope_dict[section] = {}
    if scope_dict[section].get(option, None) is None or scope_dict[section][option] != value:
        scope_dict[section][option] = value
        _save_config()


def store_global_option(section: str, option: str, value: Any) -> None:
    """Stores a global option in a specific section and writes the changes to the file.

    If the section does not exist, it will be created.

    Args:
        section: The section name (top-level key).
        option: The option name (second-level key).
        value: The value to store.

    Returns:
        None
    """
    if _config.get(ConfigParamScope.GLOBAL.value) is None:
        _config[ConfigParamScope.GLOBAL.value] = {}

    scope_dict = _config[ConfigParamScope.GLOBAL.value]
    _store_option(scope_dict, section, option, value)
    

def store_document_option(document: str, section: str, option: str, value: Any) -> None:
    """Stores a document-scoped option in a specific section and writes the changes to the file.

    If the section does not exist, it will be created.

    Args:
        document: The document name.
        section: The section name (top-level key).
        option: The option name (second-level key).
        value: The value to store.

    Returns:
        None
    """
    if _config.get(ConfigParamScope.DOCUMENT.value) is None:
        _config[ConfigParamScope.DOCUMENT.value] = {}

    if _config[ConfigParamScope.DOCUMENT.value].get(document) is None:
        app = adsk.core.Application.get()
        if app.activeDocument and app.activeDocument.dataFile:
            project_name = app.activeDocument.dataFile.name + '.' + app.activeDocument.dataFile.fileExtension
            folder = app.activeDocument.dataFile.parentFolder
            while folder:
                project_name = folder.name + '/' + project_name
                folder = folder.parentFolder
            project_name = app.activeDocument.dataFile.parentProject.name + '/' + project_name
            _config[ConfigParamScope.DOCUMENT.value][document] = {'name': project_name}
        else:
            return  # Cannot store document-scoped option without a valid document

    scope_dict = _config[ConfigParamScope.DOCUMENT.value][document]
    _store_option(scope_dict, section, option, value)


def get_document_option(document: str, section: str, option: str, fallback: Any = None) -> Optional[Any]:
    """Retrieves an option from the document scope.

    Args:
        document: The document name.
        section: The section name.
        option: The option name.
        fallback: The default value to return if the option or section is not found.

    Returns:
        Optional[Any]: The value of the option, or the fallback value.
    """
    if document and document in _config.get(ConfigParamScope.DOCUMENT.value, []):
        return copy.deepcopy(_config[ConfigParamScope.DOCUMENT.value].get(document, {}).get(section, {}).get(option, fallback))
    return fallback


def get_global_option(section: str, option: str, fallback: Any = None) -> Optional[Any]:
    """Retrieves an option from the global scope.

    Args:
        section: The section name.
        option: The option name.
        fallback: The default value to return if the option or section is not found.

    Returns:
        Optional[Any]: The value of the option, or the fallback value.
    """
    return copy.deepcopy(_config.get(ConfigParamScope.GLOBAL.value, {}).get(section, {}).get(option, fallback))


def get_stackup(document: str, file_path: Optional[str] = None) -> Optional[StackupParser]:
    """
    Retrieves a StackupParser object for a file path specified in the config.
    Caches the parser objects to avoid re-parsing the same file.

    Args:
        section (str): The section in CONFIG.JSON.
        option (str): The option in the section that holds the file path.

    Returns:
        Optional[StackupParser]: A StackupParser object if parsing is successful,
                               otherwise None.
    """
    if file_path == None:
        file_path = get_document_option(document, 'stackup', 'file_path')
    if not file_path or not isinstance(file_path, str) or not os.path.exists(file_path):
        return None

    # check the cache
    if file_path in _stackup_cache:
        lastReadTime = _stackup_cache[file_path].get('lastReadTime')
        if lastReadTime > os.path.getmtime(file_path):
            return _stackup_cache[file_path].get('data')

    # try to parse
    parser = StackupParser(file_path)
    if not parser.data:
        return None

    # cache this
    _stackup_cache[file_path] = {'data': parser, 'lastReadTime': time.time()}

    # if the file_path was an input parameter, store it in the config
    if file_path != get_document_option(document, 'stackup', 'file_path'):
        store_document_option(document, 'stackup', 'file_path', file_path)

    return parser


# Initialize the config dictionary
_config = {}

# Load the configuration on module import.
_load_config()

# Cache for StackupParser objects
_stackup_cache = {}
