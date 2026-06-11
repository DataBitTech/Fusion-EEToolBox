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

import adsk.core
import os, json
from typing import TypedDict
from ..CommandBase import CommandBase
from ..PaletteCommandBase import PaletteCommandBase
from ... import config
from ... import controls as eetbControls
from ...lib import eetbUtils as eetbutil

class Eetb_ChecklistCommand(PaletteCommandBase):

    class ChecklistItem(TypedDict):
        id: int
        text: str
        isSeparator: bool

    _next_checklist_item_id: int = 0
    _checklist_items: list[ChecklistItem] = []

    def __init__(self):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_checklist_command_id',
            command_name = 'Production checklist',
            command_description = 'Final checklist to go through before production',
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'),
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
        )

        palette_attributes = PaletteCommandBase.MandatoryPaletteCommandAttributes(
            basic_attributes = command_attributes,
            palette_id = f'{config.ADDIN_NAME}_checklist_palette_id',
            palette_name = 'Production checklist',
            palette_docking = adsk.core.PaletteDockingStates.PaletteDockStateRight, # type: ignore
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'palette.html')
        )

        super().__init__(palette_attributes)

        self._palette_is_persistent = True
      


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        eetbControls.add_command_to_panel(config.ELECTRON_LAYOUT_ENV_ID, eetbControls.LayoutPanel.COMMON_PANEL, commandDefinition)


    def on_command_execute(self, args: adsk.core.CommandEventArgs) -> None:
        palette: adsk.core.Palette = self.ui.palettes.itemById(self.palette_id)
        if palette is not None and palette.isVisible == False:
            self._send_all_data_to_html(palette)
        super().on_command_execute(args)

    def html_event_handler(self, palette: adsk.core.Palette, event_name: str, event_data = {}):
        """Handles events sent from the HTML palette.

        This method is called whenever an event is triggered from the HTML side
        of the palette. It processes the event name and data to perform appropriate
        actions, such as adding or removing checklist items. See the base class
        method for full details.

        Args:
            palette (adsk.core.Palette): The palette that triggered the event.
            event_name (str): The name of the event that was triggered.
            event_data (dict, optional): Additional data associated with the event.
        """
        if event_name == 'checklistChanged':
            new_checklist = event_data.get('items', [])
            for item in new_checklist:
                if item.get('id', 0) == 0:
                    item['id'] = Eetb_ChecklistCommand._next_checklist_item_id
                    Eetb_ChecklistCommand._next_checklist_item_id += 1
            Eetb_ChecklistCommand._checklist_items = new_checklist
            self._save_global_config()
            self._send_all_data_to_html(palette)

        elif event_name == 'checkedStateChanged':
            self._save_document_checked_states(event_data)


    def palette_ready_event_handler(self, palette: adsk.core.Palette):
        """Handles the event when the palette is ready to receive data.

        This method is called when the palette has finished loading and is ready
        to receive data. It sends the current checklist items to the HTML side
        of the palette. See the base class for more details

        Args:
            palette (adsk.core.Palette): The palette that is ready.
        """
        self._send_all_data_to_html(palette)


    def _get_global_config(self):
        """Retrieves the global configuration for the checklist.

        This method reads the checklist configuration from the global settings.
        It is used to load the saved checklist items when the palette is initialized
        or when the configuration is needed.
        """
        try:
            Eetb_ChecklistCommand._next_checklist_item_id = int(eetbutil.config_manager.get_global_option(self.command_id, 'next_id', 1)) # type: ignore
            Eetb_ChecklistCommand._checklist_items = eetbutil.config_manager.get_global_option(self.command_id, 'items', [])
        except (ValueError, TypeError):
            Eetb_ChecklistCommand._next_checklist_item_id = 1


    def _save_global_config(self):
        """Saves the current checklist configuration to global settings.

        This method stores the current state of the checklist items and the next
        available item ID into the global configuration. It is called whenever
        the checklist is modified to persist the changes across sessions.
        """
        eetbutil.config_manager.store_global_option(self.command_id, 'next_id', Eetb_ChecklistCommand._next_checklist_item_id)
        eetbutil.config_manager.store_global_option(self.command_id, 'items', Eetb_ChecklistCommand._checklist_items)


    def _get_document_checked_states(self):
        """Retrieves the checked state of checklist items for the current document.

        This method is intended to fetch the current checked status of checklist
        items specific to the active document. It is used to restore the state
        of checklist items when the palette is opened for a particular document.
        """
        return eetbutil.config_manager.get_document_option(self.document_id, self.command_id, 'checked_states', {})


    def _save_document_checked_states(self, checked_states: dict):
        """Saves the checked state of checklist items for the current document.

        This method stores the current checked status of checklist items specific
        to the active document. It is used to persist the state of checklist items
        across sessions for the current document.

        Args:
            checked_states (dict): A dictionary mapping checklist item IDs to their checked state.
        """
        eetbutil.config_manager.store_document_option(self.document_id, self.command_id, 'checked_states', checked_states)


    def _send_all_data_to_html(self, palette: adsk.core.Palette):
        """Sends all current checklist data to the HTML palette.

        This method prepares the checklist data and sends it to the HTML side
        of the palette for display. It includes the checklist items and their
        checked states.

        Args:
            palette (adsk.core.Palette): The palette to which the data is sent.
        """
        self._get_global_config()
        document_checked_item_ids = self._get_document_checked_states()
        
        data_to_send = {
            'items': Eetb_ChecklistCommand._checklist_items,
            'checkedItemIds': document_checked_item_ids
        }
        palette.sendInfoToHTML('setChecklistData', json.dumps(data_to_send))
