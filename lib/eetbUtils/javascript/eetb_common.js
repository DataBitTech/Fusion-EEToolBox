/* 
This software is released under the MIT license:
MIT License

Copyright (c) 2025 Pal Szabo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
=====================================================
*/

import { ExportDataType } from './eetb_info_generated.js';
import { theme } from './eetb_info_generated.js';
import { icon_path } from './eetb_info_generated.js';

// Reexport
export { ExportDataType }
export { theme }
export { icon_path }

// EAGLE DATA HANDLING sorted into global variables
export let gridUnit = 'mm'
export let signalList = [];
export let signalSelection = [];
export let signalData = {};
export let partList = [];
export let partSelection = [];
export let partData = {};
export let layerData = [];
export let attributeList = [];

/* make these available in the palette as global */
window.gridUnit = gridUnit;
window.signalList = signalList;
window.signalSelection = signalSelection;
window.signalData = signalData;
window.partList = partList;
window.partSelection = partSelection;
window.partData = partData;
window.layerData = layerData;
window.attributeList = attributeList;

window.eetb_onCancelButton = eetb_onCancelButton;
window.eetb_onCloseButton = eetb_onCloseButton;
window.eetb_textFields_attachAutoComplete = eetb_textFields_attachAutoComplete;
window.eetb_layerList_populate = eetb_layerList_populate;
window.eetb_layerList_getSelectedLayerNumbers = eetb_layerList_getSelectedLayerNumbers;
window.eetb_EagleData_processJson = eetb_EagleData_processJson;

window.icon_path = icon_path;
window.theme = theme;
window.ExportDataType = ExportDataType;

/**
 * Notifies Fusion that the palette is ready to handle events. This event will be caught
 * by the base class which in turn calls a must-implement callback. This can be used to
 * send data to intialize the palette
 */
document.addEventListener('DOMContentLoaded', () => {
    document.body.className = theme

    let adskWaiter = setInterval(() => {
        if (window.adsk) {
            clearInterval(adskWaiter);
            adsk.fusionSendData('paletteReady', '');
        }
    });
});


/**
 * Throws an error indicating that a custom `displayError()` implementation is required.
 * This function acts as a placeholder for error display logic that must be defined
 * by the consumer of `eetb_common.js`.
 * @throws {Error} Always throws an error with a message about implementation requirement.
 */
function displayError() {
    throw new Error("If you are using eetb_common.js, you must implement displayError()");
}


export function eetb_onCancelButton() {adsk.fusionSendData('cancelPalette', '');}
export function eetb_onCloseButton() { adsk.fusionSendData('closePalette', '');}


/**
 * Attaches autocomplete functionality to a set of input fields.
 * As the user types, a dropdown displays suggestions filtered from a provided array.
 * Supports navigation with ArrowUp/ArrowDown, selection with Enter, and dismissal with Escape.
 * Example usage:
 * 
 * document.addEventListener("DOMContentLoaded", function() {
 *     const inputFields = [
 *         document.getElementById("input1"),
 *         document.getElementById("input2")
 *     ];
 *     attachAutocomplete(inputFields);
 * });
 *
 * @param {Array<HTMLInputElement>} inputFields - An array of HTML input elements to attach autocomplete to.
 * @param {Array<string>} matchingArray - The array of strings to use for matching autocomplete suggestions.
 */
export function eetb_textFields_attachAutoComplete(inputFields, matchingArray) {
    inputFields.forEach(input => {
        const dropdown = document.createElement("div");
        dropdown.className = "autocomplete-dropdown"; // Use CSS class
        document.body.appendChild(dropdown);

        let currentIndex = -1;
        let currentMatches = [];

        function renderDropdown(matches) {
            dropdown.innerHTML = "";
            currentIndex = -1;
            currentMatches = matches;
            matches.forEach((item, idx) => {
                const entry = document.createElement("div");
                entry.className = "autocomplete-entry";
                entry.textContent = item; // Set the text content
                if (idx === currentIndex) {
                   entry.classList.add("active"); // Add 'active' class when highlighted
                }
                entry.addEventListener("mousedown", function() {
                    input.value = item.toUpperCase();
                    dropdown.style.display = "none";
                    // Manually trigger 'input' event after selection
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                });
                dropdown.appendChild(entry);
            });

            if (matches.length > 4) {
                dropdown.style.maxHeight = "120px";
                dropdown.style.overflowY = "auto";
            } else {
                dropdown.style.maxHeight = "";
                dropdown.style.overflowY = "";
            }
        }

        input.addEventListener("input", function() {
            input.value = input.value.toUpperCase();
            const query = input.value.trim();
            dropdown.innerHTML = "";
            if (query === "") {
                dropdown.style.display = "none";
                currentMatches = [];
                return;
            }

            const matches = matchingArray.filter(s => s.toUpperCase().includes(query));
            if (matches.length === 0) {
                dropdown.style.display = "none";
                currentMatches = [];
                return;
            }

            renderDropdown(matches);

            const rect = input.getBoundingClientRect();
            dropdown.style.left = `${rect.left}px`;
            dropdown.style.top = `${rect.bottom + window.scrollY}px`;
            dropdown.style.width = `${rect.width}px`;
            dropdown.style.display = "block";
        });

        input.addEventListener("keydown", function(e) {
            if (dropdown.style.display === "none" || currentMatches.length === 0) return;

            if (e.key === "ArrowDown") {
                e.preventDefault();
                currentIndex = (currentIndex + 1) % currentMatches.length;
                updateActiveDropdown();
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                currentIndex = (currentIndex - 1 + currentMatches.length) % currentMatches.length;
                updateActiveDropdown();
            } else if (e.key === "Enter" && currentIndex >= 0) {
                e.preventDefault();
                dropdown.style.display = "none";
                // Manually trigger 'input' event after selection
                input.dispatchEvent(new Event('input', { bubbles: true }));
            } else if (e.key === "Escape") {
                e.preventDefault();
                dropdown.style.display = "none";
            }
        });

        function updateActiveDropdown() {
            Array.from(dropdown.children).forEach((entry, idx) => {
                if (idx === currentIndex) {
                    entry.classList.add("active");
                } else {
                    entry.classList.remove("active");
                }
            });

            if (currentIndex >= 0) {
                input.value = currentMatches[currentIndex].toUpperCase();
            }
            
            // Scroll to selected entry
            if (currentIndex >= 0 && dropdown.children[currentIndex]) {
                dropdown.children[currentIndex].scrollIntoView({block: "nearest"});
            }
        }

        document.addEventListener("mousedown", function(e) {
            if (!dropdown.contains(e.target) && e.target !== input) {
                dropdown.style.display = "none";
            }
        });
    });
}

/**
 * Populates a given container element with a list of layer items.
 * Each layer item displays a color box and the layer name.
 * Implements multi-selection functionality:
 * - Single click: Selects the clicked item and deselects others.
 * - Ctrl + click: Toggles the selection of the clicked item.
 * - Shift + click: Selects a range of items from the last clicked item to the current item.
 *
 * @param {HTMLElement} container - The HTML element (e.g., a div) to populate with layer items.
 * @param {Array<Object>} layers - An array of layer objects, where each object has at least `number`, `name`, and `color` properties.
 */
export function eetb_layerList_populate(container, layers) {
    if (!container || !layers) {
        displayError("No data or no container")
        return;
    }

    container.innerHTML = ''; // Clear existing content

    // Helper to convert ARGB hex string to CSS rgba string
    function argbToRgbaCss(argbInt) {
        if (typeof argbInt !== 'string' || !argbInt.startsWith('#') || argbInt.length !== 9) return '#FFC0CB'; // Fallback for invalid input
        const hex = argbInt.substring(1).toUpperCase();
        const a = parseInt(hex.substring(0, 2), 16) / 255;
        const r = parseInt(hex.substring(2, 4), 16);
        const g = parseInt(hex.substring(4, 6), 16);
        const b = parseInt(hex.substring(6, 8), 16);
        return `rgba(${r}, ${g}, ${b}, ${a.toFixed(2)})`;
    }

    layers.forEach((layer, index) => {
        const item = document.createElement('div');
        item.className = 'layer-item';
        item.dataset.layerNumber = layer.number;
        item.dataset.index = index;
        item.classList.add('selected')

        const colorBox = document.createElement('span');
        colorBox.className = 'color-box';
        const color = argbToRgbaCss(layer.color);
        colorBox.style.backgroundColor = color;

        const nameSpan = document.createElement('span');
        nameSpan.textContent = ` ${layer.name}`;

        item.appendChild(colorBox);
        item.appendChild(nameSpan);

        item.addEventListener('click', (event) => {
            const currentIndex = parseInt(item.dataset.index);
            const allItems = Array.from(container.querySelectorAll('.layer-item'));

            if (event.shiftKey && lastClickedIndex !== -1) {
                const start = Math.min(lastClickedIndex, currentIndex);
                const end = Math.max(lastClickedIndex, currentIndex);
                
                if (!event.ctrlKey) {
                    allItems.forEach(i => i.classList.remove('selected'));
                }

                for (let i = start; i <= end; i++) {
                    allItems[i].classList.add('selected');
                }
            } else if (event.ctrlKey) {
                item.classList.toggle('selected');
                if (item.classList.contains('selected')) {
                    lastClickedIndex = currentIndex;
                } else if (lastClickedIndex === currentIndex) {
                    lastClickedIndex = -1; // Anchor was deselected
                }
            } else {
                allItems.forEach(i => i.classList.remove('selected'));
                item.classList.add('selected');
                lastClickedIndex = currentIndex;
            }
        });

        container.appendChild(item);
    });
}

/**
 * Retrieves the layer numbers of all currently selected layer items in the `#layer-list-container`.
 *
 * @param {HTMLElement} containerElement - The container element to search within for selected layer items
 * @returns {Array<number>} An array of integers, where each integer is the layer number of a selected item.
 */
export function eetb_layerList_getSelectedLayerNumbers(container) {
    const selectedItems = container.querySelectorAll('.layer-item.selected');
    const layerNumbers = [];
    selectedItems.forEach(item => {
        layerNumbers.push(parseInt(item.dataset.layerNumber));
    });
    return layerNumbers;
}

/**
 * Generates a JSON string representing a list of requests for the Python get_eagle_data function.
 *
 * @param {Array<string>} exportDataTypeValues - An array of ExportDataType values (e.g., ["signal_list", "signal_data"]).
 * @param {Object<string, Array<string>>} [argsMap={}] - An optional map where keys are ExportDataType keys
 *                                                      and values are arrays of strings for the 'args' field.
 *                                                      Example: { "SIGNAL_DATA": ["SIG1", "SIG2"] }
 * @returns {string} A JSON string suitable for the 'requests' parameter of get_eagle_data.
 */
function eetb_EagleData_generateRequestsJson(exportDataTypeValues, argsMap = {}) {
    const requests = [];

    // Create a reverse map from value to key (e.g., 'signal_list' -> 'SIGNAL_LIST')
    const valueToKeyMap = Object.keys(ExportDataType).reduce((obj, key) => {
        obj[ExportDataType[key]] = key;
        return obj;
    }, {});

    exportDataTypeValues.forEach(typeValue => { // typeValue is now "signal_list"
        const key = valueToKeyMap[typeValue]; // key becomes "SIGNAL_LIST"

        if (key) {
            const args = argsMap[key] || [];
            requests.push({
                type: typeValue,
                args: args
            });
        } else {
            displayError(`Unknown ExportDataType value: ${typeValue}. Skipping.`);
        }
    });

    return JSON.stringify(requests);
}

/**
 * Processes a JSON data structure from get_eagle_data and distributes the data
 * to the appropriate global variables based on the first level keys.
 * This function performs in-place updates to ensure any existing references
 * to the global data variables remain valid.
 *
 * @param {string} jsonDataString - The JSON string returned from the Python get_eagle_data function.
 */
export function eetb_EagleData_processJson(jsonDataString) {
    try {
        const data = JSON.parse(jsonDataString);

        for (const key in data) {
            if (data.hasOwnProperty(key)) {
                switch (key) {
                    case ExportDataType.GRID_UNIT:
                        // This is a single string value, save it in a global variable
                        gridUnit = data[key];
                        window.gridUnit = gridUnit;
                        break;
                    case ExportDataType.SIGNAL_LIST:
                        const signals = data[key];
                        if (Array.isArray(signals) && signals.every(item => typeof item === 'string')) {
                            // In-place update for signalList array
                            signalList.length = 0;
                            Array.prototype.push.apply(signalList, signals);
                        } else {
                            displayError("Invalid format for 'signal_list' data: expected an array of strings.");
                        }
                        break;
                    case ExportDataType.SIGNAL_SELECTION:
                        const signal_selection = data[key];
                        if (Array.isArray(signal_selection) && signal_selection.every(item => typeof item === 'string')) {
                            // In-place update for signalSelection array
                            signalSelection.length = 0;
                            Array.prototype.push.apply(signalSelection, signal_selection);
                        } else {
                            displayError("Invalid format for 'signal_selection' data: expected an array of strings.");
                        }
                        break;
                    case ExportDataType.SIGNAL_DATA:
                        const sigData = data[key];
                        if (typeof sigData === 'object' && sigData !== null) {
                            // In-place update for signalData object
                            for (const prop of Object.keys(signalData)) {
                                delete signalData[prop];
                            }
                            Object.assign(signalData, sigData);
                        } else {
                            displayError("Invalid format for 'signal_data' data: expected an object.");
                        }
                        break;
                    case ExportDataType.PART_LIST:
                        const parts = data[key];
                        if (Array.isArray(parts) && parts.every(item => typeof item === 'string')) {
                            // In-place update for signalList array
                            partList.length = 0;
                            Array.prototype.push.apply(partList, parts);
                        } else {
                            displayError("Invalid format for 'part_list' data: expected an array of strings.");
                        }
                        break;
                    case ExportDataType.PART_SELECTION:
                        const part_selection = data[key];
                        if (Array.isArray(part_selection) && part_selection.every(item => typeof item === 'string')) {
                            // In-place update for signalSelection array
                            partSelection.length = 0;
                            Array.prototype.push.apply(partSelection, part_selection);
                        } else {
                            displayError("Invalid format for 'part_selection' data: expected an array of strings.");
                        }
                        break;
                    case ExportDataType.PART_DATA:
                        const prtData = data[key];
                        if (typeof prtData === 'object' && prtData !== null) {
                            // In-place update for partData object
                            for (const prop of Object.keys(partData)) {
                                delete partData[prop];
                            }
                            Object.assign(partData, prtData);
                        } else {
                            displayError("Invalid format for 'part_data' data: expected an object.");
                        }
                        break;
                    case ExportDataType.LAYER_DATA:
                        const lyrData = data[key];
                        if (Array.isArray(lyrData)) {
                            // In-place update for layerData array
                            layerData.length = 0;
                            Array.prototype.push.apply(layerData, lyrData);
                        } else {
                            displayError("Invalid format for 'layer_data' data: expected an array.");
                        }
                        break;
                    case ExportDataType.ATTRIBUTE_LIST:
                        const attributes = data[key];
                        if (Array.isArray(attributes) && attributes.every(item => typeof item === 'string')) {
                            // In-place update for signalList array
                            attributeList.length = 0;
                            Array.prototype.push.apply(attributeList, attributes);
                        } else {
                            displayError("Invalid format for 'attribute_list' data: expected an array of strings.");
                        }
                        break;
                    default:
                        console.warn(`Unknown top-level key in Eagle data: ${key}`);
                        break;
                }
            }
        }
    } catch (e) {
        displayError("Error parsing or processing Eagle data JSON: " + e);
    }
}
