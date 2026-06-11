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
import traceback
import os
from abc import ABC, abstractmethod
from .. import config
from ..lib import fusionAddInUtils as futil
from ..lib import eetbUtils as eetbutil


class CommandBase(ABC):
    """
    Base class for all commands in the Electronics Extended ToolBox Fusion add-in.
    
    This class provides common functionality and interface for all commands including
    UI integration, data handling, and event management.
    """
    
    class MandatoryCommandAttributes:
        def __init__(self, command_id: str, command_name: str, command_description: str, icon_folder: str, json_temp_path: str):
            self.command_id = command_id
            self.command_name = command_name
            self.command_description = command_description
            self.icon_folder = icon_folder
            self.json_temp_path = json_temp_path


    ###################
    # BASIC INTERFACE #
    ###################

    def __init__(self, command_attributes: MandatoryCommandAttributes):
        # copy mandatory attributes
        self._command_id = command_attributes.command_id
        self._command_name = command_attributes.command_name
        self._command_description = command_attributes.command_description
        self._icon_folder = command_attributes.icon_folder
        self._json_temp_path = command_attributes.json_temp_path
        
        self._app = adsk.core.Application.get()
        self._ui = self._app.userInterface
        self._local_handlers = []

        # used to avoid calling eagle commands in the execute handler
        self._in_command_execute_event: bool
        self._event_error_msg = 'Logic error - ULP/script commands must not be run from the ' \
            'on_command_execute() event. This warning is a safety feature to prevent unintended side effects ' \
            '(they close the command UI, so the rest of the function will reference a non-existing object ' \
            'and Fusion will crash).\n\nIf you need to run eagle ULPs then either collect data in the ' \
            'on_command_created() event, or use a palette implementation, which is our code and ' \
            'only closes automatically when we want it :) For running scripts on command execution, either ' \
            'use a palette implementation (it does event handling differently), or use a Eetb_ExecuteScriptCommand ' \
            'instance. See Eetb_FixLineConnectionsCommand for an example'


    @abstractmethod
    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition) -> None:
        """
        Add command button to the user interface.
        
        This abstract method must be implemented by derived classes to specify
        where the command button should be added to the UI.
        
        Args:
            commandDefinition (adsk.core.CommandDefinition): The command definition to add to UI
            
        Returns:
            None
        """
        raise NotImplementedError("This method should be overridden by subclasses")


    def start(self) -> None:
        """
        Start the command and register it with the UI.
        
        Creates the command definition if it doesn't exist, sets up the command created handler,
        and adds the command button to the UI. Also validates that all required command information
        has been set by derived classes.
        
        Returns:
            None
        """
        # check if the derived classes defined all necessary variables
        if  not self.command_id or self.command_id == '' or \
            not self.command_name or self.command_name == '' or \
            not self.command_description or \
            not self.icon_folder or self.icon_folder == '' or \
            not self.json_temp_path or self.json_temp_path == '' :
            
            CommandBase.log_to_console(f"{self.__class__.__name__}.start() failed due to missing command information")
            return
        
        # Add command definitions here, this sets an id and basic info for a command that can later be assigned to an event callback
        command_definition: adsk.core.CommandDefinition = self.ui.commandDefinitions.itemById(self.command_id)
        if not command_definition:
            command_definition = self.ui.commandDefinitions.addButtonDefinition(self.command_id, self.command_name, self.command_description, self.icon_folder)
            # Add command created handler. The function passed here will be executed when the command is executed.
            self._local_handlers.append(futil.add_handler(command_definition.commandCreated, self.on_command_created))

        # Add command button to the UI
        self.add_command_button_to_ui(command_definition)


    def stop(self) -> None:
        """
        Stop the command and remove it from the UI.
        
        Deletes the command definition from the UI, effectively removing the command button
        from the user interface.
        
        Returns:
            None
        """
        # Delete the command definition
        command_definition: adsk.core.CommandDefinition = self.ui.commandDefinitions.itemById(self.command_id)

        if command_definition:
            command_definition.deleteMe()


    ##################
    # DATA INTERFACE #
    ##################

    def get_signal_list(self) -> dict:
        """
        Shorthand for the data retrievel utility's generic function
        
        Returns:
            dict: Dictionary containing the signal list data in json format
        """
        requests = [{'type': eetbutil.ExportDataType.SIGNAL_LIST.value, 'args': []}]
        return self.get_eagle_data(requests)


    def get_part_list(self) -> dict:
        """
        Shorthand for the data retrievel utility's generic function
        
        Returns:
            dict: Dictionary containing the part list data from Eagle
        """
        requests = [{'type': eetbutil.ExportDataType.PART_LIST.value, 'args': []}]
        return self.get_eagle_data(requests)
    

    def get_layer_data(self) -> dict:        
        """
        Shorthand for the data retrievel utility's generic function
        
        Returns:
            dict: Dictionary containing the layer data from Eagle
        """
        requests = [{'type': eetbutil.ExportDataType.LAYER_DATA.value, 'args': []}]
        return self.get_eagle_data(requests)


    def get_signal_data(self, signal_list: list[str], use_grid_unit = False) -> dict:        
        """
        Shorthand for the data retrievel utility's generic function
        
        Args:
            signal_list (list[str]): List of signal names to retrieve data for
            
        Returns:
            dict: Dictionary containing the signal data from Eagle
        """
        requests = [{'type': eetbutil.ExportDataType.SIGNAL_DATA.value, 'args': signal_list}]
        return self.get_eagle_data(requests, use_grid_unit)


    def get_part_data(self, part_list: list[str], use_grid_unit = False) -> dict:        
        """
        Shorthand for the data retrievel utility's generic function
        
        Args:
            part_list (list[str]): List of part names to retrieve data for
            
        Returns:
            dict: Dictionary containing the part data from Eagle
        """
        requests = [{'type': eetbutil.ExportDataType.PART_DATA.value, 'args': part_list}]
        return self.get_eagle_data(requests, use_grid_unit)


    def get_geometry_data(self, layer_list: list[int], use_grid_unit = False) -> dict:        
        """
        Shorthand for the data retrievel utility's generic function
        
        Args:
            layer_list (list[int]): List of layer numbers to retrieve data for
            
        Returns:
            dict: Dictionary containing the geometry data from Eagle
        """
        requests = [{'type': eetbutil.ExportDataType.GEOMETRY_DATA.value, 'args': layer_list}]
        return self.get_eagle_data(requests, use_grid_unit)


    def get_eagle_data(self, requests: list[dict], use_grid_unit = False) -> dict:
        """
        Get data from the Electronics workspace using the specified requests.
        
        This method prevents execution during command execution events to avoid
        UI closure issues that would cause crashes.
        
        Args:
            requests (list[dict]): List of data requests to send to Eagle
            
        Returns:
            dict: Dictionary containing the requested Eagle data
        """
        if self._in_command_execute_event:
            self.log_error_to_ui(self._event_error_msg)
            return {}
        else:
            return eetbutil.get_eagle_data(self.json_temp_path, requests, use_grid_unit)


    def run_eagle_command(self, eagleCommand: str) -> str:
        """
        Execute an Eagle command.
        This method prevents execution during command execution events to avoid
        UI closure issues that would cause crashes.
        
        Args:
            eagleCommand (str): The Eagle command to execute
            
        Returns:
            str: The result of executing the Eagle command
        """
        if self._in_command_execute_event:
            self.log_error_to_ui(self._event_error_msg)
            return ''
        else:
            return self.app.executeTextCommand(f"ELECTRON.RUN {eagleCommand}")


    def run_eagle_script(self, script: str) -> str:
        """
        Execute an Eagle script.
        
        This method is just a shorthand for run_eagle_command() to run a script.
        
        Args:
            script (str): The Eagle script to execute
            
        Returns:
            str: The result of executing the Eagle script
        """
        return self.run_eagle_command(f"SCRIPT '{script}'")


    def run_eagle_ulp(self, ulp: str) -> str:
        """
        Execute an Eagle ULP (User Language Program).

        This method is just a shorthand for run_eagle_command() to run a ULP.

        Args:
            ulp (str): The Eagle ULP to execute

        Returns:
            str: The result of executing the Eagle ULP
        """
        return self.run_eagle_command(f"RUN '{ulp}'")


    ####################
    # HELPER FUNCTIONS #
    ####################

    def log_error_to_ui(self, error_message: str = '') -> None:
        """
        Log an error message to the user interface.
        
        Displays an error message box in the UI if debugging is enabled.
        
        Args:
            error_message (str): The error message to display
            
        Returns:
            None
        """
        if (self.ui and config.DEBUG):
            self.ui.messageBox(f'Failed: {error_message}\n{traceback.format_exc()}')


    @classmethod
    def log_to_console(cls, log_string: str, level: adsk.core.LogLevels = adsk.core.LogLevels.InfoLogLevel) -> None: # type: ignore
        """
        Log a message to the Fusion360 console.
        
        Args:
            log_string (str): The string to log
            level (adsk.core.LogLevels): The log level (default: InfoLogLevel)
            
        Returns:
            None
        """
        if (config.DEBUG):
            futil.log(log_string, level, False)


    @classmethod
    def get_error_reason(cls):
        """
        Get the reason for the last error.
            
        Returns:
            str: The formatted traceback of the last error
            None
        """
        return '{}'.format(traceback.format_exc())


    ###################
    # EVENT FUNCTIONS #
    ###################

    def on_command_execute(self, args: adsk.core.CommandEventArgs) -> None:
        """
        Handle the command execute Fusion event.
        
        Args:
            args (adsk.core.CommandEventArgs): Event arguments for the command execute event
            
        Returns:
            None
        """
        CommandBase.log_to_console(f'{self.command_name} Command Execute Event')
        self._in_command_execute_event = True


    def on_execute_preview(self, args: adsk.core.CommandEventArgs) -> None:
        """
        Handle the execute preview Fusion event.
        
        This method does nothing by default but can be overridden in subclasses
        to provide preview functionality.
        
        Args:
            args (adsk.core.CommandEventArgs): Event arguments for the execute preview event
            
        Returns:
            None
        """
        # do nothing, this is here to potentially be overridden in subclasses
        return


    def on_command_created(self, args: adsk.core.CommandCreatedEventArgs) -> None:
        """
        Handle the command created Fusion event.
        
        Initializes the command state, resets execution flags, and sets up event handlers
        for the command's lifecycle events.
        
        Args:
            args (adsk.core.CommandCreatedEventArgs): Event arguments for the command created event
            
        Returns:
            None
        """
        CommandBase.log_to_console(f'{self.command_name} Command Created Event')

        # reset the flag tracking the event
        self._in_command_execute_event = False

        # Store the active project id - do it here, when this command is added to the proper workspace
        self._document_id = self._app.activeDocument.dataFile.id if self._app.activeDocument else 'unknown_project'

        # Connect to the events that are needed by this command.
        self._local_handlers.append(futil.add_handler(args.command.destroy, self.on_command_destroy))
        self._local_handlers.append(futil.add_handler(args.command.execute, self.on_command_execute))
        self._local_handlers.append(futil.add_handler(args.command.executePreview, self.on_execute_preview))


    def on_command_destroy(self, args: adsk.core.CommandEventArgs) -> None:
        """
        Handle the command destroy Fusion event.
        
        Cleans up event handlers when the command is destroyed/terminated.
        
        Args:
            args (adsk.core.CommandEventArgs): Event arguments for the command destroy event
            
        Returns:
            None
        """
        # General logging for debug.
        CommandBase.log_to_console(f'{self.command_name} Command Destroy Event')
        self._local_handlers = []
        
        # Clean up the temp json file if it exists
        if os.path.exists(self.json_temp_path):
            try:
                os.remove(self.json_temp_path)
            except Exception as e:
                CommandBase.log_to_console(f"Failed to delete temp file {self.json_temp_path}: {e}")


    ##############
    # PROPERTIES #
    ##############

    @property
    def app(self) -> adsk.core.Application:
        return self._app

    @property
    def ui(self) -> adsk.core.UserInterface:
        return self._ui
    
    @property 
    def document_id(self) -> str:
        return self._document_id
    
    @property
    def local_handlers(self) -> list:
        return self._local_handlers
    
    @local_handlers.setter
    def local_handlers(self, handler_list: list) -> None:
        self._local_handlers = handler_list

    @property
    def command_id(self) -> str:
        return self._command_id
    
    @command_id.setter
    def command_id(self, _command_id: str) -> None:
        self._command_id = _command_id

    @property
    def command_name(self) -> str:
        return self._command_name
    
    @command_name.setter
    def command_name(self, _command_name: str) -> None:
        self._command_name = _command_name

    @property
    def command_description(self) -> str:
        return self._command_description
    
    @command_description.setter
    def command_description(self, _command_description: str) -> None:
        self._command_description = _command_description

    @property
    def icon_folder(self) -> str:
        return self._icon_folder
    
    @icon_folder.setter
    def icon_folder(self, _icon_folder: str) -> None:
        self._icon_folder = _icon_folder

    @property
    def json_temp_path(self) -> str:
        return self._json_temp_path
    
    @json_temp_path.setter
    def json_temp_path(self, _json_temp_path: str) -> None:
        self._json_temp_path = _json_temp_path
