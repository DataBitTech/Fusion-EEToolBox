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


import os
import adsk.core
import adsk.fusion
import traceback


from ..CommandBase import CommandBase
from ...lib import fusionAddInUtils as futil
from ...lib import eetbUtils as eetbutil
from ... import controls as eetbControls
from ... import config


class Eetb_AlignPackageXYSymmetricalCommand(CommandBase):

    def __init__(self):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_align_packageXY_symmetrical_command_id',
            command_name = 'Align symmetrically',
            command_description = 'Align package symmetrically to footprint geometries (XY plane only)',
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources'),
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}__UNUSED__.json'))
        super().__init__(command_attributes)

        self._package_geometry_selection_input: adsk.core.SelectionCommandInput
        self._sketch_geo_selection_input: adsk.core.SelectionCommandInput

    
    def add_command_button_to_ui(self, commandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        eetbControls.add_command_to_panel(config.FUSION_PACKAGE_ENV_ID, eetbControls.PackagePanel.PACKAGE_PANEL, commandDefinition)
 

    def _create_UI(self, command: adsk.core.Command):
        """Creates the user interface for the command.

        This method is responsible for setting up the command's user interface,
        including creating input controls for selecting package geometry and sketch
        geometry, and adding them to the command's input panel.

        Args:
            command (adsk.core.Command): The command object to create the UI for.
        """
        inputs = command.commandInputs
        # Create selection inputs
        self._package_geometry_selection_input = inputs.addSelectionInput(
            'package_geometry_selection',
            'Package geometries',
            'Select symmetrical features on the package body'
        )
        self._package_geometry_selection_input.addSelectionFilter('Faces')
        self._package_geometry_selection_input.addSelectionFilter('Edges')
        self._package_geometry_selection_input.addSelectionFilter('Vertices')
        self._package_geometry_selection_input.setSelectionLimits(2, 2)

        self._sketch_geo_selection_input = inputs.addSelectionInput(
            'sketch_geo_selection',
            'Footprint geometries',
            'Select symmetrical lines or points on the footprint sketch'
        )
        self._sketch_geo_selection_input.addSelectionFilter('SketchLines')
        self._sketch_geo_selection_input.addSelectionFilter('SketchPoints')
        self._sketch_geo_selection_input.addSelectionFilter('ConstructionLines')
        self._sketch_geo_selection_input.addSelectionFilter('ConstructionPoints')

        self._sketch_geo_selection_input.setSelectionLimits(2, 2)


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
            
            self._create_UI(cmd)

            # Set command properties
            cmd.isRepeatable = False
            cmd.isExecutedWhenPreEmpted = False
            
        except Exception as e:
            adsk.core.Application.get().userInterface.messageBox(
                f"Error creating command: {str(e)}\n{traceback.format_exc()}"
            )
            

    def on_execute_preview(self, args: adsk.core.CommandEventArgs):
        """
        Event handler for when the command is previewed.

        See the base class method for full details.

        Args:
            args: CommandEventArgs containing the command execution context
        """
        # Validate selections
        if self._package_geometry_selection_input.selectionCount < 2:
            self.log_error_to_ui("Please select two symmetrical features")
            return
        
        if self._sketch_geo_selection_input.selectionCount < 2:
            self.log_error_to_ui("Please select two symmetrical lines or points on the footprint sketch")
            return
        
        # Get selected face
        package_ref: list[adsk.core.Point2D] = []
        body: adsk.fusion.BRepBody = None # type: ignore
        for i in range(2):
            package_item = self._package_geometry_selection_input.selection(i).entity
            if isinstance(package_item, adsk.fusion.BRepFace):
                centroid = package_item.centroid
                package_ref.append(adsk.core.Point2D.create(centroid.x, centroid.y))
                body = package_item.body
            elif isinstance(package_item, adsk.fusion.BRepEdge):
                (returnValue, point1, point2) = package_item.geometry.evaluator.getEndPoints()
                package_ref.append(adsk.core.Point2D.create((point1.x + point2.x) / 2, (point1.y + point2.y) / 2))
                body = package_item.body
            elif isinstance(package_item, adsk.fusion.BRepVertex):
                vertex = package_item.geometry
                package_ref.append(adsk.core.Point2D.create(vertex.x, vertex.y))
                body = package_item.body

        footprint_ref: list[adsk.core.Point2D] = []
        for i in range(2):
            footprint_item = self._sketch_geo_selection_input.selection(i).entity
            if isinstance(footprint_item, adsk.fusion.SketchLine):
                line = footprint_item.geometry
                footprint_ref.append(adsk.core.Point2D.create((line.startPoint.x + line.endPoint.x) / 2, (line.startPoint.y + line.endPoint.y) / 2))
            elif isinstance(footprint_item, adsk.fusion.SketchPoint):
                point = footprint_item.geometry
                footprint_ref.append(adsk.core.Point2D.create(point.x, point.y))
        
        
        # Create the transformation matrix
        align_transform = self._create_alignment_transform(package_ref, footprint_ref)

        # Get the body and component to move
        design = adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
        if not design:
            self.log_error_to_ui("No active design found.")
            return
        root = design.rootComponent

        # The body should already be saved
        if not body:
            raise TypeError('The parent body of the selected features could not be found')
        component = body.parentComponent
        transform_object = component if component and component.id != root.id else body
        
        try:
            # Apply the transformation
            if isinstance(transform_object, adsk.fusion.Component):
                # Find the inserted occurrence (e.g. by name)
                insertedOcc = None
                for occ in root.occurrences:
                    if occ.component.id == transform_object.id:
                        insertedOcc = occ
                        break
                    # STL imports are wrapped around with an additional component
                    if occ.component.occurrences.count:
                        for subocc in occ.component.occurrences:
                            if subocc.component.id == transform_object.id:
                                insertedOcc = occ
                                break
                if insertedOcc:
                    current_transform = insertedOcc.transform2
                    current_transform.transformBy(align_transform)
                    insertedOcc.transform2 = current_transform
            else:
                bodies = adsk.core.ObjectCollection.create()
                bodies.add(transform_object)
                moveFeats = root.features.moveFeatures
                moveInput = moveFeats.createInput(bodies, align_transform)
                moveFeats.add(moveInput)

            # Tell Fusion that this is the final result, no need to call the execute handler
            args.isValidResult = True
            
        except Exception as e:
            self.log_error_to_ui(f"Failed to apply transformation: {str(e)}")


    def _create_alignment_transform(self, package_ref: list[adsk.core.Point2D], footprint_ref: list[adsk.core.Point2D]) -> adsk.core.Matrix3D:
        """Creates a 3D transformation matrix to align package geometry with footprint geometry.

        This function calculates the necessary translation and rotation to align two
        symmetrical reference points from the package and the footprint sketch.
        The transformation is computed in the XY plane only.

        Args:
            package_ref (list[adsk.core.Point2D]): List of two reference points on the package geometry.
            footprint_ref (list[adsk.core.Point2D]): List of two reference points on the footprint sketch.

        Returns:
            adsk.core.Matrix3D: A 3D transformation matrix that can be applied to align the package with the footprint.
        """
        # Step 1. Move the first point of the package to the first footprint point
        displacement = adsk.core.Vector3D.create(footprint_ref[0].x - package_ref[0].x, footprint_ref[0].y - package_ref[0].y)

        # Step 2. - Compute where the second point of the package would end up
        moving_point = adsk.core.Vector2D.create(package_ref[1].x + displacement.x, package_ref[1].y + displacement.y)

        # Step 3 - update the translation with half the distance between the second point of the package and the footprint second point
        displacement.x += (footprint_ref[1].x - moving_point.x) / 2
        displacement.y += (footprint_ref[1].y - moving_point.y) / 2

        # Create a matrix for rotation around the calculated axis through the face center
        transform_matrix = adsk.core.Matrix3D.create()
        
        # Create translation vector (only X and Y)
        translation = transform_matrix.translation
        translation.add(adsk.core.Vector3D.create(displacement.x, displacement.y, 0))
        transform_matrix.translation = translation

        return transform_matrix
