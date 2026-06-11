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

import json
from abc import abstractmethod
import adsk.core
from .. import config
from ..lib import fusionAddInUtils as futil
from ..lib import eetbUtils as eetbutil
from .CommandBase import CommandBase


class PaletteCommandBase(CommandBase):

    class MandatoryPaletteCommandAttributes:
        def __init__(self, basic_attributes: CommandBase.MandatoryCommandAttributes, 
                     palette_id: str, palette_name:str, palette_docking: adsk.core.PaletteDockingStates, html_path: str) -> None:
            self.basic_attributes = basic_attributes
            self.palette_id = palette_id
            self.palette_name = palette_name
            self.palette_docking = palette_docking
            self.html_path = html_path


    def __init__(self, palette_attributes: MandatoryPaletteCommandAttributes) -> None:
        """
        Initialize the PaletteCommandBase.
        
        Returns:
            None
        """
        super().__init__(palette_attributes.basic_attributes)

        self._palette_id = palette_attributes.palette_id        
        self._palette_name = palette_attributes.palette_name
        self._palette_docking = palette_attributes.palette_docking
        self._html_path = palette_attributes.html_path

        # UI members - default values
        self._palette_height = 600
        self._palette_width = 400
        self._palette_isResizable = True
        self._palette_showCloseButton = True
        self._palette_is_persistent = False

        # for handling autoclose
        self._is_Eagle_command_running = False


    ###################
    # BASIC INTERFACE #
    ###################

    def start(self) -> None:
        """
        Start the palette command and register it with the UI.
        
        Creates the command definition if it doesn't exist, sets up the command created handler,
        and adds the command button to the UI. Also validates that all required command information
        has been set by derived classes.
        
        Returns:
            None
        """
        super().start()

        # check if the derived classes defined all necessary variables
        if  not self.html_path or self.html_path == '' or \
            not self.palette_name or self.palette_name == '' or \
            not self.palette_id or self.palette_id == '' or \
            self.palette_docking is None:
            CommandBase.log_to_console(f"{self.__class__.__name__}.start() failed due to missing command information")
            return


    def stop(self) -> None:
        """
        Stop the palette command and remove it from the UI.
        
        Deletes the command definition and palette from the UI, effectively removing the command button
        and palette from the user interface.
        
        Returns:
            None
        """
        super().stop()

        # Delete the Palette
        palette: adsk.core.Palette = self.ui.palettes.itemById(self.palette_id)
        if palette:
            palette.deleteMe()


    ####################
    # PALETTE SPECIFIC #
    ####################

    @abstractmethod
    def html_event_handler(self, palette: adsk.core.Palette, event_name: str, event_data = {}) -> None:
        """
        Handle HTML events from the palette.
        
        This abstract method must be implemented by derived classes to specify
        how to handle palette-specific events not caught by the _base_event_handler().
        
        Args:
            palette (adsk.core.Palette): The palette that sent the event
            event_name (str): The name of the event
            event_data: The data associated with the event
            
        Returns:
            None
        """
        raise NotImplementedError("This method should be overridden by subclasses")


    @abstractmethod
    def palette_ready_event_handler(self, palette: adsk.core.Palette) -> None:
        """
        Handle the palette ready event.
        
        This abstract method must be implemented by derived classes to specify
        how to handle the 'paletteReady' event from the palette.
        
        Args:
            palette (adsk.core.Palette): The palette that sent the event
            
        Returns:
            None
        """
        raise NotImplementedError("This method should be overridden by subclasses")


    def close_palette(self) -> None:
        """
        Closes the palette associated with this command.
        
        This method deletes the palette from the user interface and removes any references to it.
        
        Returns:
            None
        """
        # Delete the Palette
        palette: adsk.core.Palette = self.ui.palettes.itemById(self.palette_id)
        if palette:
            palette.deleteMe()


    ###################
    # EVENT FUNCTIONS #
    ###################

    # Because no command inputs are being added in the command created event, the execute
    # event is immediately fired.
    def on_command_execute(self, args: adsk.core.CommandEventArgs) -> None:
        """
        Handle the command execute event for palette commands.
        
        Because no command inputs are being added in the command created event, the execute
        event is immediately fired. The palette is created or shown in this event handler
        
        Args:
            args (adsk.core.CommandCreatedEventArgs): Event arguments for the command execute event
            
        Returns:
            None
        """
        super().on_command_execute(args)
        try:
            # Create or show the palette.
            palette: adsk.core.Palette = self.ui.palettes.itemById(self.palette_id)
            
            if not palette:
                palette = self.ui.palettes.add(
                    id = self.palette_id,
                    name = self.palette_name,
                    htmlFileURL = self.html_path.replace('\\', '/'),
                    isVisible=True,
                    showCloseButton=self.palette_show_close_button,
                    isResizable=self.palette_is_resizeable,
                    width=self.palette_width,
                    height=self.palette_height,
                    useNewWebBrowser=True)
                
                # Add handler for events from HTML.
                self.local_handlers.append(futil.add_handler(palette.incomingFromHTML, self._base_html_event_handler))
                self.local_handlers.append(futil.add_handler(palette.closed, self.on_palette_closed))
                
            if palette.dockingState == adsk.core.PaletteDockingStates.PaletteDockStateFloating:
                palette.dockingState = self.palette_docking
            palette.isVisible = True
        except:
            self.log_error_to_ui()


    def on_command_starting(self, commandId: str) -> None:
        """
        Handle command starting event to implement auto-closing palettes
        
        Prevents closing the palette if a script or ULP command is running.
        
        Args:
            commandId (str): The ID of the command that is starting
            
        Returns:
            None
        """
        # do not close this command if the started command is a script or ULP
        if self.is_Eagle_command_running and commandId in ['Electron::RunScript', 'Electron::RunULP', 'Electron::PlaceboCommand']:
            return
        
        if not self._palette_is_persistent:
            self.close_palette()


    # Use this to handle a user closing your palette.
    def on_palette_closed(self, html_args: adsk.core.HTMLEventArgs) -> None:
        """
        Handle palette closed event.
        
        Logs when the palette is closed by the user.
        
        Args:
            html_args (adsk.core.HTMLEventArgs): Event arguments for the palette closed event
            
        Returns:
            None
        """
        PaletteCommandBase.log_to_console(f'{self.command_name}: Palette was closed.')

    
    # not used for palettes
    def on_execute_preview(self, args: adsk.core.CommandEventArgs) -> None:
        """
        Handle execute preview event.
        
        This method does nothing by default for palettes.
        
        Args:
            args (adsk.core.CommandEventArgs): Event arguments for the execute preview event
            
        Returns:
            None
        """
        pass


    ##################
    # DATA INTERFACE #
    ##################

    # override these functions as palettes do not have the same limitation as ordinary
    # commands, and we handle autoclosing ourselves - DO NOT CALL base class function
    def get_eagle_data(self, requests: list[dict], use_grid_unit = False) -> dict:
        """
        Get data from the Electronics workspace using the specified requests.
        
        This method overrides the base class implementation that prevents ULP/script 
        execution during some command events. Palettes do not have this limitation
        
        Args:
            requests (list[dict]): List of data requests to send to Eagle
            
        Returns:
            dict: Dictionary containing the requested Eagle data
        """
        self._is_Eagle_command_running = True
        eagleData = eetbutil.get_eagle_data(self.json_temp_path, requests, use_grid_unit) 
        self._is_Eagle_command_running = False
        return eagleData
    

    def run_eagle_command(self, eagleCommand: str) -> str:
        """
        Execute an Eagle command.
        This method overrides the base class implementation that prevents ULP/script 
        execution during some command events. Palettes do not have this limitation.
        
        Args:
            eagleCommand (str): The Eagle command to execute
            
        Returns:
            str: The result of executing the Eagle command
        """
        self._is_Eagle_command_running = True
        result = self.app.executeTextCommand(f"ELECTRON.RUN {eagleCommand}")
        self._is_Eagle_command_running = False
        return result
    

    #######################
    # PROTECTED FUNCTIONS #
    #######################

    def _base_html_event_handler(self, args: adsk.core.HTMLEventArgs) -> None:
        """
        Handle base HTML events from the palette.
        
        This method processes events from the HTML palette and routes them to appropriate handlers.
        
        Args:
            args (adsk.core.HTMLEventArgs): Event arguments from the HTML palette
            
        Returns:
            None
        """
        if not isinstance(args.firingEvent.sender, adsk.core.Palette):
            raise TypeError("Event sender is not a palette")
        palette = args.firingEvent.sender
        event_name = args.action
        PaletteCommandBase.log_to_console(f'{self.command_name} HTML Event: {event_name}')
        args.returnData = '{OK}'
        try:
            event_data: list[dict] = [] if not args.data else json.loads(args.data)

            if event_name in ['closePalette', 'cancelPalette']:
                self.close_palette()
            elif event_name == 'paletteReady':
                self.palette_ready_event_handler(palette)
            elif event_name == 'getTheme':
                palette.sendInfoToHTML('setTheme', eetbutil.get_theme())
            elif event_name == 'getSignalList':
                palette.sendInfoToHTML('setSignalList', json.dumps(self.get_signal_list()))
            elif event_name == 'getLayerData':
                palette.sendInfoToHTML('setLayerData', json.dumps(self.get_layer_data()))
            elif event_name == 'getEagleData':
                palette.sendInfoToHTML('setEagleData', json.dumps(self.get_eagle_data(event_data)))
            else:
                self.html_event_handler(palette, event_name, event_data)
        except:
            self.log_error_to_ui('HTML event handling threw an exception')


    ##############
    # PROPERTIES #
    ##############

    @property
    def palette_id(self) -> str:
        return self._palette_id
    
    @palette_id.setter
    def palette_id(self, _palette_id: str) -> None:
        self._palette_id = _palette_id

    @property
    def palette_name(self) -> str:
        return self._palette_name
    
    @palette_name.setter
    def palette_name(self, _palette_name: str) -> None:
        self._palette_name = _palette_name

    @property
    def palette_docking(self) -> adsk.core.PaletteDockingStates:
        return self._palette_docking
    
    @palette_docking.setter
    def palette_docking(self, _palette_docking: adsk.core.PaletteDockingStates) -> None:
        self._palette_docking = _palette_docking

    @property
    def palette_show_close_button(self) -> bool:
        return self._palette_showCloseButton
    
    @palette_show_close_button.setter
    def palette_show_close_button(self, _palette_showCloseButton: bool) -> None:
        self._palette_showCloseButton = _palette_showCloseButton

    @property
    def palette_is_resizeable(self) -> bool:
        return self._palette_isResizable
    
    @palette_is_resizeable.setter
    def palette_is_resizeable(self, _palette_isResizable: bool) -> None:
        self._palette_isResizable = _palette_isResizable

    @property
    def palette_is_persistent(self) -> bool:
        return self._palette_is_persistent
    
    @palette_is_persistent.setter
    def palette_is_persistent(self, _palette_is_persistent: bool) -> None:
        self._palette_is_persistent = _palette_is_persistent

    @property
    def palette_width(self) -> int:
        return self._palette_width
    
    @palette_width.setter
    def palette_width(self, _palette_width: int) -> None:
        self._palette_width = _palette_width

    @property
    def palette_height(self) -> int:
        return self._palette_height
    
    @palette_height.setter
    def palette_height(self, _palette_height: int) -> None:
        self._palette_height = _palette_height

    @property
    def html_path(self) -> str:
        return self._html_path
    
    @html_path.setter
    def html_path(self, _html_path: str) -> None:
        self._html_path = _html_path

    @property
    def is_Eagle_command_running(self) -> bool:
        return self._is_Eagle_command_running
    
    @is_Eagle_command_running.setter
    def is_Eagle_command_running(self, _is_Eagle_command_running: bool) -> None:
        self._is_Eagle_command_running = _is_Eagle_command_running
