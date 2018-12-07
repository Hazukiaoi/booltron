# ##### BEGIN GPL LICENSE BLOCK #####
#
#  Booltron super add-on for super fast booleans.
#  Copyright (C) 2014-2018  Mikhail Rachinskiy
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# ##### END GPL LICENSE BLOCK #####


from bpy.types import Operator

from .preferences import BooltronPreferences
from .boolean_methods import BooleanMethods
from .object_utils import ObjectUtils
from . import versioning


class Setup(BooleanMethods, ObjectUtils):
    if versioning.SOLVER_OPTION:
        solver = BooltronPreferences.nondestr_solver
    double_threshold = BooltronPreferences.nondestr_double_threshold
    display_secondary = BooltronPreferences.display_secondary
    display_combined = BooltronPreferences.display_combined
    pos_correct = BooltronPreferences.nondestr_pos_correct
    pos_offset = BooltronPreferences.nondestr_pos_offset

    def draw(self, context):
        layout = self.layout

        if versioning.SOLVER_OPTION:
            split = layout.split()
            split.label("Boolean Solver")
            split.prop(self, "solver", text="")

        split = layout.split()
        split.label("Overlap Threshold")
        split.prop(self, "double_threshold", text="")

        split = layout.split()
        split.prop(self, "pos_correct")
        split.prop(self, "pos_offset", text="")

        split = layout.split()
        split.label("Secondary Object")
        split.prop(self, "display_secondary", text="")

        split = layout.split()
        split.label("Combined Object")
        split.prop(self, "display_combined", text="")

    def execute(self, context):
        ob1 = context.active_object
        obs = context.selected_objects
        if ob1.select:
            obs.remove(ob1)

        for md in ob1.modifiers:
            if md.type == "BOOLEAN" and md.operation == self.mode and md.object and "booltron_combined" in md.object:
                ob2 = md.object
                break
        else:
            name = "{} COMBINED {}".format(ob1.name, self.mode[:3])
            ob2 = self.object_add(name)
            ob2.layers = self.view_layers
            ob2.show_all_edges = True
            ob2.draw_type = self.display_combined
            ob2["booltron_combined"] = self.mode
            self.boolean_mod(ob1, ob2, self.mode, md_name=self.mode[:3] + " COMBINED", md_apply=False, terminate=False)

        if self.pos_correct:
            self.object_pos_correct(obs)

        ob2_mats = ob2.data.materials

        for ob in obs:
            if ob.type == "MESH":
                self.boolean_mod(ob2, ob, "UNION", md_apply=False, terminate=False)
                ob.draw_type = self.display_secondary
                for mat in ob.data.materials:
                    if mat.name not in ob2_mats:
                        ob2_mats.append(mat)

        return {"FINISHED"}

    def invoke(self, context, event):
        obs = [ob for ob in context.selected_objects if ob.type == "MESH"]

        if len(obs) < 2 or context.active_object.type != "MESH":
            self.report({"ERROR"}, "At least two Mesh objects must be selected")
            return {"CANCELLED"}

        prefs = context.user_preferences.addons[__package__].preferences
        self.local_view = bool(context.space_data.local_view)
        self.display_combined = prefs.display_combined
        self.display_secondary = prefs.display_secondary
        self.pos_correct = prefs.nondestr_pos_correct
        self.pos_offset = prefs.nondestr_pos_offset
        self.double_threshold = prefs.nondestr_double_threshold

        self.view_layers = [False for x in range(20)]
        self.view_layers[context.scene.active_layer] = True

        if versioning.SOLVER_OPTION:
            self.solver = prefs.nondestr_solver

        if event.ctrl:
            wm = context.window_manager
            return wm.invoke_props_dialog(self, width=300 * context.user_preferences.view.ui_scale)

        return self.execute(context)


class OBJECT_OT_booltron_nondestructive_union(Operator, Setup):
    bl_label = "Booltron Non-destructive Union"
    bl_description = "Combine active (primary) and selected (secondary) objects"
    bl_idname = "object.booltron_nondestructive_union"
    bl_options = {"REGISTER", "UNDO"}

    mode = "UNION"


class OBJECT_OT_booltron_nondestructive_difference(Operator, Setup):
    bl_label = "Booltron Non-destructive Difference"
    bl_description = "Subtract selected (secondary) objects from active (primary) object"
    bl_idname = "object.booltron_nondestructive_difference"
    bl_options = {"REGISTER", "UNDO"}

    mode = "DIFFERENCE"


class OBJECT_OT_booltron_nondestructive_intersect(Operator, Setup):
    bl_label = "Booltron Non-destructive Intersect"
    bl_description = "Keep the common part between active (primary) and selected (secondary) objects"
    bl_idname = "object.booltron_nondestructive_intersect"
    bl_options = {"REGISTER", "UNDO"}

    mode = "INTERSECT"


class OBJECT_OT_booltron_nondestructive_remove(Operator, ObjectUtils):
    bl_label = "Booltron Non-destructive Dismiss"
    bl_description = "Dismiss selected secondary objects from boolean operation"
    bl_idname = "object.booltron_nondestructive_remove"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obs = set(ob for ob in context.selected_objects if "booltron_combined" not in ob)
        is_empty = False

        if not obs:
            return {"CANCELLED"}

        for ob in context.scene.objects:
            if "booltron_combined" in ob:

                for md in ob.modifiers:
                    if md.type == "BOOLEAN" and (not md.object or md.object in obs):
                        ob.modifiers.remove(md)

                for md in ob.modifiers:
                    if md.type == "BOOLEAN":
                        break
                else:
                    is_empty = True
                    self.object_remove(ob)

        if is_empty:
            for ob in context.scene.objects:
                if ob.type == "MESH":
                    for md in ob.modifiers:
                        if md.type == "BOOLEAN" and not md.object:
                            ob.modifiers.remove(md)

        for ob in obs:
            ob.draw_type = "TEXTURED"

        return {"FINISHED"}