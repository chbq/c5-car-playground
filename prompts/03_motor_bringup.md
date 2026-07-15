# Codex Task: Four Independent Motor Bring-up

Prerequisites:

- the chassis is physically raised;
- the user has confirmed it is safe to rotate the wheels;
- each candidate PWM and direction channel has evidence;
- a bounded motor test API exists;
- automatic stop is implemented.

Test exactly one wheel channel at a time. Begin at low duty and short duration.
Verify physical position and direction. Record any mismatch rather than
changing multiple signs at once.

Do not introduce mecanum kinematics, PID, RTOS changes, or C25 code in this
task.
