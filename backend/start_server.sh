mkdir -p logs

touch logs/output.log

# redirect output to log file
echo "Starting backend server with nohup..."
nohup /home/ec2-user/miniconda3/envs/pmo311/bin/python run.py > logs/output.log 2>&1 &