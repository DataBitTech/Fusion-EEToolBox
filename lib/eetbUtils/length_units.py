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

# Define valid length dimensions
valid_length_units = ['mm', 'um', 'mic', 'cm', 'mil', 'in', 'inch']

def parse_dimension_string(input_string: str, default_unit = 'mm') -> tuple[float, str]:
    """
    Robust parser for dimension strings with handling of edge cases.
    
    Args:
        input_string (str): String to parse
        
    Returns:
        tuple: (value: float, unit: str)
        
    Raises:
        ValueError: If the conversion failed
    """
    # Strip leading and trailing whitespace
    input_string = input_string.strip()
    
    if not input_string:
        raise ValueError("Input string is empty")
    
    # Try to find a unit at the end of the string
    unit = None
    value_str = input_string
    
    # Check for each valid unit at the end of the string
    for unit_name in valid_length_units:
        # Check if the string ends with this unit (case insensitive)
        if input_string.lower().endswith(unit_name.lower()):
            # Ensure it's a complete match (not part of a larger word)
            # Find the position where the unit starts
            unit_start = input_string.lower().rfind(unit_name.lower())
            # Extract the part before the unit
            value_str = input_string[:unit_start].rstrip()
            unit = unit_name
            break
    
    # If no unit found, treat the entire string as a value
    if unit is None:
        value_str = input_string
        unit = default_unit
    
    # Try to convert the value part to float
    try:
        value = float(value_str)
        return (value, unit)
    except ValueError:
        raise ValueError(f"Cannot convert '{value_str}' to float")


def convert_to_unit(dimension_tuple: tuple[float, str], target_unit: str) -> float:
    """
    Converts a dimension tuple (value, unit) to the grid unit of the current
    Eagle data and returns only the dimensionless number in that unit.

    Args:
        dimension_tuple (tuple): A tuple of (value: float, unit: str)

    Returns:
        float: The dimensionless value in the grid unit
    """
    value, unit = dimension_tuple
    unit = unit.lower().strip()
    target_unit = target_unit.lower().strip()
    if target_unit not in valid_length_units:
        raise ValueError(f"Invalid target unit: {target_unit}")
    
    # check if any conversion is needed
    if unit == target_unit:
        return value

    # Conversion factors relative to mm (base unit)
    conversion_factors = {
        'mm': 1.0,
        'um': 0.001,
        'mic': 0.001,
        'cm': 10.0,
        'mil': 0.0254,
        'in': 25.4,
        'inch': 25.4
    }
    # Get the conversion factor for the input unit
    input_factor = conversion_factors.get(unit, 1.0)
    # Get the conversion factor for the grid unit
    grid_factor = conversion_factors.get(target_unit, 1.0)
    # Convert to grid unit and return the dimensionless value
    return value * (input_factor / grid_factor)