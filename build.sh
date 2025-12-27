#!/bin/bash -e

CONFIG_FILE="data/config.json"
COURSE_ID="$1"
DEBUG_FLAG=""

# Check for --debug flag
if [[ "$2" == "--debug" ]] || [[ "$3" == "--debug" ]]; then
  DEBUG_FLAG="--debug"
  echo "🔍 Debug mode enabled"
fi

# Get dest_folder from config
dest_folder=$(jq -r ".courses[] | select(.id == \"$COURSE_ID\") | .dest_folder" "$CONFIG_FILE")

echo "=== Building $COURSE_ID ==="
build/build_ma.sh "$COURSE_ID" $DEBUG_FLAG

echo "=== Syncing to $dest_folder ==="
rsync -avz "html/$dest_folder/" "tma_server:/mnt/xlang.me/dist/$dest_folder/"

echo "=== Done ==="
