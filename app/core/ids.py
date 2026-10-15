"""Snowflake-style 63-bit ID generator (41-bit ms timestamp | 10-bit node | 12-bit sequence)."""
import threading
import time

_EPOCH_MS = 1_735_689_600_000  # 2025-01-01T00:00:00Z
_NODE_BITS, _SEQ_BITS = 10, 12
_SEQ_MASK = (1 << _SEQ_BITS) - 1


class SnowflakeGenerator:
    def __init__(self, node_id: int = 0):
        if not 0 <= node_id < (1 << _NODE_BITS):
            raise ValueError("node_id out of range")
        self._node = node_id
        self._lock = threading.Lock()
        self._last_ms = -1
        self._seq = 0

    def next_id(self) -> int:
        with self._lock:
            now = int(time.time() * 1000)
            now = max(now, self._last_ms)  # tolerate small clock regressions
            if now == self._last_ms:
                self._seq = (self._seq + 1) & _SEQ_MASK
                if self._seq == 0:  # sequence exhausted, wait for next ms
                    while now <= self._last_ms:
                        now = int(time.time() * 1000)
            else:
                self._seq = 0
            self._last_ms = now
            return ((now - _EPOCH_MS) << (_NODE_BITS + _SEQ_BITS)) | (self._node << _SEQ_BITS) | self._seq


_generator = SnowflakeGenerator()


def new_id() -> int:
    return _generator.next_id()
