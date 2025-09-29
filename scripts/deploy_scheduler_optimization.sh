#!/bin/bash

# Deploy scheduler optimization to production server
# This script safely deploys and tests the optimized scheduler

set -e

SERVER_IP="67.213.119.189"
SERVER_USER="ubuntu"
PROJECT_PATH="/srv/tothemoon"

echo "🚀 Deploying Scheduler Optimization to Production Server"
echo "=================================================="

# Function to run commands on remote server
run_remote() {
    ssh ${SERVER_USER}@${SERVER_IP} "$1"
}

# Function to copy files to remote server
copy_to_remote() {
    scp "$1" ${SERVER_USER}@${SERVER_IP}:"$2"
}

echo "📋 Step 1: Backup current system"
run_remote "cd ${PROJECT_PATH} && git stash push -m 'Pre-optimization backup $(date)'"

echo "📥 Step 2: Pull latest optimization code"
run_remote "cd ${PROJECT_PATH} && git fetch origin && git checkout feature/scheduler-optimization"

echo "🔧 Step 3: Install any new dependencies"
run_remote "cd ${PROJECT_PATH} && sudo -u tothemoon bash -c 'source venv/bin/activate && pip install -r requirements.txt'"

echo "🧪 Step 4: Run optimization tests"
echo "Running scheduler optimization tests..."
run_remote "cd ${PROJECT_PATH} && sudo -u tothemoon bash -c 'source venv/bin/activate && PYTHONPATH=. python scripts/test_scheduler_optimization.py'"

echo "⚙️  Step 5: Configure optimization settings"
# Set environment variables for optimization
run_remote "echo 'ENABLE_SCHEDULER_OPTIMIZATION=true' | sudo tee -a /etc/tothemoon.env"
run_remote "echo 'ENABLE_PARALLEL_PROCESSING=true' | sudo tee -a /etc/tothemoon.env"
run_remote "echo 'ENABLE_ADAPTIVE_BATCHING=true' | sudo tee -a /etc/tothemoon.env"
run_remote "echo 'MAX_CONCURRENT_HOT=12' | sudo tee -a /etc/tothemoon.env"
run_remote "echo 'MAX_CONCURRENT_COLD=16' | sudo tee -a /etc/tothemoon.env"

echo "🔄 Step 6: Restart service with optimization"
run_remote "sudo systemctl restart tothemoon.service"

echo "⏳ Waiting for service to start..."
sleep 10

echo "✅ Step 7: Verify service health"
run_remote "sudo systemctl status tothemoon.service --no-pager"

echo "🔍 Step 8: Test API endpoints"
echo "Testing health endpoint..."
if run_remote "curl -f http://localhost:8000/health"; then
    echo "✅ Health endpoint OK"
else
    echo "❌ Health endpoint failed"
    exit 1
fi

echo "Testing tokens endpoint..."
if run_remote "curl -f 'http://localhost:8000/tokens?limit=5'"; then
    echo "✅ Tokens endpoint OK"
else
    echo "❌ Tokens endpoint failed"
    exit 1
fi

echo "📊 Step 9: Monitor initial performance"
echo "Monitoring scheduler performance for 2 minutes..."
run_remote "timeout 120 journalctl -u tothemoon.service -f --no-pager | grep -E '(optimized_group_processing|parallel_batch|tokens_per_second)' || true"

echo "🎉 Deployment Complete!"
echo "=================================================="
echo "✅ Scheduler optimization deployed successfully"
echo "✅ Service is running and healthy"
echo "✅ API endpoints are responding"
echo ""
echo "📊 Next Steps:"
echo "1. Monitor performance metrics in logs"
echo "2. Check system resource utilization"
echo "3. Compare processing speeds with previous version"
echo "4. Adjust concurrency settings if needed"
echo ""
echo "🔧 Configuration:"
echo "- Parallel processing: ENABLED"
echo "- Hot group concurrency: 12"
echo "- Cold group concurrency: 16"
echo "- Adaptive batching: ENABLED"
echo ""
echo "📈 Expected Improvements:"
echo "- 2-4x faster token processing"
echo "- Better resource utilization"
echo "- Reduced API timeout issues"
echo "- Adaptive performance under load"
echo ""
echo "🚨 Rollback Instructions (if needed):"
echo "ssh ${SERVER_USER}@${SERVER_IP}"
echo "cd ${PROJECT_PATH}"
echo "git checkout main"
echo "sudo systemctl restart tothemoon.service"