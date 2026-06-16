[app]

title           = Point of Sale
package.name    = pos_mvp
package.domain  = org.yourdomain

source.dir      = .
source.include_exts = py,png,jpg,kv,atlas
main            = pos_mvp_Version6.py

version         = 6.0

# All on one line — no backslash continuation which causes \n prefix bug
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,xlsxwriter,reportlab

android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE

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
