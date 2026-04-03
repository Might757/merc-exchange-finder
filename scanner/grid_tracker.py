"""
grid_tracker.py — Persists which grid cells have already been scanned,
so a resumed scan picks up where it left off rather than starting over.

State is saved to a JSON file on disk after every cell.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

_DEFAULT_STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scan_state.json",
)


@dataclass
class GridState:
    cols: int
    rows: int
    scanned: list[list[bool]] = field(default_factory=list)   # scanned[row][col]
    current_row: int = 0
    current_col: int = 0

    def __post_init__(self):
        if not self.scanned:
            self.scanned = [[False] * self.cols for _ in range(self.rows)]

    def mark(self, row: int, col: int):
        self.scanned[row][col] = True

    def is_scanned(self, row: int, col: int) -> bool:
        return self.scanned[row][col]

    def total_cells(self) -> int:
        return self.cols * self.rows

    def scanned_count(self) -> int:
        return sum(self.scanned[r][c] for r in range(self.rows) for c in range(self.cols))

    def next_unscanned(self) -> Optional[tuple[int, int]]:
        """Return (row, col) of the next unscanned cell in raster order, or None if done."""
        for row in range(self.rows):
            for col in range(self.cols):
                if not self.scanned[row][col]:
                    return row, col
        return None

    def is_complete(self) -> bool:
        return self.next_unscanned() is None


class GridTracker:
    """
    Manages scan state persistence. Loads existing state from disk if it
    matches the current grid dimensions; starts fresh otherwise.
    """

    def __init__(self, cols: int, rows: int, state_file: str = _DEFAULT_STATE_FILE):
        self._state_file = state_file
        self._state = self._load_or_create(cols, rows)

    def _load_or_create(self, cols: int, rows: int) -> GridState:
        if os.path.exists(self._state_file):
            try:
                with open(self._state_file, "r") as f:
                    data = json.load(f)
                state = GridState(
                    cols=data["cols"],
                    rows=data["rows"],
                    scanned=data["scanned"],
                    current_row=data.get("current_row", 0),
                    current_col=data.get("current_col", 0),
                )
                if state.cols == cols and state.rows == rows:
                    done = state.scanned_count()
                    total = state.total_cells()
                    print(f"[grid_tracker] Resuming scan: {done}/{total} cells already scanned.")
                    return state
                else:
                    print(f"[grid_tracker] Grid size changed ({state.cols}x{state.rows} → {cols}x{rows}). Starting fresh.")
            except Exception as e:
                print(f"[grid_tracker] Could not load state ({e}). Starting fresh.")

        return GridState(cols=cols, rows=rows)

    def save(self):
        with open(self._state_file, "w") as f:
            json.dump(asdict(self._state), f, indent=2)

    def mark_scanned(self, row: int, col: int):
        self._state.mark(row, col)
        self._state.current_row = row
        self._state.current_col = col
        self.save()

    def is_scanned(self, row: int, col: int) -> bool:
        return self._state.is_scanned(row, col)

    def is_complete(self) -> bool:
        return self._state.is_complete()

    def progress(self) -> tuple[int, int]:
        """Return (scanned_count, total_cells)."""
        return self._state.scanned_count(), self._state.total_cells()

    def reset(self):
        """Clear scan state and delete the state file."""
        if os.path.exists(self._state_file):
            os.remove(self._state_file)
        cols, rows = self._state.cols, self._state.rows
        self._state = GridState(cols=cols, rows=rows)
        print("[grid_tracker] Scan state reset.")

    @property
    def state(self) -> GridState:
        return self._state
