import bpy
import urllib.request
import urllib.error
import json
import os
import zipfile
import shutil

# ------------------------------------------------
# CONFIG — ne pas toucher sauf si le repo change
# ------------------------------------------------

GITHUB_USER     = "OMartyxXx"
GITHUB_REPO     = "Smart_File_Path"
CURRENT_VERSION = (1, 7, 4)              # ← à mettre à jour à chaque release

# ------------------------------------------------
# HELPERS
# ------------------------------------------------

def _version_tuple(tag: str):
    """Convertit 'v1.7.4' ou '1.7.4' en (1, 7, 4)."""
    tag = tag.lstrip("v")
    try:
        return tuple(int(x) for x in tag.split("."))
    except ValueError:
        return (0, 0, 0)


def _get_latest_release():
    """Interroge l'API GitHub et retourne (tag, zip_url) ou lève une exception."""
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "BlenderAddon-SmartFilePath"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())

    tag     = data.get("tag_name", "")
    assets  = data.get("assets", [])
    zip_url = next((a["browser_download_url"] for a in assets if a["name"].endswith(".zip")), None)

    if not zip_url:
        zip_url = data.get("zipball_url")

    return tag, zip_url


# ------------------------------------------------
# OPERATORS
# ------------------------------------------------

class SMARTPATH_OT_check_update(bpy.types.Operator):
    bl_idname  = "smartpath.check_update"
    bl_label   = "Check for Update"
    bl_description = "Vérifie si une nouvelle version est disponible sur GitHub"

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences

        prefs.update_status  = "checking"
        prefs.latest_version = ""
        prefs.download_url   = ""

        try:
            tag, zip_url = _get_latest_release()
            latest = _version_tuple(tag)

            prefs.latest_version = tag
            prefs.download_url   = zip_url or ""

            if latest > CURRENT_VERSION:
                prefs.update_status = "available"
                self.report({'INFO'}, f"Mise à jour disponible : {tag}")
            else:
                prefs.update_status = "uptodate"
                self.report({'INFO'}, "Vous avez la dernière version !")

        except urllib.error.URLError as e:
            prefs.update_status = "error"
            self.report({'ERROR'}, f"Impossible de contacter GitHub : {e.reason}")
        except Exception as e:
            prefs.update_status = "error"
            self.report({'ERROR'}, f"Erreur inattendue : {e}")

        return {'FINISHED'}


class SMARTPATH_OT_install_update(bpy.types.Operator):
    bl_idname  = "smartpath.install_update"
    bl_label   = "Télécharger et Installer"
    bl_description = "Télécharge la dernière version et l'installe (redémarrage Blender requis)"

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences

        if not prefs.download_url:
            self.report({'ERROR'}, "Aucune URL de téléchargement disponible")
            return {'CANCELLED'}

        try:
            # 1. Téléchargement dans un dossier temp
            tmp_dir  = bpy.app.tempdir
            zip_path = os.path.join(tmp_dir, "smartfilepath_update.zip")

            self.report({'INFO'}, "Téléchargement en cours...")
            req = urllib.request.Request(
                prefs.download_url,
                headers={"User-Agent": "BlenderAddon-SmartFilePath"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp, open(zip_path, "wb") as f:
                shutil.copyfileobj(resp, f)

            # 2. Trouver le dossier d'installation de l'addon
            addon_dir = os.path.dirname(os.path.abspath(__file__))

            # 3. Extraire le zip dans un dossier temp
            extract_dir = os.path.join(tmp_dir, "smartfilepath_extracted")
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)

            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(extract_dir)

            # 4. Trouver le dossier racine dans le zip
            extracted_items = os.listdir(extract_dir)
            if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
                source_dir = os.path.join(extract_dir, extracted_items[0])
            else:
                source_dir = extract_dir

            # 5. Copier les fichiers .py et .toml dans le dossier de l'addon
            for fname in os.listdir(source_dir):
                if fname.endswith((".py", ".toml")):
                    src  = os.path.join(source_dir, fname)
                    dest = os.path.join(addon_dir, fname)
                    shutil.copy2(src, dest)

            # 6. Nettoyage
            os.remove(zip_path)
            shutil.rmtree(extract_dir)

            prefs.update_status = "installed"
            self.report({'INFO'}, "✅ Mise à jour installée ! Redémarrez Blender.")

        except Exception as e:
            prefs.update_status = "error"
            self.report({'ERROR'}, f"Erreur lors de l'installation : {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


# ------------------------------------------------
# PREFERENCES
# ------------------------------------------------

class SMARTPATH_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    # Propriétés internes (pas affichées directement)
    update_status:   bpy.props.StringProperty(default="idle")
    latest_version:  bpy.props.StringProperty(default="")
    download_url:    bpy.props.StringProperty(default="")

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Version installée : {'.'.join(str(x) for x in CURRENT_VERSION)}", icon='INFO')
        layout.separator()

        row = layout.row()
        row.operator("smartpath.check_update", icon='FILE_REFRESH')

        status = self.update_status

        if status == "uptodate":
            layout.label(text="✅ Vous avez la dernière version !", icon='CHECKMARK')

        elif status == "available":
            box = layout.box()
            box.label(text=f"🔔 Mise à jour disponible : {self.latest_version}", icon='ERROR')
            box.operator("smartpath.install_update", icon='IMPORT')
            box.label(text="⚠️ Blender devra être redémarré après l'installation.", icon='INFO')

        elif status == "installed":
            layout.label(text="✅ Mise à jour installée — Redémarrez Blender.", icon='CHECKMARK')

        elif status == "error":
            layout.label(text="❌ Erreur — vérifiez votre connexion internet.", icon='CANCEL')

        elif status == "checking":
            layout.label(text="⏳ Vérification en cours...", icon='TIME')


# ------------------------------------------------
# REGISTER
# ------------------------------------------------

classes = (
    SMARTPATH_OT_check_update,
    SMARTPATH_OT_install_update,
    SMARTPATH_Preferences,
)


def register():
    # Sécurité — supprime le __pycache__ pour éviter les anciennes versions en cache
    pycache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "__pycache__")
    if os.path.exists(pycache_dir):
        try:
            shutil.rmtree(pycache_dir)
        except Exception:
            pass

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
