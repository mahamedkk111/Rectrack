[app]
# (str) Title of your application
title = POS App

# (str) Package name (will be used as the java package name)
package.name = pos_app

# (str) Package domain (reverse domain style)
package.domain = org.example

# (str) Source code where the main.py is located
source.dir = .

# (list) Source file extensions to include
source.include_exts = py,kv,kvlang,png,jpg,xml,db,csv

# (str) Application versioning (must be set)
version = 0.1
# alternatively you can use version.regex

# (list) Application requirements
requirements = python3,kivy==2.1.0,xlsxwriter

# (str) Supported orientation (portrait / landscape / all)
orientation = portrait

# (bool) Enable fullscreen (default False)
fullscreen = 0

# (str) Android permissions - adjust as needed (storage access on newer Android is subject to scoped storage rules)
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# (int) Android API to use (compile SDK)
android.api = 33

# (int) Minimum API supported
android.minapi = 21

# (str) NDK version to use
android.ndk = 23b

# (int) Android NDK API (C headers/API level)
android.ndk_api = 21

# (str) Supported CPU architectures
android.arch = armeabi-v7a, arm64-v8a

# (int) Logging level (0 = debug, 1 = info, 2 = warning, 3 = error)
log_level = 2

[buildozer]
warn_on_root = 1
