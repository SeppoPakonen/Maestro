import subprocess
import threading
import queue
import time
from typing import List, Dict, Any, Callable, Optional


class Console:
    """Handles process management and parallel execution for builds."""

    def __init__(self, max_jobs: int = 4, host=None):
        self.max_jobs = max_jobs
        self.host = host
        self.job_queue = queue.Queue()
        self.running_jobs = []
        self.job_results = {}
        self.verbose = True

    def execute_command(self, cmd: str, cwd: str = None, env: Dict[str, str] = None,
                       callback: Callable = None) -> subprocess.Popen:
        """Execute a single command."""
        try:
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=env,
                text=True
            )

            if callback:
                # Run callback in a separate thread
                thread = threading.Thread(target=self._wait_for_completion,
                                         args=(process, callback))
                thread.start()
                return process
            else:
                stdout, stderr = process.communicate()
                return_code = process.returncode
                return subprocess.CompletedProcess(cmd, return_code, stdout, stderr)
        except Exception as e:
            print(f"Error executing command '{cmd}': {e}")
            return None

    def _wait_for_completion(self, process: subprocess.Popen, callback: Callable):
        """Wait for process completion and call callback."""
        stdout, stderr = process.communicate()
        callback(process.returncode, stdout, stderr)

    def execute_parallel(self, commands: List[Dict[str, Any]],
                        max_jobs: int = None) -> List[subprocess.CompletedProcess]:
        """Execute commands in parallel up to max_jobs."""
        if max_jobs is None:
            max_jobs = self.max_jobs

        results = []
        command_queue = queue.Queue()
        for cmd in commands:
            command_queue.put(cmd)

        # Start worker threads
        threads = []
        for _ in range(min(max_jobs, len(commands))):
            thread = threading.Thread(target=self._worker, args=(command_queue, results))
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        return results

    def _worker(self, command_queue: queue.Queue, results: List[subprocess.CompletedProcess]):
        """Worker thread function to execute commands from queue."""
        while not command_queue.empty():
            try:
                cmd_info = command_queue.get_nowait()
                cmd = cmd_info.get('command', '')
                cwd = cmd_info.get('cwd', None)
                env = cmd_info.get('env', None)

                process = subprocess.run(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd,
                    env=env,
                    text=True
                )

                results.append(process)

                if self.verbose:
                    print(f"Completed: {cmd} (exit code: {process.returncode})")
                    if process.stdout:
                        print(process.stdout)
                    if process.stderr:
                        print(process.stderr)

            except queue.Empty:
                break
            except Exception as e:
                print(f"Error in worker: {e}")

    def execute_build_commands(self, commands: List[str], parallel: bool = True,
                              jobs: int = None) -> bool:
        """Execute a list of build commands."""
        cmd_objects = [{'command': cmd} for cmd in commands]

        if parallel and len(commands) > 1:
            results = self.execute_parallel(cmd_objects, jobs)
            return all(result.returncode == 0 for result in results)
        else:
            for cmd_info in cmd_objects:
                result = self.execute_command(cmd_info['command'])
                if hasattr(result, 'returncode') and result.returncode != 0:
                    return False
            return True


def execute_command(cmd: List[str], cwd: str = None, verbose: bool = True) -> bool:
    """Execute a command synchronously and return success status."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if verbose and result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        return result.returncode == 0
    except Exception as e:
        print(f"Error executing command {cmd}: {e}")
        return False


def parallel_execute(commands: List[List[str]], max_jobs: int = 4) -> List[bool]:
    """Execute multiple commands in parallel."""
    import sys
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def run_command(cmd):
        return execute_command(cmd, verbose=False)

    results = []
    with ThreadPoolExecutor(max_workers=max_jobs) as executor:
        future_to_cmd = {executor.submit(run_command, cmd): cmd for cmd in commands}
        for future in as_completed(future_to_cmd):
            results.append(future.result())

    return results