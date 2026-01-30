#!/bin/bash
# Complete Cleanup and Fix for Alembic Migration Issue
# Run this ON THE SERVER

set -e

echo "🔧 Alembic Migration Fix Script"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Check git commit
echo -e "${YELLOW}Step 1: Checking git status...${NC}"
cd ~/development/new-langchain-api
CURRENT_COMMIT=$(git log --oneline -1 | awk '{print $1}')
echo "Current commit: $CURRENT_COMMIT"

if [ "$CURRENT_COMMIT" != "8d995bf" ]; then
    echo -e "${RED}❌ Not on correct commit! Pulling latest...${NC}"
    git pull origin development
else
    echo -e "${GREEN}✅ On correct commit${NC}"
fi

echo ""

# 1.5 Fix Database Connection Settings (Critical for SASL Error)
echo -e "${YELLOW}Step 1.5: Fixing database connection settings...${NC}"
python3 << 'PYTHON_SCRIPT'
import os
from urllib.parse import urlparse

def update_env_file(filepath, updates):
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            lines = f.readlines()
    else:
        lines = []
    
    existing_keys = {}
    for i, line in enumerate(lines):
        if '=' in line and not line.strip().startswith('#'):
            k = line.split('=')[0].strip()
            existing_keys[k] = i
            
    with open(filepath, 'w') as f:
        # Write existing lines, updating if needed
        for i, line in enumerate(lines):
            if '=' in line and not line.strip().startswith('#'):
                k = line.split('=')[0].strip()
                if k in updates:
                    f.write(f"{k}={updates[k]}\n")
                    del updates[k]
                else:
                    f.write(line)
            else:
                f.write(line)
        
        # Append new keys
        if updates:
            f.write("\n# Added by fix script\n")
            for k, v in updates.items():
                f.write(f"{k}={v}\n")

# Read .env
env_vars = {}
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                parts = line.strip().split('=', 1)
                env_vars[parts[0]] = parts[1]

db_url = env_vars.get('DATABASE_URL')
if db_url:
    # Handle quotes if present
    db_url = db_url.strip("'").strip('"')
    
    try:
        # Parse connection string
        parsed = urlparse(db_url)
        username = parsed.username
        password = parsed.password
        hostname = parsed.hostname
        port = parsed.port
        path = parsed.path.lstrip('/')
        
        print(f"Detected DB settings - User: {username}, Host: {hostname}, DB: {path}")

        if not password:
            print("❌ Password not found in DATABASE_URL")
        else:
            # 1. Update .env with DB_* vars for PgBouncer to use backend connection
            env_updates = {
                'DB_HOST': hostname,
                'DB_PORT': str(port) if port else '5432',
                'DB_USER': username,
                'DB_PASSWORD': password,
                'DB_NAME': path
            }
            update_env_file('.env', env_updates)
            print("✅ Updated .env with DB credentials")

            # 2. Update/Create .env.docker with DATABASE_URL pointing to pgbouncer
            # We MUST use the SAME password so PgBouncer auth matches
            docker_db_url = f"postgresql://{username}:{password}@pgbouncer:5432/{path}"
            
            update_env_file('.env.docker', {'DATABASE_URL': docker_db_url})
            print("✅ Updated .env.docker with pgbouncer connection string")
        
    except Exception as e:
        print(f"❌ Error parsing DATABASE_URL: {e}")
else:
    print("❌ DATABASE_URL not found in .env")
PYTHON_SCRIPT

# 2. Verify file content
echo -e "${YELLOW}Step 2: Verifying migration file...${NC}"
REVISION=$(grep "^revision = " alembic/versions/20251223_add_updated_at_api_keys.py | cut -d'"' -f2)
echo "Found revision: $REVISION"

if [ "$REVISION" != "20251223_add_updated_at_api_keys" ]; then
    echo -e "${RED}❌ File still has wrong revision ID!${NC}"
    echo "Expected: 20251223_add_updated_at_api_keys"
    echo "Got: $REVISION"
    exit 1
else
    echo -e "${GREEN}✅ File has correct revision ID${NC}"
fi

echo ""

# 3. Remove Python cache
echo -e "${YELLOW}Step 3: Removing Python cache files...${NC}"
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo -e "${GREEN}✅ Cache cleared${NC}"

echo ""

# 4. Stop Docker
echo -e "${YELLOW}Step 4: Stopping Docker containers...${NC}"
docker compose -f docker-compose.traefik.yml --env-file .env.docker down
echo -e "${GREEN}✅ Containers stopped${NC}"

echo ""

# 5. Remove Docker images
echo -e "${YELLOW}Step 5: Removing Docker images...${NC}"
docker rmi new-langchain-api-app -f 2>/dev/null || echo "Image not found, continuing..."
docker rmi $(docker images -f "dangling=true" -q) -f 2>/dev/null || echo "No dangling images"
docker image prune -f
echo -e "${GREEN}✅ Images removed${NC}"

echo ""

# 6. Check database migration state
echo -e "${YELLOW}Step 6: Checking database migration state...${NC}"
source .venv/bin/activate
pip install psycopg2-binary -q 2>/dev/null || true

# Get current migration from database
DB_VERSION=$(python3 << 'PYTHON_SCRIPT'
import os
try:
    import psycopg2
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    cur = conn.cursor()
    cur.execute("SELECT version_num FROM alembic_version;")
    version = cur.fetchone()
    if version:
        print(version[0])
    else:
        print("NONE")
    cur.close()
    conn.close()
except Exception as e:
    print(f"ERROR: {e}")
PYTHON_SCRIPT
)

echo "Database current migration: $DB_VERSION"

if [ "$DB_VERSION" = "add_updated_at_api_keys" ]; then
    echo -e "${YELLOW}⚠️  Database has OLD revision ID! Fixing...${NC}"
    python3 << 'PYTHON_FIX'
import os
import psycopg2
conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
cur = conn.cursor()
cur.execute("UPDATE alembic_version SET version_num = '20251223_add_updated_at_api_keys' WHERE version_num = 'add_updated_at_api_keys';")
conn.commit()
print("✅ Updated database migration version")
cur.close()
conn.close()
PYTHON_FIX
fi

echo ""

# 7. Rebuild Docker
echo -e "${YELLOW}Step 7: Rebuilding Docker (this may take a while)...${NC}"
docker compose -f docker-compose.traefik.yml --env-file .env.docker build --no-cache --pull

echo ""

# 8. Start Docker
echo -e "${YELLOW}Step 8: Starting Docker containers...${NC}"
docker compose -f docker-compose.traefik.yml --env-file .env.docker up -d

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✨ Fix completed!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Monitoring logs (Ctrl+C to exit)..."
sleep 3
docker logs new-langchain-api-app-1 -f
