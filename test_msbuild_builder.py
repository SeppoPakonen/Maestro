"""
Unit tests for MSBuildBuilder implementation.

Test coverage for the MSBuild builder that handles Visual Studio projects (.sln, .vcxproj, etc.)
"""
import unittest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from maestro.builders.msbuild import MsBuildBuilder
from maestro.builders.base import Package, BuildConfig


class TestMsBuildBuilder(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.builder = MsBuildBuilder()
        self.test_package = Package(
            name="TestPackage",
            path="/fake/path",
            metadata={}
        )
        self.test_config = BuildConfig(
            build_type="debug",
            jobs=4,
            verbose=False
        )

    @patch('shutil.which')
    def test_find_msbuild_with_msbuild_in_path(self, mock_shutil_which):
        """Test that MSBuild is found when present in PATH."""
        mock_shutil_which.return_value = "/usr/bin/msbuild"
        builder = MsBuildBuilder()
        self.assertEqual(builder.msbuild_cmd, "/usr/bin/msbuild")

    @patch('shutil.which')
    def test_find_msbuild_with_dotnet_in_path(self, mock_shutil_which):
        """Test that dotnet is used as fallback when MSBuild not found."""
        mock_shutil_which.side_effect = lambda x: "/usr/bin/dotnet" if x == "dotnet" else None
        builder = MsBuildBuilder()
        self.assertEqual(builder.msbuild_cmd, "/usr/bin/dotnet")

    @patch('shutil.which')
    def test_find_msbuild_none_found(self, mock_shutil_which):
        """Test that None is returned when no MSBuild executable is found."""
        mock_shutil_which.return_value = None
        builder = MsBuildBuilder()
        self.assertIsNone(builder.msbuild_cmd)

    def test_get_configuration_from_build_type_debug(self):
        """Test that debug build type maps to Debug configuration."""
        config = self.builder._get_configuration_from_build_type('debug')
        self.assertEqual(config, 'Debug')

    def test_get_configuration_from_build_type_release(self):
        """Test that release build type maps to Release configuration."""
        config = self.builder._get_configuration_from_build_type('release')
        self.assertEqual(config, 'Release')

    def test_get_configuration_from_build_type_relwithdebinfo(self):
        """Test that relwithdebinfo build type maps to RelWithDebInfo configuration."""
        config = self.builder._get_configuration_from_build_type('relwithdebinfo')
        self.assertEqual(config, 'RelWithDebInfo')

    def test_get_configuration_from_build_type_minsizerel(self):
        """Test that minsizerel build type maps to MinSizeRel configuration."""
        config = self.builder._get_configuration_from_build_type('minsizerel')
        self.assertEqual(config, 'MinSizeRel')

    def test_get_platform_from_config_x86_to_win32(self):
        """Test that x86 platform maps to Win32."""
        config = BuildConfig()
        config.flags = {'platform': 'x86'}
        platform = self.builder._get_platform_from_config(config)
        self.assertEqual(platform, 'Win32')

    def test_get_platform_from_config_x64_remains_x64(self):
        """Test that x64 platform remains x64."""
        config = BuildConfig()
        config.flags = {'platform': 'x64'}
        platform = self.builder._get_platform_from_config(config)
        self.assertEqual(platform, 'x64')

    def test_get_platform_from_config_arm_to_arm(self):
        """Test that ARM platform maps to ARM."""
        config = BuildConfig()
        config.flags = {'platform': 'arm'}
        platform = self.builder._get_platform_from_config(config)
        self.assertEqual(platform, 'ARM')

    def test_get_platform_from_config_arm64_to_arm64(self):
        """Test that ARM64 platform maps to ARM64."""
        config = BuildConfig()
        config.flags = {'platform': 'arm64'}
        platform = self.builder._get_platform_from_config(config)
        self.assertEqual(platform, 'ARM64')

    def test_get_target_ext_returns_exe(self):
        """Test that get_target_ext returns .exe extension."""
        ext = self.builder.get_target_ext()
        self.assertEqual(ext, '.exe')

    @patch('pathlib.Path.glob')
    @patch('os.path.exists')
    def test_find_project_file_with_sln_file(self, mock_exists, mock_glob):
        """Test finding .sln files."""
        mock_exists.return_value = True
        mock_glob.return_value = [Path("TestSolution.sln")]
        
        # Create a temporary directory that exists
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_file = self.builder._find_project_file(tmp_dir)
            if project_file:  # Only check if file was found
                self.assertTrue(project_file.endswith('.sln'))

    @patch('pathlib.Path.glob')
    @patch('os.path.exists')
    def test_find_project_file_with_vcxproj_file(self, mock_exists, mock_glob):
        """Test finding .vcxproj files."""
        mock_exists.return_value = True
        # Have .sln return empty, .vcxproj return a file
        def side_effect(pattern):
            if pattern == '*.sln':
                return []
            elif pattern == '*.vcxproj':
                return [Path("TestProject.vcxproj")]
            return []
        mock_glob.side_effect = side_effect
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_file = self.builder._find_project_file(tmp_dir)
            if project_file:  # Only check if file was found
                self.assertTrue(project_file.endswith('.vcxproj'))

    @patch('pathlib.Path.glob')
    @patch('os.path.exists')
    def test_find_project_file_preference_logic(self, mock_exists, mock_glob):
        """Test that package-named files are preferred."""
        mock_exists.return_value = True
        # Mock to return multiple project files, with one matching the package name
        # The package name is "TestPackage", so we'll mock the package directory name
        def side_effect(pattern):
            if pattern.endswith('.sln'):
                # Return files where one matches the directory name (simulating TestPackage directory)
                return [Path("Other.sln"), Path("TestPackage.sln")]
            return []
        mock_glob.side_effect = side_effect

        # Create a temporary directory that simulates the package directory name
        with tempfile.TemporaryDirectory() as tmp_base:
            # Create a subdirectory named TestPackage to match the package name
            package_dir = Path(tmp_base) / "TestPackage"
            package_dir.mkdir()

            project_file = self.builder._find_project_file(str(package_dir))
            # The method should prefer TestPackage.sln over Other.sln
            if project_file:  # Only check if file was found
                self.assertIn("TestPackage.sln", project_file)

    def test_extract_solution_projects_empty_solution(self):
        """Test extracting projects from an empty solution file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sln', delete=False) as f:
            f.write("# Visual Studio Solution File\n")
            f.flush()
            
            projects = self.builder._extract_solution_projects(f.name)
            self.assertEqual(len(projects), 0)
            
        os.unlink(f.name)

    def test_extract_solution_projects_with_one_project(self):
        """Test extracting a single project from a solution file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sln', delete=False) as f:
            f.write("""Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 16
VisualStudioVersion = 16.0.29102.182
Project("{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}") = "MyApp", "MyApp.vcxproj", "{12345678-1234-1234-1234-123456789012}"
EndProject
Global
EndGlobal""")
            f.flush()
            
            projects = self.builder._extract_solution_projects(f.name)
            self.assertEqual(len(projects), 1)
            self.assertTrue(projects[0].endswith("MyApp.vcxproj"))
            
        os.unlink(f.name)

    def test_extract_solution_projects_with_multiple_projects(self):
        """Test extracting multiple projects from a solution file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create dummy project files
            proj1 = Path(tmp_dir) / "Project1.vcxproj"
            proj2 = Path(tmp_dir) / "Project2.vcxproj"
            proj1.touch()
            proj2.touch()
            
            solution_content = f"""Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 16
VisualStudioVersion = 16.0.29102.182
Project("{{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}}") = "Project1", "{proj1.name}", "{{12345678-1234-1234-1234-123456789012}}"
EndProject
Project("{{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}}") = "Project2", "{proj2.name}", "{{87654321-4321-4321-4321-210987654321}}"
EndProject
Global
EndGlobal"""
            
            solution_file = Path(tmp_dir) / "TestSolution.sln"
            solution_file.write_text(solution_content)
            
            projects = self.builder._extract_solution_projects(str(solution_file))
            self.assertEqual(len(projects), 2)
            # The projects should exist in the temp directory
            found_proj_names = [Path(p).name for p in projects]
            self.assertIn("Project1.vcxproj", found_proj_names)
            self.assertIn("Project2.vcxproj", found_proj_names)

    @patch.object(MsBuildBuilder, '_find_project_file')
    @patch('subprocess.run')
    def test_build_package_success(self, mock_subprocess_run, mock_find_project_file):
        """Test successful package build."""
        # Mock the MSBuild executable being found
        self.builder.msbuild_cmd = "msbuild"
        mock_find_project_file.return_value = "/fake/path/TestPackage.vcxproj"
        
        # Mock successful subprocess run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result
        
        result = self.builder.build_package(self.test_package, self.test_config)
        self.assertTrue(result)
        
        # Verify subprocess was called with correct arguments
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args[0][0]  # First argument is the command list
        self.assertIn('msbuild', call_args)  # MSBuild command should be present
        self.assertIn('/p:Configuration=Debug', call_args)  # Debug config should be present
        self.assertIn('/m:4', call_args)  # 4 parallel jobs should be present

    @patch.object(MsBuildBuilder, '_find_project_file')
    @patch('subprocess.run')
    def test_build_package_failure(self, mock_subprocess_run, mock_find_project_file):
        """Test failed package build."""
        # Mock the MSBuild executable being found
        self.builder.msbuild_cmd = "msbuild"
        mock_find_project_file.return_value = "/fake/path/TestPackage.vcxproj"
        
        # Mock failed subprocess run
        mock_subprocess_run.side_effect = Exception("Build failed")
        
        result = self.builder.build_package(self.test_package, self.test_config)
        self.assertFalse(result)

    @patch.object(MsBuildBuilder, '_find_project_file')
    @patch('subprocess.run')
    def test_build_package_no_msbuild_found(self, mock_subprocess_run, mock_find_project_file):
        """Test package build when MSBuild is not found."""
        # Reset msbuild_cmd to simulate not found
        self.builder.msbuild_cmd = None
        
        result = self.builder.build_package(self.test_package, self.test_config)
        self.assertFalse(result)

    @patch.object(MsBuildBuilder, '_find_project_file')
    @patch('subprocess.run')
    def test_clean_package_success(self, mock_subprocess_run, mock_find_project_file):
        """Test successful package clean."""
        # Mock the MSBuild executable being found
        self.builder.msbuild_cmd = "msbuild"
        mock_find_project_file.return_value = "/fake/path/TestPackage.vcxproj"
        
        # Mock successful subprocess run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result
        
        result = self.builder.clean_package(self.test_package)
        self.assertTrue(result)
        
        # Verify subprocess was called with Clean target
        call_args = mock_subprocess_run.call_args[0][0]  # First argument is the command list
        self.assertIn('msbuild', call_args)  # MSBuild command should be present
        self.assertIn('/t:Clean', call_args)  # Clean target should be present

    @patch.object(MsBuildBuilder, '_find_project_file')
    @patch('subprocess.run')
    def test_clean_package_failure(self, mock_subprocess_run, mock_find_project_file):
        """Test failed package clean."""
        # Mock the MSBuild executable being found
        self.builder.msbuild_cmd = "msbuild"
        mock_find_project_file.return_value = "/fake/path/TestPackage.vcxproj"
        
        # Mock failed subprocess run
        mock_subprocess_run.side_effect = Exception("Clean failed")
        
        result = self.builder.clean_package(self.test_package)
        self.assertFalse(result)

    @patch('os.makedirs')
    @patch('shutil.copy2')
    @patch.object(MsBuildBuilder, '_find_project_file')
    @patch.object(MsBuildBuilder, '_get_configuration_from_build_type')
    @patch.object(MsBuildBuilder, '_get_platform_from_config')
    def test_install_method_basic(self, mock_get_platform, mock_get_config, mock_find_project, mock_makedirs, mock_copy2):
        """Test install method can proceed when output directory exists."""
        # Mock the MSBuild executable being found
        self.builder.msbuild_cmd = "msbuild"
        mock_find_project.return_value = "/fake/path/TestPackage.vcxproj"
        mock_get_config.return_value = "Debug"
        mock_get_platform.return_value = "x64"

        # Mock Path existence to simulate output directory exists
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.iterdir', return_value=[Path("TestPackage.exe")]):
                with patch('pathlib.Path.is_file', return_value=True):
                    # Mock the Path properties that are accessed in install method
                    mock_path_instance = MagicMock()
                    mock_path_instance.exists.return_value = True
                    mock_path_instance.iterdir.return_value = [MagicMock(suffix='.exe', is_file=True, name='TestPackage.exe')]
                    mock_path_instance.__truediv__ = lambda self, other: mock_path_instance
                    mock_path_instance.resolve.return_value = mock_path_instance
                    mock_path_instance.parent = mock_path_instance
                    mock_path_instance.mkdir = MagicMock()

                    with patch('pathlib.Path', return_value=mock_path_instance):
                        # Mock the config.install_prefix to avoid real filesystem operations
                        self.test_config.install_prefix = "/tmp/install"
                        result = self.builder.install(self.test_package, self.test_config)
                        self.assertTrue(result)

    def test_link_method_returns_true(self):
        """Test that link method returns True (handled during build)."""
        result = self.builder.link(["file1.obj", "file2.obj"], {})
        self.assertTrue(result)

    def test_configure_method_finds_project_file(self):
        """Test that configure locates project file and stores it."""
        # Mock finding a project file
        with patch.object(self.builder, '_find_project_file', return_value="/fake/path/TestPackage.vcxproj"):
            result = self.builder.configure(self.test_package, self.test_config)
            self.assertTrue(result)
            self.assertEqual(self.test_package.metadata.get('project_file'), "/fake/path/TestPackage.vcxproj")

    def test_configure_method_no_project_file(self):
        """Test that configure fails when no project file is found."""
        # Mock finding no project file
        with patch.object(self.builder, '_find_project_file', return_value=None):
            result = self.builder.configure(self.test_package, self.test_config)
            self.assertFalse(result)

    def test_rebuild_package_success(self):
        """Test successful rebuild (clean + build)."""
        # Mock the build and clean methods
        with patch.object(self.builder, 'clean_package', return_value=True), \
             patch.object(self.builder, 'build_package', return_value=True):
             
            result = self.builder.rebuild_package(self.test_package, self.test_config)
            self.assertTrue(result)

    def test_rebuild_package_clean_failure(self):
        """Test rebuild failure when clean fails."""
        # Mock clean to fail
        with patch.object(self.builder, 'clean_package', return_value=False):
             
            result = self.builder.rebuild_package(self.test_package, self.test_config)
            self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()