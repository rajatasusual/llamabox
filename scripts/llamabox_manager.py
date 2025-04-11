import subprocess
from typing import Callable, List, Optional, Dict
from functools import wraps
import json
import yaml
from pathlib import Path
import os


class LlamaboxManager:
    def __init__(self):
        if os.geteuid() != 0:
            print("Warning: Not running as root. Some operations may fail.")

    # ---------------------- Systemd interactions ---------------------- #

    def _run_systemctl(self, command: str, service: str):
        if not self._service_exists(service):
            print(f"Warning: Service {service} does not exist (or isn't recognized by systemd).")
            return

        try:
            subprocess.run(["systemctl", command, service], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to {command} {service}: {e}")


    def _service_exists(self, service: str) -> bool:
        result = subprocess.run(
            ["systemctl", "show", service],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0


    def is_active(self, service: str) -> bool:
        if not self._service_exists(service):
            return False
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip() == "active"
        except subprocess.CalledProcessError:
            return False

    # ---------------------- Process priority management ---------------------- #

    def get_pids_by_keyword(self, keyword: str) -> List[str]:
        try:
            pids = subprocess.check_output(["pgrep", "-f", keyword], text=True).splitlines()
            return pids
        except subprocess.CalledProcessError:
            return []

    def get_nice_value(self, pid: str) -> int:
        try:
            result = subprocess.check_output(["ps", "-o", "ni=", "-p", pid], text=True)
            return int(result.strip())
        except Exception:
            print(f"Failed to get nice value for PID {pid}")
            return 0

    def set_nice_value(self, pid: str, nice: int):
        try:
            subprocess.run(["renice", "-n", str(nice), "-p", pid],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           check=True)
        except subprocess.CalledProcessError:
            print(f"Failed to set nice value {nice} for PID {pid}")

    def pid_exists(self, pid: str) -> bool:
        return Path(f"/proc/{pid}").exists()

    # ---------------------- Orchestration logic ---------------------- #

    def _orchestration_core(
        self,
        func: Callable,
        stop_services: List[str],
        start_services: List[str],
        deprioritize: List[str],
        prioritize: List[str]
    ):
        stop_services = stop_services or []
        start_services = start_services or []
        deprioritize = deprioritize or []
        prioritize = prioritize or []

        service_states: Dict[str, bool] = {}
        pid_nice_backup: Dict[str, int] = {}

        try:
            for service in stop_services:
                was_active = self.is_active(service)
                service_states[service] = was_active
                if was_active:
                    self._run_systemctl("stop", service)

            for service in start_services:
                was_active = self.is_active(service)
                service_states[service] = was_active
                if not was_active:
                    self._run_systemctl("start", service)

            for keyword in deprioritize:
                for pid in self.get_pids_by_keyword(keyword):
                    if pid not in pid_nice_backup and self.pid_exists(pid):
                        pid_nice_backup[pid] = self.get_nice_value(pid)
                        self.set_nice_value(pid, 19)

            for keyword in prioritize:
                for pid in self.get_pids_by_keyword(keyword):
                    if pid not in pid_nice_backup and self.pid_exists(pid):
                        pid_nice_backup[pid] = self.get_nice_value(pid)
                        self.set_nice_value(pid, -5)

            func()

        finally:
            for pid, original_nice in pid_nice_backup.items():
                if self.pid_exists(pid):
                    try:
                        self.set_nice_value(pid, original_nice)
                    except Exception as e:
                        print(f"Warning: Failed to restore nice for PID {pid}: {e}")

            for service, was_active in service_states.items():
                try:
                    currently_active = self.is_active(service)
                    if was_active and not currently_active:
                        self._run_systemctl("start", service)
                    elif not was_active and currently_active:
                        self._run_systemctl("stop", service)
                except Exception as e:
                    print(f"Warning: Failed to restore {service}: {e}")

    # ---------------------- Public orchestration interface ---------------------- #

    def with_orchestration(
        self,
        stop_services: Optional[List[str]] = None,
        start_services: Optional[List[str]] = None,
        deprioritize: Optional[List[str]] = None,
        prioritize: Optional[List[str]] = None,
        func: Optional[Callable] = None
    ):
        if func is not None:
            return self._orchestration_core(
                func, stop_services, start_services, deprioritize, prioritize
            )

        def decorator(inner_func: Callable):
            @wraps(inner_func)
            def wrapper(*args, **kwargs):
                return self._orchestration_core(
                    lambda: inner_func(*args, **kwargs),
                    stop_services, start_services, deprioritize, prioritize
                )
            return wrapper
        return decorator

    # ---------------------- Config loader ---------------------- #

    def load_config_and_orchestrate(self, config_path: str, func: Callable):
        config_data = self._load_config(config_path)
        orchestration = config_data.get("orchestration", {})
        self.with_orchestration(
            stop_services=orchestration.get("stop_services"),
            start_services=orchestration.get("start_services"),
            deprioritize=orchestration.get("deprioritize"),
            prioritize=orchestration.get("prioritize"),
            func=func
        )

    def _load_config(self, path: str) -> dict:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        try:
            if path.endswith(".yaml") or path.endswith(".yml"):
                with open(path, "r") as f:
                    return yaml.safe_load(f)
            elif path.endswith(".json"):
                with open(path, "r") as f:
                    return json.load(f)
            else:
                raise ValueError("Unsupported config format. Use .yaml or .json")
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {e}")
