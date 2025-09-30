# Deployment Guide

## Overview

This guide covers deployment options for the LangChain Agent API in different environments.

## Table of Contents

1. [Development Setup](#development-setup)
2. [Docker Deployment](#docker-deployment)
3. [Production Deployment](#production-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Environment Configuration](#environment-configuration)
6. [Monitoring and Logging](#monitoring-and-logging)
7. [Security Considerations](#security-considerations)
8. [Scaling and Performance](#scaling-and-performance)

## Development Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Node.js (for frontend development)

### Local Development

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd Langchain-API-new
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Database setup**
   ```bash
   createdb langchain_api
   alembic upgrade head
   ```

4. **Run services**
   ```bash
   # Start Redis
   redis-server

   # Start application
   uvicorn app.main:app --reload
   ```

## Docker Deployment

### Development with Docker

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production with Docker

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Scale services
docker-compose -f docker-compose.prod.yml up -d --scale app=3
```

## Production Deployment

### System Requirements

- **CPU**: 4+ cores
- **Memory**: 8GB+ RAM
- **Storage**: 50GB+ SSD
- **Database**: PostgreSQL 15+
- **Cache**: Redis 7+

### Environment Setup

1. **Create production .env file**
   ```bash
   cp .env.example .env.prod
   # Edit .env.prod with production values
   ```

2. **Database setup**
   ```bash
   # Create production database
   createdb langchain_api_prod

   # Run migrations
   DATABASE_URL=postgresql://user:pass@prod-db:5432/langchain_api_prod alembic upgrade head
   ```

3. **SSL/TLS Certificates**
   ```bash
   # Obtain SSL certificates
   sudo certbot certonly --standalone -d your-domain.com

   # Copy certificates to ssl directory
   sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./ssl/
   sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./ssl/
   ```

### Systemd Service

Create `/etc/systemd/system/langchain-api.service`:

```ini
[Unit]
Description=LangChain Agent API
After=network.target

[Service]
Type=exec
User=app
Group=app
WorkingDirectory=/opt/langchain-api
Environment=PATH=/opt/langchain-api/venv/bin
ExecStart=/opt/langchain-api/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl enable langchain-api
sudo systemctl start langchain-api
```

## Cloud Deployment

### AWS Deployment

#### Using ECS

1. **Create ECR repository**
   ```bash
   aws ecr create-repository --repository-name langchain-api
   ```

2. **Build and push Docker image**
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
   docker build -t langchain-api .
   docker tag langchain-api:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/langchain-api:latest
   docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/langchain-api:latest
   ```

3. **Create ECS task definition**
   ```json
   {
     "family": "langchain-api",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "1024",
     "memory": "2048",
     "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
     "containerDefinitions": [
       {
         "name": "langchain-api",
         "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/langchain-api:latest",
         "portMappings": [
           {
             "containerPort": 8000,
             "protocol": "tcp"
           }
         ],
         "environment": [
           {
             "name": "DATABASE_URL",
             "value": "postgresql://user:password@rds-endpoint:5432/langchain_api"
           },
           {
             "name": "REDIS_URL",
             "value": "redis://redis-endpoint:6379/0"
           }
         ],
         "logConfiguration": {
           "logDriver": "awslogs",
           "options": {
             "awslogs-group": "/ecs/langchain-api",
             "awslogs-region": "us-east-1",
             "awslogs-stream-prefix": "ecs"
           }
         }
       }
     ]
   }
   ```

#### Using RDS and ElastiCache

```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier langchain-api-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username postgres \
  --master-user-password password \
  --allocated-storage 20 \
  --db-name langchain_api

# Create ElastiCache cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id langchain-api-redis \
  --engine redis \
  --cache-node-type cache.t2.micro \
  --num-cache-nodes 1
```

### Google Cloud Deployment

#### Using Cloud Run

1. **Build and push to GCR**
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/langchain-api
   ```

2. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy langchain-api \
     --image gcr.io/PROJECT_ID/langchain-api \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

#### Using Cloud SQL and Memorystore

```bash
# Create Cloud SQL instance
gcloud sql instances create langchain-api-db \
  --database-version=POSTGRES_15 \
  --tier=db-custom-1-3840 \
  --region=us-central1

# Create Memorystore instance
gcloud redis instances create langchain-api-redis \
  --tier=standard \
  --size=1 \
  --region=us-central1
```

### Azure Deployment

#### Using Container Instances

```bash
# Create resource group
az group create --name langchain-api-rg --location eastus

# Create container instance
az container create \
  --resource-group langchain-api-rg \
  --name langchain-api \
  --image your-registry/langchain-api:latest \
  --dns-name-label langchain-api-unique \
  --ports 8000
```

## Environment Configuration

### Production Environment Variables

```bash
# Security
SECRET_KEY=your-very-secure-secret-key-here
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:secure-password@db:5432/langchain_api_prod

# Redis
REDIS_URL=redis://redis:6379/0

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://your-domain.com/api/v1/auth/google/callback

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# CORS
BACKEND_CORS_ORIGINS=https://your-frontend.com,https://admin.your-domain.com

# Performance
MAX_CONCURRENT_AGENTS=10000
AGENT_EXECUTION_TIMEOUT=300
```

### Database Configuration

```sql
-- Production PostgreSQL configuration
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
```

## Monitoring and Logging

### Application Monitoring

1. **Prometheus and Grafana**
   ```bash
   # Install Prometheus
   docker run -d -p 9090:9090 prom/prometheus

   # Install Grafana
   docker run -d -p 3000:3000 grafana/grafana
   ```

2. **Application Metrics**
   ```python
   from prometheus_client import Counter, Histogram, Gauge

   REQUEST_COUNT = Counter('app_requests_total', 'Total requests')
   REQUEST_DURATION = Histogram('app_request_duration_seconds', 'Request duration')
   ACTIVE_AGENTS = Gauge('app_active_agents', 'Number of active agents')
   ```

### Log Aggregation

1. **ELK Stack**
   ```yaml
   # docker-compose.elk.yml
   version: '3.8'
   services:
     elasticsearch:
       image: docker.elastic.co/elasticsearch/elasticsearch:8.8.0
       environment:
         - discovery.type=single-node
         - xpack.security.enabled=false
       ports:
         - "9200:9200"

     logstash:
       image: docker.elastic.co/logstash/logstash:8.8.0
       volumes:
         - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
       ports:
         - "5000:5000"

     kibana:
       image: docker.elastic.co/kibana/kibana:8.8.0
       ports:
         - "5601:5601"
   ```

2. **Logstash Configuration**
   ```conf
   input {
     tcp {
       port => 5000
       codec => json
     }
   }

   filter {
     date {
       match => [ "timestamp", "ISO8601" ]
     }
   }

   output {
     elasticsearch {
       hosts => ["elasticsearch:9200"]
       index => "langchain-api-%{+YYYY.MM.dd}"
     }
   }
   ```

### Health Checks

```python
from fastapi import HTTPException
from sqlalchemy import text
from app.core.database import get_db

@app.get("/health")
async def health_check():
    try:
        # Check database
        db = next(get_db())
        db.execute(text("SELECT 1"))

        # Check Redis
        redis_client.ping()

        return {
            "status": "healthy",
            "database": "connected",
            "redis": "connected"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Security Considerations

### Network Security

1. **Firewall Configuration**
   ```bash
   # UFW configuration
   sudo ufw allow 22/tcp      # SSH
   sudo ufw allow 80/tcp      # HTTP
   sudo ufw allow 443/tcp     # HTTPS
   sudo ufw deny 8000/tcp     # Direct API access
   sudo ufw enable
   ```

2. **Nginx Security Headers**
   ```nginx
   add_header X-Frame-Options "SAMEORIGIN" always;
   add_header X-Content-Type-Options "nosniff" always;
   add_header X-XSS-Protection "1; mode=block" always;
   add_header Referrer-Policy "strict-origin-when-cross-origin" always;
   add_header Content-Security-Policy "default-src 'self'" always;
   ```

### Application Security

1. **Environment Variables**
   ```bash
   # Secure environment file
   chmod 600 .env.prod

   # Use secrets management
   # AWS Secrets Manager, Azure Key Vault, or Google Secret Manager
   ```

2. **Database Security**
   ```sql
   -- Create limited user for application
   CREATE USER langchain_app WITH PASSWORD 'secure_password';
   GRANT CONNECT ON DATABASE langchain_api TO langchain_app;
   GRANT USAGE ON SCHEMA public TO langchain_app;
   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO langchain_app;
   GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO langchain_app;
   ```

3. **Rate Limiting**
   ```python
   from slowapi import Limiter
   from slowapi.util import get_remote_address

   limiter = Limiter(key_func=get_remote_address)

   @app.get("/api/v1/agents")
   @limiter.limit("10/minute")
   async def get_agents(request: Request):
       pass
   ```

## Scaling and Performance

### Horizontal Scaling

1. **Load Balancer Configuration**
   ```nginx
   upstream langchain_api {
       server app1:8000;
       server app2:8000;
       server app3:8000;
   }

   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://langchain_api;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

2. **Database Scaling**
   ```sql
   -- Read replica setup
   CREATE USER replica_user WITH PASSWORD 'replica_password';
   GRANT CONNECT ON DATABASE langchain_api TO replica_user;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO replica_user;
   ```

### Performance Optimization

1. **Database Optimization**
   ```sql
   -- Add indexes for frequently queried columns
   CREATE INDEX idx_agents_user_id ON agents(user_id);
   CREATE INDEX idx_executions_agent_id ON executions(agent_id);
   CREATE INDEX idx_executions_status ON executions(status);
   CREATE INDEX idx_embeddings_agent_id ON embeddings(agent_id);

   -- Partition large tables
   CREATE TABLE executions_y2023 PARTITION OF executions
       FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');
   ```

2. **Caching Strategy**
   ```python
   import redis
   from fastapi_cache import FastAPICache
   from fastapi_cache.backends.redis import RedisBackend

   @app.on_event("startup")
   async def startup():
       redis = aioredis.from_url("redis://localhost:6379")
       FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")

   @app.get("/api/v1/tools")
   @cache(expire=300)
   async def get_tools():
       return await tool_service.get_tools()
   ```

3. **Connection Pooling**
   ```python
   from sqlalchemy import create_engine
   from sqlalchemy.pool import QueuePool

   engine = create_engine(
       DATABASE_URL,
       poolclass=QueuePool,
       pool_size=20,
       max_overflow=30,
       pool_timeout=30,
       pool_recycle=3600
   )
   ```

## Backup and Recovery

### Database Backup

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="langchain_api_prod"

pg_dump -h localhost -U postgres -d $DB_NAME | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# Keep last 30 days of backups
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete
```

### Disaster Recovery

1. **Automated Backup**
   ```yaml
   # Kubernetes CronJob
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: db-backup
   spec:
     schedule: "0 2 * * *"
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: backup
               image: postgres:15
               command: ["pg_dump"]
               args: ["-h", "db", "-U", "postgres", "langchain_api"]
             restartPolicy: OnFailure
   ```

2. **Restore Procedure**
   ```bash
   # Stop application
   docker-compose down

   # Restore database
   gunzip -c /backups/db_backup_20231201_020000.sql.gz | psql -h localhost -U postgres -d langchain_api_prod

   # Start application
   docker-compose up -d
   ```

This deployment guide provides comprehensive instructions for deploying the LangChain Agent API in various environments, from local development to production cloud deployments.