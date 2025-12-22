"""
Parser module for the Codex wrapper.

This module handles parsing of input prompts, AI outputs, and separating tool usage
from the codex CLI application.
"""
import json
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class ParsedInput:
    """Represents a parsed input prompt."""
    raw_content: str
    processed_content: str
    metadata: Dict[str, Any]


@dataclass
class ToolUsage:
    """Represents a tool usage extracted from AI output."""
    tool_name: str
    arguments: Dict[str, Any]
    raw_content: str
    execution_result: Optional[str] = None


@dataclass
class ParsedOutput:
    """Represents a parsed AI output."""
    raw_content: str
    text_content: str
    tools: List[ToolUsage]
    metadata: Dict[str, Any]


class CodexParser:
    """
    Parser for codex CLI input/output and tool usage.
    
    This class handles parsing of prompts, responses, and extraction of tool usage
    from the codex application.
    """
    
    def __init__(self):
        # Regex patterns for identifying tool usage in codex output
        self.tool_patterns = [
            # Pattern for tool calls like [TOOL: name, args...]
            r'\[TOOL:\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*,\s*(\{.*?\})\s*\]',
            # Pattern for file operations like [FILE: operation, path...]
            r'\[FILE:\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*,\s*([^\]]*?)\s*\]',
            # Pattern for execution commands like [EXEC: command...]
            r'\[EXEC:\s*([^\]]*?)\s*\]',
            # Pattern for search commands like [SEARCH: query...]
            r'\[SEARCH:\s*([^\]]*?)\s*\]',
        ]
    
    def parse_input(self, input_text: str) -> ParsedInput:
        """
        Parse an input prompt from the user.
        
        Args:
            input_text: Raw input text from user
            
        Returns:
            ParsedInput object with processed content and metadata
        """
        # Remove leading/trailing whitespace
        processed_content = input_text.strip()
        
        # Extract metadata if present (for example, if the input has special formatting)
        metadata = self._extract_input_metadata(input_text)
        
        return ParsedInput(
            raw_content=input_text,
            processed_content=processed_content,
            metadata=metadata
        )
    
    def _extract_input_metadata(self, input_text: str) -> Dict[str, Any]:
        """Extract metadata from input text."""
        metadata = {}
        
        # Check if this is a command (starts with /)
        if input_text.strip().startswith('/'):
            metadata['type'] = 'command'
            command_parts = input_text.strip().split(' ', 1)
            metadata['command'] = command_parts[0][1:]  # Remove the '/'
            if len(command_parts) > 1:
                metadata['arguments'] = command_parts[1]
        else:
            metadata['type'] = 'prompt'
        
        return metadata
    
    def parse_output(self, output_text: str) -> ParsedOutput:
        """
        Parse AI output from codex, separating text content from tool usage.
        
        Args:
            output_text: Raw output from codex
            
        Returns:
            ParsedOutput object with text content, tools, and metadata
        """
        # Extract tool usage
        tools = self._extract_tools(output_text)
        
        # Remove tool usage from the text to get pure text content
        text_content = self._remove_tool_markers(output_text)
        
        # Extract metadata
        metadata = self._extract_output_metadata(output_text)
        
        return ParsedOutput(
            raw_content=output_text,
            text_content=text_content,
            tools=tools,
            metadata=metadata
        )
    
    def _extract_tools(self, text: str) -> List[ToolUsage]:
        """Extract tool usage from text."""
        tools = []
        
        for pattern in self.tool_patterns:
            matches = re.finditer(pattern, text, re.DOTALL)
            for match in matches:
                raw_match = match.group(0)

                # Extract the tool name from the pattern type
                if '[TOOL:' in raw_match:
                    tool_name = "TOOL"
                    try:
                        # Extract arguments part (group 2 for TOOL pattern)
                        args_str = match.group(2)
                        arguments = json.loads(args_str)
                    except (json.JSONDecodeError, IndexError):
                        # If JSON parsing fails or group doesn't exist, extract from raw match
                        arguments = {"raw": match.group(1) if len(match.groups()) > 0 else ""}
                elif '[FILE:' in raw_match:
                    tool_name = "FILE"
                    operation = match.group(1)
                    path = match.group(2) if len(match.groups()) > 1 else ""
                    arguments = {"operation": operation, "path": path}
                elif '[EXEC:' in raw_match:
                    tool_name = "EXEC"
                    command = match.group(1)  # This is the command part
                    arguments = {"command": command}
                elif '[SEARCH:' in raw_match:
                    tool_name = "SEARCH"
                    query = match.group(1)  # This is the query part
                    arguments = {"query": query}
                else:
                    # Generic fallback
                    tool_name = match.group(1)  # First capture group is the tool name
                    arguments = {"raw": " ".join(match.groups()[1:])}

                tool = ToolUsage(
                    tool_name=tool_name,
                    arguments=arguments,
                    raw_content=raw_match
                )
                tools.append(tool)
        
        return tools
    
    def _remove_tool_markers(self, text: str) -> str:
        """Remove tool markers from text, leaving only the readable content."""
        result = text
        for pattern in self.tool_patterns:
            result = re.sub(pattern, '', result, flags=re.DOTALL)
        
        # Clean up any extra whitespace created by removal
        result = re.sub(r'\n\s*\n', '\n\n', result)  # Replace multiple newlines with double
        result = result.strip()
        
        return result
    
    def _extract_output_metadata(self, output_text: str) -> Dict[str, Any]:
        """Extract metadata from output text."""
        metadata = {
            'has_tools': len(self._extract_tools(output_text)) > 0,
            'char_count': len(output_text),
            'line_count': len(output_text.split('\n'))
        }
        
        return metadata
    
    def encode_as_json(self, parsed_input: Optional[ParsedInput] = None, 
                      parsed_output: Optional[ParsedOutput] = None) -> str:
        """
        Encode parsed input/output as JSON for client communication.
        
        Args:
            parsed_input: Optional parsed input
            parsed_output: Optional parsed output
            
        Returns:
            JSON-encoded string
        """
        data = {}
        
        if parsed_input:
            data['input'] = {
                'raw': parsed_input.raw_content,
                'processed': parsed_input.processed_content,
                'metadata': parsed_input.metadata
            }
        
        if parsed_output:
            data['output'] = {
                'raw': parsed_output.raw_content,
                'text_content': parsed_output.text_content,
                'tools': [
                    {
                        'name': tool.tool_name,
                        'arguments': tool.arguments,
                        'raw': tool.raw_content,
                        'execution_result': tool.execution_result
                    }
                    for tool in parsed_output.tools
                ],
                'metadata': parsed_output.metadata
            }
        
        return json.dumps(data, indent=2)