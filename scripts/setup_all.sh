#!/bin/bash
# ================================================
# LandTen MVP 3.0 - Complete Setup Script
# ================================================
# This script sets up the entire LandTen environment:
# - DynamoDB tables
# - S3 buckets with CORS
# - Backend dependencies
# - Frontend dependencies
# - Environment verification
# ================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Parse command line arguments
LOCAL_MODE=false
SKIP_AWS=false
STAGE="dev"

while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            LOCAL_MODE=true
            shift
            ;;
        --skip-aws)
            SKIP_AWS=true
            shift
            ;;
        --stage)
            STAGE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--local] [--skip-aws] [--stage dev|staging|prod]"
            exit 1
            ;;
    esac
done

# ================================================
# START SETUP
# ================================================

print_header "🚀 LandTen MVP 3.0 Setup - Stage: $STAGE"

if [ "$LOCAL_MODE" = true ]; then
    print_warning "Running in LOCAL mode (using LocalStack)"
fi

# ================================================
# 1. VERIFY PREREQUISITES
# ================================================
print_header "📋 Verifying Prerequisites"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_success "Python installed: $PYTHON_VERSION"
else
    print_error "Python 3 is not installed"
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_success "Node.js installed: $NODE_VERSION"
else
    print_error "Node.js is not installed"
    exit 1
fi

# Check npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    print_success "npm installed: $NPM_VERSION"
else
    print_error "npm is not installed"
    exit 1
fi

# Check AWS CLI (optional for local mode)
if [ "$SKIP_AWS" = false ] && [ "$LOCAL_MODE" = false ]; then
    if command -v aws &> /dev/null; then
        AWS_VERSION=$(aws --version)
        print_success "AWS CLI installed: $AWS_VERSION"
    else
        print_warning "AWS CLI is not installed (required for production setup)"
        print_warning "Install: https://aws.amazon.com/cli/"
    fi
fi

# ================================================
# 2. ENVIRONMENT CONFIGURATION
# ================================================
print_header "🔧 Environment Configuration"

# Check backend .env
if [ ! -f "backend/.env" ]; then
    print_warning "backend/.env not found, copying from .env.example"
    cp backend/.env.example backend/.env
    print_warning "Please edit backend/.env with your credentials"
else
    print_success "backend/.env exists"
fi

# Check frontend .env.local
if [ ! -f "frontend/.env.local" ]; then
    print_warning "frontend/.env.local not found, copying from .env.example"
    cp frontend/.env.example frontend/.env.local
    print_warning "Please edit frontend/.env.local with your credentials"
else
    print_success "frontend/.env.local exists"
fi

# ================================================
# 3. INSTALL BACKEND DEPENDENCIES
# ================================================
print_header "🐍 Installing Backend Dependencies"

cd backend

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    print_warning "Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate
print_success "Activated virtual environment"

# Install dependencies
print_warning "Installing Python packages..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
print_success "Backend dependencies installed"

cd ..

# ================================================
# 4. INSTALL FRONTEND DEPENDENCIES
# ================================================
print_header "⚛️  Installing Frontend Dependencies"

cd frontend
print_warning "Installing npm packages (this may take a few minutes)..."
npm install > /dev/null 2>&1
print_success "Frontend dependencies installed"
cd ..

# ================================================
# 5. SETUP DYNAMODB TABLES
# ================================================
if [ "$SKIP_AWS" = false ]; then
    print_header "📊 Creating DynamoDB Tables"

    if [ "$LOCAL_MODE" = true ]; then
        print_warning "Creating tables in local DynamoDB..."
        python3 scripts/create_dynamodb_tables.py --stage "$STAGE" --local
    else
        print_warning "Creating tables in AWS DynamoDB..."
        python3 scripts/create_dynamodb_tables.py --stage "$STAGE"
    fi

    print_success "DynamoDB tables created"
else
    print_warning "Skipping AWS setup (--skip-aws flag)"
fi

# ================================================
# 6. SETUP S3 BUCKETS
# ================================================
if [ "$SKIP_AWS" = false ] && [ "$LOCAL_MODE" = false ]; then
    print_header "📦 Creating S3 Buckets"

    # Create buckets
    BUCKET_INCIDENTS="landten-${STAGE}-incident-photos"
    BUCKET_JOBS="landten-${STAGE}-job-completion-photos"

    # Create incident photos bucket
    if aws s3 ls "s3://${BUCKET_INCIDENTS}" 2>&1 | grep -q 'NoSuchBucket'; then
        aws s3 mb "s3://${BUCKET_INCIDENTS}"
        print_success "Created bucket: ${BUCKET_INCIDENTS}"
    else
        print_warning "Bucket already exists: ${BUCKET_INCIDENTS}"
    fi

    # Create job completion photos bucket
    if aws s3 ls "s3://${BUCKET_JOBS}" 2>&1 | grep -q 'NoSuchBucket'; then
        aws s3 mb "s3://${BUCKET_JOBS}"
        print_success "Created bucket: ${BUCKET_JOBS}"
    else
        print_warning "Bucket already exists: ${BUCKET_JOBS}"
    fi

    # Apply CORS configuration
    if [ -f "scripts/s3-cors.json" ]; then
        print_warning "Applying CORS configuration to buckets..."
        aws s3api put-bucket-cors --bucket "${BUCKET_INCIDENTS}" --cors-configuration file://scripts/s3-cors.json
        aws s3api put-bucket-cors --bucket "${BUCKET_JOBS}" --cors-configuration file://scripts/s3-cors.json
        print_success "CORS configuration applied"
    else
        print_warning "scripts/s3-cors.json not found, skipping CORS setup"
    fi
fi

# ================================================
# 7. VERIFICATION
# ================================================
print_header "✅ Verification"

ISSUES=0

# Check if backend can import key modules
cd backend
source .venv/bin/activate
if python3 -c "import fastapi, boto3, stripe" 2>/dev/null; then
    print_success "Backend dependencies verified"
else
    print_error "Backend dependencies missing"
    ISSUES=$((ISSUES + 1))
fi
cd ..

# Check if frontend node_modules exists
if [ -d "frontend/node_modules" ]; then
    print_success "Frontend dependencies verified"
else
    print_error "Frontend node_modules missing"
    ISSUES=$((ISSUES + 1))
fi

# Check environment files
if [ -f "backend/.env" ]; then
    print_success "Backend .env exists"
else
    print_error "Backend .env missing"
    ISSUES=$((ISSUES + 1))
fi

if [ -f "frontend/.env.local" ]; then
    print_success "Frontend .env.local exists"
else
    print_error "Frontend .env.local missing"
    ISSUES=$((ISSUES + 1))
fi

# ================================================
# FINAL SUMMARY
# ================================================
print_header "📝 Setup Summary"

if [ $ISSUES -eq 0 ]; then
    print_success "Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Configure environment variables:"
    echo "   - Edit backend/.env (AWS, Stripe, Stream keys)"
    echo "   - Edit frontend/.env.local (Stripe publishable key)"
    echo ""
    echo "2. Configure Stripe webhook:"
    echo "   - Go to: https://dashboard.stripe.com/webhooks"
    echo "   - Add endpoint: https://your-domain.com/api/v1/payments/webhooks/stripe"
    echo "   - Copy webhook secret to backend/.env"
    echo ""
    echo "3. Start development servers:"
    echo "   Backend:  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000"
    echo "   Frontend: cd frontend && npm run dev"
    echo ""
    echo "4. Run tests:"
    echo "   ./scripts/test_flow.sh"
    echo ""
else
    print_error "Setup completed with $ISSUES issue(s)"
    echo ""
    echo "Please fix the issues above and run setup again."
    exit 1
fi
