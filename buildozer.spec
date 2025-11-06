[app]
title = Record Tracker
package.name = recordtracker
package.domain = org.muhammad
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,csv
icon.filename = %(source.dir)s/icon.png
requirements = python3,kivy,sqlite3,xlsxwriter,csv
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
orientation = portrait
