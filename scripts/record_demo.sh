#!/bin/bash
# StateWeave Demo Recorder
# Records the full_demo.py output as a GIF using asciinema + agg
# Usage: bash scripts/record_demo.sh

set -e

echo "🎬 StateWeave Demo Recorder"
echo "=========================="
echo ""

# Check for asciinema
if ! command -v asciinema &> /dev/null; then
    echo "Installing asciinema..."
    brew install asciinema
fi

# Check for agg (asciinema GIF generator)
if ! command -v agg &> /dev/null; then
    echo "Installing agg (GIF converter)..."
    brew install agg
fi

CAST_FILE="/tmp/stateweave_demo.cast"
GIF_FILE="assets/demo.gif"
PYTHON="/usr/local/bin/python3.11"

# Ensure assets directory exists
mkdir -p assets

echo ""
echo "📹 Recording demo..."
echo "   (The demo will run automatically. Just watch!)"
echo ""

# Record the demo non-interactively
asciinema rec "$CAST_FILE" \
    --cols 80 \
    --rows 35 \
    --title "StateWeave v0.3.3 Demo" \
    --command "$PYTHON examples/full_demo.py" \
    --overwrite

echo ""
echo "🎨 Converting to GIF..."

# Convert to GIF with nice styling
agg "$CAST_FILE" "$GIF_FILE" \
    --cols 80 \
    --rows 35 \
    --font-size 16 \
    --theme dracula

echo ""
echo "✅ Done!"
echo "   Cast file: $CAST_FILE"
echo "   GIF file:  $GIF_FILE"
echo ""
echo "📋 Next steps:"
echo "   1. Check the GIF looks good: open $GIF_FILE"
echo "   2. Upload to GitHub (it's already in assets/)"
echo "   3. Post to HN/Reddit with the GIF embedded"
