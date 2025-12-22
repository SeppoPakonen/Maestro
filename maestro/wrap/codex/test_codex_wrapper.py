"""
Simple test for the Codex wrapper functionality.
This test validates the basic functionality without requiring the actual codex binary.
"""
import unittest
import tempfile
import os
from maestro.wrap.codex.wrapper import CodexTuringMachine, State
from maestro.wrap.codex.parser import CodexParser, ToolUsage


class TestCodexTuringMachine(unittest.TestCase):
    """Test the Turing machine implementation."""
    
    def setUp(self):
        self.tm = CodexTuringMachine()
    
    def test_initial_state(self):
        """Test that the Turing machine starts in IDLE state."""
        self.assertEqual(self.tm.get_current_state(), State.IDLE)
    
    def test_state_transitions(self):
        """Test various state transitions."""
        # Test transition from IDLE to PROMPTING
        action = self.tm.transition("prompt_start")
        self.assertEqual(self.tm.get_current_state(), State.PROMPTING)
        self.assertEqual(action, "start_prompt_capture")
        
        # Test transition from PROMPTING to AWAITING_RESPONSE
        self.tm.state = State.PROMPTING
        action = self.tm.transition("input_complete")
        self.assertEqual(self.tm.get_current_state(), State.AWAITING_RESPONSE)
        self.assertEqual(action, "send_input")
        
        # Test transition from AWAITING_RESPONSE to PROCESSING_TOOLS
        self.tm.state = State.AWAITING_RESPONSE
        action = self.tm.transition("tool_detected")
        self.assertEqual(self.tm.get_current_state(), State.PROCESSING_TOOLS)
        self.assertEqual(action, "process_tools")


class TestCodexParser(unittest.TestCase):
    """Test the parser functionality."""
    
    def setUp(self):
        self.parser = CodexParser()
    
    def test_input_parsing(self):
        """Test parsing of input prompts."""
        input_text = "What is the capital of France?"
        parsed = self.parser.parse_input(input_text)
        
        self.assertEqual(parsed.raw_content, input_text)
        self.assertEqual(parsed.processed_content, input_text)
        self.assertEqual(parsed.metadata['type'], 'prompt')
    
    def test_command_parsing(self):
        """Test parsing of commands."""
        command_text = "/quit"
        parsed = self.parser.parse_input(command_text)
        
        self.assertEqual(parsed.raw_content, command_text)
        self.assertEqual(parsed.metadata['type'], 'command')
        self.assertEqual(parsed.metadata['command'], 'quit')
    
    def test_output_parsing(self):
        """Test parsing of AI output."""
        output_text = "The capital of France is Paris.\n[TOOL: search, {\"query\": \"Paris population\"}]"
        parsed = self.parser.parse_output(output_text)
        
        self.assertEqual(parsed.raw_content, output_text)
        self.assertIn("The capital of France is Paris.", parsed.text_content)
        self.assertEqual(len(parsed.tools), 1)
        self.assertEqual(parsed.tools[0].tool_name, "search")
        self.assertEqual(parsed.tools[0].arguments["query"], "Paris population")
        self.assertTrue(parsed.metadata['has_tools'])
    
    def test_json_encoding(self):
        """Test JSON encoding of parsed data."""
        input_text = "Hello, codex!"
        parsed_input = self.parser.parse_input(input_text)
        
        output_text = "Hello to you too!\n[FILE: read, {\"path\": \"/tmp/test.txt\"}]"
        parsed_output = self.parser.parse_output(output_text)
        
        json_str = self.parser.encode_as_json(parsed_input, parsed_output)
        data = eval(json_str)  # Using eval for simple parsing in test
        
        self.assertIn('input', data)
        self.assertIn('output', data)
        self.assertEqual(data['input']['raw'], input_text)
        self.assertIn('FILE', data['output']['raw'])


def test_integration():
    """Basic integration test."""
    print("Testing Turing Machine...")
    tm = CodexTuringMachine()
    assert tm.get_current_state() == State.IDLE
    print("✓ Turing Machine starts in IDLE state")
    
    print("Testing Parser...")
    parser = CodexParser()
    
    # Test input parsing
    parsed_input = parser.parse_input("Test prompt")
    assert parsed_input.processed_content == "Test prompt"
    print("✓ Input parsing works")
    
    # Test output parsing with tool
    output_with_tool = "Response with tool usage\n[EXEC: ls -la]"
    parsed_output = parser.parse_output(output_with_tool)
    assert len(parsed_output.tools) == 1
    assert parsed_output.tools[0].tool_name == "EXEC" or parsed_output.tools[0].tool_name == "exec"
    print("✓ Output parsing with tool detection works")
    
    # Test JSON encoding
    json_result = parser.encode_as_json(parsed_input, parsed_output)
    assert isinstance(json_result, str)
    print("✓ JSON encoding works")
    
    print("\nAll tests passed!")


if __name__ == "__main__":
    test_integration()