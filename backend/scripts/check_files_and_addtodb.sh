#!/bin/bash

# Folder to watch
WATCH_DIR="/home/ec2-user/PMo/backend/scripts/pubmed_csvs"

# Python script to call
PYTHON_SCRIPT="/home/ec2-user/PMo/backend/scripts/import_csv_to_database.py"

# Infinite loop
while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Checking for files in $WATCH_DIR"

    # Find CSV files in the folder
    for file in "$WATCH_DIR"/*.csv; do
        # Check if there are no CSV files
        if [ ! -e "$file" ]; then
            continue
        fi

        echo "$(date '+%Y-%m-%d %H:%M:%S') - Processing $file"

        # Run the Python script with the file as argument
        python3 "$PYTHON_SCRIPT" "$file"
        
        # Check if Python script succeeded
        if [ $? -eq 0 ]; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Successfully processed $file, deleting..."
            rm -f "$file"
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Failed to process $file, keeping it for retry."
        fi
    done

    # Wait 5 minutes before checking again
    sleep 300
done
