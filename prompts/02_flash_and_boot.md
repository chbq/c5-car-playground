# Codex Task: Explicit Flash and Boot Check

Prerequisite: the minimal target builds with zero errors and motor outputs are
documented to remain inactive at startup.

Review the exact image path and programmer command first. Use
`tools/flash.ps1` only with its explicit confirmation switch. Do not change
option bytes or protection settings.

After programming and verification, reset the board and collect the diagnostic
UART boot output. Record observed facts separately from expectations.

No motor output is permitted in this task.
