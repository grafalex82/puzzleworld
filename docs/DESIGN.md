# Puzzle World design

## Product vocabulary

- **Puzzle definition**: pure rules for one puzzle family. It creates and validates states, applies commands, and recognizes solved states.
- **Board state**: an immutable ordered collection of pieces for one puzzle.
- **Piece**: an immutable `ColorId` and optional orientation. Its kind comes from the board position.
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

## TriLotica rules

TriLotica has two circles whose centers are one radius apart. Three copies of the right circle around the left center, separated by 120 degrees, define three small lenses. The intersections with the left circle, after those lenses are removed, define three curved triangular pieces. The left turn cycles the three lens slots and three triangle slots independently by 120 degrees. The bridge group in the right disk consists of two lenses and one triangle; its half turn swaps those slots with their three right-side counterparts. No TriLotica piece has logical orientation, so a right half turn is its own inverse in the model. The two remaining right-disk triangles are renderer-only decorative paths and rotate during its animation.

## TriLotica v2 rules

TriLotica v2 has two equal turnable disks whose centres, and whose three left-disk auxiliary-circle centres, are `50/60 R` from the left centre. Their common intersection is an added central triangle. The two auxiliary circles on either side of the right centre form one of three large truncated lenses carried by the left disk; each is cut out of a large triangle. The three ordinary lenses, three large truncated lenses, and three cut-out triangles each cycle by 120 degrees with the left disk. The right half-turn swaps its two lenses and triangle with their three opposing slots, and also carries the central left triangle into its green partner on the right.

## Double TriLotica and Triple TriLotica rules

Double TriLotica adds two of TriLotica's right disks around the same central disk,
and Triple TriLotica adds all three, at 120-degree intervals. The central disk keeps
TriLotica's six alternating lens and curved-triangle slots and turns by 120 degrees.
Each outer disk makes a 180-degree turn, swapping its lens/triangle/lens bridge with
its three corresponding outer slots. The curved triangles are solid, flat pieces;
the reference object's cut-outs are intentionally not modeled.

## Lemons rules

Lemons has a large disk of diameter 80 and a small right disk of diameter 50. Their centres are 40 units apart. Six copies of the large circle, at 60-degree intervals around the small-disk centre, divide the small disk into twelve alternating lens and triangle elements. Five of those elements lie in the large disk. Quarter-turn copies of that five-element region make the upper, left, and lower groups; the remaining central cross is decorative only.

The large disk turns by 90 degrees and cycles each of its five elements through the right, lower, left, and upper group positions. The small disk turns by 60 degrees, cycling its twelve elements in two independent shape-family rings. Pieces have no orientation. A completed puzzle has all twelve yellow pieces in the small disk and a uniform red, green, and blue group in the other three positions, in any order.

## Domain invariants

1. States and commands are immutable.
2. A state always contains exactly nine Looper positions with a valid color inventory.
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
