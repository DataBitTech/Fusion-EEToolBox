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

import adsk.core
import re
import copy
import webbrowser
import os, json

from ..CommandBase import CommandBase
from ..PaletteCommandBase import PaletteCommandBase
from ... import config
from ... import controls as eetbControls
from ...lib import eetbUtils as eetbutil

class Eetb_ToDoListCommand(PaletteCommandBase):

    def __init__(self):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_todo_list_command_id',
            command_name = 'ToDo List',
            command_description = 'Keep track of your tasks in the electronics $1,',
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'),
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources'))

        palette_attributes = PaletteCommandBase.MandatoryPaletteCommandAttributes(
            basic_attributes = command_attributes,
            palette_id = f'{config.ADDIN_NAME}_todo_list_palette_id',
            palette_name = 'ToDo',
            palette_docking = adsk.core.PaletteDockingStates.PaletteDockStateFloating, # type: ignore
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'palette.html'))
        super().__init__(palette_attributes)

        self.palette_width = 600
        self.palette_height = 600
        self.palette_is_persistent = True


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        eetbControls.add_command_to_panel(config.ELECTRON_SCHEMATIC_ENV_ID, eetbControls.SchematicPanel.COMMON_PANEL, commandDefinition)
        eetbControls.add_command_to_panel(config.ELECTRON_LAYOUT_ENV_ID,    eetbControls.LayoutPanel.COMMON_PANEL,    commandDefinition)


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
        if event_name == 'addItem':
            self._add_item(event_data.get('text', ''))
        elif event_name == 'removeItem':
            self._remove_item(event_data.get('id'))
        elif event_name == 'editItem':
            self._edit_item(event_data.get('id'), event_data.get('text', ''))
        elif event_name == 'clickableTextClick':
            self._handle_clickable_text_action(event_data.get('text'))
        elif event_name == 'getItems':
            self._send_items_to_html(palette)


    def palette_ready_event_handler(self, palette: adsk.core.Palette):
        """Handles the palette ready event.

        This function is called when the palette is fully initialized and ready for interaction.
        It is used to perform initialization tasks that require the palette to be active.
        It overrides the base class method as required by the base class

        Args:
            palette (adsk.core.Palette): The palette that triggered the event.
        """
        self._send_items_to_html(palette)


    def _get_stored_items(self) -> list:
        """Retrieves the list of stored to-do items from the user configuration file.

        Returns:
            list: A list of to-do items, or an empty list if the file doesn't exist or is invalid.
        """
        return eetbutil.config_manager.get_document_option(self.document_id, self.command_id, 'items', []) # type: ignore


    def _save_items(self, items: list):
        """Saves the provided list of to-do items to the user configuration file.

        Args:
            items (list): The list of to-do items to be saved.
        """
        eetbutil.config_manager.store_document_option(self.document_id, self.command_id, 'items', items)


    def _process_items_for_frontend(self, items: list) -> list:
        """Processes the list of to-do items for display in the frontend.

        This function prepares the items for rendering in the HTML palette by adding
        any necessary formatting or metadata required for the frontend display.

        Args:
            items (list): A list of to-do items to be processed.

        Returns:
            list: A processed list of to-do items ready for frontend display.
        """
        processed_items = copy.deepcopy(items)
        
        # get the data from Fusion
        requests = [{'type': eetbutil.ExportDataType.SIGNAL_LIST.value, 'args': []},
                    {'type': eetbutil.ExportDataType.PART_LIST.value, 'args': []}]
        eagle_objects = self.get_eagle_data(requests)
        clickable_words: list[str] = eagle_objects.get('signal_list', [])
        clickable_words.extend(eagle_objects.get('part_list', []))
        
        for item in processed_items:
            text = item['text']

            words = re.split(r'(\s+)', text)
            processed_words = []
            for word in words:
                if not word or word.isspace():
                    processed_words.append(word)
                    continue

                clean_word = word.strip('.,:;?()[]{}')

                is_link = (
                    clean_word.startswith('http://') or
                    clean_word.startswith('https://') or
                    clean_word.startswith('www.') or
                    clean_word.count('/') >= 2
                )

                if is_link or clean_word in clickable_words:
                    prefix_len = word.find(clean_word)
                    suffix_start = prefix_len + len(clean_word)
                    prefix = word[:prefix_len]
                    suffix = word[suffix_start:]
                    processed_words.append(f"{prefix}<{clean_word}>{suffix}")
                else:
                    processed_words.append(word)
            
            text = ''.join(processed_words)

            if self._app.activeDocument.dataFile.fileExtension == 'fsch':
                # Look for 'sheet' or 'page' (case insensitive) followed by optional whitespace and a number
                sheet_page_pattern = re.compile(r'\b(?:sheet|page|p)\s*(\d+)\b', re.IGNORECASE)
                def replace_sheet_page(match):
                    sheet_or_page = match.group(0)
                    number = match.group(1)
                    return f"<{sheet_or_page}>"

                text = sheet_page_pattern.sub(replace_sheet_page, text)

            item['text'] = text
        return processed_items


    def _send_items_to_html(self, palette: adsk.core.Palette):
        """Sends the current list of to-do items to the HTML palette for display.

        This function retrieves the stored to-do items, processes them for frontend
        display, and sends them to the palette's HTML side to be rendered.

        Args:
            palette (adsk.core.Palette): The palette to send the items to.
        """
        items = self._get_stored_items()
        processed_items = self._process_items_for_frontend(items)
        palette.sendInfoToHTML('setItems', json.dumps(processed_items))


    def _handle_clickable_text_action(self, clicked_text: str):
        """Handles the action when a clickable text element is clicked in the ToDo list.

        This function is triggered when a user clicks on a text element in the ToDo list
        that is recognized as clickable (e.g., a URL, a sheet reference, or a part/signal name).
        It determines the type of the clicked text and performs the appropriate action,
        such as opening a URL in a browser or navigating to a specific sheet.

        Args:
            clicked_text (str): The text content of the clicked element.
        """
        is_link = (
            clicked_text.startswith('http://') or
            clicked_text.startswith('https://') or
            clicked_text.startswith('www.') or
            # A simple heuristic for potential local file paths or URLs without schemes
            clicked_text.count('/') >= 2
        )

        if is_link:
            url_to_open = clicked_text
            if not (url_to_open.startswith('http://') or url_to_open.startswith('https://')):
                # Prepend http:// if it looks like a domain but lacks scheme
                if url_to_open.startswith('www.'):
                    url_to_open = 'http://' + url_to_open
                elif url_to_open.count('/') >= 2:
                    # If it has slashes, it might be a local path or a schemeless URL.
                    # webbrowser.open handles local files too.
                    pass 
            
            try:
                webbrowser.open(url_to_open)
            except Exception as e:
                adsk.core.Application.get().userInterface.messageBox(f"Failed to open link {url_to_open}: {e}")
        else:
            # Not a link, could be a component, a signal, etc.
            # Check if clicked_text starts with 'page' or 'sheet' (case insensitive) and is followed by optional whitespace and a number
            sheet_page_pattern = re.compile(r'^\s*(?:page|sheet|p)\s*(\d+)', re.IGNORECASE)
            match = sheet_page_pattern.match(clicked_text.strip())
            if match:
                sheet_number = match.group(1)
                # Handle the page/sheet number here, e.g., open the corresponding sheet/page in the document
                self.app.executeTextCommand(f"ELECTRON.RUN EDIT .s{sheet_number}")
            else:
                # Handle other types of clickable text (e.g., components, signals)
                self.app.executeTextCommand(f"ELECTRON.RUN SHOW {clicked_text}")


    def _add_item(self, text: str):
        """Adds a new to-do item to the list.

        This function takes the text of a new to-do item, creates a unique ID for it,
        and stores it in the configuration. The updated list is then sent to the HTML
        palette for display.

        Args:
            text (str): The text content of the new to-do item to be added.
        """
        if not text:
            return
        items = self._get_stored_items()
        
        max_id = 0
        for item in items:
            try:
                # The running id is an int, but could be stored as a string in the JSON.
                item_id = int(item.get('id', 0))
                if item_id > max_id:
                    max_id = item_id
            except (ValueError, TypeError):
                # This will catch old non-integer IDs like 'item_...'
                continue
        
        new_item = {
            'id': max_id + 1,
            'text': text
        }
        
        items.append(new_item)
        self._save_items(items)
        
        palette: adsk.core.Palette = self.ui.palettes.itemById(self.palette_id)
        if palette:
            self._send_items_to_html(palette)


    def _edit_item(self, item_id: str, new_text: str):
        """Edits an existing to-do item with the provided new text.

        This function updates the text of an existing to-do item identified by its ID.
        The updated list is then saved to the user configuration and sent to the HTML
        palette for display.

        Args:
            item_id (str): The unique identifier of the to-do item to be edited.
            new_text (str): The new text content for the to-do item.
        """
        items = self._get_stored_items()
        
        id_to_edit = int(item_id)

        found = False
        for item in items:
            if item.get('id') == id_to_edit:
                item['text'] = new_text
                found = True
                break
        
        if found:
            self._save_items(items)
        
            palette: adsk.core.Palette = self.ui.palettes.itemById(self.palette_id)
            if palette:
                self._send_items_to_html(palette)


    def _remove_item(self, item_id: str):
        """Removes a to-do item with the specified ID from the list.

        This function finds and removes the to-do item identified by its ID from the
        stored list. The updated list is then saved to the user configuration and
        sent to the HTML palette for display.

        Args:
            item_id (str): The unique identifier of the to-do item to be removed.
        """
        items = self._get_stored_items()

        # User confirms only integer-based IDs are stored.
        # item_id from HTML will be a string representation of an integer.
        id_to_remove = int(item_id)

        items = [item for item in items if item['id'] != id_to_remove]
        self._save_items(items)
        
        palette: adsk.core.Palette = self.ui.palettes.itemById(self.palette_id)
        if palette:
            self._send_items_to_html(palette)
