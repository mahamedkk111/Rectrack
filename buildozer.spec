[app]
title = POS Tracker
package.name = pos_tracker
package.domain = org.muhammad
source.dir = .
source.include_exts = py,kv,png,jpg,db,csv,ttf
version = 1.0.0
requirements = python3,kivy,sqlite3,xlsxwriter
orientation = portrait
fullscreen = 0
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 27
android.archs = arm64-v8a,armeabi-v7a
log_level = 2
icon.filename = icon.png
p4a.local_recipes = 

[buildozer]
log_level = 2
warn_on_root = 1
