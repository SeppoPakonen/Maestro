# Cross-Agent Delta Table: Tool Event Granularity Gaps Analysis

## Overview
This document analyzes the tool event granularity gaps across various AI agents (Codex, Claude-Code, Copilot-CLI, and Gemini-CLI) for the AI CLI Live Tool Protocol integration. This analysis is part of Task aicli5-5: Cross-Agent Delta Table - Note tool event granularity gaps.

## Tool Event Granularity Comparison

### 1. Tool Call Request Granularity

#### Codex
- **Granularity Level**: Coarse-grained
- **Event Trigger**: Per external process execution
- **Information Captured**: 
  - Initial prompt sent to process
  - Process execution parameters
  - Basic command structure
- **Limitations**: 
  - Cannot capture internal tool calls within the process
  - Limited visibility into decision-making process
  - Single event per process run

#### Claude-Code
- **Granularity Level**: Coarse-grained
- **Event Trigger**: Per external process execution
- **Information Captured**:
  - Initial prompt sent to Claude CLI
  - Command-line arguments
  - Process execution context
- **Limitations**:
  - Similar to Codex limitations
  - No visibility into Claude's internal planning
  - Cannot capture individual tool decisions within response

#### Copilot-CLI
- **Granularity Level**: Medium-grained
- **Event Trigger**: Per API request or CLI command
- **Information Captured**:
  - Request parameters and context
  - Tool suggestions made by Copilot
  - Intent recognition results
- **Limitations**:
  - Dependent on how Copilot structures its responses
  - May not capture all sub-operations

#### Gemini-CLI
- **Granularity Level**: Medium-to-fine-grained
- **Event Trigger**: Per API request and streaming chunks
- **Information Captured**:
  - Complete request context
  - Individual text/code blocks
  - Safety and moderation events
- **Limitations**:
  - Granularity depends on API chunking
  - May require additional parsing for tool identification

### 2. Tool Call Response Granularity

#### Codex and Claude-Code
- **Granularity Level**: Coarse-grained
- **Event Timing**: At process completion
- **Information Captured**:
  - Complete output from process
  - Exit code and error status
  - Execution timing
- **Limitations**:
  - No intermediate progress updates
  - Cannot separate individual logical operations
  - All-or-nothing response capture

#### Copilot-CLI
- **Granularity Level**: Medium-grained
- **Event Timing**: Per API response
- **Information Captured**:
  - Structured response content
  - Suggested operations
  - Confidence levels (if provided)
- **Limitations**:
  - Granularity limited by API response structure
  - May not distinguish between different operation types

#### Gemini-CLI
- **Granularity Level**: Fine-grained (with streaming)
- **Event Timing**: During streaming (if enabled)
- **Information Captured**:
  - Individual content blocks
  - Streaming progress
  - Real-time response formation
- **Advantages**:
  - Can capture response as it forms
  - Better visibility into response structure
  - More granular error detection

### 3. Tool Execution Status Granularity

#### CLI-Based Agents (Codex, Claude-Code)
- **Granularity Level**: Very coarse-grained
- **Status Events**: Minimal
- **Information Captured**:
  - Process start
  - Process end
  - Basic completion status
- **Limitations**:
  - No intermediate progress
  - Cannot detect internal state changes
  - Limited timing insights

#### API-Based Agents (Copilot-CLI, Gemini-CLI)
- **Granularity Level**: Medium-to-fine-grained
- **Status Events**: More detailed
- **Information Captured**:
  - API request progress
  - Potential intermediate status calls
  - Connection and communication status
- **Advantages**:
  - Better visibility during execution
  - Can capture API-level status updates
  - More detailed progress tracking

## Granularity Gap Analysis

### 1. Temporal Granularity Gaps

#### Gap: Intermediate Progress Visibility
- **Issue**: CLI-based agents offer no visibility into ongoing operations
- **Impact**: Cannot detect or report on intermediate progress
- **Solution**: Implement heartbeat mechanism with periodic status updates

#### Gap: Real-time Response Formation
- **Issue**: Non-streaming agents don't capture response formation in real-time
- **Impact**: Cannot provide streaming feedback to users
- **Solution**: Enhance non-streaming agents with internal chunking

### 2. Semantic Granularity Gaps

#### Gap: Sub-operation Visibility
- **Issue**: Cannot distinguish between different logical operations within a single agent response
- **Impact**: Reduced visibility into agent's decision-making process
- **Solution**: Implement response parsing to identify logical operations

#### Gap: Intent Recognition
- **Issue**: Cannot distinguish agent's intent from its actions
- **Impact**: Blurred line between analysis and action
- **Solution**: Capture agent's intent before action execution

### 3. Context Granularity Gaps

#### Gap: Context Window Awareness
- **Issue**: No visibility into agent's context window management
- **Impact**: Cannot track what context is being considered
- **Solution**: Capture context snapshots with each operation

#### Gap: Tool Selection Process
- **Issue**: Cannot observe agent's tool selection reasoning
- **Impact**: Loss of insight into decision-making
- **Solution**: Log tool selection criteria and alternatives

## Impact of Granularity Differences

### 1. User Experience Impact
- **High Granularity**: Better feedback on progress and status
- **Low Granularity**: Limited user feedback, potential for perceived unresponsiveness

### 2. Debugging and Monitoring Impact
- **High Granularity**: Better debugging capabilities and detailed logs
- **Low Granularity**: Difficulty in diagnosing issues and understanding behavior

### 3. Integration Complexity Impact
- **High Granularity**: More complex integration with many event points
- **Low Granularity**: Simpler integration but less detailed monitoring

## Recommendations for Granularity Improvement

### 1. Implement Agent-Enhanced Visibility
For CLI-based agents (Codex, Claude-Code), implement mechanisms to:
- Parse internal responses for logical operations
- Add artificial checkpoints for progress reporting
- Capture intermediate states through process communication

### 2. Standardize Granularity Levels
Define standard granularity levels that all agents should support:
- **Level 1**: Basic request/response (minimum for all agents)
- **Level 2**: Progress reporting for long-running operations
- **Level 3**: Sub-operation visibility within agent responses
- **Level 4**: Real-time streaming of response formation

### 3. Protocol Enhancement for Granularity
Enhance the AI CLI Live Tool Protocol to:
- Support different granularity levels
- Allow agents to indicate their supported granularity
- Provide mechanisms for fine-grained event correlation

### 4. Adaptive Granularity
Implement adaptive granularity based on:
- Operation complexity
- Expected duration
- User configuration preferences
- Network or performance constraints

## Implementation Priorities

### High Priority
1. Add basic progress reporting for CLI-based agents
2. Standardize event correlation across granularity levels
3. Implement response parsing for logical operations

### Medium Priority
1. Enhance streaming support in all agents
2. Add context window visibility
3. Implement tool selection logging

### Low Priority
1. Add fine-grained internal state visibility
2. Implement adaptive granularity mechanisms
3. Add detailed intent recognition logging

## Summary of Key Gaps

1. **CLI vs API Granularity Gap**: CLI-based agents inherently have coarser granularity than API-based agents
2. **Streaming Capability Gap**: Non-streaming agents miss real-time response visibility
3. **Sub-operation Recognition Gap**: Difficulty in identifying individual operations within agent responses
4. **Progress Visibility Gap**: CLI-based agents provide minimal progress feedback during execution
5. **Context Awareness Gap**: Limited visibility into agent's context utilization

These granularity gaps represent opportunities to enhance the visibility and monitoring capabilities of the AI CLI Live Tool Protocol across different agent implementations.