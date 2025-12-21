#!/usr/bin/env python3
"""
Unit tests for AutotoolsBuilder class.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from maestro.builders.autotools import AutotoolsBuilder
from maestro.builders.base import Package, BuildConfig


class TestAutotoolsBuilder(unittest.TestCase):
    def setUp(self):
        self.builder = AutotoolsBuilder()

        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.package = Package(
            name="test_package",
            path=self.temp_dir,
            metadata={"build_system": "autoconf"}
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
        """Test AutotoolsBuilder initialization."""
        self.assertEqual(self.builder.name, "autotools")

    @patch('maestro.builders.autotools.execute_command')
    def test_configure(self, mock_execute):
        """Test the configure method."""
        # Mock the subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_execute.return_value = mock_result

        # Create a fake configure script
        configure_path = os.path.join(self.temp_dir, 'configure')
        with open(configure_path, 'w') as f:
            f.write('#!/bin/bash\necho "configure executed"')

        result = self.builder.configure(self.package, self.config)

        self.assertTrue(result)
        mock_execute.assert_called_once()

    @patch('maestro.builders.autotools.execute_command')
    def test_build_package(self, mock_execute):
        """Test the build_package method."""
        # Mock the subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_execute.return_value = mock_result

        # Create a fake configure script
        configure_path = os.path.join(self.temp_dir, 'configure')
        with open(configure_path, 'w') as f:
            f.write('#!/bin/bash\necho "configure executed"')

        result = self.builder.build_package(self.package, self.config)

        self.assertTrue(result)
        # Configure is called first, then build
        self.assertEqual(mock_execute.call_count, 2)

    @patch('maestro.builders.autotools.execute_command')
    def test_build_package_with_target(self, mock_execute):
        """Test building a specific target from package config."""
        # Mock the subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_execute.return_value = mock_result

        # Create a fake configure script
        configure_path = os.path.join(self.temp_dir, 'configure')
        with open(configure_path, 'w') as f:
            f.write('#!/bin/bash\necho "configure executed"')

        # Set a target in package config
        self.package.config['target'] = 'install'

        result = self.builder.build_package(self.package, self.config)

        self.assertTrue(result)
        # Verify that execute_command was called with the target parameter
        self.assertEqual(mock_execute.call_count, 2)  # configure + build

    @patch('maestro.builders.autotools.execute_command')
    def test_clean_package(self, mock_execute):
        """Test the clean_package method."""
        # Mock the subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_execute.return_value = mock_result

        result = self.builder.clean_package(self.package)

        self.assertTrue(result)
        mock_execute.assert_called_once()

    @patch('maestro.builders.autotools.execute_command')
    def test_install_package(self, mock_execute):
        """Test the install_package method."""
        # Mock the subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_execute.return_value = mock_result

        result = self.builder.install_package(self.package, self.config)

        self.assertTrue(result)
        mock_execute.assert_called_once()

    def test_get_target_ext(self):
        """Test the target extension method."""
        ext = self.builder.get_target_ext()
        # Should return a string
        self.assertIsInstance(ext, str)

    def test_get_make_command(self):
        """Test the make command detection method."""
        make_cmd = self.builder._get_make_command()
        # Should return a string
        self.assertIsInstance(make_cmd, str)
        # Should be either 'make' or 'gmake'
        self.assertIn(make_cmd, ['make', 'gmake'])

    @patch('maestro.builders.autotools.execute_command')
    def test_distclean_package(self, mock_execute):
        """Test the distclean_package method."""
        # Mock the subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_execute.return_value = mock_result

        result = self.builder.distclean_package(self.package)

        self.assertTrue(result)
        mock_execute.assert_called_once()

    @patch('os.path.exists')
    def test_needs_autoreconf(self, mock_exists):
        """Test the _needs_autoreconf method."""
        # Test when configure exists
        mock_exists.return_value = True
        result = self.builder._needs_autoreconf(self.temp_dir)
        self.assertFalse(result)

        # Test when configure doesn't exist
        mock_exists.return_value = False
        result = self.builder._needs_autoreconf(self.temp_dir)
        self.assertTrue(result)

    @patch('maestro.builders.autotools.execute_command')
    def test_run_autoreconf(self, mock_execute):
        """Test the _run_autoreconf method."""
        # Mock the subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_execute.return_value = mock_result

        result = self.builder._run_autoreconf(self.temp_dir, self.config)

        self.assertTrue(result)
        mock_execute.assert_called_once()

    @patch('maestro.builders.autotools.execute_command')
    def test_out_of_source_build(self, mock_execute):
        """Test out-of-source build functionality."""
        # Mock the subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_execute.return_value = mock_result

        # Create a fake configure script
        configure_path = os.path.join(self.temp_dir, 'configure')
        with open(configure_path, 'w') as f:
            f.write('#!/bin/bash\necho "configure executed"')

        # Enable out-of-source build
        self.config.flags['out_of_source'] = True

        result = self.builder.build_package(self.package, self.config)

        self.assertTrue(result)
        # Configure is called first, then build
        self.assertEqual(mock_execute.call_count, 2)

    @patch('maestro.builders.autotools.execute_command')
    def test_cross_compilation_flags(self, mock_execute):
        """Test cross-compilation flags in configure."""
        # Mock the subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_execute.return_value = mock_result

        # Create a fake configure script
        configure_path = os.path.join(self.temp_dir, 'configure')
        with open(configure_path, 'w') as f:
            f.write('#!/bin/bash\necho "configure executed"')

        # Add cross-compilation config
        self.package.config['host'] = 'arm-linux-gnueabihf'
        self.package.config['build'] = 'x86_64-pc-linux-gnu'
        self.package.config['target'] = 'arm-linux-gnueabihf'

        result = self.builder.configure(self.package, self.config)

        self.assertTrue(result)
        # Check that execute_command was called with cross-compilation flags
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args[0][0]  # Get the first argument which is the command list
        self.assertIn('--host=arm-linux-gnueabihf', call_args)
        self.assertIn('--build=x86_64-pc-linux-gnu', call_args)
        self.assertIn('--target=arm-linux-gnueabihf', call_args)

    @patch('maestro.builders.autotools.execute_command')
    def test_custom_configure_options(self, mock_execute):
        """Test custom configure options."""
        # Mock the subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_execute.return_value = mock_result

        # Create a fake configure script
        configure_path = os.path.join(self.temp_dir, 'configure')
        with open(configure_path, 'w') as f:
            f.write('#!/bin/bash\necho "configure executed"')

        # Add custom configure options
        self.package.config['configure_options'] = ['--enable-feature', '--with-option=value']

        result = self.builder.configure(self.package, self.config)

        self.assertTrue(result)
        # Check that execute_command was called with custom options
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args[0][0]  # Get the first argument which is the command list
        self.assertIn('--enable-feature', call_args)
        self.assertIn('--with-option=value', call_args)


if __name__ == '__main__':
    unittest.main()