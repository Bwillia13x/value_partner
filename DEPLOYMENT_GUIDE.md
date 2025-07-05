# Value Partner Platform - Deployment Guide

## 🚀 Quick Start - Local Development

### Prerequisites
- Node.js (v16 or higher)
- npm
- Python 3.8+
- Git

### 1. Clone and Deploy Locally
```bash
git clone <repository-url>
cd value_partner
./deploy_local.sh
```

The local deployment script will:
- ✅ Check prerequisites
- ✅ Set up environment configuration
- ✅ Install Python dependencies
- ✅ Set up database (SQLite for local development)
- ✅ Install frontend dependencies
- ✅ Start both backend and frontend services

### 2. Access Your Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### 3. Stop Services
```bash
./deploy_local.sh stop
```

## 📋 Deployment Options

### Option 1: Local Development (Recommended for Testing)
- **Use**: `./deploy_local.sh`
- **Database**: SQLite
- **Environment**: Development
- **Requirements**: Node.js, Python, npm

### Option 2: Production Deployment
- **Use**: `./deploy.sh`
- **Database**: PostgreSQL
- **Environment**: Production
- **Requirements**: Docker, Kubernetes, Terraform, Helm

### Option 3: Cloud Deployment

#### AWS ECS + RDS
```bash
# Set environment variables
export AWS_REGION=us-east-1
export ENVIRONMENT=production

# Deploy infrastructure
./deploy.sh --environment production
```

#### Vercel (Frontend) + Railway (Backend)
```bash
# Frontend to Vercel
cd frontend
vercel deploy

# Backend to Railway
cd services
railway deploy
```

#### Heroku
```bash
# Backend
cd services
heroku create value-partner-api
git push heroku main

# Frontend
cd frontend
heroku create value-partner-app
git push heroku main
```

## 🔧 Configuration

### Environment Variables
Copy `services/.env.example` to `services/.env` and configure:

#### Critical Security Settings
```bash
# Generate with: openssl rand -hex 32
SECRET_KEY=your_secure_32_byte_hex_key

# Restrict to your actual domains
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Enable for production
CSRF_PROTECTION_ENABLED=true
DEBUG=false
TESTING=false
```

#### Database Configuration
```bash
# Production (PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost:5432/value_partner_db

# Development (SQLite)
DATABASE_URL=sqlite:///./portfolio.db
```

#### Third-Party Integrations
```bash
# Plaid (Financial Data)
PLAID_CLIENT_ID=your_plaid_client_id
PLAID_SECRET=your_plaid_secret_key
PLAID_ENV=sandbox  # or 'production'
PLAID_WEBHOOK_SECRET=your_webhook_secret

# Alpaca (Trading)
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # or production URL

# Market Data
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key

# Email Notifications
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PASSWORD=your_sendgrid_api_key

# Redis (Sessions & Caching)
REDIS_URL=redis://localhost:6379/0
```

## 🛠️ Manual Setup (Alternative to Scripts)

### Backend Setup
```bash
cd services

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up database
cp .env.example .env
# Edit .env with your configuration

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Or build for production
npm run build
npm start
```

## 🔒 Security Checklist

### Pre-Deployment Security
- [ ] Generate secure JWT secret key
- [ ] Configure CORS for your domains only
- [ ] Enable CSRF protection
- [ ] Set up webhook signature verification
- [ ] Configure SSL certificates
- [ ] Set DEBUG=false in production

### Post-Deployment Verification
```bash
# Test authentication
curl -H "Authorization: Bearer invalid_token" https://your-api.com/api/portfolio

# Test CORS protection
curl -H "Origin: https://malicious-site.com" https://your-api.com/api/health

# Test CSRF protection
curl -X POST https://your-api.com/api/portfolio/rebalance

# Test webhook security
curl -X POST https://your-api.com/webhooks/plaid -d '{"test": "data"}'
```

## 📊 Database Setup

### SQLite (Local Development)
- Automatically created by the deployment script
- Located at `services/portfolio.db`
- Suitable for development and testing only

### PostgreSQL (Production)
```bash
# Install PostgreSQL
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql

# Create database
sudo -u postgres createdb value_partner_db
sudo -u postgres createuser --interactive

# Update DATABASE_URL in .env
DATABASE_URL=postgresql://username:password@localhost:5432/value_partner_db

# Run migrations
cd services
source venv/bin/activate
alembic upgrade head
```

## 🏗️ Infrastructure as Code

### Terraform (AWS)
```bash
cd infra

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var="environment=production"

# Apply infrastructure
terraform apply
```

### Kubernetes Deployment
```bash
# Deploy with Helm
helm upgrade --install value-partner-api \
    ./infra/helm/value-investing-api \
    --namespace value-partner \
    --create-namespace \
    --set environment=production
```

## 📈 Monitoring & Observability

### Health Checks
- **Basic**: http://localhost:8000/health
- **Detailed**: http://localhost:8000/health/detailed
- **Performance**: http://localhost:8000/admin/performance

### Logging
```bash
# View backend logs
tail -f backend.log

# View frontend logs
tail -f frontend.log

# View specific service logs
docker logs value-partner-api
```

### Error Tracking
Configure Sentry for production error tracking:
```bash
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

## 🔄 CI/CD Pipeline

### GitHub Actions
The platform includes automated CI/CD with:
- Automated testing
- Security scanning
- Docker image building
- Deployment to staging/production

### Manual Deployment
```bash
# Build and tag Docker images
docker build -t value-partner-api:latest services/

# Push to registry
docker tag value-partner-api:latest your-registry/value-partner-api:latest
docker push your-registry/value-partner-api:latest

# Deploy to Kubernetes
kubectl apply -f k8s/
```

## 🚨 Troubleshooting

### Common Issues

#### Backend Won't Start
```bash
# Check logs
tail -f backend.log

# Verify dependencies
cd services && source venv/bin/activate
pip install -r requirements.txt

# Test import
python -c "from app.main import app; print('Import successful')"
```

#### Database Connection Issues
```bash
# Test database connection
cd services && source venv/bin/activate
python -c "
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Database connection successful')
"
```

#### Frontend Build Errors
```bash
cd frontend

# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Fix ESLint errors
npm run lint -- --fix

# Build with verbose output
npm run build -- --verbose
```

#### Port Already in Use
```bash
# Find and kill processes
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9

# Or use different ports
uvicorn app.main:app --port 8001
npm run dev -- --port 3001
```

### Performance Issues
```bash
# Check system resources
htop
df -h

# Monitor database performance
# PostgreSQL
SELECT * FROM pg_stat_activity;

# Check Redis performance
redis-cli info memory
```

## 📞 Support

### Development Support
- View logs: `tail -f backend.log` or `tail -f frontend.log`
- Check health: http://localhost:8000/health/detailed
- API documentation: http://localhost:8000/docs

### Production Support
- 24/7 monitoring and alerting
- Automated backups and disaster recovery
- Performance monitoring and optimization
- Security incident response

### Getting Help
1. Check the logs for error messages
2. Verify environment configuration
3. Test database and service connectivity
4. Review the security and deployment guide
5. Check GitHub issues for known problems

---

**Last Updated**: 2025-07-04  
**Version**: 1.0  
**Status**: Production Ready 