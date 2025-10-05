# AIcast Room - Deployment Guide

**Version:** 2.0 (MCF Enhanced)  
**Last Updated:** 2025-01-04  
**Status:** 🎖️ Production Ready

---

## 🚀 Quick Deployment

### 1. Local Development Setup

```bash
# Clone repository
git clone https://github.com/your-repo/aicast-app.git
cd aicast-app

# Install dependencies
pip3 install -r requirements.txt

# Setup Google Cloud authentication
gcloud auth application-default login --no-launch-browser

# Start application
python3 run.py
```

### 2. Production Deployment (Sakura VPS)

```bash
# Connect to server
ssh user@your-server-ip

# Navigate to project directory
cd /home/user/aicast-app

# Pull latest changes
git pull origin main

# Restart application
screen -S aicast -X quit
sleep 2
screen -dmS aicast bash -c 'python3 run.py'

# Verify deployment
curl http://localhost:8501
```

---

## 🛠️ Environment Setup

### Required Environment Variables

```bash
# Google Cloud Project
export GCP_PROJECT="aicast-472807"

# MCF Configuration (Optional - uses defaults if not set)
export MCF_CLOUD_FUNCTIONS_URL="https://asia-northeast1-aicast-472807.cloudfunctions.net/x-poster"

# Database Configuration (Optional)
export DATABASE_PATH="casting_office.db"

# Streamlit Configuration
export STREAMLIT_SERVER_PORT=8501
export STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

### Python Dependencies

```txt
streamlit>=1.28.0
pandas>=2.0.0
google-cloud-aiplatform>=1.34.0
google-auth>=2.17.0
vertexai>=0.0.1
gspread>=5.10.0
google-auth-oauthlib>=1.0.0
requests>=2.31.0
```

---

## 🔧 Configuration Files

### 1. Streamlit Config (`.streamlit/config.toml`)

```toml
[server]
port = 8501
address = "0.0.0.0"
enableCORS = false
enableXsrfProtection = false

[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"

[browser]
gatherUsageStats = false
```

### 2. Google Cloud Authentication

Place your service account key at:
```
credentials/service-account-key.json
```

For OAuth (Google Sheets):
```
credentials/credentials.json
credentials/token.pickle
```

---

## 🐳 Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p .streamlit credentials

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  aicast-room:
    build: .
    ports:
      - "8501:8501"
    environment:
      - GCP_PROJECT=aicast-472807
      - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account-key.json
    volumes:
      - ./credentials:/app/credentials:ro
      - ./casting_office.db:/app/casting_office.db
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Build and Run

```bash
# Build image
docker build -t aicast-room:latest .

# Run container
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop container
docker-compose down
```

---

## 🌐 Cloud Deployment Options

### 1. Google Cloud Run

```bash
# Build and deploy to Cloud Run
gcloud builds submit --tag gcr.io/aicast-472807/aicast-room
gcloud run deploy aicast-room \
  --image gcr.io/aicast-472807/aicast-room \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --port 8501 \
  --memory 2Gi \
  --cpu 1
```

### 2. Streamlit Cloud

1. Connect GitHub repository to Streamlit Cloud
2. Set up secrets in Streamlit Cloud dashboard:
   - `GCP_PROJECT`
   - `GOOGLE_APPLICATION_CREDENTIALS` (paste JSON content)
3. Deploy automatically from main branch

### 3. Heroku

```bash
# Install Heroku CLI
heroku create aicast-room

# Set config vars
heroku config:set GCP_PROJECT=aicast-472807
heroku config:set STREAMLIT_SERVER_PORT=$PORT

# Deploy
git push heroku main
```

---

## 🔒 Security Configuration

### 1. Environment Security

```bash
# Set proper file permissions
chmod 600 credentials/*
chmod 644 *.py
chmod 755 *.sh

# Secure database
chmod 600 casting_office.db
```

### 2. Network Security

```bash
# Configure firewall (Ubuntu/Debian)
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8501/tcp  # Streamlit

# For production, use reverse proxy
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
```

### 3. SSL/TLS Setup (Nginx Reverse Proxy)

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/private.key;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 📊 Monitoring & Maintenance

### 1. Application Monitoring

```bash
# Check application status
curl -f http://localhost:8501/_stcore/health

# View logs
tail -f app.log

# Monitor resource usage
htop
df -h
free -h
```

### 2. Database Maintenance

```bash
# Backup database
cp casting_office.db "backup_$(date +%Y%m%d_%H%M%S).db"

# Vacuum database (optimize)
sqlite3 casting_office.db "VACUUM;"

# Check database integrity
sqlite3 casting_office.db "PRAGMA integrity_check;"
```

### 3. Log Rotation

```bash
# Setup logrotate
sudo tee /etc/logrotate.d/aicast-room > /dev/null <<EOF
/home/user/aicast-app/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 user user
}
EOF
```

---

## 🚨 Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   sudo netstat -tlnp | grep 8501
   sudo kill -9 <PID>
   ```

2. **Authentication errors**
   ```bash
   gcloud auth application-default login --no-launch-browser
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   ```

3. **Database locked**
   ```bash
   # Find and kill processes using the database
   fuser casting_office.db
   kill -9 <PID>
   ```

4. **Memory issues**
   ```bash
   # Monitor memory usage
   free -h
   # Restart application
   screen -S aicast -X quit && screen -dmS aicast bash -c 'python3 run.py'
   ```

### Health Check Script

```bash
#!/bin/bash
# health_check.sh

APP_URL="http://localhost:8501"
LOG_FILE="health_check.log"

echo "$(date): Starting health check..." >> $LOG_FILE

# Check if application is responding
if curl -f --silent --max-time 10 $APP_URL/_stcore/health > /dev/null 2>&1; then
    echo "$(date): ✅ Application is healthy" >> $LOG_FILE
else
    echo "$(date): ❌ Application is unhealthy, restarting..." >> $LOG_FILE
    screen -S aicast -X quit
    sleep 5
    screen -dmS aicast bash -c 'python3 run.py'
fi
```

### Automated Deployment Script

```bash
#!/bin/bash
# deploy.sh

set -e

echo "🚀 Starting AIcast Room deployment..."

# Backup current version
if [ -f "app.py" ]; then
    cp app.py "app.py.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Pull latest changes
git pull origin main

# Install/update dependencies
pip3 install -r requirements.txt

# Restart application
screen -S aicast -X quit || true
sleep 2
screen -dmS aicast bash -c 'python3 run.py'

# Wait and verify
sleep 10
if curl -f --silent http://localhost:8501/_stcore/health > /dev/null; then
    echo "✅ Deployment successful!"
    echo "🌐 Application available at: http://localhost:8501"
else
    echo "❌ Deployment failed - application not responding"
    exit 1
fi
```

---

## 📈 Performance Optimization

### 1. Application Optimization

- Use `@st.cache_data` for expensive computations
- Implement database connection pooling
- Optimize database queries with indexes
- Use lazy loading for large datasets

### 2. System Optimization

```bash
# Increase file descriptor limits
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# Optimize Python for production
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1
```

### 3. Database Optimization

```sql
-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_posts_cast_id ON posts(cast_id);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);
CREATE INDEX IF NOT EXISTS idx_casts_name ON casts(name);
```

---

## 🔄 Backup & Recovery

### 1. Automated Backup

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/home/user/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
cp casting_office.db "$BACKUP_DIR/db_$DATE.db"

# Backup credentials
tar -czf "$BACKUP_DIR/credentials_$DATE.tar.gz" credentials/

# Backup configuration
cp -r .streamlit "$BACKUP_DIR/streamlit_config_$DATE"

# Clean old backups (keep 30 days)
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

### 2. Recovery Procedure

```bash
# Stop application
screen -S aicast -X quit

# Restore database
cp backup_YYYYMMDD_HHMMSS.db casting_office.db

# Restore credentials
tar -xzf credentials_YYYYMMDD_HHMMSS.tar.gz

# Restart application
python3 run.py
```

---

## 📞 Support & Resources

- **Documentation:** `/docs` directory
- **MCF Baseline:** `docs/MCF_BASELINE.md`
- **X API Guide:** `docs/X_API_IMPLEMENTATION_GUIDE.md`
- **Logs:** `app.log`, `schedule.log`, `retweet.log`
- **Health Check:** `http://localhost:8501/_stcore/health`

---

**🎖️ Remember: Always validate MCF settings before production deployment!**