# Runs the app on a connected Android device/emulator with Gradle's cache on drive D:
# (drive C: on this PC is nearly full). Usage: powershell -File tool/run_android.ps1
$env:GRADLE_USER_HOME = "D:\gradle-home"
Set-Location (Split-Path $PSScriptRoot -Parent)
flutter run @args
