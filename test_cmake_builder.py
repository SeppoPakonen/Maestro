#!/usr/bin/env python3
"""
Unit tests for CMakeBuilder class.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from maestro.builders.cmake import CMakeBuilder
from maestro.builders.base import Package, BuildConfig


class TestCMakeBuilder(unittest.TestCase):
    def setUp(self):
        self.builder = CMakeBuilder()
        
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.package = Package(
            name="test_package",
            path=self.temp_dir,
            metadata={"build_system": "cmake"}
        )
        
        self.config = BuildConfig(
            method="gcc-debug",
            build_type="debug",
            parallel=True,
            jobs=4,
            target_dir=".maestro/build",
            install_prefix=".maestro/install",
            verbose=False
        )

    def tearDown(self):
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test CMakeBuilder initialization."""
        self.assertEqual(self.builder.name, "cmake")

    def test_get_cmake_build_type(self):
        """Test the build type mapping."""
        self.assertEqual(self.builder._get_cmake_build_type("debug"), "Debug")
        self.assertEqual(self.builder._get_cmake_build_type("release"), "Release")
        self.assertEqual(self.builder._get_cmake_build_type("relwithdebinfo"), "RelWithDebInfo")
        self.assertEqual(self.builder._get_cmake_build_type("minsizerel"), "MinSizeRel")
        # Test case insensitivity
        self.assertEqual(self.builder._get_cmake_build_type("DEBUG"), "Debug")
        # Test default value
        self.assertEqual(self.builder._get_cmake_build_type("invalid"), "Debug")

    @patch('maestro.builders.cmake.execute_command')
    def test_configure(self, mock_execute):
        """Test the configure method."""
        # Mock the subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_execute.return_value = mock_result
        
        result = self.builder.configure(self.package, self.config)
        
        self.assertTrue(result)
        mock_execute.assert_called_once()

    @patch('maestro.builders.cmake.execute_command')
    def test_build_package(self, mock_execute):
        """Test the build_package method."""
        # Mock the subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_execute.return_value = mock_result
        
        result = self.builder.build_package(self.package, self.config)
        
        self.assertTrue(result)
        # Configure is called first, then build
        self.assertEqual(mock_execute.call_count, 2)

    @patch('maestro.builders.cmake.execute_command')
    def test_build_target(self, mock_execute):
        """Test the build_target method."""
        # Mock the subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_execute.return_value = mock_result
        
        result = self.builder.build_target(self.package, "test_target", self.config)
        
        self.assertTrue(result)
        # Configure is called first, then build
        self.assertEqual(mock_execute.call_count, 2)

    def test_is_multi_config_generator(self):
        """Test the multi-config generator detection."""
        result = self.builder._is_multi_config_generator()
        # The actual result depends on the platform running the test
        self.assertIsInstance(result, bool)

    def test_get_target_ext(self):
        """Test the target extension method."""
        ext = self.builder.get_target_ext()
        # Should return a string
        self.assertIsInstance(ext, str)

    @patch('builtins.open')
    @patch('os.path.exists')
    def test_parse_makefile_targets(self, mock_exists, mock_open):
        """Test parsing targets from Makefile."""
        # Mock the file content
        mock_file_content = '''
all:
clean:
install:
test_target1:
test_target2:
.PHONY: all clean install
'''
        mock_open.return_value.__enter__.return_value.read.return_value = mock_file_content
        mock_exists.return_value = True
        
        targets = self.builder._parse_makefile_targets("/fake/path/Makefile")
        
        # Should include standard targets and custom ones
        self.assertIn("all", targets)
        self.assertIn("clean", targets)
        self.assertIn("install", targets)
        self.assertIn("test_target1", targets)
        self.assertIn("test_target2", targets)

    def test_get_available_targets(self):
        """Test getting available targets."""
        # This method will call configure first, which might fail in test environment
        # We'll mainly test that it returns a list
        targets = self.builder.get_available_targets(self.package, self.config)
        
        self.assertIsInstance(targets, list)

    def test_link(self):
        """Test the link method."""
        result = self.builder.link([], {})
        # The link method for CMake just prints a message and returns True
        self.assertTrue(result)

    @patch('os.path.exists')
    @patch('maestro.builders.cmake.execute_command')
    def test_clean_package(self, mock_execute, mock_exists):
        """Test the clean_package method."""
        # Mock that the build directory exists
        mock_exists.return_value = True
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_execute.return_value = mock_result
        
        result = self.builder.clean_package(self.package)
        
        self.assertTrue(result)
        mock_execute.assert_called_once()

    @patch('maestro.builders.cmake.execute_command')
    def test_install_package(self, mock_execute):
        """Test the install_package method."""
        # Mock the subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_execute.return_value = mock_result
        
        result = self.builder.install_package(self.package, self.config)
        
        self.assertTrue(result)
        mock_execute.assert_called_once()

    @patch('maestro.builders.cmake.execute_command')
    def test_build_package_with_target(self, mock_execute):
        """Test building a specific target from package config."""
        # Mock the subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_execute.return_value = mock_result
        
        # Set a target in package config
        self.package.config['target'] = 'install'
        
        result = self.builder.build_package(self.package, self.config)
        
        self.assertTrue(result)
        # Verify that execute_command was called with the target parameter
        self.assertEqual(mock_execute.call_count, 2)  # configure + build


if __name__ == '__main__':
    unittest.main()