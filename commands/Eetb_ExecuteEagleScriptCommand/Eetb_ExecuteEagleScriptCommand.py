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
import os

from ... import config
from ..CommandBase import CommandBase

class Eetb_ExecuteEagleScriptCommand(CommandBase):

    def __init__(self):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_execute_script_command_id',
            command_name = 'Execute Script',
            command_description = 'Execute an Eagle script in Fusion 360',
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources'),
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'))
        super().__init__(command_attributes)
        self._script_path: list[str] = []


    def run_script(self, script_path: str):
        """
        Executes an Eagle script within Fusion 360 environment.

        This method takes the path to an Eagle script file and saves it.
        It then invokes itself as a Fusion command and executes the script
        in the CommandCreated event, so that Fusion does not crash.
        This mechanism can be used by any command to run scripts even at
        forbidden places by 'outsourcing' the running of the script to
        this command that has the possibility to run it from the proper
        event handler 

        Args:
            script_path (str): The absolute path to the Eagle script file
                              that needs to be executed.
        """
        command_definition: adsk.core.CommandDefinition = self.ui.commandDefinitions.itemById(self.command_id)
        if command_definition:
            self._script_path.append(script_path)
            command_definition.execute()


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """No visible button for this command.
        
        See the base class method for full details.
        """
        pass


    def on_command_created(self, args: adsk.core.CommandCreatedEventArgs):
        """
        Event handler for when the command is created.

        See the base class method for full details.
        
        Args:
            args: CommandCreatedEventArgs
        """
        super().on_command_created(args)

        for script in self._script_path:
            if script != '' and os.path.exists(script):
                self.log_to_console(f"Running Eagle script {script}")
                self.run_eagle_script(script)
        self._script_path = []
