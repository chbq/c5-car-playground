[CmdletBinding(SupportsShouldProcess=$true)]
param(
    [string]$ImagePath = $Env:C5_FIRMWARE_IMAGE,
    [switch]$IUnderstandThisWillFlashHardware
)

. (Join-Path $PSScriptRoot "common.ps1")

if (-not $IUnderstandThisWillFlashHardware) {
    throw @"
Flashing is disabled by default.
Re-run with -IUnderstandThisWillFlashHardware only after:
1. the build passed;
2. the exact MCU and image are confirmed;
3. motor outputs are known to remain inactive at startup;
4. the board is connected safely.
"@
}

$cubeProgrammer = Resolve-ToolPath `
    -Configured $Env:C5_CUBE_PROGRAMMER_EXE `
    -Candidates @(
        "D:\Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe",
        "$Env:ProgramFiles\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe",
        "${Env:ProgramFiles(x86)}\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"
    ) `
    -CommandName "STM32_Programmer_CLI.exe"

$cubeProgrammer = Require-File $cubeProgrammer "STM32CubeProgrammer CLI"
$ImagePath = Require-File $ImagePath "Firmware image"

$logPath = Join-Path $BuildDir "flash.log"

if ($PSCmdlet.ShouldProcess($ImagePath, "Program and verify STM32 over SWD")) {
    # This command intentionally avoids option-byte changes and mass erase.
    Invoke-LoggedProcess `
        -Executable $cubeProgrammer `
        -Arguments @("-c", "port=SWD", "-w", $ImagePath, "-v", "-rst") `
        -LogPath $logPath
}

Write-Host "Flash command completed. Log: $logPath"
