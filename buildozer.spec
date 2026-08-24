[app]

# Название приложения (видно под иконкой на телефоне)
title = InnovationDino

# Внутреннее имя пакета (только латиница, нижний регистр)
package.name = innovationdino

# Домен пакета
package.domain = org.innovationdino

# Исходный код
source.dir = .
source.include_exts = py,png,jpg,ttf,json,txt

# Версия приложения
version = 1.0

# Зависимости Python
# НЕ указывай sdl2,sdl2_image,sdl2_mixer,sdl2_ttf отдельно —
# рецепт pygame подтянет их сам
requirements = python3,pygame

# Ориентация экрана
orientation = landscape

# Полноэкранный режим
fullscreen = 1

# Разрешения Android
android.permissions = INTERNET

# Автопринятие лицензий SDK
android.accept_sdk_license = True

# Архитектуры процессора
android.archs = arm64-v8a, armeabi-v7a

# Иконка приложения (512x512 PNG)
icon.filename = img/icon.png

# Экран загрузки (splash screen)
presplash.filename = img/icon.png

# Минимальная версия Android API
android.minapi = 24

# Целевая версия Android API
android.api = 33

# ВАЖНО: фиксируем стабильную версию NDK
# NDK r28c/r27/r26 НЕ поддерживаются рецептом pygame
# r25b — последняя гарантированно рабочая версия
android.ndk_api = 24
android.ndk_version = 25b

# Bootstrap
p4a.bootstrap = sdl2

# Уровень логирования (2 = подробно)
log_level = 2

# [buildozer]
# Для отладки можно раскомментировать:
# log_level = 2
# warn_on_root = 0