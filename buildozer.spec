[app]

# App identity
title           = Rectrack
package.name    = Rectrack
package.domain  = org.yourdomain

# Entry point — must match your .py filename
source.dir      = .
source.include_exts = py,png,jpg,kv,atlas
main            = pos_mvp_Version4.py

# Version
version         = 1.0

# ── Dependencies ──────────────────────────────────────────────────────────────
# KivyMD must be pinned to a version compatible with your Kivy version.
# Kivy 2.3.x  →  KivyMD 1.2.0
requirements    = python3,kivy==2.3.0,kivymd==1.2.0,xlsxwriter,reportlab

# ── Android permissions ───────────────────────────────────────────────────────
android.permissions = WRITE_EXTERNAL_STORAGE,\
                      READ_EXTERNAL_STORAGE,\
                      MANAGE_EXTERNAL_STORAGE

# Target Android API — 33 = Android 13 (safe for most modern devices)
android.api         = 34
android.minapi      = 21
android.ndk         = 25b
android.sdk         = 33
android.accept_sdk_license = True

# Architecture — include both for wider device support
android.archs       = arm64-v8a, armeabi-v7a

# Allow backup
android.allow_backup = True

# ── Orientation ───────────────────────────────────────────────────────────────
orientation = portrait

# ── Fullscreen ────────────────────────────────────────────────────────────────
# 0 = show status bar (recommended)
fullscreen = 0

# ── Icons / Presplash (optional — add your own files) ────────────────────────
# icon.filename     = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

# ── iOS (not needed but required section) ─────────────────────────────────────
[buildozer]
log_level = 2
warn_on_root = 1
