[app]

title           = Point of Sale
package.name    = pos_mvp
package.domain  = org.yourdomain

source.dir      = .
source.include_exts = py,png,jpg,kv,atlas
main            = main.py

version         = 6.0

# Pillow removed — KivyMD includes what it needs
# pyjnius pinned to version with Android wheels
requirements = python3,kivy==2.3.0,kivymd==1.2.0,xlsxwriter,reportlab

android.permissions = MANAGE_EXTERNAL_STORAGE

android.accept_sdk_license = True

android.api    = 33
android.minapi = 21
android.ndk    = 25b

android.archs = arm64-v8a, armeabi-v7a

android.allow_backup = True

orientation = portrait

fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1
