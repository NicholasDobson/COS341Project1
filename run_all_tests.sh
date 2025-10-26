# SPL Compiler - Automated Test Runner for Mac
# Run this script to test everything automatically

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

print_header "Checking Python Version"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    print_success "Python3 found: $(python3 --version)"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    print_success "Python found: $(python --version)"
else
    print_error "Python not found! Please install Python 3.8+"
    exit 1
fi

print_header "Checking Required Files"
REQUIRED_FILES=("compiler.py" "scopeTesting.py" "LabelandJumpTesting.py" "example_test.spl")
ALL_FILES_PRESENT=true

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_success "$file found"
    else
        print_error "$file not found!"
        ALL_FILES_PRESENT=false
    fi
done

if [ "$ALL_FILES_PRESENT" = false ]; then
    print_error "Missing required files. Please download all files first."
    exit 1
fi

print_header "Running Scope Tests (30 tests)"
print_info "This will take ~10-15 seconds..."
$PYTHON_CMD scopeTesting.py > scope_test_output.txt 2>&1
SCOPE_EXIT_CODE=$?

SCOPE_PASSED=$(grep "^Passed:" scope_test_output.txt | tail -1 | awk '{print $2}' | tr -d ',')
SCOPE_FAILED=$(grep "^Failed:" scope_test_output.txt | tail -1 | awk '{print $2}')

if [ -z "$SCOPE_PASSED" ]; then
    SCOPE_PASSED=0
fi
if [ -z "$SCOPE_FAILED" ]; then
    SCOPE_FAILED=0
fi

if [ $SCOPE_EXIT_CODE -eq 0 ]; then
    if [ "$SCOPE_FAILED" = "0" ]; then
        print_success "Scope Tests: $SCOPE_PASSED passed, $SCOPE_FAILED failed"
    else
        print_error "Scope Tests: $SCOPE_PASSED passed, $SCOPE_FAILED failed"
        print_info "See scope_test_output.txt for details"
    fi
else
    print_error "Scope tests encountered an error"
    print_info "See scope_test_output.txt for details"
fi

# Run Label/Jump Tests
print_header "Running Label/Jump Tests (15 tests)"
print_info "This will take ~8-12 seconds..."
$PYTHON_CMD LabelandJumpTesting.py > label_test_output.txt 2>&1
LABEL_EXIT_CODE=$?

# Extract summary from output - look for the exact pattern
LABEL_PASSED=$(grep "^Passed:" label_test_output.txt | tail -1 | awk '{print $2}' | tr -d ',')
LABEL_FAILED=$(grep "^Failed:" label_test_output.txt | tail -1 | awk '{print $2}')

# Default to 0 if not found
if [ -z "$LABEL_PASSED" ]; then
    LABEL_PASSED=0
fi
if [ -z "$LABEL_FAILED" ]; then
    LABEL_FAILED=0
fi

if [ $LABEL_EXIT_CODE -eq 0 ]; then
    if [ "$LABEL_FAILED" = "0" ]; then
        print_success "Label/Jump Tests: $LABEL_PASSED passed, $LABEL_FAILED failed"
    else
        print_error "Label/Jump Tests: $LABEL_PASSED passed, $LABEL_FAILED failed"
        print_info "See label_test_output.txt for details"
    fi
else
    print_error "Label/Jump tests encountered an error"
    print_info "See label_test_output.txt for details"
fi

# Compile Example Program
print_header "Compiling Example Program"
print_info "Compiling example_test.spl..."
$PYTHON_CMD compiler.py example_test.spl output.txt > compile_output.txt 2>&1
COMPILE_EXIT_CODE=$?

if [ $COMPILE_EXIT_CODE -eq 0 ]; then
    print_success "Example compilation successful!"
    print_info "Output written to output.txt"
    
    # Show label mapping from output
    if grep -q "Label Mapping:" compile_output.txt; then
        echo ""
        print_info "Label Mapping:"
        grep -A 10 "Label Mapping:" compile_output.txt | grep -E "^\s+_L[0-9]+" | sed 's/^/  /'
    fi
else
    print_error "Example compilation failed"
    print_info "See compile_output.txt for details"
fi

# Overall Summary
print_header "OVERALL SUMMARY"
echo ""
echo "Test Results:"
echo "  Scope Tests:      $SCOPE_PASSED/30 passed"
echo "  Label/Jump Tests: $LABEL_PASSED/15 passed"
echo "  Example Compile:  $([ $COMPILE_EXIT_CODE -eq 0 ] && echo 'Success' || echo 'Failed')"
echo ""

TOTAL_PASSED=$((SCOPE_PASSED + LABEL_PASSED))
TOTAL_TESTS=45

if [ "$SCOPE_FAILED" = "0" ] && [ "$LABEL_FAILED" = "0" ] && [ $COMPILE_EXIT_CODE -eq 0 ]; then
    print_success "ALL TESTS PASSED! ($TOTAL_PASSED/$TOTAL_TESTS)"
    echo ""
    print_info "Detailed outputs saved to:"
    echo "  - scope_test_output.txt"
    echo "  - label_test_output.txt"
    echo "  - compile_output.txt"
    echo "  - output.txt (compiled BASIC code)"
    echo ""
    print_success "🎉 Everything is working perfectly!"
    exit 0
else
    print_error "Some tests failed. Please review the output files."
    echo ""
    print_info "Detailed outputs saved to:"
    echo "  - scope_test_output.txt"
    echo "  - label_test_output.txt"
    echo "  - compile_output.txt"
    exit 1
fi
