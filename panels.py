import bpy
from .utils import draw_section


class VIEW3D_PT_FilePath(bpy.types.Panel):
    bl_label = "Render Path Tool"
    bl_idname = "VIEW3D_PT_filepath"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SmartPath"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props  = context.scene.filepath_fp_props

        box = draw_section(layout, props, "show_path", "Path Settings")
        if box:
            box.prop(props, "filepath")
            box.prop(props, "filename")

            box.prop(props, "use_multi_pass", text="Multi Pass")
            if props.use_multi_pass:
                box.prop(props, "passe_name")

            row = box.row(align=True)
            row.label(text="Version")
            row.prop(props, "version", text="")

            row = box.row(align=True)
            row.prop(props, "resolution", expand=True)

            box.operator("updatepath.set_render_path", icon='FILE_TICK')

            sub = box.box()
            sub.label(text="Output Path")
            if props.last_path:
                sub.label(text=props.last_path, icon='CHECKMARK')
                row = sub.row(align=True)
                row.operator("updatepath.open_folder", icon='FILE_FOLDER')
                row.operator("updatepath.copy_path", icon='COPYDOWN')
            else:
                sub.label(text="Not set", icon='ERROR')

            if "DeadlineBlenderClient" in bpy.context.preferences.addons:
                box.operator("scene.send_deadline", icon='RENDER_STILL')
            else:
                box.label(text="Deadline non activé", icon='INFO')


class VIEW3D_PT_CamRigCreator(bpy.types.Panel):
    bl_label = "Create Cam Rig"
    bl_idname = "VIEW3D_PT_camrigcreator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SmartPath"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        layout.operator("scene.create_camera_rig", icon='CAMERA_DATA')
        layout.operator("scene.set_camfrange", icon='KEYFRAME')
        layout.operator("scene.set_mistpasse", icon='WORLD')


class VIEW3D_PT_PreviewPath(bpy.types.Panel):
    bl_label = "Preview Path Tool"
    bl_idname = "VIEW3D_PT_previewpath"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SmartPath"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props  = context.scene.filepath_fp_props

        pbox = draw_section(layout, props, "GreyBox_render", "Greybox Render")
        if pbox:
            pbox.prop(props, "Preview_filepath")
            pbox.prop(props, "Preview_filename")

            row = pbox.row(align=True)
            row.label(text="Version")
            row.prop(props, "Preview_version", text="")

            pbox.operator("greyboxrender.set_greybox_path", icon='FILE_TICK')

            sub = pbox.box()
            sub.label(text="Output Preview")
            if props.last_previewpath:
                sub.label(text=props.last_previewpath, icon='CHECKMARK')
                row = sub.row(align=True)
                row.operator("updatepreviewpath.open_previewfolder", icon='FILE_FOLDER')
                row.operator("updatepreviewpath.copy_previewpath", icon='COPYDOWN')
            else:
                sub.label(text="Not set", icon='ERROR')

            pbox.separator()
            pbox.operator("greyboxrender.viewport_render_animation", icon='RENDER_ANIMATION')


# ------------------------
# REGISTER
# ------------------------

classes = (
    VIEW3D_PT_FilePath,
    VIEW3D_PT_CamRigCreator,
    VIEW3D_PT_PreviewPath,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
