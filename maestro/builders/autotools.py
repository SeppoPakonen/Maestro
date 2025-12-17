"""
Autotools Builder Implementation

This builder implements the Autotools (autoconf/automake) build system.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
import platform

from .base import Builder, Package
from .config import MethodConfig
from .console import execute_command


class AutotoolsBuilder(Builder):
    """Autotools builder implementation."""

    def __init__(self, config: MethodConfig = None):
        super().__init__("autotools", config)

    def configure(self, package: Package) -> bool:
        """Run ./configure script for autotools-based package."""
        # Determine if we need to run autoreconf to generate configure script
        if not self._needs_autoreconf(package.path):
            print(f"Using existing configure script for {package.name}")
        else:
            print(f"Running autoreconf for {package.name}")
            if not self._run_autoreconf(package.path):
                return False

        # Determine if we should use out-of-source build
        use_out_of_source = self.config.custom.get('out_of_source', False)
        if use_out_of_source:
            # Create build directory for out-of-source build
            build_dir = os.path.join(
                self.config.config.target_dir,
                self.config.name,
                package.name,
                "build"
            )
            os.makedirs(build_dir, exist_ok=True)
            configure_dir = build_dir  # Configuration will run in build directory
            configure_script_path = os.path.join(package.path, 'configure')  # Configure script still in source
        else:
            # In-source build
            configure_dir = package.path
            configure_script_path = os.path.join(package.path, 'configure')

        # Set up configure arguments
        configure_args = [configure_script_path]

        # Add installation prefix
        configure_args.append(f'--prefix={self.config.config.install_prefix}')

        # Add build type flags for debug/release
        if self.config.config.build_type.value.lower() == 'debug':
            configure_args.append('--enable-debug')
            # Additional debug flags
            # Add compiler flags from config
            cflags = " ".join(self.config.compiler.cflags)
            cxxflags = " ".join(self.config.compiler.cxxflags)
            ldflags = " ".join(self.config.compiler.ldflags)

            if cflags:
                configure_args.append(f'CFLAGS={cflags}')
            if cxxflags:
                configure_args.append(f'CXXFLAGS={cxxflags}')
            if ldflags:
                configure_args.append(f'LDFLAGS={ldflags}')
        else:
            configure_args.append('--disable-debug')
            # Additional release flags
            cflags = " ".join(self.config.compiler.cflags)
            cxxflags = " ".join(self.config.compiler.cxxflags)
            ldflags = " ".join(self.config.compiler.ldflags)

            if cflags:
                configure_args.append(f'CFLAGS={cflags}')
            if cxxflags:
                configure_args.append(f'CXXFLAGS={cxxflags}')
            if ldflags:
                configure_args.append(f'LDFLAGS={ldflags}')

        # Add compiler from config
        if self.config.compiler.cc:
            configure_args.append(f'CC={self.config.compiler.cc}')
        if self.config.compiler.cxx:
            configure_args.append(f'CXX={self.config.compiler.cxx}')

        # Add cross-compilation support if specified in package config
        if 'host' in package.config:
            configure_args.append(f'--host={package.config["host"]}')
        if 'build' in package.config:
            configure_args.append(f'--build={package.config["build"]}')
        if 'target' in package.config:
            configure_args.append(f'--target={package.config["target"]}')

        # Add custom configure options from package metadata
        custom_options = package.config.get('configure_options', [])
        for option in custom_options:
            configure_args.append(option)

        # Add platform-specific defaults
        if platform.system().lower() == 'darwin':  # macOS
            # Set proper SDK for macOS
            configure_args.extend([
                'CPPFLAGS=-mmacosx-version-min=10.9',
                'CFLAGS=-mmacosx-version-min=10.9',
                'CXXFLAGS=-mmacosx-version-min=10.9'
            ])

        try:
            result = execute_command(configure_args, cwd=configure_dir, verbose=self.config.config.verbose)
            return result.returncode == 0
        except Exception as e:
            print(f"Autotools configure failed: {str(e)}")
            return False

    def build_package(self, package: Package) -> bool:
        """Build using make."""
        # First run configure to ensure the environment is set up
        if not self.configure(package):
            return False

        # Determine build directory based on out-of-source setting
        use_out_of_source = self.config.custom.get('out_of_source', False)
        if use_out_of_source:
            build_dir = os.path.join(
                self.config.config.target_dir,
                self.config.name,
                package.name,
                "build"
            )
            build_cwd = build_dir
        else:
            build_cwd = package.path

        # Determine which make command to use (gnu make vs bsd make)
        make_cmd = self._get_make_command()

        # Prepare make arguments
        make_args = [make_cmd]

        # Add parallel build support if enabled
        jobs = self.config.config.jobs if self.config.config.jobs > 0 else os.cpu_count() or 4
        if self.config.config.parallel:
            # GNU make uses -j, BSD make uses -j too for parallel jobs
            make_args.extend(['-j', str(jobs)])

        # Add specific target if requested
        target = package.config.get('target')
        if target:
            make_args.append(target)

        try:
            result = execute_command(make_args, cwd=build_cwd, verbose=self.config.config.verbose)
            return result.returncode == 0
        except Exception as e:
            print(f"Autotools build failed: {str(e)}")
            return False

    def link(self, linkfiles: List[str], linkoptions: Dict[str, Any]) -> bool:
        """For autotools projects, linking is typically handled by make.

        This method would be called if Maestro needs to perform a custom link step,
        but for typical autotools projects, the build step handles linking.
        """
        # In autotools, linking is usually handled by the build process itself
        # This is just a placeholder implementation for interface compliance
        print("Autotools link step: For autotools projects, linking is typically handled by the build process.")
        return True

    def clean_package(self, package: Package) -> bool:
        """Clean package build artifacts using make."""
        # Determine directory based on out-of-source setting
        # Usually, clean is run in the same directory as the build
        # For in-source builds, this is the package path
        # For out-of-source builds, this is the build directory

        # For simplicity, we can try both directories
        # First try the build directory if it exists
        build_dir = os.path.join('.maestro', 'build', self.name, package.name, "build")

        # Get the appropriate make command
        make_cmd = self._get_make_command()

        # Prepare make arguments
        make_args = [make_cmd, 'clean']

        if os.path.exists(build_dir):
            # If build directory exists, clean there
            try:
                result = execute_command(make_args, cwd=build_dir)
                return result.returncode == 0
            except:
                # If clean fails in build dir, try in source dir
                pass

        # If build dir doesn't exist or clean failed there, try in source dir
        try:
            result = execute_command(make_args, cwd=package.path)
            return result.returncode == 0
        except Exception as e:
            print(f"Autotools clean failed: {str(e)}")
            return False

    def install_package(self, package: Package) -> bool:
        """Install the package using make install."""
        # Installation is typically done from the build directory for out-of-source builds
        # but the make install command doesn't need to be run from the build directory
        # since it knows where the built files are

        # Determine directory based on out-of-source setting
        use_out_of_source = self.config.custom.get('out_of_source', False)
        if use_out_of_source:
            build_dir = os.path.join(
                self.config.config.target_dir,
                self.config.name,
                package.name,
                "build"
            )
            if os.path.exists(build_dir):
                install_cwd = build_dir
            else:
                # If build dir doesn't exist, try configure script location
                install_cwd = package.path
        else:
            install_cwd = package.path

        # Get the appropriate make command
        make_cmd = self._get_make_command()
        make_args = [make_cmd, 'install']

        try:
            result = execute_command(make_args, cwd=install_cwd, verbose=self.config.config.verbose)
            return result.returncode == 0
        except Exception as e:
            print(f"Autotools install failed: {str(e)}")
            return False

    def distclean_package(self, package: Package) -> bool:
        """Remove configuration files and generated sources."""
        # For distclean, we usually want to run it from source directory since
        # it cleans up the configure-generated files there

        # Get the appropriate make command
        make_cmd = self._get_make_command()
        make_args = [make_cmd, 'distclean']

        # Try build directory first if using out-of-source
        build_dir = os.path.join('.maestro', 'build', self.name, package.name, "build")

        if os.path.exists(build_dir):
            try:
                result = execute_command(make_args, cwd=build_dir)
                if result.returncode == 0:
                    return True
            except:
                # If distclean fails in build dir, continue to try source dir
                pass

        # Try source directory
        try:
            result = execute_command(make_args, cwd=package.path)
            if result.returncode != 0:
                raise Exception("distclean failed in source directory")
            return True
        except Exception as e:
            print(f"Autotools distclean failed: {str(e)}")
            # If distclean fails, try to clean as much as possible
            # Attempt to remove common generated files/directories
            import shutil
            generated_dirs = ['autom4te.cache', '.deps', 'build-aux']
            for gen_dir in generated_dirs:
                gen_path = os.path.join(package.path, gen_dir)
                if os.path.exists(gen_path):
                    try:
                        shutil.rmtree(gen_path)
                    except:
                        pass  # Continue even if removal fails for some dirs
            return True  # Consider distclean successful if we got this far

    def get_target_ext(self) -> str:
        """Return target file extension based on platform."""
        system = platform.system().lower()

        if system == 'windows':
            return '.exe'  # On Windows, executables typically have .exe
        elif system in ['linux', 'darwin']:  # Darwin is macOS
            return ''  # Unix-like systems typically have no extension for executables
        else:
            return ''  # Default case

    def _needs_autoreconf(self, package_path: str) -> bool:
        """Check if autoreconf needs to be run by checking for configure script."""
        configure_script = os.path.join(package_path, 'configure')
        return not os.path.exists(configure_script)

    def _get_make_command(self) -> str:
        """Detect and return the appropriate make command (gnu make vs bsd make)."""
        import subprocess
        import platform

        # On macOS, BSD make is typical but GNU make might be installed as 'gmake'
        # On Linux and other Unix systems, make is typically GNU make
        # On some systems GNU make might be installed as 'gmake' vs 'make'

        system = platform.system().lower()

        # On macOS, first try to see if gmake is available
        if system == 'darwin':  # macOS
            try:
                result = subprocess.run(['which', 'gmake'],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      text=True)
                if result.returncode == 0:
                    return 'gmake'  # Use GNU make if available
                else:
                    # Fall back to regular make (BSD make on macOS)
                    return 'make'
            except:
                return 'make'

        # On other systems, test if make is GNU make
        try:
            result = subprocess.run(['make', '--version'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  text=True)
            if result.returncode == 0 and 'GNU' in result.stdout:
                return 'make'  # GNU make
            else:
                # If not GNU make, see if gmake is available
                result = subprocess.run(['which', 'gmake'],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      text=True)
                if result.returncode == 0:
                    return 'gmake'
                else:
                    return 'make'  # Default to make
        except:
            return 'make'  # Default fallback

    def _run_autoreconf(self, package_path: str) -> bool:
        """Run autoreconf to generate configure script from configure.ac."""
        autoreconf_args = ['autoreconf', '-i', '-f']  # -i for install aux files, -f for force

        # Add verbose flag if needed
        if self.config.config.verbose:
            autoreconf_args.append('-v')

        try:
            result = execute_command(autoreconf_args, cwd=package_path, verbose=self.config.config.verbose)
            return result.returncode == 0
        except Exception as e:
            print(f"Autoreconf failed: {str(e)}")
            return False