#!/bin/bash

# Get the current day of the week (1=Monday, 7=Sunday)
DAY_OF_WEEK=$(date +%u)

# Check if it's weekend (Saturday=6, Sunday=7)
if [ $DAY_OF_WEEK -eq 6 ] || [ $DAY_OF_WEEK -eq 7 ]; then
    # It's weekend - do nothing and exit
    exit 0
fi

# It's a weekday (Monday-Friday) - run the script
~/miniconda3/bin/python /home/ec2-user/PMo/backend/scripts/daily_email/send_daily_to_subscribers.py