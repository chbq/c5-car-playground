"""Thread-safe local runtime state; UART transport lives in motion_link.py."""

import threading
from enum import Enum


class SystemState(Enum):
    IDLE = "IDLE"
    INFERENCE = "INFERENCE"


class StateManager:
    def __init__(self):
        self._state = SystemState.IDLE
        self._lock = threading.Lock()

    @property
    def state(self) -> SystemState:
        with self._lock:
            return self._state

    @state.setter
    def state(self, new_state: SystemState):
        if not isinstance(new_state, SystemState):
            raise ValueError("new_state must be a SystemState")
        with self._lock:
            old = self._state
            if old != new_state:
                self._state = new_state
                print(f"[状态] {old.value} → {new_state.value}")

    def is_idle(self) -> bool:
        return self.state == SystemState.IDLE

    def is_inference(self) -> bool:
        return self.state == SystemState.INFERENCE
