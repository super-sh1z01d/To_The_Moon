#!/bin/bash

# Migration Verification Script
# Compares old and new servers to ensure successful migration

set -e

OLD_SERVER="5.129.247.78"
NEW_SERVER="67.213.119.189"

echo "🔍 Verifying migration from $OLD_SERVER to $NEW_SERVER"

echo ""
echo "📊 Checking database record counts..."

echo "Old server token count:"
ssh root@$OLD_SERVER "cd /srv/tothemoon && source venv/bin/activate && python3 -c \"
from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
with SessionLocal() as sess:
    repo = TokensRepository(sess)
    print(f'Active: {len(repo.list_by_status(\"active\", limit=10000))}')
    print(f'Monitoring: {len(repo.list_by_status(\"monitoring\", limit=10000))}')
    print(f'Archived: {len(repo.list_by_status(\"archived\", limit=10000))}')
\""

echo ""
echo "New server token count:"
ssh root@$NEW_SERVER "cd /srv/tothemoon && source venv/bin/activate && python3 -c \"
from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository
with SessionLocal() as sess:
    repo = TokensRepository(sess)
    print(f'Active: {len(repo.list_by_status(\"active\", limit=10000))}')
    print(f'Monitoring: {len(repo.list_by_status(\"monitoring\", limit=10000))}')
    print(f'Archived: {len(repo.list_by_status(\"archived\", limit=10000))}')
\""

echo ""
echo "🌐 Checking API endpoints..."

echo "Old server health:"
curl -s "http://$OLD_SERVER/health" | jq '.' || echo "Failed"

echo ""
echo "New server health:"
curl -s "http://$NEW_SERVER/health" | jq '.' || echo "Failed"

echo ""
echo "Old server tokens (first 3):"
curl -s "http://$OLD_SERVER/tokens?limit=3" | jq '.items[] | {mint_address: .mint_address[:20], score, status}' || echo "Failed"

echo ""
echo "New server tokens (first 3):"
curl -s "http://$NEW_SERVER/tokens?limit=3" | jq '.items[] | {mint_address: .mint_address[:20], score, status}' || echo "Failed"

echo ""
echo "🔧 Checking services..."

echo "Old server service status:"
ssh root@$OLD_SERVER "systemctl is-active tothemoon.service" || echo "Not running"

echo "New server service status:"
ssh root@$NEW_SERVER "systemctl is-active tothemoon.service" || echo "Not running"

echo ""
echo "📈 Checking system resources..."

echo "Old server resources:"
ssh root@$OLD_SERVER "echo 'CPU:' && top -bn1 | grep 'Cpu(s)' && echo 'Memory:' && free -h | grep Mem"

echo ""
echo "New server resources:"
ssh root@$NEW_SERVER "echo 'CPU:' && top -bn1 | grep 'Cpu(s)' && echo 'Memory:' && free -h | grep Mem"

echo ""
echo "✅ Verification completed!"
echo ""
echo "🎯 If all checks pass:"
echo "1. Update DNS: tothemoon.sh1z01d.ru -> $NEW_SERVER"
echo "2. Wait for DNS propagation (5-30 minutes)"
echo "3. Test with domain name"
echo "4. Shutdown old server: ssh root@$OLD_SERVER 'shutdown -h now'"