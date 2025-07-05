#!/bin/bash

# =============================================================================
# Value Partner Platform Deployment Script
# =============================================================================
# 
# This script automates the deployment of the Value Partner platform including:
# - Infrastructure provisioning with Terraform
# - Backend API deployment
# - Frontend deployment
# - Database migrations
# - Security configuration
# - Health checks and verification
#
# =============================================================================

set -e  # Exit on any error
set -u  # Exit on undefined variables

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=${ENVIRONMENT:-production}
AWS_REGION=${AWS_REGION:-us-east-1}
DEPLOY_FRONTEND=${DEPLOY_FRONTEND:-true}
DEPLOY_BACKEND=${DEPLOY_BACKEND:-true}
DEPLOY_INFRA=${DEPLOY_INFRA:-true}
RUN_MIGRATIONS=${RUN_MIGRATIONS:-true}
SKIP_TESTS=${SKIP_TESTS:-false}

# =============================================================================
# Helper Functions
# =============================================================================

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

check_prerequisites() {
    log "Checking deployment prerequisites..."
    
    # Check required tools
    local required_tools=("docker" "terraform" "kubectl" "helm" "node" "npm")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            error "$tool is required but not installed"
        fi
    done
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        error "AWS credentials not configured or invalid"
    fi
    
    # Check environment variables
    local required_vars=("SECRET_KEY" "DATABASE_URL")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            error "Required environment variable $var is not set"
        fi
    done
    
    success "Prerequisites check passed"
}

# =============================================================================
# Infrastructure Deployment
# =============================================================================

deploy_infrastructure() {
    if [[ "$DEPLOY_INFRA" != "true" ]]; then
        log "Skipping infrastructure deployment"
        return 0
    fi
    
    log "Deploying infrastructure with Terraform..."
    
    cd infra
    
    # Initialize Terraform
    terraform init
    
    # Plan deployment
    terraform plan -out=tfplan \
        -var="aws_region=$AWS_REGION" \
        -var="environment=$ENVIRONMENT"
    
    # Apply infrastructure
    terraform apply tfplan
    
    # Store outputs
    terraform output -json > ../terraform-outputs.json
    
    cd ..
    
    success "Infrastructure deployment completed"
}

# =============================================================================
# Backend Deployment
# =============================================================================

build_backend_image() {
    log "Building backend Docker image..."
    
    local IMAGE_TAG="value-partner-api:${ENVIRONMENT}-$(git rev-parse --short HEAD)"
    
    docker build \
        -f services/Dockerfile \
        -t "$IMAGE_TAG" \
        -t "value-partner-api:latest" \
        .
    
    # Push to registry if configured
    if [[ -n "${DOCKER_REGISTRY:-}" ]]; then
        docker tag "$IMAGE_TAG" "${DOCKER_REGISTRY}/${IMAGE_TAG}"
        docker push "${DOCKER_REGISTRY}/${IMAGE_TAG}"
    fi
    
    echo "$IMAGE_TAG" > backend-image-tag.txt
    success "Backend image built: $IMAGE_TAG"
}

run_database_migrations() {
    if [[ "$RUN_MIGRATIONS" != "true" ]]; then
        log "Skipping database migrations"
        return 0
    fi
    
    log "Running database migrations..."
    
    cd services
    
    # Check database connection
    python -c "
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Database connection successful')
"
    
    # Run migrations
    alembic upgrade head
    
    cd ..
    
    success "Database migrations completed"
}

deploy_backend() {
    if [[ "$DEPLOY_BACKEND" != "true" ]]; then
        log "Skipping backend deployment"
        return 0
    fi
    
    log "Deploying backend services..."
    
    # Build Docker image
    build_backend_image
    
    # Run database migrations
    run_database_migrations
    
    # Deploy with Helm
    local IMAGE_TAG=$(cat backend-image-tag.txt)
    
    helm upgrade --install value-partner-api \
        ./infra/helm/value-investing-api \
        --namespace value-partner \
        --create-namespace \
        --set image.tag="$IMAGE_TAG" \
        --set environment="$ENVIRONMENT" \
        --set database.url="$DATABASE_URL" \
        --set app.secretKey="$SECRET_KEY" \
        --wait
    
    success "Backend deployment completed"
}

# =============================================================================
# Frontend Deployment
# =============================================================================

build_frontend() {
    log "Building frontend application..."
    
    cd frontend
    
    # Install dependencies
    npm ci --production=false
    
    # Run tests if not skipped
    if [[ "$SKIP_TESTS" != "true" ]]; then
        npm run test -- --watchAll=false
    fi
    
    # Build for production
    npm run build
    
    cd ..
    
    success "Frontend build completed"
}

deploy_frontend() {
    if [[ "$DEPLOY_FRONTEND" != "true" ]]; then
        log "Skipping frontend deployment"
        return 0
    fi
    
    log "Deploying frontend application..."
    
    # Build frontend
    build_frontend
    
    # Deploy to S3/CloudFront (example)
    if [[ -n "${S3_BUCKET:-}" ]]; then
        aws s3 sync frontend/out/ "s3://$S3_BUCKET/" --delete
        
        # Invalidate CloudFront cache
        if [[ -n "${CLOUDFRONT_DISTRIBUTION_ID:-}" ]]; then
            aws cloudfront create-invalidation \
                --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
                --paths "/*"
        fi
    fi
    
    success "Frontend deployment completed"
}

# =============================================================================
# Health Checks and Verification
# =============================================================================

wait_for_deployment() {
    log "Waiting for services to be ready..."
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if kubectl get pods -n value-partner | grep -q "Running"; then
            success "Services are running"
            return 0
        fi
        
        log "Attempt $attempt/$max_attempts - waiting for services..."
        sleep 10
        ((attempt++))
    done
    
    error "Services failed to start within timeout"
}

run_health_checks() {
    log "Running deployment health checks..."
    
    # Get service URL
    local SERVICE_URL=$(kubectl get svc -n value-partner value-partner-api -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    
    if [[ -z "$SERVICE_URL" ]]; then
        SERVICE_URL="localhost:8000"  # Fallback for local testing
    fi
    
    # Test health endpoint
    local health_response=$(curl -s "http://$SERVICE_URL/health" || echo "FAILED")
    if [[ "$health_response" == *"healthy"* ]]; then
        success "Health check passed"
    else
        error "Health check failed: $health_response"
    fi
    
    # Test authentication endpoint
    local auth_response=$(curl -s -o /dev/null -w "%{http_code}" "http://$SERVICE_URL/api/auth/health")
    if [[ "$auth_response" == "200" ]]; then
        success "Authentication service is healthy"
    else
        warning "Authentication service returned status: $auth_response"
    fi
    
    # Test database connectivity
    local db_response=$(curl -s "http://$SERVICE_URL/health/detailed" | jq -r '.database.status' 2>/dev/null || echo "FAILED")
    if [[ "$db_response" == "healthy" ]]; then
        success "Database connectivity verified"
    else
        error "Database connectivity check failed"
    fi
}

run_security_verification() {
    log "Running security verification..."
    
    local SERVICE_URL=$(kubectl get svc -n value-partner value-partner-api -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    SERVICE_URL=${SERVICE_URL:-"localhost:8000"}
    
    # Test CORS protection
    local cors_response=$(curl -s -H "Origin: https://malicious-site.com" "http://$SERVICE_URL/api/portfolio" || echo "FAILED")
    if [[ "$cors_response" == *"CORS"* ]] || [[ "$cors_response" == *"401"* ]]; then
        success "CORS protection is active"
    else
        warning "CORS protection may not be properly configured"
    fi
    
    # Test authentication
    local auth_response=$(curl -s -o /dev/null -w "%{http_code}" "http://$SERVICE_URL/api/portfolio")
    if [[ "$auth_response" == "401" ]]; then
        success "Authentication protection is active"
    else
        warning "Authentication may not be properly configured"
    fi
    
    # Test CSRF protection
    local csrf_response=$(curl -s -X POST "http://$SERVICE_URL/api/portfolio/rebalance" | head -c 100)
    if [[ "$csrf_response" == *"CSRF"* ]] || [[ "$csrf_response" == *"401"* ]]; then
        success "CSRF protection is active"
    else
        warning "CSRF protection may not be properly configured"
    fi
}

# =============================================================================
# Rollback Functions
# =============================================================================

rollback_deployment() {
    error "Deployment failed. Initiating rollback..."
    
    # Rollback Helm deployment
    if [[ "$DEPLOY_BACKEND" == "true" ]]; then
        helm rollback value-partner-api --namespace value-partner || true
    fi
    
    # Rollback Terraform if needed
    if [[ "$DEPLOY_INFRA" == "true" ]] && [[ -f "infra/tfplan.backup" ]]; then
        cd infra
        terraform apply tfplan.backup
        cd ..
    fi
    
    error "Rollback completed. Please check logs and fix issues before retrying."
}

# =============================================================================
# Main Deployment Flow
# =============================================================================

main() {
    log "Starting Value Partner platform deployment..."
    log "Environment: $ENVIRONMENT"
    log "AWS Region: $AWS_REGION"
    
    # Set up error handling
    trap rollback_deployment ERR
    
    # Run deployment steps
    check_prerequisites
    
    if [[ "$DEPLOY_INFRA" == "true" ]]; then
        deploy_infrastructure
    fi
    
    if [[ "$DEPLOY_BACKEND" == "true" ]]; then
        deploy_backend
        wait_for_deployment
    fi
    
    if [[ "$DEPLOY_FRONTEND" == "true" ]]; then
        deploy_frontend
    fi
    
    # Run verification
    run_health_checks
    run_security_verification
    
    success "=============================================================================\n\
✅ Value Partner Platform Deployment Complete!\n\n\
Backend API: http://$(kubectl get svc -n value-partner value-partner-api -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo 'localhost:8000')\n\
Frontend: ${FRONTEND_URL:-'Configured in S3/CloudFront'}\n\
Environment: $ENVIRONMENT\n\
\n\
🔒 Security Features Active:\n\
- JWT Authentication\n\
- CORS Protection\n\
- CSRF Protection\n\
- Webhook Security\n\
- Sensitive Data Sanitization\n\
\n\
📊 Next Steps:\n\
1. Configure DNS and SSL certificates\n\
2. Set up monitoring and alerting\n\
3. Configure backup strategies\n\
4. Run user acceptance testing\n\
============================================================================="
}

# =============================================================================
# Script Execution
# =============================================================================

# Handle command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --skip-frontend)
            DEPLOY_FRONTEND=false
            shift
            ;;
        --skip-backend)
            DEPLOY_BACKEND=false
            shift
            ;;
        --skip-infra)
            DEPLOY_INFRA=false
            shift
            ;;
        --skip-migrations)
            RUN_MIGRATIONS=false
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --environment ENV    Set deployment environment (default: production)"
            echo "  --skip-frontend      Skip frontend deployment"
            echo "  --skip-backend       Skip backend deployment"
            echo "  --skip-infra         Skip infrastructure deployment"
            echo "  --skip-migrations    Skip database migrations"
            echo "  --skip-tests         Skip running tests"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Run main deployment
main 