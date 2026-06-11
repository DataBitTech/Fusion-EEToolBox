# This file is exempt from the general license as most of the code was downloaded from 
# https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-d2b85a7e-fd08-11e4-9e07-3417ebd3d5be

# Copyright (c) Autodesk Inc.


import adsk.core
import traceback
import os

from ... import config, controls
from ..CommandBase import CommandBase
from ...lib import fusionAddInUtils as futil
from ...lib import eetbUtils as eetbutil

class Eetb_UIStructureWriterCommand(CommandBase):
    
    def __init__(self):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_UI_structure_writer_command_id',
            command_name = 'Write the UI structure to a file',
            command_description = 'Helper command for development',
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources'),
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}_extracted_data.json'))
        super().__init__(command_attributes)


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        if config.DEVELOPER_MODE:
            controls.add_command_to_panel(config.ELECTRON_SCHEMATIC_ENV_ID, controls.SchematicPanel.COMMON_PANEL, commandDefinition)


    def on_command_execute(self, args: adsk.core.CommandEventArgs):
        """
        Event handler for when the command is executed.

        See the base class method for full details.
        
        Args:
            args: CommandEventArgs
        """
        super().on_command_execute(args)
        self.run(None)


    def on_command_created(self, args: adsk.core.CommandCreatedEventArgs):
        """
        Event handler for when the command is created.

        See the base class method for full details.
        
        Args:
            args: CommandCreatedEventArgs
        """
        super().on_command_created(args)
        try:
            cmd = args.command
            inputs = cmd.commandInputs
            
            # Set command properties
            cmd.isRepeatable = False
            cmd.isExecutedWhenPreEmpted = False
        except Exception as e:
            self.log_error_to_ui(f"Error creating command: {self.get_error_reason()}")


    def _create_UI(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs):
        """Creates the UI elements for the command.

        Args:
            command: The command object.
            inputs: The command inputs object.
        """
        inputs.addStringValueInput('dummy_id', 'Display Name')
        self._commandLineInput = inputs.addStringValueInput('command_line_input_id', 'Command line')
        self._synchronousCallInput = inputs.addBoolValueInput('synchronous_call_id', 'Wait until finished', True, "", True)
        explanation_text = "Click OK to write the UI structure to an XML"
        inputs.addTextBoxCommandInput('explanation_id', '', explanation_text, 10, True)


    def run(self, context):
        """Writes the UI structure to an XML file for development purposes."""
        try:
            fileDialog = self.ui.createFileDialog()
            fileDialog.isMultiSelectEnabled = False
            fileDialog.title = "Specify result filename"
            fileDialog.filter = 'XML files (*.xml)'
            fileDialog.filterIndex = 0
            dialogResult = fileDialog.showSave()
            if dialogResult == adsk.core.DialogResults.DialogOK:
                filename = fileDialog.filename
            else:
                return

            result = '<UserInterface>\n'
            result += f'{self.TabSpace(1)}<Workspaces count="{self.ui.workspaces.count}">\n'
            for wsIndex in range(self.ui.workspaces.count):
                try:
                    ws: adsk.core.Workspace = self.ui.workspaces.item(wsIndex)
                except:
                    ws = None # type: ignore

                if ws:
                    result += f'{self.TabSpace(2)}<Workspace name="{ws.name}" id="{ws.id}">\n'
                    try:
                        tabs = ws.toolbarTabs
                    except:
                        tabs = None

                    if tabs:
                        result += f'{self.TabSpace(3)}<ToolbarTabs count="{tabs.count}">\n'
                        for tab in tabs:
                            result += f'{self.TabSpace(4)}<ToolbarTab name="{tab.name}" id="{tab.id}">\n'

                            result += self.GetPanelsXML(tab.toolbarPanels, 5)

                            result += f'{self.TabSpace(4)}</ToolbarTab>\n'

                        result += f'{self.TabSpace(3)}</ToolbarTabs>\n'
                    else:
                        result += f'{self.TabSpace(3)}<ToolbarTabs error="Failed to get toolbar tabs.">\n'
                        result += f'{self.TabSpace(3)}</ToolbarTabs>\n'

                    result += f'{self.TabSpace(2)}</Workspace>\n'

            result += f'{self.TabSpace(1)}</Workspaces>\n'

            result += f'{self.TabSpace(1)}<Toolbars count="{self.ui.toolbars.count}">\n'
            toolbar: adsk.core.Toolbar
            for toolbar in self.ui.toolbars:
                result += f'{self.TabSpace(2)}<Toolbar id="{toolbar.id}">\n'
                result += f'{self.TabSpace(3)}<ToolbarControls count="{toolbar.controls.count}">\n'
                result += self.GetControls(toolbar.controls, 1, False)
                result += f'{self.TabSpace(3)}</ToolbarControls>\n'
                result += f'{self.TabSpace(2)}</Toolbar>\n'            
            result += f'{self.TabSpace(1)}</Toolbars>\n'

            result += f'{self.TabSpace(1)}<CommandDefinitions count="{self.ui.commandDefinitions.count}">\n'
            for command in self.ui.commandDefinitions:
                result += f'{self.TabSpace(2)}<Command id="{command.id}">\n'
                result += f'{self.TabSpace(3)}<CommandName="{command.name}">\n'
                result += f'{self.TabSpace(3)}</CommandName>\n'
                result += f'{self.TabSpace(2)}</Command>\n'  
            result += f'{self.TabSpace(1)}</CommandDefinitions>\n'

            result += '</UserInterface>'

            f = open(filename, 'w', -1, 'utf-8-sig')
            f.write(result)
            f.close()
            self.ui.messageBox(f'Finished writing to:\n{filename}')
        except:
            if self.ui:
                self.ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


    def GetPanelsXML(self, panels: adsk.core.ToolbarPanels, tabs: int) -> str:
        """Generates XML representation of toolbar panels and their controls.

        Args:
            panels: The ToolbarPanels collection to process.
            tabs: The indentation level for the XML output.

        Returns:
            A string containing the XML representation of the panels and controls.
        """
        result = f'{self.TabSpace(tabs)}<ToolbarPanels count="{panels.count}">\n'
        for panelIndex in range(panels.count):
            try:
                panel: adsk.core.ToolbarPanel = panels.item(panelIndex)
            except:
                panel = None # type: ignore

            if panel:
                result += f'{self.TabSpace(tabs + 1)}<ToolbarPanel name="{panel.name}" id="{panel.id}">\n'
                result += f'{self.TabSpace(tabs + 2)}<ToolbarControls count="{panel.controls.count}">\n'
                result += self.GetControls(panel.controls, tabs, True)
                result += f'{self.TabSpace(tabs + 2)}</ToolbarControls>\n'
                result += f'{self.TabSpace(tabs + 1)}</ToolbarPanel>\n'

        result += f'{self.TabSpace(tabs + 1)}</ToolbarPanels>\n'
        return result


    def GetControls(self, controls: adsk.core.ToolbarControls, tabs: int, isPanel: bool) -> str:
        """Generates XML representation of toolbar controls.

        Args:
            controls: The ToolbarControls collection to process.
            tabs: The indentation level for the XML output.
            isPanel: Indicates if the controls belong to a panel.

        Returns:
            A string containing the XML representation of the controls.
        """
        result = ''
        for control in controls:
            if control.objectType == adsk.core.DropDownControl.classType():
                dropControl: adsk.core.DropDownControl = control # type: ignore

                if isPanel:
                    try:
                        dropName = dropControl.name
                    except:
                        dropName = "**** Error getting name."

                    result += f'{self.TabSpace(tabs + 3)}<DropDownControl name="{dropName}" id="{dropControl.id}" count="{dropControl.controls.count}">\n'
                else:
                    result += f'{self.TabSpace(tabs + 3)}<DropDownControl id="{dropControl.id}" count="{dropControl.controls.count}">\n'

                result += self.GetControls(dropControl.controls, tabs + 1, isPanel)
                result += f'{self.TabSpace(tabs + 3)}</DropDownControl>\n'
            elif control.objectType == adsk.core.SplitButtonControl.classType():
                splitControl: adsk.core.SplitButtonControl = control # type: ignore
                result += f'{self.TabSpace(tabs + 3)}<SplitButtonControl>\n'

                try:
                    defaultCmdDef = splitControl.defaultCommandDefinition
                except:
                    defaultCmdDef = None
                
                if defaultCmdDef:
                    result += f'{self.TabSpace(tabs + 4)}<defaultCommandDefinition name="{defaultCmdDef.name}" id="{defaultCmdDef.id}"/>\n'

                    additionalDefs = splitControl.additionalDefinitions
                    result += f'{self.TabSpace(tabs + 4)}<additionalDefinitions count="{len(additionalDefs)}">\n'
                    for additionalDef in additionalDefs:
                        result += f'{self.TabSpace(tabs + 5)}<{self.ObjectName(additionalDef)} name="{additionalDef.name}" id="{additionalDef.id}"/>\n'
                    result += f'{self.TabSpace(tabs + 4)}</additionalDefinitions>\n'
                else:
                    result += f'{self.TabSpace(tabs + 4)}<defaultCommandDefinition error="**** Failed to get CommandDefinition"/>\n'

                result += f'{self.TabSpace(tabs + 3)}</SplitButtonControl>\n'

            else:
                if control.objectType == adsk.core.SeparatorControl.classType():
                    result += f'{self.TabSpace(tabs + 3)}<SeparatorControl id="{control.id}" />\n'
                else:
                    cmdDef: adsk.core.CommandDefinition = None # type: ignore
                    try:                 
                        cmdDef = control.commandDefinition # type: ignore
                    except:
                        cmdDef = None # type: ignore

                    if cmdDef:
                        try:
                            commandType = self.ObjectName(cmdDef.controlDefinition)
                        except:
                            commandType = '**** Failed to get associated control.'

                        isPromotedOK = True
                        try:
                            isPromoted = control.isPromoted # type: ignore
                        except:
                            isPromotedOK = False


                        if isPanel and isPromotedOK:
                            result += f'{self.TabSpace(tabs + 3)}<{self.ObjectName(control)} name="{cmdDef.name}" id="{cmdDef.id}" commandType="{commandType}" isPromoted="{isPromoted}" />\n' # type: ignore
                        else:
                            result += f'{self.TabSpace(tabs + 3)}<{self.ObjectName(control)} name="{cmdDef.name}" id="{cmdDef.id}" commandType="{commandType}" />\n'
                    else:
                        result += f'{self.TabSpace(tabs + 3)}<{self.ObjectName(control)} error="**** Failed to get CommandDefinition for {control.id}" />\n'

        return result


    def TabSpace(self, tabs: int) -> str:
        """Returns a string of spaces representing the specified number of tabs.

        Args:
            tabs: The number of tabs (indentation levels) to represent.

        Returns:
            A string containing the appropriate number of spaces for indentation.
        """
        spacesPerTab = 4
        return ' ' * (spacesPerTab * tabs)


    def ObjectName(self, object: adsk.core.Base) -> str:
        """Extracts and returns the simple class name from a Fusion360 object.

        Args:
            object: The Fusion360 object to extract the name from.

        Returns:
            A string containing the simple class name of the object.
        """
        parts = object.objectType.split('::')
        return parts[len(parts)-1]
