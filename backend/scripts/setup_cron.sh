SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CRON_JOB="0 */4 * * * cd $SCRIPT_DIR && /home/ec2-user/miniconda3/bin/python fetch_papers.py --days 2 >> ../logs/cron_fetch.log 2>&1"

(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "Cron job has been set up successfully!"
