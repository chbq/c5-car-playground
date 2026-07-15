# Codex Task: Create Minimal C5 Target

Prerequisite: Phase 0 evidence and unresolved questions have been reviewed.

Create the minimal target under `target/c5-firmware/` using the approved
baseline. Configure only verified hardware:

- exact MCU and clock;
- SWD;
- diagnostic UART;
- status LED if confirmed;
- explicit motor-safe startup state.

Keep application code separate from CubeMX-generated code. Implement a boot
banner and fault report, but no motor commands.

Make `tools/generate.ps1` and `tools/build.ps1` pass. Do not flash unless the
user explicitly requests it in the current task.

Update the acceptance checklist and write `build/task-report.md`.
