# Adding a puzzle family

This guide is the implementation contract for a new Puzzle World puzzle family.
Follow it when a puzzle needs its own rules and artwork but must keep the shared
session, history, scramble, save, and window behavior.

## Design the logical puzzle first

Start with a written slot table before drawing geometry. A slot is a stable
position in `BoardState.pieces`; it is not a physical piece identity. For every
slot, record its index, geometric kind, allowed colors, whether it can have an
orientation, and which turns move it. Also record each turn as a permutation of
slot indices and any orientation changes.

Use these rules when designing the model:

- Give the family a permanent, lower-case, hyphenated `puzzle_id`. It is stored
  in saves and settings, so never rename or reuse it after release.
- Keep a canonical solved state. If the puzzle accepts multiple visually valid
  finishes, make that explicit in `is_solved`, as Lemons does for its three outer
  color groups.
- A slot's geometric kind never changes. Validate the color inventory separately
  for every kind, so a lens cannot silently become a triangle just because the
  overall color counts still match.
- Use `ColorId` and, where needed, `Orientation` from `game.domain.state`.
  Add a new domain color only when it is a stable logical color; display values
  belong in `game.puzzles.colors`, never in the model or save data.
- Treat decorative gaps, fixed backgrounds, and renderer-only cut-outs as
  renderer state, not logical pieces. Compound artwork that always moves as one
  piece still has one logical slot.
- Define the exact order and direction of every turn. The renderer animation
  must use the same permutation, center, and angle as the model.

## Implement the domain definition

Create `game/puzzles/<puzzle_id>/` with at least `model.py`, `renderer.py`, and
`__init__.py`. The model implements `PuzzleDefinition` from
`game.domain.rules` and must expose:

```python
puzzle_id: str
display_name: str
circle_count: int

def slot_kind(self, slot: int) -> str: ...
def solved_state(self) -> BoardState: ...
def validate_state(self, state: BoardState) -> None: ...
def apply(self, state: BoardState, command: TurnCommand) -> BoardState: ...
def is_solved(self, state: BoardState) -> bool: ...
```

The model is pure domain code: it must not import Qt, render paths, files,
clocks, randomness, session classes, or persistence code. Build immutable
`BoardState` and `Piece` values and return a new state from `apply`; do not
mutate the input state or its pieces.

`validate_state` is the trust boundary for both moves and loaded saves. It must
reject a non-`BoardState`, the wrong piece count, invalid orientation for every
slot, and an invalid per-kind color inventory. `apply` should validate its input,
reject a command for another puzzle or an out-of-range/non-integer circle with
`DomainError`, construct the result atomically, and validate the result.
`is_solved` should validate before deciding. These checks ensure a bad save or a
failed command cannot leave a partially changed live session.

Represent turns with small, inspectable tables where practical: for example,
one tuple of slots per rotating ring or a source-to-destination permutation.
Copy from the pre-turn tuple and write into a separate list; this prevents a
cycle from overwriting values it still needs. For a directed move, use
`TurnDirection.CLOCKWISE` and `COUNTERCLOCKWISE` consistently. The inverse must
be `command.inverse()`; a half-turn may legitimately have identical results in
both directions, but it must still accept both directions.

## Implement the renderer

The renderer implements `PuzzleRenderer` from `game.ui.renderer`:

```python
@property
def bounds(self) -> QRectF: ...
def shortcut_circles(self) -> tuple[int, ...]: ...
def shortcut_labels(self) -> tuple[str, ...]: ...
def hit_test_circle(self, point: QPointF) -> int | None: ...
def draw(self, painter: QPainter, state: BoardState, hover_circle: int | None) -> None: ...
def draw_transition(
    self, painter: QPainter, transition: MoveTransition,
    progress: float, hover_circle: int | None,
) -> None: ...
```

Keep all Qt geometry, painting, hit testing, palette lookup, and animation in
this module. `bounds` is in logical coordinates and must include the whole
visible puzzle so the shared camera can fit it. `hit_test_circle` must return a
model circle index or `None`; when disks overlap, use a deterministic rule such
as the nearest center. Return at most four shortcut circles, in the desired
`Q`, `W`, `E`, `R` order, and supply one label for each.

`draw` renders a stable state. During `draw_transition`, the domain state has
already advanced: draw unaffected slots from `transition.after`, then clip and
rotate the affected artwork from `transition.before` around the exact physical
turn center. Draw renderer-only decoration in the same transformed layer if it
moves with that disk. The final frame must visually equal `draw(after, ...)`.
Never update model state from paint or animation code.

## Register and document the family

1. Import the definition and renderer in `game/puzzles/registry.py`.
2. Add one `PuzzleDescriptor(puzzle_id, display_name, Definition(), Renderer())`
   to `_DESCRIPTORS`. The registry drives the puzzle menu, session lookup,
   settings validation, save loading, and renderer selection.
3. Add the puzzle to `README.md`: a short player-facing description and, when
   available, a solved screenshot in `docs/screenshots/`.
4. Add its physical rules and logical exceptions to `docs/DESIGN.md`.
5. If the puzzle needs a color not in `ColorId`, add it deliberately and update
   the shared palette. Do not encode RGB/HEX values in state or JSON.

The compact save codec is already puzzle-agnostic. A registered definition that
uses `BoardState`/`Piece` normally needs no codec changes: saves contain only
`puzzle_id` plus ordered `color` and `orientation` values and are validated by
the new model on load. If a puzzle cannot be represented by those values, treat
the proposed schema change as a format-versioning project: specify migration,
strict validation, backwards compatibility, and tests before changing it.

## Implementation algorithm

Use this order to avoid mismatches between rules, geometry, and animation:

1. Assign the permanent id, display name, circle indices, stable slot order, and
   canonical solved-state table.
2. Write each move as a slot permutation plus orientation transform; identify
   its inverse and order.
3. Implement and unit-test the pure model before starting Qt geometry.
4. Build a geometry helper and map every logical slot to exactly one visible
   path or intentional compound path. Identify decoration separately.
5. Implement stable drawing, deterministic hit testing, and shortcut mapping.
6. Implement transition drawing directly from the model's affected slots and
   turn specification.
7. Register the paired model and renderer, then verify selection, a seeded
   scramble, undo/redo, and save/load through the shared application.
8. Add the player-facing entry, rule documentation, and a solved screenshot.

## Required tests and review checklist

Create `tests/domain/test_<puzzle_id>.py` and UI renderer tests following the
nearest existing family. At minimum, cover:

- solved-state validity and each turn's expected permutation;
- the order of every turn (for example, four quarter turns restore the state);
- `command.inverse()` restoring arbitrary representative states;
- orientation changes, if the puzzle has oriented pieces;
- rejected wrong puzzle ids, booleans/non-integers, and invalid circle indices;
- rejection of malformed state inventories and orientations without changing the
  caller's previous state;
- all accepted solved arrangements, including any non-canonical alternatives;
- geometry counts, selected overlap behavior, and representative hit tests;
- a transition frame that proves affected artwork rotates while required fixed
  or decorative artwork remains correct;
- a save/load round trip after at least one move.

Before merging, run `pytest` from the repository root and manually check the
new entry in the Puzzle type menu at more than one window size. Confirm that
free play does not declare victory, a scramble never begins solved, undo/redo
uses the correct directed inverse, loading an invalid save preserves the current
session, and no Qt imports leaked into the model.

## Common mistakes

- Defining slots in a renderer-specific or unstable visual order, then losing
  save compatibility after a geometry refactor.
- Moving only colors in a permutation and forgetting the piece orientation.
- Reading from the destination list while applying a cycle instead of copying
  from the original state.
- Giving every painted fragment a logical slot when several fragments are one
  inseparable piece, or persisting decoration as if it were a piece.
- Letting animation infer affected slots independently of the domain move.
- Adding special cases to `GameSession`, history, input translation, or the
  generic save codec for behavior that belongs to the new definition/renderer.
