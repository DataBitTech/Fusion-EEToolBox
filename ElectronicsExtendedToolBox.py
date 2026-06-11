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
from . import commands
from . import controls
from .lib import fusionAddInUtils as futil
from .lib import eetbUtils

events = []

class CommandStartingHandler(adsk.core.ApplicationCommandEventHandler):
    """Event handler for application command starting events.

    This handler notifies commands about command starting events, in order
    for some palettes to be able to close automatically. It also ckecks if
    the last started command was editing the program preferences, and if
    so, it updates the used theme if necessary.
    """
    def __init__(self):
        super().__init__()
        self.lastCommandId = ''

    def notify(self, eventArgs) -> None:
        """Handles application command starting events.

        This method is called when a command is about to start. It handles
        updating the JavaScript include files when the preferences command
        was the last command, and notifies commands about the command 
        starting event.

        Args:
            args: The event arguments containing command information.

        Returns:
            None
        """
        app = adsk.core.Application.get()
        ui = app.userInterface
        try:
            # the preferences command terminates immediately, so handle it possibly
            # having changed at the start of the next command
            if self.lastCommandId == 'PreferencesCommand':
                eetbUtils.generate_js_include()
            commands.on_command_starting(eventArgs.commandId)
            self.lastCommandId = eventArgs.commandId
        except Exception as e:
            ui.messageBox(f'Error closing palette: {str(e)}')


def run(context) -> None:
    """Entry point function to start the Electronics Extended Toolbox add-in.

    Initializes the add-in by starting controls and commands, setting up event handlers,
    and generating JavaScript include files.

    Args:
        context: The add-in context provided by Fusion.

    Returns:
        None
    """
    try:
        controls.start()
        commands.start()

        onCommandStarting = CommandStartingHandler()

        app = adsk.core.Application.get()
        app.userInterface.commandStarting.add(onCommandStarting)
        # Store the event handle
        events.append(onCommandStarting)

        eetbUtils.generate_js_include()

    except Exception:
        futil.handle_error('run')


def stop(context) -> None:
    """Entry point function to stop the Electronics Extended Toolbox add-in.

    Cleans up by removing all event handlers, stopping commands and controls,
    and clearing the events list.

    Args:
        context: The add-in context provided by Fusion.

    Returns:
        None
    """
    try:
        # Remove all of the event handlers your app has created
        futil.clear_handlers()

        # This will run the start function in each of your commands as defined in commands/__init__.py
        commands.stop()
        controls.stop()

        events = []

    except Exception:
        futil.handle_error('stop')