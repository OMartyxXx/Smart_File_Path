import bpy
import os
import math

from .utils import open_folder


# ------------------------
# OPERATORS — RENDER PATH
# ------------------------

class UPDATEPATH_OT_missing_nodes_popup(bpy.types.Operator):
    bl_idname = "updatepath.missing_nodes_popup"
    bl_label = "Nodes introuvables"
    bl_options = {'INTERNAL'}

    missing_nodes: bpy.props.StringProperty()

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=420)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Chemin appliqué, mais des nodes sont introuvables :", icon='ERROR')
        layout.separator()
        for node in self.missing_nodes.split(","):
            layout.label(text=f"  • Node '{node.strip()}' non trouvé dans le compositor", icon='DOT')
        layout.separator()
        layout.label(text="Vérifiez que le label du node est exactement :")
        row = layout.row(align=True)
        row.label(text='  "EXR"', icon='DOT')
        row.label(text='  "CRYPTO"', icon='DOT')
        layout.separator()
        layout.label(text="Cliquez en dehors pour fermer.", icon='INFO')


class UPDATEPATH_OT_set_render_path(bpy.types.Operator):
    bl_idname = "updatepath.set_render_path"
    bl_label = "Apply Path"
    bl_description = "Applique le chemin de rendu et configure les nodes EXR/CRYPTO"

    def execute(self, context):
        props = context.scene.filepath_fp_props
        scene = context.scene

        if not props.filename.strip():
            self.report({'WARNING'}, "Impossible d'appliquer : le nom de fichier est vide")
            return {'CANCELLED'}

        cam        = scene.camera.name if scene.camera else "NoCam"
        version    = f"V{props.version:02d}"

        abs_filepath = os.path.normpath(bpy.path.abspath(props.filepath))
        props.filepath = abs_filepath

        if props.use_multi_pass and props.passe_name.strip():
            final_path = os.path.join(abs_filepath, f"{props.filename}_{cam}_{props.passe_name.strip()}_{version}_")
        else:
            final_path = os.path.join(abs_filepath, f"{props.filename}_{cam}_{version}_")

        scene.use_nodes = True

        settings = scene.render.image_settings
        if settings.file_format != 'PNG' or settings.color_mode != 'RGBA':
            settings.file_format = 'PNG'
            settings.color_mode  = 'RGBA'
            self.report({'INFO'}, "Format forcé en PNG RGBA")

        scene.render.filepath = final_path
        props.last_path       = final_path

        nodeEXR    = scene.node_tree.nodes.get("EXR")
        nodeCrypto = scene.node_tree.nodes.get("CRYPTO")
        missing    = []

        if nodeEXR:
            nodeEXR.base_path = final_path
        else:
            missing.append("EXR")

        if nodeCrypto:
            nodeCrypto.base_path = final_path + "CRYPTO_"
        else:
            missing.append("CRYPTO")

        if missing:
            bpy.ops.updatepath.missing_nodes_popup('INVOKE_DEFAULT', missing_nodes=", ".join(missing))

        self.report({'INFO'}, f"Chemin appliqué : {final_path}")
        return {'FINISHED'}


class UPDATEPATH_OT_open_folder(bpy.types.Operator):
    bl_idname = "updatepath.open_folder"
    bl_label = "Open Folder"
    bl_description = "Ouvre le dossier de rendu dans l'explorateur"

    def execute(self, context):
        props = context.scene.filepath_fp_props
        if not open_folder(props.filepath):
            self.report({'WARNING'}, "Dossier introuvable")
        return {'FINISHED'}


class UPDATEPATH_OT_copy_path(bpy.types.Operator):
    bl_idname = "updatepath.copy_path"
    bl_label = "Copy Path"
    bl_description = "Copie le chemin dans le presse-papier"

    def execute(self, context):
        props = context.scene.filepath_fp_props
        context.window_manager.clipboard = props.filepath
        self.report({'INFO'}, "Chemin copié")
        return {'FINISHED'}


# ------------------------
# OPERATORS — DEADLINE
# ------------------------

def _apply_camera_properties(context):
    """Applique les custom properties de la caméra active à la scène."""
    scene     = context.scene
    activecam = scene.camera
    applied   = []

    if activecam is None:
        return applied

    cam_data = activecam.data

    # Frame Range
    if "Frame Start" in cam_data and "Frame End" in cam_data:
        scene.frame_start = int(cam_data["Frame Start"])
        scene.frame_end   = int(cam_data["Frame End"])
        applied.append(f"Frame Range: {scene.frame_start} → {scene.frame_end}")

    # Mist
    if "Mist Start" in cam_data and "Mist Depth" in cam_data:
        if scene.world is None:
            scene.world = bpy.data.worlds.new(name="World")
        scene.world.mist_settings.start = float(cam_data["Mist Start"])
        scene.world.mist_settings.depth = float(cam_data["Mist Depth"])
        applied.append(f"Mist: {scene.world.mist_settings.start}m → {scene.world.mist_settings.depth}m")

    return applied


def _deadline_send(operator, context):
    """Exécute l'envoi à Deadline."""
    # Appliquer les custom properties de la cam active avant l'envoi
    applied = _apply_camera_properties(context)
    for info in applied:
        operator.report({'INFO'}, f"Cam → Scène : {info}")

    bpy.ops.file.make_paths_absolute()
    try:
        bpy.ops.ops.submit_blender_to_deadline()
        operator.report({'INFO'}, "Envoyé à Deadline")
    except Exception as e:
        operator.report({'ERROR'}, f"Deadline inaccessible : {e}")
        return {'CANCELLED'}
    return {'FINISHED'}


def _check_missing_paths(context):
    """Retourne la liste des paramètres manquants avant envoi Deadline."""
    props   = context.scene.filepath_fp_props
    scene   = context.scene
    missing = []

    if not scene.use_nodes:
        missing.append("Use Nodes non coché — lancez 'Apply Path' avant d'envoyer")

    if not props.last_path.strip():
        missing.append("Output Render (Apply Path jamais utilisé)")

    if scene.use_nodes and scene.node_tree:
        nodeEXR    = scene.node_tree.nodes.get("EXR")
        nodeCrypto = scene.node_tree.nodes.get("CRYPTO")
        if nodeEXR and not nodeEXR.base_path.strip():
            missing.append("Node EXR (base_path vide)")
        if nodeCrypto and not nodeCrypto.base_path.strip():
            missing.append("Node CRYPTO (base_path vide)")

    return missing


class SEND_OT_deadline_missing_paths(bpy.types.Operator):
    bl_idname = "scene.send_deadline_missing_paths"
    bl_label = "Chemins manquants"
    bl_options = {'INTERNAL'}

    missing_paths: bpy.props.StringProperty()

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=420)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Envoi annulé — des chemins ne sont pas renseignés :", icon='ERROR')
        layout.separator()
        for path in self.missing_paths.split("|"):
            layout.label(text=f"  • {path.strip()}", icon='DOT')
        layout.separator()
        layout.label(text="Utilisez 'Apply Path' avant d'envoyer à Deadline.")
        layout.separator()
        layout.label(text="Cliquez en dehors pour fermer.", icon='INFO')


class SEND_OT_deadline_overwrite(bpy.types.Operator):
    bl_idname = "scene.send_deadline_overwrite"
    bl_label = "Fichiers existants"
    bl_options = {'INTERNAL'}

    existing_count: bpy.props.IntProperty()
    folder: bpy.props.StringProperty()

    def execute(self, context):
        bpy.ops.scene.send_deadline_summary('INVOKE_DEFAULT')
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=420, confirm_text="Continuer")

    def cancel(self, context):
        def draw_cancel(self, context):
            self.layout.label(text="Envoi vers Deadline annulé", icon='INFO')
        context.window_manager.popup_menu(draw_cancel, title="Deadline", icon='INFO')

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"{self.existing_count} fichier(s) déjà présent(s) dans :", icon='ERROR')
        layout.label(text=self.folder)
        layout.separator()
        layout.label(text="Cliquez Continuer pour écraser, ou Annuler pour stopper.")


class SEND_OT_deadline_summary(bpy.types.Operator):
    bl_idname = "scene.send_deadline_summary"
    bl_label = "Résumé avant envoi"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        return _deadline_send(self, context)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=1200, confirm_text="Valider et lancer le rendu")

    def draw(self, context):
        scene  = context.scene
        layout = self.layout
        layout.scale_y = 1.2

        cam = scene.camera.name if scene.camera else "Aucune caméra active ⚠️"
        layout.label(text="Résumé du job Deadline", icon='RENDER_STILL')
        layout.separator()

        # Lire les custom properties de la cam pour afficher les valeurs qui seront appliquées
        frame_start = scene.frame_start
        frame_end   = scene.frame_end
        mist_start  = scene.world.mist_settings.start
        mist_depth  = scene.world.mist_settings.depth

        frame_label = f"{frame_start}  →  {frame_end}"
        mist_label  = f"{mist_start}  →  {mist_depth}"
        
        col = layout.column(align=True)

        def info_row(col, label, value, icon):
            split = col.split(factor=0.25)
            split.label(text=label, icon=icon)
            split.label(text=value)

        info_row(col, "Caméra :",        cam,                                                                        'CAMERA_DATA')

        
        info_row(col, "Frame Range :",   frame_label,                                                                'KEYFRAME')
        info_row(col, "Mist:",   mist_label,                                                                'WORLD')
        info_row(col, "Frame Rate :",    f"{scene.render.fps} fps",                                                  'TIME')
        col.separator()
        info_row(col, "Résolution :",    f"{scene.render.resolution_x} x {scene.render.resolution_y}  ({scene.render.resolution_percentage} %)", 'RESTRICT_RENDER_OFF')
        col.separator()

        engine = scene.render.engine
        if engine == 'CYCLES':
            samples = scene.cycles.samples
            denoise = "On" if scene.cycles.use_denoising else "Off"
        else:
            samples = "—"
            denoise = "—"

        info_row(col, "Samples :",  str(samples), 'SHADERFX')
        info_row(col, "Denoise :",  denoise,       'OUTLINER_OB_LIGHTPROBE')
        col.separator()

        cm = scene.view_settings
        info_row(col, "Color Management View :", cm.view_transform or "—", 'RESTRICT_COLOR_OFF')
        info_row(col, "Color Management Look :", cm.look or "None",        'RESTRICT_COLOR_OFF')
        col.separator()

        info_row(col, "Output Render :", scene.render.filepath or "— non défini —", 'OUTPUT')

        exr_path    = "— node introuvable —"
        crypto_path = "— node introuvable —"
        if scene.use_nodes and scene.node_tree:
            nodeEXR    = scene.node_tree.nodes.get("EXR")
            nodeCrypto = scene.node_tree.nodes.get("CRYPTO")
            if nodeEXR:
                exr_path = nodeEXR.base_path or "— vide —"
            if nodeCrypto:
                crypto_path = nodeCrypto.base_path or "— vide —"

        info_row(col, "EXR :",    exr_path,    'FILE_IMAGE')
        info_row(col, "CRYPTO :", crypto_path, 'NODE_COMPOSITING')


class SEND_OT_deadline(bpy.types.Operator):
    bl_idname = "scene.send_deadline"
    bl_label = "Check and Send to Deadline"
    bl_description = "Vérification des chemins d'accès, affiche un récap si tout est bon et envois le job à Deadline après"

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        if "DeadlineBlenderClient" not in bpy.context.preferences.addons:
            self.report({'ERROR'}, "Le plugin Deadline n'est pas activé")
            return {'CANCELLED'}

        missing = _check_missing_paths(context)
        if missing:
            bpy.ops.scene.send_deadline_missing_paths(
                'INVOKE_DEFAULT',
                missing_paths="|".join(missing)
            )
            return {'CANCELLED'}

        props  = context.scene.filepath_fp_props
        folder = props.filepath.strip()
        if folder and os.path.isdir(folder):
            existing = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
            if existing:
                bpy.ops.scene.send_deadline_overwrite(
                    'INVOKE_DEFAULT',
                    existing_count=len(existing),
                    folder=folder
                )
                return {'FINISHED'}

        bpy.ops.scene.send_deadline_summary('INVOKE_DEFAULT')
        return {'FINISHED'}


# ------------------------
# OPERATOR — CAMERA RIG / SWITCHER
# ------------------------

class CREATE_RIG_OT_camera_rig(bpy.types.Operator):
    bl_idname = "scene.create_camera_rig"
    bl_label = "Create Camera Rig"
    bl_description = "Crée un rig de caméra (LOC > Offset > Camera)"
    bl_options = {'REGISTER', 'UNDO'}

    cam_name: bpy.props.StringProperty(
        name="Camera Name",
        default="P"
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "cam_name")

    def execute(self, context):
        if "CAM" in bpy.data.collections:
            cam_collection = bpy.data.collections["CAM"]
        else:
            cam_collection = bpy.data.collections.new("CAM")
            context.scene.collection.children.link(cam_collection)
        cam_collection.color_tag = 'COLOR_06'

        bpy.ops.object.empty_add(type='PLAIN_AXES')
        empty_root      = context.active_object
        empty_root.name = "LOC_" + self.cam_name

        bpy.ops.object.empty_add(type='CUBE')
        empty_child                    = context.active_object
        empty_child.name               = "Offset_" + self.cam_name
        empty_child.parent             = empty_root
        empty_child.location           = (0, 0, 0)
        empty_child.empty_display_size = 0.25

        bpy.ops.object.camera_add()
        cam                  = context.active_object
        cam.name             = self.cam_name
        cam.parent           = empty_child
        cam.location         = (0, 0, 0)
        cam.rotation_euler   = (math.radians(90), 0, 0)

        # Création dans l'ordre inverse pour que l'UI affiche :
        # Frame Start → Frame End → Mist Start → Mist Depth
        cam.data["Mist Depth"]  = 25.0
        cam.data["Mist Start"]  = 0.0
        cam.data["Frame End"]   = context.scene.frame_end
        cam.data["Frame Start"] = context.scene.frame_start
        cam.data.id_properties_ui("Mist Depth").update(min=0.0,  subtype="DISTANCE", description="Profondeur du mist")
        cam.data.id_properties_ui("Mist Start").update(min=0.0,  subtype="DISTANCE", description="Distance de début du mist")
        cam.data.id_properties_ui("Frame End").update(min=0,     description="Frame de fin")
        cam.data.id_properties_ui("Frame Start").update(min=0,   description="Frame de début")

        for obj in [empty_root, empty_child, cam]:
            for col in list(obj.users_collection):
                col.objects.unlink(obj)
            cam_collection.objects.link(obj)

        self.report({'INFO'}, f"Rig '{self.cam_name}' créé")
        return {'FINISHED'}


class SETCAMFRAMERANGE_OT_set_camframerange(bpy.types.Operator):
    bl_idname = "scene.set_camfrange"
    bl_label = "Set Frame Range to Active Camera"
    bl_description = "Applique le frame range de la scène dans les custom properties de la cam active"

    def execute(self, context):
        scene     = context.scene
        activecam = scene.camera

        if activecam is None:
            self.report({'WARNING'}, "Aucune caméra active dans la scène")
            return {'CANCELLED'}

        if "Frame Start" in activecam.data and "Frame End" in activecam.data:
            activecam.data["Frame Start"] = scene.frame_start
            activecam.data["Frame End"]   = scene.frame_end
            activecam.data.update_tag()
            for area in context.screen.areas:
                area.tag_redraw()
            self.report({'INFO'}, "Frame Range appliqué a la CAM active")
        else:
            self.report({'WARNING'}, "La caméra active n'a pas de custom properties Frame Start / Frame End")
        return {'FINISHED'}


class SETMISTPASSE_OT_set_mist_passe(bpy.types.Operator):
    bl_idname = "scene.set_mistpasse"
    bl_label = "Set Mist Path to Active Camera"
    bl_description = "Applique la mist actuelle de la scène dans les custom properties de la cam active"

    def execute(self, context):
        scene     = context.scene
        world     = scene.world
        activecam = scene.camera

        if activecam is None:
            self.report({'WARNING'}, "Aucune caméra active dans la scène")
            return {'CANCELLED'}

        if world is None:
            self.report({'WARNING'}, "Aucune world dans la scène")
            return {'CANCELLED'}
            

        if "Mist Start" in activecam.data and "Mist Depth" in activecam.data:
            activecam.data["Mist Start"] = world.mist_settings.start
            activecam.data["Mist Depth"] = world.mist_settings.depth
            activecam.data.update_tag()
            for area in context.screen.areas:
                area.tag_redraw()
            self.report({'INFO'}, "Mist appliqué a la CAM active")
        else:
            self.report({'WARNING'}, "La caméra active n'a pas de custom properties Frame Start / Frame End")
        return {'FINISHED'}


class CAMERA_OT_set_active(bpy.types.Operator):
    """Définit cette caméra comme caméra active de la scène"""
    bl_idname = "camera.set_active_from_panel"
    bl_label = "Set Active Camera"
    bl_options = {'REGISTER', 'UNDO'}

    camera_name: bpy.props.StringProperty()

    def execute(self, context):
        
        cam_obj = bpy.data.objects.get(self.camera_name)

        scene       = context.scene
        active_cam  = scene.camera
        
        if world is None:
            self.report({'WARNING'}, "Aucun world dans la scéne")
            return {'CANCELLED'}

        if active_cam id None:
            self.report({'CANCELLED'}, "Aucune caméra active dans la scène")
        
        cod         = cam_obj.data #cod pour cam_object_data : nom plus court pour la vérif plus bas
        world       = scene.world


        mist_start  = camera_name.data["Mist Start"]
        mist_depth  = camera_name.data["Mist Depth"]

        frame_start = camera_name.data["Frame Start"]
        frame_end   = camera_name.data["Frame End"]

        if cam_obj and cam_obj.type == 'CAMERA':
            
            if "Mist Start" in acd and "Mist Depth" in acd and "Frame Start" in acd and "Frame End" in acd:

                world.mist_settings.start = mist_start
                world.mist_settings.depth = mist_depth

                scene.frame_start = frame_start
                scene.frame_end = frame_end

                return {'FINISHED'}


            active_cam = cam_obj
            self.report({'INFO'}, f"Caméra active : {cam_obj.name}")

            

        else:
            self.report({'WARNING'}, f"Caméra introuvable : {self.camera_name}")
            return {'CANCELLED'}
        return {'FINISHED'}



# ------------------------
# OPERATORS — PREVIEW PATH
# ------------------------

class GREYBOXRENDER_OT_set_greybox_path(bpy.types.Operator):
    bl_idname = "greyboxrender.set_greybox_path"
    bl_label = "Apply Preview Path"
    bl_description = "Applique le chemin de preview (MP4, pas de compositor)"

    def execute(self, context):
        props = context.scene.filepath_fp_props
        scene = context.scene

        previewcam     = scene.camera.name if scene.camera else "NoCam"
        previewversion = f"V{props.Preview_version:02d}"
        preview_path   = os.path.join(
            props.Preview_filepath,
            f"{props.Preview_filename}_Preview_{previewcam}_{previewversion}_"
        )

        scene.use_nodes = False

        settings = scene.render.image_settings
        encoding = scene.render.ffmpeg
        if settings.file_format != 'FFMPEG' or encoding.format != 'MPEG4':
            settings.file_format = 'FFMPEG'
            encoding.format      = 'MPEG4'
            self.report({'INFO'}, "Format forcé en FFMPEG MP4")

        scene.render.filepath  = preview_path
        props.last_previewpath = preview_path

        self.report({'INFO'}, f"Preview path appliqué : {preview_path}")
        return {'FINISHED'}


class UPDATEPREVIEWPATH_OT_open_previewfolder(bpy.types.Operator):
    bl_idname = "updatepreviewpath.open_previewfolder"
    bl_label = "Open Folder"
    bl_description = "Ouvre le dossier preview dans l'explorateur"

    def execute(self, context):
        props = context.scene.filepath_fp_props
        if not open_folder(props.Preview_filepath):
            self.report({'WARNING'}, "Dossier introuvable")
        return {'FINISHED'}


class UPDATEPREVIEWPATH_OT_copy_previewpath(bpy.types.Operator):
    bl_idname = "updatepreviewpath.copy_previewpath"
    bl_label = "Copy Path"
    bl_description = "Copie le chemin preview dans le presse-papier"

    def execute(self, context):
        props = context.scene.filepath_fp_props
        context.window_manager.clipboard = props.Preview_filepath
        self.report({'INFO'}, "Chemin copié")
        return {'FINISHED'}


class GREYBOXRENDER_OT_wait_and_open(bpy.types.Operator):
    """Modal operator qui attend la fin du rendu viewport puis ouvre le dossier."""
    bl_idname = "greyboxrender.wait_and_open"
    bl_label = "Wait Render"
    bl_options = {'INTERNAL'}

    _timer  = None
    _folder = ""

    def modal(self, context, event):
        if event.type != 'TIMER':
            return {'PASS_THROUGH'}

        scene   = context.scene
        current = scene.frame_current

        if not self._was_rendering:
            if current != self._start_frame:
                self._was_rendering = True
                self._last_frame    = current
            else:
                self._wait_count += 1
                if self._wait_count > 20:
                    self._was_rendering = True
        else:
            if current != self._last_frame:
                if current < self._last_frame and self._last_frame >= self._end_frame - 1:
                    self.cancel(context)
                    open_folder(self._folder)
                    return {'FINISHED'}
                self._last_frame = current

        return {'PASS_THROUGH'}

    def execute(self, context):
        self._folder        = self.__class__._folder
        self._was_rendering = False
        self._start_frame   = context.scene.frame_current
        self._end_frame     = context.scene.frame_end
        self._last_frame    = context.scene.frame_current
        self._wait_count    = 0
        self._timer = context.window_manager.event_timer_add(0.5, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None


class GREYBOXRENDER_OT_viewport_render_animation(bpy.types.Operator):
    bl_idname = "greyboxrender.viewport_render_animation"
    bl_label = "Viewport Render Animation"
    bl_description = "Lance le rendu viewport et ouvre le dossier à la fin"

    def execute(self, context):
        scene = context.scene
        props = context.scene.filepath_fp_props

        if not scene.render.filepath.strip():
            def draw_error(self, context):
                self.layout.label(text="Output Render non défini.", icon='ERROR')
                self.layout.label(text="Utilisez 'Apply Preview Path' avant de lancer le rendu.")
            context.window_manager.popup_menu(draw_error, title="Chemin manquant", icon='ERROR')
            return {'CANCELLED'}

        folder = bpy.path.abspath(props.Preview_filepath.strip()) if props.Preview_filepath.strip() \
                 else os.path.dirname(bpy.path.abspath(scene.render.filepath))

        GREYBOXRENDER_OT_wait_and_open._folder = folder

        bpy.ops.render.opengl('INVOKE_DEFAULT', animation=True)
        bpy.ops.greyboxrender.wait_and_open('INVOKE_DEFAULT')

        return {'FINISHED'}


# ------------------------
# REGISTER
# ------------------------

classes = (
    UPDATEPATH_OT_missing_nodes_popup,
    UPDATEPATH_OT_set_render_path,
    UPDATEPATH_OT_open_folder,
    UPDATEPATH_OT_copy_path,
    SEND_OT_deadline_missing_paths,
    SEND_OT_deadline_overwrite,
    SEND_OT_deadline_summary,
    SEND_OT_deadline,
    CREATE_RIG_OT_camera_rig,
    SETCAMFRAMERANGE_OT_set_camframerange,
    SETMISTPASSE_OT_set_mist_passe,
    CAMERA_OT_set_active,
    GREYBOXRENDER_OT_set_greybox_path,
    GREYBOXRENDER_OT_wait_and_open,
    GREYBOXRENDER_OT_viewport_render_animation,
    UPDATEPREVIEWPATH_OT_open_previewfolder,
    UPDATEPREVIEWPATH_OT_copy_previewpath,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
