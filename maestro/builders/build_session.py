"""
Build session management and error recovery module.

Implements BuildSession class and error recovery functionality
as required in Phase 12: Error Recovery and Build Sessions.
"""

import json
import os
import time
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from enum import Enum


class BuildStatus(Enum):
    """Status of a build operation."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BuildStepResult:
    """Result of a single build step."""
    package_name: str
    status: BuildStatus
    start_time: float
    end_time: float
    duration: float
    error_message: Optional[str] = None
    output_log: str = ""
    dependencies: List[str] = field(default_factory=list)
    build_system: str = "upp"


@dataclass
class BuildSession:
    """Manages a build session with error recovery and tracking."""
    
    session_id: str
    start_time: float
    packages_to_build: List[str]
    config: Dict[str, Any] = field(default_factory=dict)
    results: List[BuildStepResult] = field(default_factory=list)
    completed_packages: List[str] = field(default_factory=list)
    failed_packages: List[str] = field(default_factory=list)
    skipped_packages: List[str] = field(default_factory=list)
    continue_on_error: bool = True  # Whether to continue when one package fails
    resume_from: Optional[str] = None  # Package to resume from if restarting
    output_dir: str = ""
    end_time: Optional[float] = None
    total_duration: Optional[float] = None
    
    def __post_init__(self):
        """Initialize the session after dataclass creation."""
        if not self.session_id:
            self.session_id = f"build_session_{int(self.start_time)}_{hash(str(self.packages_to_build)) % 10000}"
        
        # Create output directory if it doesn't exist
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
    
    def add_result(self, result: BuildStepResult):
        """Add a build result to the session."""
        self.results.append(result)
        
        if result.status == BuildStatus.SUCCESS:
            self.completed_packages.append(result.package_name)
        elif result.status == BuildStatus.FAILED:
            self.failed_packages.append(result.package_name)
        elif result.status == BuildStatus.SKIPPED:
            self.skipped_packages.append(result.package_name)
    
    def get_next_package(self) -> Optional[str]:
        """Get the next package to build based on completed and failed packages."""
        for pkg in self.packages_to_build:
            if pkg not in self.completed_packages and pkg not in self.failed_packages:
                # Check if dependencies are satisfied
                # This is simplified - in a real scenario, you might want to integrate with dependency resolver
                return pkg
        return None
    
    def has_failed(self) -> bool:
        """Check if any packages have failed."""
        return len(self.failed_packages) > 0
    
    def is_complete(self) -> bool:
        """Check if all packages have been processed."""
        processed = set(self.completed_packages + self.failed_packages + self.skipped_packages)
        return processed == set(self.packages_to_build)
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of the session status."""
        total_packages = len(self.packages_to_build)
        completed = len(self.completed_packages)
        failed = len(self.failed_packages)
        skipped = len(self.skipped_packages)
        remaining = total_packages - completed - failed - skipped
        
        current_duration = (time.time() - self.start_time) if not self.end_time else self.total_duration
        
        return {
            'session_id': self.session_id,
            'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
            'current_time': datetime.fromtimestamp(time.time()).isoformat(),
            'total_packages': total_packages,
            'completed': completed,
            'failed': failed,
            'skipped': skipped,
            'remaining': remaining,
            'success_rate': completed / total_packages if total_packages > 0 else 0,
            'current_duration': current_duration,
            'status': 'completed' if self.is_complete() else 'running'
        }
    
    def save_session_state(self, filepath: Optional[str] = None) -> str:
        """Save the current session state to a file."""
        if not filepath:
            if self.output_dir:
                filepath = os.path.join(self.output_dir, f"{self.session_id}.json")
            else:
                # Use current directory if no output dir specified
                filepath = f"{self.session_id}.json"
        
        # Convert the session to a dictionary, handling non-serializable objects
        session_dict = {
            'session_id': self.session_id,
            'start_time': self.start_time,
            'packages_to_build': self.packages_to_build,
            'config': self.config,
            'results': [
                {
                    'package_name': r.package_name,
                    'status': r.status.value,
                    'start_time': r.start_time,
                    'end_time': r.end_time,
                    'duration': r.duration,
                    'error_message': r.error_message,
                    'output_log': r.output_log[:10000],  # Limit log size to avoid huge files
                    'dependencies': r.dependencies,
                    'build_system': r.build_system
                } for r in self.results
            ],
            'completed_packages': self.completed_packages,
            'failed_packages': self.failed_packages,
            'skipped_packages': self.skipped_packages,
            'continue_on_error': self.continue_on_error,
            'resume_from': self.resume_from,
            'output_dir': self.output_dir,
            'end_time': self.end_time,
            'total_duration': self.total_duration
        }
        
        with open(filepath, 'w') as f:
            json.dump(session_dict, f, indent=2)
        
        return filepath
    
    @classmethod
    def load_session_state(cls, filepath: str) -> 'BuildSession':
        """Load a session state from a file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Reconstruct BuildStepResults
        results = []
        for r_data in data.get('results', []):
            result = BuildStepResult(
                package_name=r_data['package_name'],
                status=BuildStatus(r_data['status']),
                start_time=r_data['start_time'],
                end_time=r_data['end_time'],
                duration=r_data['duration'],
                error_message=r_data.get('error_message'),
                output_log=r_data.get('output_log', ''),
                dependencies=r_data.get('dependencies', []),
                build_system=r_data.get('build_system', 'upp')
            )
            results.append(result)
        
        session = cls(
            session_id=data['session_id'],
            start_time=data['start_time'],
            packages_to_build=data['packages_to_build'],
            config=data.get('config', {}),
            results=results,
            completed_packages=data.get('completed_packages', []),
            failed_packages=data.get('failed_packages', []),
            skipped_packages=data.get('skipped_packages', []),
            continue_on_error=data.get('continue_on_error', True),
            resume_from=data.get('resume_from'),
            output_dir=data.get('output_dir', ''),
            end_time=data.get('end_time')
        )
        
        session.total_duration = data.get('total_duration')
        
        return session
    
    def mark_completed(self):
        """Mark the session as completed."""
        self.end_time = time.time()
        self.total_duration = self.end_time - self.start_time
    
    def can_resume_from(self, package_name: str) -> bool:
        """Check if we can resume from a specific package."""
        # Can resume from a package if:
        # 1. It's in our build list
        # 2. All its dependencies have been successfully built
        # 3. It hasn't been processed yet (not in completed, failed, or skipped)
        
        if package_name not in self.packages_to_build:
            return False
        
        if (package_name in self.completed_packages or 
            package_name in self.failed_packages or 
            package_name in self.skipped_packages):
            return False
        
        # In a real implementation, we'd check dependency completion
        # For now, we'll just say we can resume from the package
        return True
    
    def resume_session(self, from_package: str = None) -> List[str]:
        """Get list of packages to build when resuming session."""
        if from_package and self.can_resume_from(from_package):
            # Find the index of the resume package and return remaining packages
            start_idx = self.packages_to_build.index(from_package)
            remaining = self.packages_to_build[start_idx:]
        else:
            # Return packages that haven't been processed yet
            processed = set(self.completed_packages + self.failed_packages + self.skipped_packages)
            remaining = [pkg for pkg in self.packages_to_build if pkg not in processed]
        
        return remaining


class BuildSessionManager:
    """Manages multiple build sessions."""
    
    def __init__(self, sessions_dir: str = ".maestro/build_sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.active_session: Optional[BuildSession] = None
    
    def create_session(self, 
                      packages_to_build: List[str], 
                      config: Dict[str, Any] = None,
                      continue_on_error: bool = True,
                      output_dir: str = "") -> BuildSession:
        """Create a new build session."""
        session = BuildSession(
            session_id=f"session_{int(time.time())}_{len(packages_to_build)}pkgs",
            start_time=time.time(),
            packages_to_build=packages_to_build,
            config=config or {},
            continue_on_error=continue_on_error,
            output_dir=output_dir
        )
        
        self.active_session = session
        return session
    
    def save_active_session(self) -> Optional[str]:
        """Save the currently active session."""
        if self.active_session:
            return self.active_session.save_session_state()
        return None
    
    def load_session(self, session_id: str) -> Optional[BuildSession]:
        """Load a session by ID."""
        session_file = self.sessions_dir / f"{session_id}.json"
        if session_file.exists():
            session = BuildSession.load_session_state(str(session_file))
            self.active_session = session
            return session
        return None
    
    def list_sessions(self) -> List[str]:
        """List available session files."""
        sessions = []
        for file_path in self.sessions_dir.glob("*.json"):
            sessions.append(file_path.stem)
        return sessions
    
    def cleanup_old_sessions(self, days: int = 7) -> int:
        """Remove session files older than specified days."""
        import datetime
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        removed_count = 0
        
        for file_path in self.sessions_dir.glob("*.json"):
            if file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                removed_count += 1
        
        return removed_count


# Convenience functions for --keep-going and --resume flags mentioned in requirements
def should_continue_on_error(args) -> bool:
    """Determine if build should continue when errors occur based on args."""
    # Default to True, but can be overridden by args
    return getattr(args, 'keep_going', True)


def get_resume_package(args, session: BuildSession) -> Optional[str]:
    """Get the package to resume from based on args."""
    resume_from = getattr(args, 'resume_from', None)
    if resume_from:
        if session.can_resume_from(resume_from):
            return resume_from
        else:
            print(f"Warning: Cannot resume from '{resume_from}', starting from beginning")
            return None
    return None