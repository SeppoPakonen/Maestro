import platform
import socket
import subprocess
from enum import Enum
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod


class HostType(Enum):
    LOCAL = "local"
    REMOTE_SSH = "remote_ssh"
    DOCKER = "docker"
    CONTAINER = "container"


class Host:
    """Base class for host abstraction (local, remote, docker)."""

    def __init__(self, host_type: HostType, name: str = "default"):
        self.host_type = host_type
        self.name = name
    
    def execute_command(self, command: str, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> tuple[int, str, str]:
        """Execute a command on the host."""
        raise NotImplementedError("execute_command must be implemented by subclasses")
    
    def get_platform_info(self) -> Dict[str, str]:
        """Get platform information about the host."""
        raise NotImplementedError("get_platform_info must be implemented by subclasses")
    
    def file_exists(self, path: str) -> bool:
        """Check if a file exists on the host."""
        raise NotImplementedError("file_exists must be implemented by subclasses")
    
    def copy_file(self, src: str, dest: str) -> bool:
        """Copy a file to/from the host."""
        raise NotImplementedError("copy_file must be implemented by subclasses")


class LocalHost(Host):
    """Local host implementation."""
    
    def __init__(self):
        super().__init__(HostType.LOCAL, "localhost")
        self.platform = platform.system().lower()
        self.architecture = platform.machine()
        self.hostname = socket.gethostname()
    
    def execute_command(self, command: str, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> tuple[int, str, str]:
        """Execute a command locally."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return -1, "", str(e)
    
    def get_platform_info(self) -> Dict[str, str]:
        """Get local platform information."""
        return {
            "os": platform.system(),
            "platform": platform.platform(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": self.hostname
        }
    
    def file_exists(self, path: str) -> bool:
        """Check if a file exists locally."""
        import os
        return os.path.exists(path)
    
    def copy_file(self, src: str, dest: str) -> bool:
        """Copy a file locally."""
        import shutil
        try:
            shutil.copy2(src, dest)
            return True
        except Exception:
            return False


class RemoteSSHHost(Host):
    """Remote host connected via SSH."""
    
    def __init__(self, hostname: str, username: str, port: int = 22, ssh_key_path: Optional[str] = None):
        super().__init__(HostType.REMOTE_SSH, hostname)
        self.hostname = hostname
        self.username = username
        self.port = port
        self.ssh_key_path = ssh_key_path
    
    def execute_command(self, command: str, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> tuple[int, str, str]:
        """Execute a command on remote host via SSH."""
        ssh_cmd = ["ssh"]
        
        if self.ssh_key_path:
            ssh_cmd.extend(["-i", self.ssh_key_path])
        
        ssh_cmd.extend([f"-p{self.port}", f"{self.username}@{self.hostname}"])
        
        if cwd:
            command = f"cd {cwd} && {command}"
        
        if env:
            env_str = " ".join([f"{k}={v}" for k, v in env.items()])
            command = f"{env_str} {command}"
        
        ssh_cmd.append(command)
        
        try:
            result = subprocess.run(
                " ".join(ssh_cmd),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return -1, "", str(e)
    
    def get_platform_info(self) -> Dict[str, str]:
        """Get platform information from remote host."""
        # Execute uname command to get OS info from remote system
        ret_code, stdout, stderr = self.execute_command("uname -a")
        if ret_code == 0:
            parts = stdout.strip().split()
            if len(parts) >= 3:
                return {
                    "os": parts[0],
                    "hostname": parts[1],
                    "kernel_version": parts[2]
                }
        
        return {
            "os": "unknown",
            "hostname": self.hostname
        }
    
    def file_exists(self, path: str) -> bool:
        """Check if a file exists on remote host."""
        ret_code, _, _ = self.execute_command(f"test -e {path}")
        return ret_code == 0
    
    def copy_file(self, src: str, dest: str) -> bool:
        """Copy a file to/from the remote host using scp."""
        scp_cmd = ["scp"]
        
        if self.ssh_key_path:
            scp_cmd.extend(["-i", self.ssh_key_path])
        
        scp_cmd.extend([f"-P{self.port}", src, f"{self.username}@{self.hostname}:{dest}"])
        
        try:
            result = subprocess.run(
                " ".join(scp_cmd),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False


class DockerHost(Host):
    """Docker container as a build host."""
    
    def __init__(self, container_id: str, image_name: str):
        super().__init__(HostType.DOCKER, container_id)
        self.container_id = container_id
        self.image_name = image_name
    
    def execute_command(self, command: str, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> tuple[int, str, str]:
        """Execute a command in the docker container."""
        docker_cmd = ["docker", "exec"]
        
        if cwd:
            docker_cmd.extend(["-w", cwd])
        
        if env:
            for k, v in env.items():
                docker_cmd.extend(["-e", f"{k}={v}"])
        
        docker_cmd.extend([self.container_id, "sh", "-c", command])
        
        try:
            result = subprocess.run(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return -1, "", str(e)
    
    def get_platform_info(self) -> Dict[str, str]:
        """Get platform information from the container."""
        ret_code, stdout, stderr = self.execute_command("uname -a")
        if ret_code == 0:
            parts = stdout.strip().split()
            if len(parts) >= 3:
                return {
                    "os": parts[0],
                    "hostname": parts[1],
                    "kernel_version": parts[2]
                }
        
        return {
            "os": "unknown",
            "container_id": self.container_id
        }
    
    def file_exists(self, path: str) -> bool:
        """Check if a file exists in the container."""
        ret_code, _, _ = self.execute_command(f"test -e {path}")
        return ret_code == 0
    
    def copy_file(self, src: str, dest: str) -> bool:
        """Copy a file to/from the container using docker cp."""
        try:
            result = subprocess.run(
                ["docker", "cp", src, f"{self.container_id}:{dest}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False


def get_current_host() -> Host:
    """Get the current host based on platform."""
    return LocalHost()


def create_host(host_type: HostType, **kwargs) -> Host:
    """Factory function to create hosts based on type."""
    if host_type == HostType.LOCAL:
        return LocalHost()
    elif host_type == HostType.REMOTE_SSH:
        return RemoteSSHHost(
            hostname=kwargs.get('hostname'),
            username=kwargs.get('username'),
            port=kwargs.get('port', 22),
            ssh_key_path=kwargs.get('ssh_key_path')
        )
    elif host_type == HostType.DOCKER:
        return DockerHost(
            container_id=kwargs.get('container_id'),
            image_name=kwargs.get('image_name')
        )
    else:
        raise ValueError(f"Unsupported host type: {host_type}")