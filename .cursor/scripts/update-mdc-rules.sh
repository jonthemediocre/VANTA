#!/bin/bash
# Script to update MDC rules from the Elie222/inbox-zero GitHub repository
# Usage: Run this script from the root of your project
# Example: bash .cursor/scripts/update-mdc-rules.sh

# Ensure the opensource directory exists
MDC_DIR=".cursor/rules/opensource"
mkdir -p "$MDC_DIR"

echo "Fetching MDC rule files list from GitHub..."
FILES=$(curl -s "https://api.github.com/repos/elie222/inbox-zero/git/trees/main?recursive=1" | 
        grep -o '"path":.*".cursor/rules/.*\.mdc"' | 
        cut -d'"' -f4)

if [ -z "$FILES" ]; then
    echo "No MDC files found in the repository. Check the repository structure or your internet connection."
    exit 1
fi

FILE_COUNT=$(echo "$FILES" | wc -l)
echo "Found $FILE_COUNT MDC files. Downloading..."

# Download each file
for FILE_PATH in $FILES; do
    FILE_NAME=$(basename "$FILE_PATH")
    OUTPUT_PATH="$MDC_DIR/$FILE_NAME"
    URL="https://raw.githubusercontent.com/elie222/inbox-zero/main/$FILE_PATH"
    
    echo "Downloading $FILE_NAME..."
    if curl -s "$URL" -o "$OUTPUT_PATH"; then
        echo "  ✓ Downloaded: $FILE_NAME"
    else
        echo "  ✗ Failed to download $FILE_NAME"
    fi
done

echo ""
echo "MDC rules update completed."
echo "Files are located in: $MDC_DIR"
echo "To use these rules, reference them in your code or consult the 700-opensource-mdc.mdc file." 