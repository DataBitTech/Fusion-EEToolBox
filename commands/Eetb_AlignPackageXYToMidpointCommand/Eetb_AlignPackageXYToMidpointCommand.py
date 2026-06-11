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


class Eetb_AlignPackageXYToMidpointCommand(CommandBase):

    def __init__(self):
        command_attributes = CommandBase.MandatoryCommandAttributes(
            command_id = f'{config.ADDIN_NAME}_align_packageXY_to_midpoint_command_id',
            command_name = 'Align package sideways',
            command_description = 'Align package to footprint geometry (XY plane only)',
            icon_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources'),
            json_temp_path = os.path.join(config.TEMP_DIR, f'fusion360_{__class__.__qualname__}__UNUSED__.json'))
        super().__init__(command_attributes)

        self._face_selection_input: adsk.core.SelectionCommandInput
        self._sketch_geo_selection_input: adsk.core.SelectionCommandInput
        self._rotation_input: adsk.core.AngleValueCommandInput

    
    def add_command_button_to_ui(self, commandDefinition):
        """Adds the command button to the UI.
        
        See the base class method for full details.
        """
        eetbControls.add_command_to_panel(config.FUSION_PACKAGE_ENV_ID, eetbControls.PackagePanel.PACKAGE_PANEL, commandDefinition)
 

    def _create_UI(self, command: adsk.core.Command):
        """Creates the user interface for the command.

        This method sets up the input controls for selecting a face, sketch geometry,
        and rotation angle, and adds them to the command's UI.

        Args:
            command (adsk.core.Command): The command object to which the UI elements are added.
        """
        inputs = command.commandInputs
        # Create selection inputs
        self._face_selection_input = inputs.addSelectionInput(
            'face_selection',
            'Package face',
            'Select a planar face on the package body'
        )
        self._face_selection_input.addSelectionFilter('Faces')
        self._face_selection_input.setSelectionLimits(1, 1)
        
        self._sketch_geo_selection_input = inputs.addSelectionInput(
            'sketch_geo_selection',
            'Footprint geometry',
            'Select a circle, line, or point from the footprint sketch'
        )
        self._sketch_geo_selection_input.addSelectionFilter('SketchCurves')
        self._sketch_geo_selection_input.addSelectionFilter('SketchPoints')
        self._sketch_geo_selection_input.addSelectionFilter('ConstructionPoints')
        self._sketch_geo_selection_input.addSelectionFilter('ConstructionLines')
        self._sketch_geo_selection_input.setSelectionLimits(1, 1)
        
        # Rotation input around Z axis
        self._rotation_input = inputs.addAngleValueCommandInput(
            'rotation_angle',
            'Rotation around Z axis',
            adsk.core.ValueInput.createByReal(0.0)
        )
        self._rotation_input.tooltip = 'Rotation around the Z axis'
        self._rotation_input.tooltipDescription = 'The centroid of the selected geometry on the package will first be aligned to the \
            center of the selected footprint geometry. Then, the package will be rotated around an Z-axis through this common point'


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
        if self._face_selection_input.selectionCount < 1:
            self.log_error_to_ui("Please select a planar face.")
            return
        
        if self._sketch_geo_selection_input.selectionCount < 1:
            self.log_error_to_ui("Please select a circle, line, or point from a sketch.")
            return
        
        # Get selected face
        selected_face_item = self._face_selection_input.selection(0)
        selected_face = adsk.fusion.BRepFace.cast(selected_face_item.entity)
        
        if not selected_face:
            self.log_error_to_ui("Invalid face selection.")
            return
        
        # Get selected sketch geometry
        selected_geo_item = self._sketch_geo_selection_input.selection(0)
        selected_geo = selected_geo_item.entity
        
        # Get the target point based on geometry type
        target_point = self._get_target_point(selected_geo)
        
        if not target_point:
            self.log_error_to_ui("Invalid sketch geometry selection.")
            return
        
        design = adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
        if not design:
            self.log_error_to_ui("No active design found.")
            return
        root = design.rootComponent

        # Get face center
        face_center = selected_face.centroid
        
        # Get rotation angle in radians
        rotation_angle_rad = self._rotation_input.value

        # Create the transformation matrix
        align_transform = self._create_alignment_transform(face_center, target_point, rotation_angle_rad)

        # Get the body and component to move
        body = selected_face.body
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


    def _create_alignment_transform(self, face_center: adsk.core.Point3D, target_point: adsk.core.Point3D, rotation_angle_rad: float) -> adsk.core.Matrix3D:
        """Creates a transformation matrix to align the face center with the target point and rotate around Z-axis.

        This function calculates a 3D transformation matrix that:
        1. Translates the face center to the target point (XY plane alignment)
        2. Rotates the object around the Z-axis by the specified angle

        Args:
            face_center (adsk.core.Point3D): The centroid of the selected face on the package
            target_point (adsk.core.Point3D): The reference point from the footprint sketch
            rotation_angle_rad (float): The rotation angle in radians around the Z-axis

        Returns:
            adsk.core.Matrix3D: The transformation matrix for the alignment and rotation
        """
        # Calculate XY displacement (ignore Z)
        displacement_x = target_point.x - face_center.x
        displacement_y = target_point.y - face_center.y

        # Create a matrix for rotation around the calculated axis through the face center
        transform_matrix = adsk.core.Matrix3D.create()
        
        # Set the origin to the face center for rotation
        transform_matrix.setWithCoordinateSystem(
            face_center,
            adsk.core.Vector3D.create(1, 0, 0),
            adsk.core.Vector3D.create(0, 1, 0),
            adsk.core.Vector3D.create(0, 0, 1)
        )
        
        z_axis = adsk.core.Vector3D.create(0, 0, 1)
        transform_matrix.setToRotation(rotation_angle_rad, z_axis, face_center)

        # Create translation vector (only X and Y)
        translation = transform_matrix.translation
        translation.add(adsk.core.Vector3D.create(displacement_x, displacement_y, 0))
        transform_matrix.translation = translation

        return transform_matrix
    
    
    def _get_target_point(self, geometry):
        """
        Extract target point from sketch geometry.
        Supports circles, lines, and points.
        
        Args:
            geometry: SketchCircle, SketchLine, SketchPoint, or SketchArc
        
        Returns:
            adsk.core.Point3D: The target point
        """
        try:
            # Handle SketchCircle
            if isinstance(geometry, adsk.fusion.SketchCircle):
                return geometry.centerSketchPoint.geometry
            
            # Handle SketchArc
            elif isinstance(geometry, adsk.fusion.SketchArc):
                return geometry.centerSketchPoint.geometry
            
            # Handle SketchLine - return midpoint
            elif isinstance(geometry, adsk.fusion.SketchLine):
                start_point = geometry.startSketchPoint.geometry
                end_point = geometry.endSketchPoint.geometry
                
                midpoint = adsk.core.Point3D.create(
                    (start_point.x + end_point.x) / 2,
                    (start_point.y + end_point.y) / 2,
                    (start_point.z + end_point.z) / 2
                )
                return midpoint
            
            # Handle SketchPoint
            elif isinstance(geometry, adsk.fusion.SketchPoint):
                return geometry.geometry
            
            return None
            
        except Exception as e:
            adsk.core.Application.get().userInterface.messageBox(
                f"Error extracting point from geometry: {str(e)}"
            )
            return None
