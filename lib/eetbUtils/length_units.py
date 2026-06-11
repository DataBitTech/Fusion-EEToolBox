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

from enum import Enum
import re

# Define valid length dimensions
class LengthUnits(Enum):
    MILLIMETER = 'mm'
    MICROMETER = 'um'
    MICRON = 'mic'
    CENTIMETER = 'cm'
    MIL = 'mil'
    IN = 'in'
    INCH = 'inch'


def parse_length_unit(unit_string: str) -> LengthUnits:
    """
    Find the corresponding LengthUnits enum value for a given unit string.

    This function takes a unit string (e.g., 'mm', 'in') and returns the
    corresponding LengthUnits enum value. It raises a ValueError if the unit
    string is not recognized.

    Args:
        unit_string (str): The unit string to find (e.g., 'mm', 'in')

    Returns:
        LengthUnits: The corresponding LengthUnits enum value
    """
    # Remove any whitespace
    unit_string = unit_string.strip()

    # Find the matching unit in LengthUnits enum
    for unit in LengthUnits:
        if unit.value == unit_string:
            return unit

    # If no matching unit found, raise an error
    raise ValueError(f"Invalid unit '{unit_string}' in input string")


def parse_dimension_string(input_string: str, default_unit: LengthUnits = LengthUnits.MILLIMETER) -> tuple[float, LengthUnits]:
    """
    Parse a dimension string and return the value and unit.

    This function takes a string representing a dimension (e.g., '10mm', '5.5in')
    and returns a tuple containing the numeric value and the corresponding
    LengthUnits enum value. If no unit is specified, the default_unit is used.

    Args:
        input_string (str): The dimension string to parse (e.g., '10mm', '5.5in')
        default_unit (LengthUnits): The unit to use if no unit is specified in
                                   the input string. Defaults to MILLIMETER.

    Returns:
        tuple[float, LengthUnits]: A tuple containing (value, unit) where value
                                   is the numeric dimension and unit is the
                                   corresponding LengthUnits enum value.
    """
    # Remove any whitespace
    input_string = input_string.strip()

    # Check if the input string is empty
    if not input_string:
        raise ValueError("Input string is empty")

    # Use regex to find the numeric part and unit part
    # This pattern matches: optional sign, digits, optional decimal point, digits, optional exponent
    # followed by optional whitespace and unit
    pattern = r'^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*(\w*)'
    match = re.match(pattern, input_string)
    
    if not match:
        raise ValueError("Invalid format in input string")
    
    numeric_part = match.group(1)
    unit_part = match.group(2)
    
    # Convert the numeric part to float
    try:
        value = float(numeric_part)
    except ValueError:
        raise ValueError("Invalid numeric part in input string")

    # If no unit part, use the default unit
    if not unit_part:
        return (value, default_unit)

    # Find the matching unit in LengthUnits enum
    try:
        unit = parse_length_unit(unit_part)
        return (value, unit)
    except ValueError:
        raise ValueError(f"Invalid unit '{unit_part}' in input string")


def is_valid_dimension_string(dimension_string: str, allow_negative: bool = True) -> bool:
    """
    Check if a dimension string is valid.

    This function validates a dimension string (e.g., '10mm', '5.5in') to ensure
    it follows the expected format. It can optionally allow or disallow negative values.

    Args:
        dimension_string (str): The dimension string to validate (e.g., '10mm', '5.5in')
        allow_negative (bool): Whether negative values are allowed. Defaults to True.

    Returns:
        bool: True if the dimension string is valid, False otherwise.
    """
    try:
        value, _ = parse_dimension_string(dimension_string)
        if not allow_negative and value < 0:
            return False
        return True
    except ValueError:
        return False


def convert_to_unit(dimension_tuple: tuple[float, LengthUnits], target_unit: LengthUnits) -> float:
    """
    Convert a dimension value from its current unit to a target unit.

    This function takes a tuple containing a numeric value and its current
    LengthUnits enum value, and converts it to the specified target unit.
    The conversion is done using predefined conversion factors to millimeters.

    Args:
        dimension_tuple (tuple[float, LengthUnits]): A tuple containing (value, unit)
                                                     where value is the numeric dimension
                                                     and unit is the current LengthUnits enum value.
        target_unit (LengthUnits): The target LengthUnits enum value to convert to.

    Returns:
        float: The converted value in the target unit.
    """
    # Define conversion factors to millimeters
    conversion_factors = {
        LengthUnits.MILLIMETER: 1.0,
        LengthUnits.MICROMETER: 0.001,
        LengthUnits.MICRON: 0.001,
        LengthUnits.CENTIMETER: 10.0,
        LengthUnits.MIL: 0.0254,
        LengthUnits.IN: 25.4,
        LengthUnits.INCH: 25.4
    }

    # Extract value and current unit from the input tuple
    value, current_unit = dimension_tuple

    # If the current unit is the same as the target unit, return the value as is
    if current_unit == target_unit:
        return value

    # Convert the input value to millimeters first
    value_in_mm = value * conversion_factors[current_unit]

    # Convert from millimeters to the target unit
    converted_value = value_in_mm / conversion_factors[target_unit]

    return converted_value
