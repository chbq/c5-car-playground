# Host-side tests

Add serial protocol tests here only after the diagnostic protocol is defined.

Recommended future files:

- `requirements.txt`
- `serial_smoke_test.py`
- `scenarios/boot.json`
- `scenarios/motor_single_wheel.json`

Hardware tests must never issue unbounded motor commands.
