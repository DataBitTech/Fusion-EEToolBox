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

from __future__ import annotations
from abc import ABC, abstractmethod

from ...PartDataExportCommandBase import PartDataExportCommandBase


class Eetb_BOMExporterBase(ABC):
    """Abstract base class defining the interface for BOM exporters."""
    
    def __init__(self, exportBomCommand: PartDataExportCommandBase):
        self._exportBomCommand = exportBomCommand


    @abstractmethod
    def export(self, filtered_part_data: list[dict], column_attributes: list[str]) -> list[list[str]]:
        """Export part data in the specific format.
        
        Args:
            filtered_part_data: List of part dictionaries to export
            column_attributes: List of column attribute names to include in the export. These are the 
                               attribute names selected by the user on the UI. The order is the same 
                               as the child class defines it in its `output_attributes` property

        Returns:
            List of lists representing the exported data rows
        """
        raise NotImplementedError("Subclasses must implement this method")


    @abstractmethod
    def notify_selected(self) -> None:
        """Notify that this export format was selected in the UI."""
        raise NotImplementedError("Subclasses must implement this method")    


    ##############
    # PROPERTIES #
    ##############

    @property
    @abstractmethod
    def output_attributes(self) -> list[tuple[str, bool]]:
        """Returns a list of tuples representing the column attributes to be exported. Each tuple contains
        (attribute_name, is_visible). This property defines which columns are to be mapped to attributes 
        and whether they are mandatory to be mapped to one."""
        raise NotImplementedError("Subclasses must implement this property")
    

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Returns the display name of the export format. This string is used on the UI to represent the 
        selected export option to the user."""
        raise NotImplementedError("Subclasses must implement this method")

    
    ##################
    # IMPLEMENTATION #
    ##################
    def group_by_parts(self, part_data: list[dict], distinctive_attributes: list[str] = []) -> list[dict]:
        """
        Groups part data by part number, aggregating attributes from multiple entries.

        This method takes a list of part data dictionaries and groups them by the 'part_number' key.
        For each unique part number, it creates a single dictionary that contains all attributes
        from the original entries, with duplicate attributes merged into lists. Attributes specified
        in `keys_to_ignore` are ignored during the grouping process. The method ensures that
        part data is consolidated for easier processing and export, especially when dealing with
        multiple instances of the same part in a design.
        Args:
            part_data (list[dict]): A list of dictionaries, where each dictionary represents
                                    a part with its attributes as key-value pairs. Each dictionary
                                    must contain a 'part_number' key for grouping.
            distinctive_attributes (list[str], optional): A list of attribute names that are
                                                          considered significant to differentiate for grouping.
                                                          If not provided,all attributes are considered differentiating.
                                                          Defaults to an empty list.

        Returns:
            list[dict]: A list of dictionaries, where each dictionary represents a unique part
                        with its attributes consolidated. Attributes that appear multiple times
                        are stored as lists, while unique attributes are stored as single values.
        """
        group_dict: dict[str, tuple[str, int, dict]] = {}
        # extend the keys to ignore
        keys_to_ignore = ['name', 'first_sheet', 'angle', 'locked', 'mirror', 'x', 'y']
        for part in part_data:
            designator = part.get("name", "")
            serialData = self._serialize_part_data(part, keys_to_ignore, distinctive_attributes)
            if serialData not in group_dict.keys():
                group_dict[serialData] = (designator, 1, part)
            else:
                (part_list, count, part_dict) = group_dict[serialData]
                part_list += ', ' + designator
                count += 1
                group_dict[serialData] = (part_list, count, part_dict)

        grouped_data = []
        for (part_list, count, part_dict) in group_dict.values():
            part_dict['name'] = part_list
            part_dict['__quantity__'] = count
            grouped_data.append(part_dict)
        return grouped_data
    

    def _serialize_part_data(self, part: dict, keys_to_ignore: list[str] = [], distinctive_attributes: list[str] = []) -> str:
        """Serializes part data into a string representation.

        This method takes a dictionary representing a part and converts it into a
        string representation. It allows for filtering out specific keys, considering
        all attributes, or focusing on significant attributes. The serialized string
        is formatted as a tab-separated list of key-value pairs.

        Args:
            part (dict): A dictionary representing the part data, where keys are
                attribute names and values are attribute values.
            keys_to_ignore (list[str], optional): A list of keys to exclude from
                the serialization. Defaults to an empty list.
            distinctive_attributes (list[str], optional): A list of attribute names
                to include in the serialization. If empty, all attributes are included
                in the serialization. Defaults to an empty list.

        Returns:
            str: A tab-separated string representation of the part data, with each
                key-value pair separated by a tab character.
        """
        serialized_data = ''
        for key, value in part.items():
            if key not in keys_to_ignore:
                if key == "attributes" and isinstance(value, list):
                    if distinctive_attributes:
                        # Only include attributes that are in significant_attributes
                        filtered_attrs = [attr for attr in value if attr.get("name") in distinctive_attributes]
                    else:
                        # the name and value are also stored as attributes for some reason
                        filtered_attrs = [attr for attr in value if attr.get("name") not in ["NAME", "VALUE"]]
                    # Sort the filtered attributes by name to ensure consistent ordering
                    filtered_attrs = sorted(filtered_attrs, key=lambda attr: attr.get("name", ""))
                    serialized_data += ",".join([f"{attr['name']}={attr['value']}" for attr in filtered_attrs])
                else:
                    serialized_data += f"{key}={value},"
        # Remove the trailing comma
        if serialized_data.endswith(","):
            serialized_data = serialized_data[:-1]
        return serialized_data
