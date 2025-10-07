#!/bin/bash

# Starting ID
start_id=1029

# Number of files to download at a time
batch_size=20

# Directories
mkdir -p down_xml
mkdir -p unzip_xml
mkdir -p pubmed_parsed_csv

# Paths to scripts
GENERATE_CSV_SCRIPT="/home/sb2957/PMo/backend/scripts/generate_csv.py"
ADD_EMBED_SCRIPT="/home/sb2957/PMo/backend/scripts/add_embeddings_to_csv.py"

# Remote server details
REMOTE_USER="ec2-user"
REMOTE_HOST="100.25.52.216"
REMOTE_DIR="/home/ec2-user/PMo/backend/scripts/pubmed_csvs"

# Log file
LOG_FILE="./pubmed_processing_log.txt"

for ((i=0; i<batch_size; i++)); do
    file_id=$((start_id - i))
    gz_file="pubmed25n${file_id}.xml.gz"
    xml_file="unzip_xml/pubmed25n${file_id}.xml"
    csv_file="pubmed_parsed_csv/pubmed25n${file_id}.csv"
    url="https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/${gz_file}"

    # Download
    if [[ -f "down_xml/$gz_file" ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - $gz_file already exists, skipping download." | tee -a "$LOG_FILE"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Downloading $gz_file ..." | tee -a "$LOG_FILE"
        wget -q --show-progress -P down_xml "$url"
    fi

    # Unzip
    if [[ -f "$xml_file" ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - $xml_file already exists, skipping unzip." | tee -a "$LOG_FILE"
    elif [[ -f "down_xml/$gz_file" ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Unzipping $gz_file ..." | tee -a "$LOG_FILE"
        gunzip -c "down_xml/$gz_file" > "$xml_file"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - $gz_file not found, cannot unzip." | tee -a "$LOG_FILE"
        continue
    fi

    # Generate CSV
    if [[ -f "$csv_file" ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - $csv_file already exists, skipping CSV generation." | tee -a "$LOG_FILE"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Generating CSV from $xml_file ..." | tee -a "$LOG_FILE"
        python "$GENERATE_CSV_SCRIPT" "$xml_file"
    fi

    # Add embeddings
    if [[ -f "$csv_file" ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Adding embeddings to $csv_file ..." | tee -a "$LOG_FILE"
        python "$ADD_EMBED_SCRIPT" "$csv_file"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Finished $csv_file" | tee -a "$LOG_FILE"

        # Move CSV to another AWS server
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Moving $csv_file to $REMOTE_HOST:$REMOTE_DIR ..." | tee -a "$LOG_FILE"
        rsync -avz -e "ssh -i ipapers.ai.key.pem" \
            "$csv_file" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"

        if [[ $? -eq 0 ]]; then
            # Delete CSV, gz, and xml manually
            rm -f "$csv_file"
            rm -f "down_xml/$gz_file"
            rm -f "$xml_file"
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Successfully moved $csv_file and cleaned up local files" | tee -a "$LOG_FILE"
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Failed to move $csv_file" | tee -a "$LOG_FILE"
        fi
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - CSV not found for $xml_file, skipping embeddings." | tee -a "$LOG_FILE"
    fi
    sleep 1800

done

echo "$(date '+%Y-%m-%d %H:%M:%S') - Batch processing complete." | tee -a "$LOG_FILE"
