import bpy

# ------------------------
# RÉSOLUTIONS
# ------------------------

RESOLUTIONS = {
    'HD':  (1280,  720),
    'FHD': (1920, 1080),
    '4K':  (3840, 2160),
}


def apply_resolution(scene, resolution_key):
    if resolution_key in RESOLUTIONS:
        x, y = RESOLUTIONS[resolution_key]
        scene.render.resolution_x = x
        scene.render.resolution_y = y


def update_resolution(self, context):
    apply_resolution(context.scene, self.resolution)


@bpy.app.handlers.persistent
def sync_resolution_on_load(dummy):
    for scene in bpy.data.scenes:
        if hasattr(scene, "filepath_fp_props"):
            apply_resolution(scene, scene.filepath_fp_props.resolution)


# ------------------------
# PROPERTIES
# ------------------------

class FP_Properties(bpy.types.PropertyGroup):
    filename: bpy.props.StringProperty(
        name="File Name",
        default="client_projet",
        description="Le nom doit etre 'client_projet' par exemple: 'DAIKIN_Multi' Il ne faut pas mettre de ' _ ' avant ou après le nom ",
    )
    filepath: bpy.props.StringProperty(
        name="Folder",
        subtype='DIR_PATH',
        description="Champ pour reseigner le dossier dans lequel on veut que le rendu se sauvegarde. Le mieux c'est d'avoir un chemin en absolute, mais dans tout les cas il y a une sécurité pour passer le chemin de relative à absolute",
    )
    version: bpy.props.IntProperty(
        name="Version",
        default=0,
        min=0,
        max=9999,
        description="Version du rendu",
    )
    resolution: bpy.props.EnumProperty(
        name="Resolution",
        items=[
            ('HD',  "HD",  "1280x720"),
            ('FHD', "FHD", "1920x1080"),
            ('4K',  "4K",  "3840x2160"),
        ],
        default='FHD',
        update=update_resolution
    )
    Preview_filename: bpy.props.StringProperty(
        name="Preview Name",
        default="client_projet",
        description="Le nom doit etre 'client_projet' par exemple: 'DAIKIN_Multi' Il ne faut pas mettre de ' _ ' avant ou après le nom ",
    )
    Preview_filepath: bpy.props.StringProperty(
        name="Preview Folder",
        subtype='DIR_PATH',
        description="Champ pour reseigner le dossier dans lequel on veut que le rendu se sauvegarde. Le mieux c'est d'avoir un chemin en absolute, mais dans tout les cas il y a une sécurité pour passer le chemin de relative à absolute",
    )
    Preview_version: bpy.props.IntProperty(
        name="Preview Version",
        default=0,
        min=0,
        max=9999,
        description="Version de la Preview"
    )
    show_path: bpy.props.BoolProperty(default=True)
    GreyBox_render: bpy.props.BoolProperty(default=True)
    use_multi_pass: bpy.props.BoolProperty(
        name="Multi Pass",
        default=False,
        description="Si le rendu a besoin de plusieurs passes, permet de rajouter le nom de la passe dans le rendu"
    )
    passe_name: bpy.props.StringProperty(
        name="Passe Name",
        default="A",
        description="Nom de la passe"
    )
    last_path: bpy.props.StringProperty(default="")
    last_previewpath: bpy.props.StringProperty(default="")


def register():
    bpy.utils.register_class(FP_Properties)
    bpy.types.Scene.filepath_fp_props = bpy.props.PointerProperty(type=FP_Properties)
    bpy.app.handlers.load_post.append(sync_resolution_on_load)


def unregister():
    bpy.utils.unregister_class(FP_Properties)
    del bpy.types.Scene.filepath_fp_props
    if sync_resolution_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(sync_resolution_on_load)
