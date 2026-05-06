import bpy
from .utils import draw_section


class VIEW3D_PT_camera_switcher(bpy.types.Panel):
    """Panel listant toutes les caméras de la scène avec switch rapide."""
    bl_label = "Cam Switcher"
    bl_idname = "VIEW3D_PT_camera_switcher"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SmartPath"
    bl_order = 0


def draw(self, context):
    layout = self.layout
    scene  = context.scene

    cameras = sorted(
        [obj for obj in scene.objects if obj.type == 'CAMERA'],
        key=lambda c: c.name.lower()
    )

    active_cam = scene.camera

    if not cameras:
        layout.label(text="Aucune caméra dans la scène", icon='INFO')
    else:
        col = layout.column(align=True)
        for cam in cameras:
            is_active = (cam == active_cam)
            row = col.row(align=True)
            icon = 'OUTLINER_OB_CAMERA' if is_active else 'CAMERA_DATA'
            op = row.operator(
                "camera.set_active_from_panel",
                text=cam.name,
                icon=icon,
                depress=is_active
            )
            op.camera_name = cam.name

        if active_cam and active_cam.type == 'CAMERA':
            cam_data = active_cam.data
            box = layout.box()
            box.label(text=f"Properties de {active_cam.name}", icon='PROPERTIES')

            sub = box.column(align=True)

            if "Frame Start" in cam_data and "Frame End" in cam_data:
                fs = int(cam_data["Frame Start"])
                fe = int(cam_data["Frame End"])
                row = sub.row(align=True)
                row.label(text="Frame Range :", icon='KEYFRAME')
                row.label(text=f"{fs}  →  {fe}")
            else:
                row = sub.row(align=True)
                row.label(text="Frame Range :", icon='KEYFRAME')
                row.label(text="propriétés non assignées", icon='ERROR')

            if "Mist Start" in cam_data and "Mist Depth" in cam_data:
                ms = float(cam_data["Mist Start"])
                md = float(cam_data["Mist Depth"])
                row = sub.row(align=True)
                row.label(text="Mist :", icon='WORLD')
                row.label(text=f"{ms:.2f}m  →  {md:.2f}m")
            else:
                row = sub.row(align=True)
                row.label(text="Mist :", icon='WORLD')
                row.label(text="propriétés non assignées", icon='ERROR')

    # Toujours afficher les boutons Cam Rig (même sans cam dans la scène)
    layout.separator()
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
    bl_order = 1


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



class VIEW3D_PT_FilePath(bpy.types.Panel):
    bl_label = "Render Path Tool"
    bl_idname = "VIEW3D_PT_filepath"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SmartPath"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 2


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



# ------------------------
# REGISTER
# ------------------------

classes = (
    VIEW3D_PT_camera_switcher,
    VIEW3D_PT_PreviewPath,
    VIEW3D_PT_FilePath,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
