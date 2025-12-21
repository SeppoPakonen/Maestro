#!/bin/bash
# Test script to validate input injection during active Qwen sessions for AI CLI Live Tool Protocol
# Test IDs: II-001, II-002, II-003

set -e  # Exit on any error

# Configuration
DEFAULT_HOST="localhost"
DEFAULT_PORT="7774"
TEST_TIMEOUT=30
SESSION_ID="test-session-$(date +%s)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up test resources..."
    if [ ! -z "$SERVER_PID" ]; then
        echo "Stopping server (PID: $SERVER_PID)..."
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
    fi

    # Kill any background processes
    jobs -p | xargs -r kill 2>/dev/null || true

    # Clean up temporary files
    rm -f /tmp/qwen_input_test_*.txt /tmp/qwen_client_pipe_* /tmp/qwen_response_*

    echo "Cleanup complete"
}

trap cleanup EXIT INT TERM

# Print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Validate JSON format
validate_json() {
    local json_string="$1"
    echo "$json_string" | python3 -m json.tool > /dev/null 2>&1
    return $?
}

# Function to run a long-running "tool" for testing input injection during execution
start_long_running_tool() {
    local output_file=$1
    {
        # Simulate a long-running tool by outputting periodic status updates
        for i in {1..10}; do
            local json_msg="{\"type\":\"tool_execution_status\", \"timestamp\":\"$(date -Iseconds)Z\", \"session_id\":\"${SESSION_ID}\", \"data\":{\"step\":${i}, \"total_steps\":10, \"status\":\"running\"}}"
            if validate_json "$json_msg"; then
                echo "$json_msg"
            else
                echo "{\"type\":\"error\", \"timestamp\":\"$(date -Iseconds)Z\", \"session_id\":\"${SESSION_ID}\", \"data\":{\"message\":\"Invalid JSON generated\"}}" >&2
            fi
            sleep 1
        done
        # Final tool completion message
        local json_msg="{\"type\":\"tool_call_response\", \"timestamp\":\"$(date -Iseconds)Z\", \"session_id\":\"${SESSION_ID}\", \"data\":{\"result\":\"Long-running tool completed successfully\"}}"
        if validate_json "$json_msg"; then
            echo "$json_msg"
        else
            echo "{\"type\":\"error\", \"timestamp\":\"$(date -Iseconds)Z\", \"session_id\":\"${SESSION_ID}\", \"data\":{\"message\":\"Invalid JSON generated\"}}" >&2
        fi
    } > "$output_file" &

    echo $!  # Return the PID of the background process
}

# Test 1: User Input Message Emission (II-001)
test_user_input_emission() {
    print_status $BLUE "Running Test II-001: User Input Message Emission"

    local test_input="Hello from test script"
    local temp_output="/tmp/qwen_input_test_output_$$"

    # Create a named pipe to simulate communication
    local pipe="/tmp/qwen_client_pipe_$$"
    mkfifo "$pipe" 2>/dev/null || { print_status $RED "Failed to create pipe"; return 1; }

    # Start a mock server that listens for input
    {
        timeout $TEST_TIMEOUT nc -l -p 7775 > "$temp_output" 2>&1
    } &
    MOCK_SERVER_PID=$!

    # Give the server time to start
    sleep 1

    # Verify port is available
    if ! nc -z localhost 7775 2>/dev/null; then
        print_status $RED "Mock server failed to start on port 7775"
        rm -f "$pipe"
        return 1
    fi

    # Send user input message
    local input_msg="{\"type\":\"user_input\", \"timestamp\":\"$(date -Iseconds)Z\", \"session_id\":\"${SESSION_ID}\", \"data\":{\"content\":\"${test_input}\"}}"

    # Validate the message format before sending
    if ! validate_json "$input_msg"; then
        print_status $RED "Generated invalid JSON for user input message"
        rm -f "$pipe"
        return 1
    fi

    {
        echo "$input_msg" > "$pipe"
        sleep 2  # Allow time for transmission
    } &

    # Close the pipe after writing
    exec 3>"$pipe"
    exec 3>&-

    # Wait for server to receive the message or timeout
    sleep 3

    # Stop the mock server
    kill $MOCK_SERVER_PID 2>/dev/null || true
    wait $MOCK_SERVER_PID 2>/dev/null || true

    # Verify the message was received correctly
    if [ -f "$temp_output" ] && grep -q "user_input" "$temp_output" && grep -q "$test_input" "$temp_output"; then
        # Additional validation: check if the received message is valid JSON
        local received_msg=$(grep "user_input" "$temp_output" | head -n 1)
        if validate_json "$received_msg"; then
            print_status $GREEN "✓ Test II-001 PASSED: User input message emitted correctly"
            rm -f "$temp_output" "$pipe"
            return 0
        else
            print_status $RED "✗ Test II-001 FAILED: Received message is not valid JSON"
            rm -f "$temp_output" "$pipe"
            return 1
        fi
    else
        print_status $RED "✗ Test II-001 FAILED: User input message not received or incorrect"
        if [ -f "$temp_output" ]; then
            echo "Received content:"
            cat "$temp_output"
        fi
        rm -f "$temp_output" "$pipe"
        return 1
    fi
}

# Test 2: Input Injection During Tool Execution (II-002)
test_input_injection_during_tool_execution() {
    print_status $BLUE "Running Test II-002: Input Injection During Tool Execution"

    local tool_output="/tmp/qwen_tool_output_$$"
    local temp_output="/tmp/qwen_input_test_output_$$"

    # Start a long-running "tool"
    TOOL_PID=$(start_long_running_tool "$tool_output")

    # Verify the tool actually started
    if ! kill -0 $TOOL_PID 2>/dev/null; then
        print_status $RED "Failed to start long-running tool simulation"
        rm -f "$tool_output"
        return 1
    fi

    # Create a named pipe to inject input
    local pipe="/tmp/qwen_client_pipe_$$"
    mkfifo "$pipe" 2>/dev/null || { print_status $RED "Failed to create pipe"; return 1; }

    # Set up a mock server to capture injected input
    {
        timeout $TEST_TIMEOUT nc -l -p 7776 > "$temp_output" 2>&1
    } &
    MOCK_SERVER_PID=$!

    # Give the server time to start
    sleep 1

    # Verify port is available
    if ! nc -z localhost 7776 2>/dev/null; then
        print_status $RED "Mock server failed to start on port 7776"
        rm -f "$tool_output" "$pipe"
        return 1
    fi

    # Inject user input while tool is running
    local injection_msg="{\"type\":\"user_input\", \"timestamp\":\"$(date -Iseconds)Z\", \"session_id\":\"${SESSION_ID}\", \"data\":{\"content\":\"Injected input during tool execution\"}}"

    # Validate the message format before sending
    if ! validate_json "$injection_msg"; then
        print_status $RED "Generated invalid JSON for injection message"
        rm -f "$tool_output" "$pipe"
        return 1
    fi

    {
        sleep 2  # Wait for tool to start running
        echo "$injection_msg" > "$pipe"
        sleep 1
    } &

    CLIENT_PID=$!

    # Close the pipe after writing
    exec 3>"$pipe"
    exec 3>&-

    # Wait for all processes to complete
    wait $TOOL_PID 2>/dev/null || true
    wait $CLIENT_PID 2>/dev/null || true
    sleep 2  # Allow time for server to process

    # Stop the mock server
    kill $MOCK_SERVER_PID 2>/dev/null || true
    wait $MOCK_SERVER_PID 2>/dev/null || true

    # Verify both tool execution and injected input were handled
    local tool_success=false
    local input_received=false

    if [ -f "$tool_output" ]; then
        if grep -q "tool_call_response" "$tool_output" && grep -q "Long-running tool completed successfully" "$tool_output"; then
            tool_success=true
        fi
    fi

    if [ -f "$temp_output" ]; then
        if grep -q "user_input" "$temp_output" && grep -q "Injected input during tool execution" "$temp_output"; then
            # Additional validation: check if the received message is valid JSON
            local received_msg=$(grep "user_input" "$temp_output" | head -n 1)
            if validate_json "$received_msg"; then
                input_received=true
            fi
        fi
    fi

    if [ "$tool_success" = true ] && [ "$input_received" = true ]; then
        print_status $GREEN "✓ Test II-002 PASSED: Input injection during tool execution handled correctly"
        rm -f "$tool_output" "$temp_output" "$pipe"
        return 0
    else
        print_status $RED "✗ Test II-002 FAILED: Issues with tool execution or input injection"
        echo "Tool execution success: $tool_success"
        echo "Input received: $input_received"

        if [ -f "$tool_output" ]; then
            echo "Tool output:"
            cat "$tool_output"
        fi

        if [ -f "$temp_output" ]; then
            echo "Received input:"
            cat "$temp_output"
        fi

        rm -f "$tool_output" "$temp_output" "$pipe"
        return 1
    fi
}

# Test 3: Interrupt Signal Injection (II-003)
test_interrupt_signal_injection() {
    print_status $BLUE "Running Test II-003: Interrupt Signal Injection"

    local temp_output="/tmp/qwen_interrupt_test_output_$$"

    # Create a named pipe to inject interrupt
    local pipe="/tmp/qwen_client_pipe_$$"
    mkfifo "$pipe" 2>/dev/null || { print_status $RED "Failed to create pipe"; return 1; }

    # Set up a mock server to capture interrupt
    {
        timeout $TEST_TIMEOUT nc -l -p 7777 > "$temp_output" 2>&1
    } &
    MOCK_SERVER_PID=$!

    # Give the server time to start
    sleep 1

    # Verify port is available
    if ! nc -z localhost 7777 2>/dev/null; then
        print_status $RED "Mock server failed to start on port 7777"
        rm -f "$pipe"
        return 1
    fi

    # Send interrupt message
    local interrupt_msg="{\"type\":\"interrupt\", \"timestamp\":\"$(date -Iseconds)Z\", \"session_id\":\"${SESSION_ID}\", \"data\":{\"reason\":\"test_interrupt\"}}"

    # Validate the message format before sending
    if ! validate_json "$interrupt_msg"; then
        print_status $RED "Generated invalid JSON for interrupt message"
        rm -f "$pipe"
        return 1
    fi

    {
        echo "$interrupt_msg" > "$pipe"
        sleep 1
    } &

    CLIENT_PID=$!

    # Close the pipe after writing
    exec 3>"$pipe"
    exec 3>&-

    # Wait for client to finish
    wait $CLIENT_PID 2>/dev/null || true
    sleep 1  # Allow time for server to process

    # Stop the mock server
    kill $MOCK_SERVER_PID 2>/dev/null || true
    wait $MOCK_SERVER_PID 2>/dev/null || true

    # Verify interrupt message was received
    if [ -f "$temp_output" ] && grep -q "interrupt" "$temp_output" && grep -q "test_interrupt" "$temp_output"; then
        # Additional validation: check if the received message is valid JSON
        local received_msg=$(grep "interrupt" "$temp_output" | head -n 1)
        if validate_json "$received_msg"; then
            print_status $GREEN "✓ Test II-003 PASSED: Interrupt signal injected and received correctly"
            rm -f "$temp_output" "$pipe"
            return 0
        else
            print_status $RED "✗ Test II-003 FAILED: Received interrupt message is not valid JSON"
            rm -f "$temp_output" "$pipe"
            return 1
        fi
    else
        print_status $RED "✗ Test II-003 FAILED: Interrupt signal not received or incorrect"
        if [ -f "$temp_output" ]; then
            echo "Received content:"
            cat "$temp_output"
        fi
        rm -f "$temp_output" "$pipe"
        return 1
    fi
}

# Main execution
echo "AI CLI Live Tool Protocol - Input Injection Validation Tests"
echo "============================================================="
echo "Session ID: $SESSION_ID"
echo ""

# Check for required tools
if ! command -v nc >/dev/null 2>&1; then
    print_status $RED "Error: 'nc' (netcat) is required but not installed"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    print_status $RED "Error: 'python3' is required but not installed"
    exit 1
fi

# Run all tests
all_passed=true

if ! test_user_input_emission; then
    all_passed=false
fi

if ! test_input_injection_during_tool_execution; then
    all_passed=false
fi

if ! test_interrupt_signal_injection; then
    all_passed=false
fi

echo ""
if [ "$all_passed" = true ]; then
    print_status $GREEN "🎉 All input injection tests PASSED!"
    exit 0
else
    print_status $RED "❌ Some input injection tests FAILED!"
    exit 1
fi