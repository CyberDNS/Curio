#!/bin/bash
# Quick test runner script

set -e

echo "🧪 Curio Test Suite Runner"
echo "=========================="
echo ""

# Check if we're in the project root
if [ ! -f "Makefile" ]; then
    echo "❌ Error: Must run from project root directory"
    exit 1
fi

# Function to run backend tests
run_backend_tests() {
    echo "📦 Running Backend Tests..."
    cd backend
    
    # Install dependencies if needed
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi
    
    # Run tests
    pytest -v
    TEST_EXIT_CODE=$?
    
    deactivate
    cd ..
    
    return $TEST_EXIT_CODE
}

# Function to run frontend tests
run_frontend_tests() {
    echo "⚛️  Running Frontend Tests..."
    cd frontend
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "Installing npm dependencies..."
        npm install
    fi
    
    # Run tests
    npm test -- --run
    TEST_EXIT_CODE=$?
    
    cd ..
    
    return $TEST_EXIT_CODE
}

# Parse command line arguments
case "${1:-all}" in
    backend|be)
        run_backend_tests
        ;;
    frontend|fe)
        run_frontend_tests
        ;;
    coverage|cov)
        echo "📊 Running tests with coverage..."
        make test-coverage
        ;;
    all|*)
        echo "Running all tests..."
        echo ""
        
        run_backend_tests
        BACKEND_EXIT=$?
        
        echo ""
        
        run_frontend_tests
        FRONTEND_EXIT=$?
        
        echo ""
        echo "=========================="
        
        if [ $BACKEND_EXIT -eq 0 ] && [ $FRONTEND_EXIT -eq 0 ]; then
            echo "✅ All tests passed!"
            exit 0
        else
            echo "❌ Some tests failed"
            [ $BACKEND_EXIT -ne 0 ] && echo "  - Backend tests failed"
            [ $FRONTEND_EXIT -ne 0 ] && echo "  - Frontend tests failed"
            exit 1
        fi
        ;;
esac
