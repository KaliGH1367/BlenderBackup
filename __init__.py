bl_info = {
    "name": "BlenderBackup",
    "description": "Automatically creates backups of your Blender file on save.",
    "location": "File > Save",
    "author": "FAS",
    "license": "GPL-3.0",
    "version": (1, 0, 0),
    "blender": (4, 1, 0),
    "warning": "",
    "wiki_url": "",
    "tracker_url": "https://github.com/KaliGH1367/BlenderBackup/issues",
    "category": "System",
    "support": "COMMUNITY",
}

import bpy
import os
import shutil
import datetime
import logging
from bpy.app.handlers import persistent


class BlenderBackupPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    backup_dir: bpy.props.StringProperty(
        name="Backup Directory",
        default="backup",
        description="Directory where backups will be stored. Relative to the current blend file."
    )

    max_backups: bpy.props.IntProperty(
        name="Max Backups",
        default=0,
        min=0,
        description="Maximum number of backup files to keep. Set to 0 for unlimited backups."
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "backup_dir")
        layout.prop(self, "max_backups")
        layout.operator("wm.reset_backup_preferences", text="Reset to Default Settings")

class WM_OT_reset_backup_preferences(bpy.types.Operator):
    bl_idname = "wm.reset_backup_preferences"
    bl_label = "Reset Backup Preferences"

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        prefs.backup_dir = "backup"
        prefs.max_backups = 0
        self.report({'INFO'}, "Backup preferences reset to default settings")
        return {'FINISHED'}

class BlenderBackup:
    def __init__(self):
        self.logger = self.setup_logger()
        self.update_preferences()

    def setup_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levellevel)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def update_preferences(self):
        addon_prefs = bpy.context.preferences.addons.get(__package__)
        if addon_prefs is not None:
            prefs = addon_prefs.preferences
            self.backup_dir_name = prefs.backup_dir.lstrip('/\\')  # Sanitize input by stripping leading slashes
            self.max_backups = prefs.max_backups
        else:
            self.backup_dir_name = "backup"
            self.max_backups = 0

    @persistent
    def backup_handler(self, dummy, context):
        self.update_preferences()  # Ensure preferences are up-to-date
        source = bpy.data.filepath
        if not source:
            return  # No blender file is currently saved

        # Construct the backup directory path
        fname = bpy.path.display_name_from_filepath(source)
        blend_dir = os.path.dirname(bpy.path.abspath(source))
        backup_dir = os.path.join(blend_dir, self.backup_dir_name)
        
        # Create backup directory if it doesn't exist
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)  
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dstfile = os.path.join(backup_dir, f"{timestamp}_{fname}.blend")
        
        try:
            shutil.copy2(source, dstfile)
            self.cleanup_old_backups(backup_dir, fname)
            self.logger.info(f"Backup created at: {dstfile}")
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")

    def cleanup_old_backups(self, backup_dir, fname):
        if self.max_backups == 0:
            return  # No backup limit
        backups = sorted(
            [f for f in os.listdir(backup_dir) if f.endswith(".blend") and f.split('_', 2)[2] == fname + ".blend"],
            key=lambda x: os.path.getmtime(os.path.join(backup_dir, x))
        )
        while len(backups) > self.max_backups:
            os.remove(os.path.join(backup_dir, backups.pop(0)))

    def register(self):
        if self.backup_handler not in bpy.app.handlers.save_post:
            bpy.app.handlers.save_post.append(self.backup_handler)

    def unregister(self):
        if self.backup_handler in bpy.app.handlers.save_post:
            bpy.app.handlers.save_post.remove(self.backup_handler)


backup_addon = None

def register():
    global backup_addon
    bpy.utils.register_class(BlenderBackupPreferences)
    bpy.utils.register_class(WM_OT_reset_backup_preferences)
    backup_addon = BlenderBackup()
    backup_addon.register()

def unregister():
    global backup_addon
    backup_addon.unregister()
    bpy.utils.unregister_class(WM_OT_reset_backup_preferences)
    bpy.utils.unregister_class(BlenderBackupPreferences)


if __name__ == "__main__":
    register()
