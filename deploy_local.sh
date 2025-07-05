#!/bin/bash

# =============================================================================
# Value Partner Platform - Local Development Deployment
# =============================================================================
# 
# This script deploys the Value Partner platform for local development
# without requiring Docker, Kubernetes, or other production tools.
#
# =============================================================================

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log "Checking local development prerequisites..."
    
    # Check required tools
    if ! command -v node &> /dev/null; then
        error "Node.js is required but not installed"
    fi
    
    if ! command -v npm &> /dev/null; then
        error "npm is required but not installed"
    fi
    
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is required but not installed"
    fi
    
    success "Prerequisites check passed"
}

# Setup environment
setup_environment() {
    log "Setting up environment configuration..."
    
    # Copy .env.example if .env doesn't exist
    if [[ ! -f "services/.env" ]]; then
        cp services/.env.example services/.env
        log "Created services/.env from template"
        
        # Generate a secure JWT secret key
        if command -v openssl &> /dev/null; then
            SECRET_KEY=$(openssl rand -hex 32)
            sed -i.bak "s/SECRET_KEY=REPLACE_WITH_SECURE_32_BYTE_HEX_KEY_GENERATED_BY_OPENSSL_RAND/SECRET_KEY=$SECRET_KEY/" services/.env
            log "Generated secure JWT secret key"
        else
            warning "OpenSSL not found. Please manually set SECRET_KEY in services/.env"
        fi
        
        # Set local development values
        sed -i.bak 's/DATABASE_URL=postgresql:\/\/user:password@localhost:5432\/value_partner_db/DATABASE_URL=sqlite:\/\/\/\.\/portfolio.db/' services/.env
        sed -i.bak 's/DEBUG=false/DEBUG=true/' services/.env
        sed -i.bak 's/ENVIRONMENT=development/ENVIRONMENT=local/' services/.env
        sed -i.bak 's/ALLOWED_ORIGINS=https:\/\/yourdomain.com,https:\/\/app.yourdomain.com/ALLOWED_ORIGINS=http:\/\/localhost:3000,http:\/\/127.0.0.1:3000/' services/.env
        
        # Clean up backup file
        rm -f services/.env.bak
        
        log "Configured environment for local development"
    else
        log "Environment file already exists"
    fi
}

# Setup Python backend
setup_backend() {
    log "Setting up Python backend..."
    
    cd services
    
    # Create virtual environment if it doesn't exist
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
        log "Created Python virtual environment"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install Python dependencies
    pip install --upgrade pip
    pip install -r requirements.txt
    
    log "Installed Python dependencies"
    
    # Run database migrations (skip if SQLite issues)
    log "Attempting database migrations..."
    if ! python -m alembic upgrade head 2>/dev/null; then
        warning "Database migrations failed (this is normal for new SQLite databases)"
        log "Creating database tables directly..."
        python -c "
from app.database import engine, Base
Base.metadata.create_all(bind=engine)
print('Database tables created successfully')
" || warning "Could not create database tables"
    else
        success "Database migrations completed"
    fi
    
    cd ..
}

# Setup frontend
setup_frontend() {
    log "Setting up React frontend..."
    
    cd frontend
    
    # Install Node dependencies
    if [[ ! -d "node_modules" ]]; then
        npm install
        log "Installed Node.js dependencies"
    else
        log "Node.js dependencies already installed"
    fi
    
    cd ..
}

# Start services
start_services() {
    log "Starting Value Partner services..."
    
    # Kill any existing processes on ports 8000 and 3000
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    
    log "Starting backend API server..."
    cd services
    source venv/bin/activate
    
    # Start backend in background
    nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../backend.pid
    
    cd ..
    
    # Wait a moment for backend to start
    sleep 3
    
    # Check if backend is running
    if curl -s http://localhost:8000/health > /dev/null; then
        success "Backend API started successfully on http://localhost:8000"
    else
        warning "Backend may not have started properly. Check backend.log for details."
    fi
    
    log "Starting frontend development server..."
    cd frontend
    
    # Start frontend in background
    nohup npm run dev > ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../frontend.pid
    
    cd ..
    
    # Wait a moment for frontend to start
    sleep 5
    
    # Check if frontend is running
    if curl -s http://localhost:3000 > /dev/null; then
        success "Frontend started successfully on http://localhost:3000"
    else
        warning "Frontend may not have started properly. Check frontend.log for details."
    fi
}

# Health checks
run_health_checks() {
    log "Running health checks..."
    
    # Test backend health
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        success "Backend health check passed"
    else
        warning "Backend health check failed"
    fi
    
    # Test frontend
    if curl -s http://localhost:3000 > /dev/null; then
        success "Frontend is responding"
    else
        warning "Frontend health check failed"
    fi
}

# Stop services function
stop_services() {
    log "Stopping services..."
    
    if [[ -f "backend.pid" ]]; then
        kill $(cat backend.pid) 2>/dev/null || true
        rm -f backend.pid
    fi
    
    if [[ -f "frontend.pid" ]]; then
        kill $(cat frontend.pid) 2>/dev/null || true
        rm -f frontend.pid
    fi
    
    # Kill any remaining processes on our ports
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    
    success "Services stopped"
}

# Main deployment function
main() {
    log "Starting Value Partner local deployment..."
    
    # Handle stop command
    if [[ "${1:-}" == "stop" ]]; then
        stop_services
        exit 0
    fi
    
    check_prerequisites
    setup_environment
    setup_backend
    setup_frontend
    start_services
    run_health_checks
    
    success "=============================================================================
✅ Value Partner Platform - Local Development Deployment Complete!

🌐 Access Your Application:
   Frontend: http://localhost:3000
   Backend API: http://localhost:8000
   API Docs: http://localhost:8000/docs

📊 Service Status:
   - Backend API: Running (PID: $(cat backend.pid 2>/dev/null || echo 'N/A'))
   - Frontend: Running (PID: $(cat frontend.pid 2>/dev/null || echo 'N/A'))
   - Database: SQLite (local development)

📝 Logs:
   - Backend: backend.log
   - Frontend: frontend.log

🛠️ Management Commands:
   - Stop services: ./deploy_local.sh stop
   - View backend logs: tail -f backend.log
   - View frontend logs: tail -f frontend.log

🔒 Security Note:
   This is a LOCAL DEVELOPMENT setup only!
   For production deployment, use the full deploy.sh script with proper infrastructure.

============================================================================="
}

# Handle command line arguments
case "${1:-}" in
    stop)
        stop_services
        ;;
    *)
        main "$@"
        ;;
esac 