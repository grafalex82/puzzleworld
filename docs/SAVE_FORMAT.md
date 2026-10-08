# Save format

Puzzle World saves are UTF-8 JSON. Version 1 has this shape:

```json
{
  "format": "puzzle-world-save",
  "version": 1,
  "puzzle_id": "looper",
  "mode": "solving",
  "solving_active": true,
  "move_count": 7,
  "final_move_count": null,
  "board": {
    "pieces": [
      {"color": "red", "orientation": "up"}
    ]
  }
}
```

All documented fields are required. `final_move_count` is either a non-negative integer or `null`. Additional top-level, board, or piece fields are rejected so corrupt or incompatible data cannot be silently accepted.

Pieces have no identity beyond their position, color, and optional orientation. Looper position determines the piece geometry: using one-based numbering, odd positions are small and even positions are large. Color values are stable identifiers from the domain `ColorId` enum, never renderer-specific RGB or HEX values. Small pieces store `up` or `down`; large pieces store `null` orientation.

History and scramble provenance (difficulty, generated turns, and seed) are intentionally not saved. After loading, undo and redo are empty. `format` prevents unrelated JSON from being mistaken for a save; `version` controls future migrations. During pre-release development the compact schema remains version 1. Unknown versions are rejected instead of guessed.

The writer creates a temporary file in the destination directory, flushes it to disk, and then atomically replaces the target. If serialization or replacement fails, the pre-existing target remains unchanged whenever the operating system provides atomic replacement semantics.
