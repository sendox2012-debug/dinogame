[app]
title = InnovationDino
package.name = innovationdino
package.domain = org.innovationdino

source.dir = .
source.include_exts = py,png,jpg,ttf,json,txt

version = 1.0

# ТОЛЬКО pygame, без sdl2_* — они подтянутся автоматически
requirements = python3,pygame

orientation = landscape
fullscreen = 1

android.permissions = INTERNET
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a

icon.filename = img/icon.png
presplash.filename = img/icon.png

# ВАЖНО: зафиксируй стабильный NDK
android.ndk_api = 24
p4a.bootstrap = sdl2

log_level = 2