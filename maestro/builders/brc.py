"""
Binary Resource Compilation (.brc) support for Maestro.

Implements embedding of binary files into executables by generating 
C++ arrays from binary data with optional compression support.
"""

import os
import gzip
import bz2
import lzma
try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
import base64
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from ..repo.package import PackageInfo


@dataclass
class BRCConfig:
    """Configuration for binary resource compilation."""
    enabled: bool = True
    compress: bool = True  # Whether to compress resources
    compression_method: str = 'gzip'  # gzip, bz2, lzma, zstd, or 'none'
    embed_as_base64: bool = False  # Embed as base64 instead of raw bytes
    include_guard_pattern: str = "#ifdef EMBEDDED_RESOURCES\n{content}\n#endif"
    resource_extensions: List[str] = None  # Extensions to treat as resources
    max_resource_size: int = 100 * 1024 * 1024  # 100MB max resource size

    def __post_init__(self):
        if self.resource_extensions is None:
            self.resource_extensions = [
                # Images
                '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tga', '.dds',
                '.psd', '.svg', '.ico', '.webp',
                # Audio
                '.wav', '.mp3', '.ogg', '.flac', '.m4a', '.aac',
                # Video
                '.mp4', '.avi', '.mov', '.wmv', '.flv',
                # Text/data
                '.txt', '.json', '.xml', '.yaml', '.yml', '.ini', '.cfg',
                '.sql', '.csv', '.dat', '.bin',
                # Fonts
                '.ttf', '.otf', '.woff', '.woff2',
                # Other
                '.data', '.res', '.assets', '.pak', '.zip', '.rar'
            ]

        # If zstd is not available, remove it from possible compression methods
        if not ZSTD_AVAILABLE and self.compression_method == 'zstd':
            self.compression_method = 'gzip'  # Fallback to gzip


class CompressionError(Exception):
    """Raised when compression fails."""
    pass


class BRCEncoder:
    """Encodes binary data into C++ arrays."""
    
    @staticmethod
    def to_cpp_array(data: bytes, array_name: str = "embedded_data", 
                     compress: bool = False, method: str = 'gzip') -> str:
        """
        Converts binary data to a C++ byte array.
        
        Args:
            data: Binary data to convert
            array_name: Name of the C++ array variable
            compress: Whether to compress the data
            method: Compression method ('gzip', 'bz2', 'lzma', 'zstd', 'none')
            
        Returns:
            C++ code defining the byte array
        """
        if compress and method != 'none':
            original_size = len(data)
            if method == 'gzip':
                data = gzip.compress(data)
            elif method == 'bz2':
                data = bz2.compress(data)
            elif method == 'lzma':
                data = lzma.compress(data)
            elif method == 'zstd':
                if not ZSTD_AVAILABLE:
                    raise CompressionError("zstd compression is not available, please install the zstandard package")
                cctx = zstd.ZstdCompressor()
                data = cctx.compress(data)
            else:
                raise CompressionError(f"Unknown compression method: {method}")

            compression_info = f"// Original size: {original_size} bytes, Compressed size: {len(data)} bytes"
        else:
            compression_info = f"// Size: {len(data)} bytes"

        # Format data as C++ byte array
        hex_values = []
        for i, byte in enumerate(data):
            if i % 16 == 0 and i > 0:
                hex_values.append("\n    ")
            hex_values.append(f"0x{byte:02x}")
            if i < len(data) - 1:
                hex_values.append(", ")

        hex_string = "".join(hex_values)

        return f"""{compression_info}
static const unsigned char {array_name}[] = {{
    {hex_string}
}};
static const size_t {array_name}_size = {len(data)};"""


class BRCGenerator:
    """Generates C++ arrays from binary resources."""
    
    def __init__(self, config: BRCConfig = None):
        self.config = config or BRCConfig()
        
    def embed_resource(
        self, 
        resource_path: str, 
        array_name: str = None,
        output_dir: str = None
    ) -> Tuple[str, str]:
        """
        Embeds a binary resource as a C++ array.
        
        Args:
            resource_path: Path to the binary resource file
            array_name: Name of the C++ array (auto-generated if None)
            output_dir: Directory to write the generated file to
            
        Returns:
            Tuple of (path to generated C++ file, variable name of the embedded data)
        """
        if not os.path.exists(resource_path):
            raise FileNotFoundError(f"Resource file not found: {resource_path}")
            
        # Validate file size
        file_size = os.path.getsize(resource_path)
        if file_size > self.config.max_resource_size:
            raise ValueError(f"Resource file '{resource_path}' is too large ({file_size} bytes), max allowed: {self.config.max_resource_size} bytes")
        
        # Determine array name
        if array_name is None:
            # Generate array name from file path
            rel_path = os.path.relpath(resource_path)
            # Replace problematic characters with underscores
            array_name = ("resource_" + rel_path.replace('/', '_').replace('\\', '_').replace('.', '_').replace('-', '_')).replace(' ', '_')
        
        # Determine output directory
        if output_dir is None:
            output_dir = os.path.dirname(resource_path)
            
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Read the binary data
        with open(resource_path, 'rb') as f:
            binary_data = f.read()
        
        # Generate the C++ array code
        cpp_code = BRCEncoder.to_cpp_array(
            binary_data, 
            array_name,
            compress=self.config.compress,
            method=self.config.compression_method
        )
        
        # Create header file with the embedded resource
        resource_basename = os.path.basename(resource_path)
        output_filename = f"embedded_{resource_basename.replace('.', '_')}.h"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"""// Automatically generated by Maestro BRC system
// Source: {resource_path}
// This file contains embedded binary resource as C++ array

#ifndef EMBEDDED_RESOURCE_{array_name.upper()}_H
#define EMBEDDED_RESOURCE_{array_name.upper()}_H

{cpp_code}

#endif // EMBEDDED_RESOURCE_{array_name.upper()}_H
""")
        
        return output_path, array_name
    
    def embed_package_resources(
        self, 
        package: PackageInfo, 
        resource_files: List[str], 
        output_dir: str
    ) -> Dict[str, str]:
        """
        Embeds all specified resource files for a package as C++ arrays.
        
        Args:
            package: Package information
            resource_files: List of resource files to embed
            output_dir: Directory to write generated files to
            
        Returns:
            Dictionary mapping resource file paths to variable names
        """
        results = {}
        
        for resource_path in resource_files:
            full_resource_path = os.path.join(package.dir, resource_path) if not os.path.isabs(resource_path) else resource_path
            
            if not os.path.exists(full_resource_path):
                continue  # Skip non-existent files
                
            # Generate array name based on resource path
            rel_path = os.path.relpath(full_resource_path, package.dir)
            array_name = ("resource_" + rel_path.replace('/', '_').replace('\\', '_').replace('.', '_').replace('-', '_')).replace(' ', '_')
            
            # Embed the resource
            try:
                embedded_path, var_name = self.embed_resource(full_resource_path, array_name, output_dir)
                results[resource_path] = var_name
            except Exception as e:
                print(f"Warning: Could not embed resource {full_resource_path}: {str(e)}")
                
        return results


def is_resource_file(filepath: str, config: BRCConfig = None) -> bool:
    """
    Determines if a file should be treated as a resource file.
    
    Args:
        filepath: Path to the file to check
        config: BRC configuration (uses default if None)
        
    Returns:
        True if the file should be treated as a resource, False otherwise
    """
    if config is None:
        config = BRCConfig()
        
    _, ext = os.path.splitext(filepath.lower())
    return ext in config.resource_extensions


def get_all_resource_files(package_dir: str, config: BRCConfig = None) -> List[str]:
    """
    Finds all resource files in a package directory.
    
    Args:
        package_dir: Directory of the package
        config: BRC configuration (uses default if None)
        
    Returns:
        List of resource file paths relative to package directory
    """
    if config is None:
        config = BRCConfig()
        
    resource_files = []
    
    for root, dirs, files in os.walk(package_dir):
        for file in files:
            filepath = os.path.join(root, file)
            if is_resource_file(filepath, config):
                rel_path = os.path.relpath(filepath, package_dir)
                resource_files.append(rel_path)
                
    return resource_files


class BRCResource:
    """Represents an embedded binary resource."""
    
    def __init__(self, name: str, data: bytes, original_path: str = None):
        self.name = name
        self.data = data
        self.original_path = original_path
        
    def decompress(self, method: str = 'gzip') -> bytes:
        """
        Decompresses the embedded resource data.
        
        Args:
            method: Compression method used ('gzip', 'bz2', 'lzma', 'zstd', 'none')
            
        Returns:
            Decompressed data
        """
        if method == 'none':
            return self.data
        elif method == 'gzip':
            return gzip.decompress(self.data)
        elif method == 'bz2':
            return bz2.decompress(self.data)
        elif method == 'lzma':
            return lzma.decompress(self.data)
        elif method == 'zstd':
            if not ZSTD_AVAILABLE:
                raise CompressionError("zstd decompression is not available, please install the zstandard package")
            dctx = zstd.ZstdDecompressor()
            return dctx.decompress(self.data)
        else:
            raise CompressionError(f"Unknown compression method: {method}")
    
    def save_to_file(self, output_path: str, compressed: bool = False, 
                     compression_method: str = 'gzip'):
        """
        Saves the embedded resource to a file.
        
        Args:
            output_path: Path where to save the file
            compressed: Whether the embedded data is compressed
            compression_method: Method used for compression if compressed=True
        """
        data_to_save = self.data
        if compressed:
            data_to_save = self.decompress(compression_method)
            
        with open(output_path, 'wb') as f:
            f.write(data_to_save)