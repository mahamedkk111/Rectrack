[app]

# App identity
title           = Point of Sale
package.name    = pos_mvp
package.domain  = org.yourdomain

# Entry point — must match your .py filename
source.dir      = .
source.include_exts = py,png,jpg,kv,atlas
main            = pos_mvp_Version6.py

# Version
version         = 6.0

# ── Dependencies ──────────────────────────────────────────────────────────────
requirements    = python3,\
                  kivy==2.3.0,\
                  kivymd==1.2.0,\
                  pillow,\
                  xlsxwriter,\
                  reportlab

# ── Android permissions ───────────────────────────────────────────────────────
android.permissions = WRITE_EXTERNAL_STORAGE,\
                      READ_EXTERNAL_STORAGE,\
                      MANAGE_EXTERNAL_STORAGE

# Accept SDK/NDK licenses automatically
android.accept_sdk_license = True

# Target Android API
android.api     = 33
android.minapi  = 21
android.ndk     = 25b
android.sdk     = 33

# Architecture
android.archs   = arm64-v8a, armeabi-v7a

# Allow backup
android.allow_backup = True

# ── Orientation ───────────────────────────────────────────────────────────────
orientation = portrait

# ── Fullscreen ────────────────────────────────────────────────────────────────
fullscreen = 0

# ── Icons / Presplash (optional) ─────────────────────────────────────────────
# icon.filename      = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

[buildozer]
log_level = 2
warn_on_root = 1
