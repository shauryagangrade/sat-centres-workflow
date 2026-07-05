# VHS Tape — sat-centres-workflow demo GIF
# Run with: vhs docs/media/demo.tape
# Output:   docs/media/demo.gif

Output docs/media/demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 1100
Set Height 600
Set Theme "Dracula"
Set TypingSpeed 40ms
Set Padding 16

# ── Banner ─────────────────────────────────────────────────────────────────
Type "# SAT Centre Updater — live demo"
Sleep 600ms
Enter
Sleep 400ms

# ── Step 1: show help ──────────────────────────────────────────────────────
Type "python main.py --help"
Sleep 500ms
Enter
Sleep 2500ms

# ── Step 2: normalize ─────────────────────────────────────────────────────
Type "python main.py --normalize"
Sleep 500ms
Enter
Sleep 3000ms

# ── Step 3: validate ──────────────────────────────────────────────────────
Type "python main.py --validate"
Sleep 500ms
Enter
Sleep 3000ms

# ── Step 4: generate reports ──────────────────────────────────────────────
Type "python main.py --reports"
Sleep 500ms
Enter
Sleep 3000ms

# ── Step 5: preview summary report ────────────────────────────────────────
Type "cat datasets/sat/reports/summary.md"
Sleep 500ms
Enter
Sleep 3000ms

# ── Hold final frame ──────────────────────────────────────────────────────
Sleep 2000ms
