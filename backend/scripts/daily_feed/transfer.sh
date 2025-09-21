#!/bin/bash

LOGFILE="./transfer.log"

# Get the current day of the week (1=Monday, 7=Sunday)
DAY_OF_WEEK=$(date +%u)

# Check if it's weekend (Saturday=6, Sunday=7)
if [ $DAY_OF_WEEK -eq 6 ] || [ $DAY_OF_WEEK -eq 7 ]; then
    echo "[$(date '+%F %T')] 今天是周末，不执行传输任务。" >> "$LOGFILE"
    exit 0
fi

echo "[$(date '+%F %T')] 开始执行传输任务…" >> "$LOGFILE"

# If it's Monday, calculate last Friday's date and construct filename
if [ $DAY_OF_WEEK -eq 1 ]; then
    # Get last Friday's date (3 days ago from Monday)
    LAST_FRIDAY=$(date -d "last Friday" +%Y-%m-%d)
    NEXT_DAY=$(date -d "$LAST_FRIDAY + 1 day" +%Y-%m-%d)
    FILENAME="$LAST_FRIDAY-$NEXT_DAY.json"
else
    # Tuesday to Friday - use yesterday's date
    YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
    TODAY=$(date +%Y-%m-%d)
    FILENAME="$YESTERDAY-$TODAY.json"
fi

echo "[$(date '+%F %T')] 传输文件: $FILENAME" >> "$LOGFILE"

rsync -avz -e "ssh -i /home/zx283/.ssh/ipapers.ai.key.pem" ec2-user@100.25.52.216:/home/ec2-user/PMo/backend/scripts/daily_feed/data/$FILENAME /home/zx283/2025summer/PMo/backend/scripts/daily_feed/data

echo "[$(date '+%F %T')] 传输任务完成。" >> "$LOGFILE"