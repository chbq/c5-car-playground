# Copy this file to local.env.ps1 and adjust values when auto-detection is
# insufficient. local.env.ps1 is ignored by Git.

$Env:C5_CUBEMX_EXE = ""
$Env:C5_UV4_EXE = ""
$Env:C5_CUBE_PROGRAMMER_EXE = ""
$Env:C5_ARMCC_EXE = ""
$Env:C5_ARMCLANG_EXE = ""
$Env:C5_PYTHON_EXE = ""
$Env:C5_GIT_EXE = ""
$Env:C5_JAVA_EXE = ""

# Toolchain/package selections:
$Env:C5_ARM_COMPILER = "5"
$Env:C5_CUBE_REPOSITORY = ""
$Env:C5_CUBEF1_VERSION = "1.8.7"
$Env:C5_KEIL_PACK_ROOT = ""
$Env:C5_STM32F1_DFP_VERSION = "2.4.1"

# Set after the target project exists:
$Env:C5_IOC_PATH = "D:\path\to\c5-car-playground\target\c5-firmware\c5-firmware.ioc"
$Env:C5_UVPROJX_PATH = "D:\path\to\c5-car-playground\target\c5-firmware\MDK-ARM\c5-firmware.uvprojx"
$Env:C5_KEIL_TARGET = "c5-firmware"
$Env:C5_FIRMWARE_IMAGE = "D:\path\to\c5-car-playground\target\c5-firmware\MDK-ARM\c5-firmware\c5-firmware.hex"

# Optional:
$Env:C5_SERIAL_PORT = ""
$Env:C5_SERIAL_BAUD = ""
