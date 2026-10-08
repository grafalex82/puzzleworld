# Puzzle World design

## Product vocabulary

- **Puzzle definition**: pure rules for one puzzle family. It creates and validates states, applies commands, and recognizes solved states.
- **Board state**: an immutable ordered collection of pieces for one puzzle.
- **Piece**: an immutable identity, `ColorId`, kind, and optional orientation.
- **Turn command**: an immutable request containing a puzzle id, circle index, and direction.
- **Session**: application state around a puzzle: mode, history, move count, dirty state, and solving lifecycle.
- **Scramble**: a reproducible scenario that applies generated turns without adding them to user history, then starts a solving game.
- **Transition**: the immutable before/after pair returned by the session for UI animation. Animation never drives domain state.

## Looper rules

Looper has nine colored positions arranged from left to right. Even positions contain five small lens/diamond pieces with an up/down marker. Odd positions contain four large vertical pieces without orientation. The solved colors are paired from left to right: red, orange, yellow, green, and blue, with the two outer colors represented by only one of the two piece kinds.

Three overlapping circles are indexed `0`, `1`, and `2`. They affect positions `0..4`, `2..6`, and `4..8` respectively. A 180-degree turn reverses the five positions in that window and flips every oriented small piece. Clockwise and counter-clockwise commands are retained as distinct input intent for future puzzles, although they produce the same Looper half-turn.

The gray triangular gaps shown in the physical puzzle are decorative. They can participate in visual animation but never occur in the logical state.

The Looper renderer derives every boundary from equal circles of radius `R`. Adjacent movable-circle centers are separated by `0.8R`, which is 40 percent of the diameter. A small piece is the intersection of circles separated by `1.6R`. A large piece is an adjacent-circle intersection with its two small side lenses removed. The remaining top and bottom regions complete each movable circle as two gray pieces. Consequently, each animated circle is exactly tiled by three small pieces, two large pieces, and two gray pieces; their rigid rotation is clipped to that circle.

## Super Looper rules

Super Looper also has three circles, but adjacent movable-circle centers are separated by `0.56R`, or 28 percent of a circle diameter. Its board has 15 logical colored pieces. A lens is the intersection of circles separated by three basic offsets. An oriented vertical piece is an intersection separated by two offsets with the two neighboring lenses removed. A diamond is a single logical piece drawn as an inseparable upper/lower pair: it starts as an intersection separated by one offset and has three lenses and two vertical pieces removed.

Each circle rotates four lenses, three vertical pieces, and two diamonds. The two gray triangular remnants are renderer-only paths that rotate with their circle. A 180-degree turn reverses that circle's nine logical positions atomically and flips only vertical-piece orientation.

## Hyper Looper rules

Hyper Looper has three circles offset by 22 percent of their diameter. Its 22 colored logical pieces comprise seven oriented lenses, six unoriented vertical pieces, five oriented large diamond pairs, and four unoriented small diamond pairs. The final lens is light gray. A large or small diamond always remains an inseparable upper/lower pair in the renderer and model.

A lens is an intersection of circles separated by four basic offsets. A vertical is an intersection separated by three offsets with two lenses removed. A large diamond pair is an intersection separated by two offsets with three lenses and two verticals removed. A small diamond pair is an intersection separated by one offset with four lenses, three verticals, and two large diamond pairs removed.

Each circle rotates five lenses, four verticals, three large diamonds, and two small diamonds. The two gray triangular remnants are renderer-only paths that rotate with the circle. A 180-degree turn atomically follows the geometric half-turn permutation and flips only the lens and large-diamond orientations.

## Domain invariants

1. States and commands are immutable.
2. A state always contains exactly nine uniquely identified Looper pieces.
3. Slot kind is stable: small pieces occupy even slots and large pieces occupy odd slots.
4. Only small pieces have an orientation; large pieces never do.
5. Applying a command is atomic and deterministic.
6. Every accepted command has an inverse. For Looper, applying either half-turn twice restores the exact state.
7. Solved means exact equality with the definition's canonical solved state, including small-piece orientation.
8. Random scrambles accept an explicit seed and never write into user undo history.
9. A failed validation or load leaves the live session unchanged.
10. Domain colors use the bounded `ColorId` enum. Concrete display values belong only to renderers.

## Session rules

`FREE_PLAY` starts solved, has no scored move count, and never raises a victory event. `SOLVING` starts only after a scramble. Manual moves and redo increment its count; undo decrements it without going below zero. Reaching solved state ends the active scored game and records the final count.

History is a linear sequence plus a cursor. A new command after undo truncates the redo suffix. Undo returns an inverse command and moves the cursor backward; redo returns the original command and moves it forward. Both are applied through the same transition path as normal turns.

Reset, puzzle replacement, or loading a save ends any current scored game. History is deliberately not persisted and is cleared after loading.

## Architecture and extension points

```text
game/domain             shared immutable values and puzzle protocols
game/puzzles/<id>       one puzzle's pure model; UI renderer is separate
game/application        session, history, and seeded scramble orchestration
game/input              UI-event-to-application-command mapping only
game/persistence        validated versioned JSON and separate app settings
game/ui                 Qt windows, camera, hit testing, rendering, animation
```

The puzzle registry resolves a stable `puzzle_id` to a domain definition. The renderer registry independently resolves the same id to a renderer. Looper and Super Looper use these extension points; their model and renderer files remain puzzle-specific while `GameSession`, history, persistence envelope, and `GameWindow` stay shared.

The domain imports no Qt, filesystem, clock, or rendering module. Persistence can convert a session snapshot to JSON, but filesystem I/O never occurs in the session. UI invokes public session methods and consumes returned transitions; it never mutates pieces or arrays.

## Rendering and animation

The board uses logical coordinates transformed by a camera. Fit scale reserves ten percent margin. Geometry is cached per viewport/camera revision. A stable state is rendered from the session snapshot. For a transition, the model has already advanced; the renderer interpolates affected pieces from the transition's before state to its after positions. Input that could create a conflicting move is disabled until the indivisible animation ends.

## Save compatibility

Saves use an explicit format name and integer version. A loader validates the entire document, including puzzle-specific state, before returning a replacement snapshot. Unknown versions are rejected. Writes use a temporary sibling file followed by atomic replacement. See `SAVE_FORMAT.md`.
