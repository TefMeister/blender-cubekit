"""run_lines.py - a line drawn on a forge model has no gaps (2026-11-10). Plain Python, no Blender needed:

    python tests/run_lines.py

Found on the home PC on 2026-11-07 as "dotted lines": the scratches, grooves, cracks and raised lines on every forge
gun came out as rows of separate dots. Model._line_q walked each segment in int(length * 4) steps, and a length that is
a hair under a round number in floating point (0.7 - 0.2 is 0.49999999999999994) lost a whole step, so the walk jumped
two quarter cells at once and skipped the one between. The test walks polylines of short segments at awkward offsets
and checks every quarter cell is next to the one before it (side by side or corner to corner). Exit 0 = pass."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import forge  # noqa: E402

NEIGHBOUR = 1            # two cells touch when neither coordinate differs by more than this
OFFSETS = [0.0, 0.1, 0.2, 0.3, 0.45, 0.7, 1.15, 2.3]
SEGMENT = 0.5            # half a cube, the length the home PC's scratches use
SEGMENTS = 8


def polylines():
    for a0 in OFFSETS:
        for b0 in OFFSETS:
            for da, db in ((SEGMENT, 0.0), (0.0, SEGMENT), (SEGMENT, SEGMENT), (SEGMENT, -SEGMENT), (SEGMENT, SEGMENT / 2)):
                yield [(a0 + da * i, b0 + db * i) for i in range(SEGMENTS + 1)]


def gaps(cells):
    return [(p, q) for p, q in zip(cells, cells[1:])
            if abs(p[0] - q[0]) > NEIGHBOUR or abs(p[1] - q[1]) > NEIGHBOUR]


def main():
    model = forge.Model.__new__(forge.Model)      # _line_q uses nothing of the model itself
    lines, bad = 0, []
    for pts in polylines():
        lines += 1
        found = gaps(model._line_q(pts))
        if found:
            bad.append((pts[0], pts[1], found[0]))
    for start, second, gap in bad[:5]:
        print("FAIL  a line from %s through %s jumps from cell %s to %s" % (start, second, gap[0], gap[1]))
    print("lines: %d drawn, %d with a gap" % (lines, len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
