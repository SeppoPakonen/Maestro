#!/bin/bash
# Test runner script for Live Tool Events and Input Injection tests

set -e  # Exit on any error

echo "AI CLI Live Tool Protocol - Live Tool Events and Input Injection Test Runner"
echo "============================================================================="

# Define test categories
TEST_CATEGORIES=(
    "Basic Message Framing and Structure Tests"
    "Tool Event Tests"
    "Input Injection Tests"
    "Stream Event Tests"
    "Session Management Tests"
    "Backpressure Handling Tests"
    "Error Handling and Recovery Tests"
    "Transport Mechanism Tests"
    "Integration and End-to-End Tests"
    "Performance and Stress Tests"
)

# Display menu
echo ""
echo "Available Test Categories:"
for i in "${!TEST_CATEGORIES[@]}"; do
    printf "%2d. %s\n" $((i+1)) "${TEST_CATEGORIES[$i]}"
done
echo "11. Run ALL tests"
echo "12. Exit"
echo ""

read -p "Select test category to run (1-${#TEST_CATEGORIES[@]}, 11 for all, 12 to exit): " selection

case $selection in
    1)
        echo "Running: Basic Message Framing and Structure Tests"
        python -m pytest tests/ -k "test_framing or test_message_structure" -v
        ;;
    2)
        echo "Running: Tool Event Tests"
        python -m pytest tests/ -k "tool_event or tool_call" -v
        ;;
    3)
        echo "Running: Input Injection Tests"
        python -m pytest tests/ -k "input_injection or user_input or interrupt" -v
        ;;
    4)
        echo "Running: Stream Event Tests"
        python -m pytest tests/ -k "stream_event or content_block" -v
        ;;
    5)
        echo "Running: Session Management Tests"
        python -m pytest tests/ -k "session or session_management" -v
        ;;
    6)
        echo "Running: Backpressure Handling Tests"
        python -m pytest tests/ -k "backpressure or flow_control" -v
        ;;
    7)
        echo "Running: Error Handling and Recovery Tests"
        python -m pytest tests/ -k "error_handling or recovery" -v
        ;;
    8)
        echo "Running: Transport Mechanism Tests"
        python -m pytest tests/ -k "transport or stdio or tcp or named_pipe" -v
        ;;
    9)
        echo "Running: Integration and End-to-End Tests"
        python -m pytest tests/ -k "integration or end_to_end or full_workflow" -v
        ;;
    10)
        echo "Running: Performance and Stress Tests"
        python -m pytest tests/ -k "performance or stress or load" -v
        ;;
    11)
        echo "Running ALL tests for Live Tool Events and Input Injection"
        python -m pytest tests/ -k "live_tool or input_injection or ai_cli_protocol" -v
        ;;
    12)
        echo "Exiting test runner."
        exit 0
        ;;
    *)
        echo "Invalid selection. Exiting."
        exit 1
        ;;
esac

echo ""
echo "Test execution completed."