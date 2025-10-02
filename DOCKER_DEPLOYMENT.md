# Aurora FastAPI - Docker Deployment Guide

## 🐳 Docker Deployment Options

### Option 1: Local Docker Development
```bash
# Build and run locally
docker build -t aurora-fastapi .
docker run -p 8000:8000 --env-file .env aurora-fastapi
```

### Option 2: Docker Compose (Recommended)
```bash
# Copy environment template
cp env.docker.template .env
# Edit .env with your API keys

# Run with docker-compose
docker-compose up -d

# Check logs
docker-compose logs -f aurora-fastapi
```

### Option 3: Cloud Docker Deployment

#### Railway (Docker Support)
```bash
# Push to GitHub with Dockerfile
# Railway auto-detects Docker and deploys
```

#### Render (Docker Support)
```bash
# Connect GitHub repo
# Render auto-detects Dockerfile
# Add environment variables in dashboard
```

#### Fly.io (Docker Native)
```bash
# Install flyctl
flyctl auth login

# Deploy
flyctl launch
flyctl deploy
```

#### Google Cloud Run
```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/aurora-fastapi
gcloud run deploy --image gcr.io/PROJECT_ID/aurora-fastapi
```

#### AWS ECS/Fargate
```bash
# Build and push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin
docker tag aurora-fastapi:latest ECR_URI/aurora-fastapi:latest
docker push ECR_URI/aurora-fastapi:latest
```

## 🚀 Quick Start Commands

### Local Development
```bash
# Build image
docker build -t aurora-fastapi .

# Run container
docker run -p 8000:8000 \
  -e CEREBRAS_API_KEY=your_key \
  -e TWILIO_ACCOUNT_SID=your_sid \
  -e TWILIO_AUTH_TOKEN=your_token \
  -e TWILIO_PHONE_NUMBER=your_number \
  aurora-fastapi
```

### Production Deployment
```bash
# Using docker-compose
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🔧 Docker Benefits for Aurora

✅ **Consistent Environment**: Same setup everywhere
✅ **Easy Scaling**: Run multiple containers
✅ **Isolation**: No dependency conflicts
✅ **Portability**: Deploy anywhere Docker runs
✅ **Version Control**: Tagged images for rollbacks
✅ **Resource Management**: CPU/memory limits
✅ **Health Checks**: Automatic restart on failure

## 📊 Production Considerations

### Resource Limits
```yaml
# In docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 512M
```

### Persistent Storage
```yaml
# Volumes for data persistence
volumes:
  - ./active_calls:/app/active_calls
  - ./call_logs:/app/call_logs
```

### Health Monitoring
```yaml
# Health checks
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/"]
  interval: 30s
  timeout: 10s
  retries: 3
```

## 🌐 Cloud Platform Docker Support

| Platform | Docker Support | Free Tier | Auto-Deploy |
|----------|---------------|-----------|-------------|
| Railway | ✅ Native | $5/month credit | ✅ GitHub |
| Render | ✅ Native | 750 hours/month | ✅ GitHub |
| Fly.io | ✅ Native | 3 small VMs | ✅ CLI |
| Google Cloud Run | ✅ Native | 2M requests/month | ✅ CLI |
| AWS ECS | ✅ Native | 12 months free | ✅ CLI |
| Heroku | ✅ Container | $7/month | ✅ GitHub |

## 🎯 Recommended: Railway + Docker

1. **Push code with Dockerfile to GitHub**
2. **Connect Railway to GitHub repo**
3. **Railway auto-detects Dockerfile**
4. **Add environment variables**
5. **Deploy automatically!**

**Total Cost: $0/month** 🎉
