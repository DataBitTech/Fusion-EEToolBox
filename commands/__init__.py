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

# If you want to add an additional command, duplicate one of the existing directories and import it here.
from .CommandBase import CommandBase
from .PaletteCommandBase import PaletteCommandBase
from .Eetb_ExecuteEagleScriptCommand.Eetb_ExecuteEagleScriptCommand import Eetb_ExecuteEagleScriptCommand
from .Eetb_LengthAndDelayMeasureCommand.Eetb_LengthAndDelayMeasureCommand import Eetb_LengthAndDelayMeasureCommand
from .Eetb_SwapSignalsCommand.Eetb_SwapSignalsCommand import Eetb_SwapSignalsCommand
from .Eetb_SwapComponentsCommand.Eetb_SwapComponentsCommand import Eetb_SwapComponentsCommand
from .Eetb_FixLineConnectionsCommand.Eetb_FixLineConnectionsCommand import Eetb_FixLineConnectionsCommand
from .Eetb_ExportCPLDataCommand.Eetb_ExportCPLDataCommand import Eetb_ExportCPLDataCommand
from .Eetb_ExportBOMCommand.Eetb_ExportBOMCommand import Eetb_ExportBOMCommand
from .Eetb_EditUserScriptCommand.Eetb_EditUserScriptCommand import Eetb_EditUserScriptCommand
from .Eetb_AlignPackageFaceToXYPlaneCommand.Eetb_AlignPackageFaceToXYPlaneCommand import Eetb_AlignPackageFaceToXYPlaneCommand
from .Eetb_AlignPackageXYToMidpointCommand.Eetb_AlignPackageXYToMidpointCommand import Eetb_AlignPackageXYToMidpointCommand
from .Eetb_AlignPackageXYSymmetricalCommand.Eetb_AlignPackageXYSymmetricalCommand import Eetb_AlignPackageXYSymmetricalCommand
from .Eetb_ToDoListCommand.Eetb_ToDoListCommand import Eetb_ToDoListCommand
from .Eetb_UIStructureWriterCommand.Eetb_UIStructureWriterCommand import Eetb_UIStructureWriterCommand
from .Eetb_AppInfoCommand.Eetb_AppInfoCommand import Eetb_AppInfoCommand
from .Eetb_DefineUserScriptAndULPButtonCommand.Eetb_DefineUserScriptAndULPButtonCommand import Eetb_DefineUserScriptAndULPButtonCommand
from .Eetb_ViaFenceCommand.Eetb_ViaFenceCommand import Eetb_ViaFenceCommand
from .Eetb_ChecklistCommand.Eetb_ChecklistCommand import Eetb_ChecklistCommand
from .Eetb_AttributeRenameDeleteCommand.Eetb_AttributeRenameDeleteCommand import Eetb_AttributeRenameDeleteCommand
from .Eetb_AttributeAddCopyCommand.Eetb_AttributeAddCopyCommand import Eetb_AttributeAddCopyCommand


# these commands are also input to other command constructors
script_execute_command = Eetb_ExecuteEagleScriptCommand()
edit_user_script_command = Eetb_EditUserScriptCommand()

# Fusion will automatically call the start() and stop() functions.
commands: list[CommandBase]  = [
    script_execute_command,
    edit_user_script_command,
    Eetb_DefineUserScriptAndULPButtonCommand(),
    Eetb_LengthAndDelayMeasureCommand(),
    Eetb_SwapSignalsCommand(),
    Eetb_SwapComponentsCommand(),
    Eetb_ExportCPLDataCommand(edit_user_script_command),
    Eetb_ExportBOMCommand(edit_user_script_command),
    Eetb_AlignPackageFaceToXYPlaneCommand(),
    Eetb_AlignPackageXYToMidpointCommand(),
    Eetb_FixLineConnectionsCommand(script_execute_command),
    Eetb_AlignPackageXYSymmetricalCommand(),
    Eetb_ViaFenceCommand(),
    Eetb_ToDoListCommand(),
    Eetb_ChecklistCommand(),
    Eetb_UIStructureWriterCommand(),
    Eetb_AttributeAddCopyCommand(False),
    Eetb_AttributeRenameDeleteCommand(script_execute_command, False),
    Eetb_AttributeRenameDeleteCommand(script_execute_command, True),
    Eetb_AttributeAddCopyCommand(True),
    Eetb_AppInfoCommand() # make this the last entry so that its icon is the last one in the toolbar(s)
]

# The start function will be run when the add-in is started.
def start():
    for command in commands:
        command.start()


# The stop function will be run when the add-in is stopped.
def stop():
    for command in commands:
        command.stop()


def on_command_starting(commandId: str):
    try:        
        for command in commands:
            if commandId == command.command_id:
                continue

            if isinstance(command, PaletteCommandBase):
                command.on_command_starting(commandId)

    except Exception as e:
        app = adsk.core.Application.get()
        ui = app.userInterface
        if ui:
            ui.messageBox(f'Error closing palette: {str(e)}')