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
import math

from ..CommandBase import CommandBase
from ...lib import fusionAddInUtils as futil
from ...lib import eetbUtils as eetbutil
from ... import controls as eetbControls
from ... import config


class Eetb_AlignPackageFaceToXYPlaneCommand(CommandBase):

    def __init__(self):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_align_package_to_XY_plane_command_id',
            command_name = 'Select the PCB plane on the package',
            command_description = 'Align the 3D package to the PCB plane by selecting the package face that rests on the PCB',
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources'),
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}__UNUSED__.json'))
        super().__init__(command_attributes)

        # UI input elements
        self._face_selection_input: adsk.core.SelectionCommandInput
        self._flip_input: adsk.core.BoolValueCommandInput


    def add_command_button_to_ui(self, commandDefinition: adsk.core.CommandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        eetbControls.add_command_to_panel(config.FUSION_PACKAGE_ENV_ID, eetbControls.PackagePanel.PACKAGE_PANEL, commandDefinition)


    def _create_UI(self, command: adsk.core.Command):
        """
        Create the face selection input for the command.
        This should be called when setting up the command UI.
        
        Args:
            command: The Command object
        """
        # Create a selection input for faces
        self._face_selection_input = command.commandInputs.addSelectionInput(
            'face_selection',
            'Package face',
            'Select a face to align to the PCB plane'
        )
        self._face_selection_input.addSelectionFilter('PlanarFaces')
        self._face_selection_input.setSelectionLimits(1, 1)

        self._flip_input = command.commandInputs.addBoolValueInput('flip_checkbox', 'Flip', True)


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
            
            # Create face selection input
            self._create_UI(cmd)

            # Set command properties
            cmd.isRepeatable = False
            cmd.isExecutedWhenPreEmpted = False
            
        except Exception as e:
            self.log_error_to_ui(f"Error creating command: {self.get_error_reason()}")


    def on_execute_preview(self, args: adsk.core.CommandEventArgs):
        """
        Event handler for when the command is previewed.

        See the base class method for full details.

        Args:
            args: CommandEventArgs containing the command execution context
        """
        # Get the selected face
        if self._face_selection_input.selectionCount < 1:
            self.log_error_to_ui("Please select a face.")
            return
        
        selected_item = self._face_selection_input.selection(0)
        selected_face = adsk.fusion.BRepFace.cast(selected_item.entity)
        
        if not selected_face:
            self.log_error_to_ui("Invalid selection. Please select a face.")
            return
        
        design = adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
        if not design:
            self.log_error_to_ui("No active design found.")
            return
        root = design.rootComponent

        # Get the body and component
        body = selected_face.body
        component = body.parentComponent

        # Determine which object to transform
        transform_object = component if component and component.id != root.id else body
        
        # Get the face normal and geometry
        face_center = selected_face.centroid
        (result, face_normal) = selected_face.evaluator.getNormalAtPoint(face_center)
    
        if not result:
            return

        # Create the transformation matrix
        align_transform = self._create_alignment_transform(face_normal, face_center, self._flip_input.value)

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
            self.log_error_to_ui(f"Error creating command: {self.get_error_reason()}")


    def _create_alignment_transform(self, face_normal: adsk.core.Vector3D, face_center: adsk.core.Point3D, flip: bool) -> adsk.core.Matrix3D:
        """
        Create a transformation matrix that:
        1. Orients the face normal to point in -Z direction
        2. Positions the face center at the origin
        Args:
            face_normal: The normal vector of the selected face
            face_center: The centroid of the selected face
            flip: If True, flip the orientation of the face normal

        Returns:
            adsk.core.Matrix3D: The transformation matrix to align the face
        """
        
        # Target direction: -Z axis
        target_normal = adsk.core.Vector3D.create(0, 0, -1)
        
        # Calculate rotation needed
        rotation_axis = face_normal.crossProduct(target_normal)
        
        # Check if vectors are parallel
        if rotation_axis.length < 1e-10:
            # Vectors are parallel or anti-parallel
            if face_normal.z < 0:
                # Already pointing in -Z direction, no rotation needed
                rotation_angle = 0
                rotation_axis = adsk.core.Vector3D.create(1, 0, 0)
            else:
                # Pointing in +Z direction, rotate 180 degrees around X-axis
                rotation_angle = 3.141592653589793  # pi
                rotation_axis = adsk.core.Vector3D.create(1, 0, 0)
        else:
            rotation_axis.normalize()
            # Calculate rotation angle using dot product
            dot_product = face_normal.dotProduct(target_normal)
            # Clamp to [-1, 1] to avoid numerical errors with acos
            dot_product = max(-1, min(1, dot_product))
            rotation_angle = math.acos(dot_product)
        
        # Create a matrix for rotation around the calculated axis through the face center
        transform_matrix = adsk.core.Matrix3D.create()
        
        # Set the origin to the face center for rotation
        transform_matrix.setWithCoordinateSystem(
            face_center,
            adsk.core.Vector3D.create(1, 0, 0),
            adsk.core.Vector3D.create(0, 1, 0),
            adsk.core.Vector3D.create(0, 0, 1)
        )
        
        # Apply rotation
        if rotation_axis.length > 1e-10:
            transform_matrix.setToRotation(rotation_angle, rotation_axis, face_center)

        # Apply an additional 180 degree rotation around the X-axis if flip is true
        if flip:
            x_rotation = adsk.core.Matrix3D.create()
            x_rotation.setToRotation(math.pi, adsk.core.Vector3D.create(1, 0, 0), face_center)
            transform_matrix.transformBy(x_rotation)
        
        # Apply translation to move face center to origin
        current_translation = transform_matrix.translation
        current_translation.add(adsk.core.Vector3D.create(
            -face_center.x,
            -face_center.y,
            -face_center.z
        ))
        transform_matrix.translation = current_translation
        
        return transform_matrix
