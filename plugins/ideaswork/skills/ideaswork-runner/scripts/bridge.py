#!/usr/bin/env python3
"""IdeasWork Plugin bridge: run a Skill's Python script with ``call_platform_api`` injected.

This is a credential-separating supervisor, not a filesystem sandbox. The parent process (this file)
reads the Runtime lease from **stdin** and talks to the Remote MCP lease endpoint. The Python child only
receives a one-time bridge secret and a local socket address: it can ask the parent to call a platform
API, but it never sees the lease, the endpoint credentials or any token-like environment variable.

Usage (lease on stdin, never on the command line or in the environment)::

    printf '%s' "$LEASE" | python3 bridge.py --runtime-endpoint "$ENDPOINT" --runtime-lease-stdin \\
        --workspace <workspace_dir> --script <path relative to workspace> [--args-json '[...]'|@file]

Prints one JSON object on stdout: ``{"success", "exit_code", "stdout", "stderr", ...}``. Exit status is 0
when the script succeeded, 1 when it failed, 6 when a platform call's outcome is unknown (do not replay),
7 when the lease needs renewal, 2 for invalid arguments or a missing interpreter.

Standard library only. Written to run on Python 3.9+ (the child needs 3.10+ because Skill scripts use
``X | None`` annotations).
"""
from __future__ import annotations

import argparse
import hmac
import json
import mimetypes
import os
import secrets
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

FILE_PREFIX = "__call_platform_api_file:"
CALL_PATH = "/mcp/runtime/lease/call"
UPLOAD_SUFFIX = "/materials/upload"
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_UPLOAD_BYTES = 500 * 1024 * 1024
MAX_OUTPUT_CHARS = 20000
BUSY_RETRY_DELAYS = (0.2, 0.4, 0.8)
MIN_CHILD_PYTHON = (3, 10)
REDACTED = "[REDACTED]"

# What the child may ask the parent to do. Everything else is refused.
OPERATIONS = ("query_api_docs", "exec_api")

CHILD_BRIDGE = r'''
import builtins
import json
import os
import runpy
import socket
import sys
import types


def bridge_call(operation, api_code, body=None):
    request = json.dumps({
        "secret": os.environ["IDEASWORK_RUNTIME_BRIDGE_SECRET"],
        "api_code": str(api_code or ""),
        "operation": operation,
        "body": body or {},
    }).encode("utf-8")
    address = os.environ["IDEASWORK_RUNTIME_BRIDGE_SOCKET"]
    if address.startswith("tcp:"):
        host, _, port = address[4:].rpartition(":")
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target = (host, int(port))
    else:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        target = address
    with client:
        client.connect(target)
        client.sendall(request)
        client.shutdown(socket.SHUT_WR)
        chunks = []
        total = 0
        while True:
            chunk = client.recv(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > 16 * 1024 * 1024:
                raise RuntimeError("Runtime bridge response exceeds limit")
            chunks.append(chunk)
    response = json.loads(b"".join(chunks).decode("utf-8"))
    if response.get("transport_error"):
        raise RuntimeError(response["transport_error"])
    return response.get("result") or {"error": "Runtime bridge returned no result"}


def call_platform_api(api_code, body=None):
    return bridge_call("exec_api", api_code, body)


def query_api_docs(api_code):
    return bridge_call("query_api_docs", api_code)


def setup(**kwargs):
    if kwargs:
        raise RuntimeError("Runtime bridge does not accept credentials or endpoint overrides")
    return {"runtime": "plugin-python-bridge", "bridge": True}


# Import compatibility for Builder thin scripts written against the older local helper names.
avp_local = types.ModuleType("avp_local")
for name, function in {
    "setup": setup,
    "call_platform_api": call_platform_api,
    "call_plat_api": call_platform_api,
    "blue_exec_api": call_platform_api,
    "execapi": call_platform_api,
    "blue_query_api_docs": query_api_docs,
    "querydocs": query_api_docs,
}.items():
    setattr(avp_local, name, function)
sys.modules["avp_local"] = avp_local
builtins.call_platform_api = call_platform_api
builtins.call_plat_api = call_platform_api
script = sys.argv[1]
args = json.loads(sys.argv[2])
paths = json.loads(sys.argv[3])
# -I removes the working directory from sys.path; restore only the selected workspace and Skill paths.
sys.path[:0] = [os.path.dirname(script), os.environ["IDEASWORK_RUNTIME_WORKDIR"]] + paths
sys.argv = [script] + args
try:
    runpy.run_path(script, run_name="__main__")
except SystemExit as error:
    code = error.code
    if code is None:
        raise SystemExit(0)
    if isinstance(code, int):
        raise SystemExit(code)
    print(code, file=sys.stderr)
    raise SystemExit(1)
'''


class RuntimeFailure(Exception):
    """A structured failure the Agent can act on. ``result()`` is what is reported."""

    def __init__(self, code: str, message: str, next_action: str, retryable: bool = False, exit_code: int = 1):
        super().__init__(message)
        self.code = code
        self.message = message
        self.next_action = next_action
        self.retryable = retryable
        self.exit_code = exit_code

    def result(self) -> dict:
        return {"error_code": self.code, "error": self.message,
                "next_action": self.next_action, "retryable": self.retryable}


def invalid(message: str) -> RuntimeFailure:
    return RuntimeFailure("invalid_arguments", message, "check_command_help", exit_code=2)


def unknown_outcome(detail: str = "") -> RuntimeFailure:
    message = "Runtime request outcome is unknown; do not replay the operation"
    if detail:
        message = detail + "; request outcome is unknown; do not replay the operation"
    return RuntimeFailure("runtime_request_outcome_unknown", message, "inspect_remote_state", exit_code=6)


def network_unreachable(cause: str) -> RuntimeFailure:
    return RuntimeFailure(
        "network_unreachable",
        "Request was not sent: no connection to the server could be established (%s); nothing was changed. "
        "Inside a sandbox, ask the user to allow network access for this command, then run it again" % cause,
        "allow_network_then_retry", retryable=True)


def redact(value, secret: str):
    """Remove a known credential from any string or key, however deeply it was echoed."""
    if not secret:
        return value
    if isinstance(value, str):
        return value.replace(secret, REDACTED)
    if isinstance(value, dict):
        return {redact(k, secret): redact(v, secret) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, secret) for v in value]
    return value


def has_file_ref(value) -> bool:
    if isinstance(value, str):
        return value.startswith(FILE_PREFIX)
    if isinstance(value, dict):
        return any(has_file_ref(v) for v in value.values())
    if isinstance(value, list):
        return any(has_file_ref(v) for v in value)
    return False


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never forward a bearer credential or replay a POST through a redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401 - urllib hook
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


class _MultipartBody:
    """``body`` JSON field + one streamed ``file`` part, with an exact Content-Length."""

    def __init__(self, fields_json: str, filename: str, content_type: str, fileobj, size: int):
        boundary = "ideaswork" + secrets.token_hex(16)
        safe_name = filename.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "").replace("\n", "")
        head = (
            "--%s\r\nContent-Disposition: form-data; name=\"body\"\r\n\r\n%s\r\n"
            "--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"%s\"\r\n"
            "Content-Type: %s\r\n\r\n" % (boundary, fields_json, boundary, safe_name, content_type)
        ).encode("utf-8")
        tail = ("\r\n--%s--\r\n" % boundary).encode("utf-8")
        self.content_type = "multipart/form-data; boundary=" + boundary
        self.length = len(head) + size + len(tail)
        self._head, self._tail, self._file = head, tail, fileobj
        self._stage = 0

    def read(self, amt: int = 8192) -> bytes:
        if self._stage == 0:
            self._stage = 1
            return self._head
        if self._stage == 1:
            chunk = self._file.read(amt)
            if chunk:
                return chunk
            self._stage = 2
        if self._stage == 2:
            self._stage = 3
            return self._tail
        return b""


class LeaseClient:
    """POST JSON / multipart to the Remote MCP lease endpoint with ``Authorization: Bearer <lease>``."""

    def __init__(self, endpoint: str, lease: str, timeout: float = 60.0, retry_delays=BUSY_RETRY_DELAYS):
        if not endpoint or not lease:
            raise RuntimeFailure("runtime_lease_missing", "Runtime lease required; obtain it from Remote MCP",
                                 "create_runtime_lease", retryable=True, exit_code=7)
        parsed = urllib.parse.urlparse(endpoint)
        host = parsed.hostname or ""
        if not host or parsed.username or parsed.password or parsed.fragment or parsed.query:
            raise invalid("Invalid runtime endpoint")
        loopback = host == "localhost" or host.startswith("127.") or host == "::1"
        if parsed.scheme != "https" and not (parsed.scheme == "http" and loopback):
            raise invalid("Runtime endpoint requires HTTPS (HTTP allowed only on loopback)")
        if parsed.path.rstrip("/") != CALL_PATH:
            raise invalid("Runtime endpoint must be the %s gateway endpoint" % CALL_PATH)
        if "\r" in lease or "\n" in lease:
            raise invalid("Invalid runtime lease")
        self.endpoint = endpoint.rstrip("/")
        self.upload_endpoint = self.endpoint[: -len("/call")] + UPLOAD_SUFFIX
        self._lease = lease
        self._timeout = timeout
        self._retry_delays = tuple(retry_delays)

    # -- public operations -------------------------------------------------
    def query_docs(self, api_code: str) -> dict:
        return self._json_call({"operation": "query_api_docs", "api_code": api_code})

    def exec_api(self, api_code: str, body: dict) -> dict:
        return self._json_call({"operation": "exec_api", "api_code": api_code, "body": body})

    def upload(self, path: str, filename: str, content_type: str, params: dict) -> dict:
        size = os.path.getsize(path)
        with open(path, "rb") as handle:
            body = _MultipartBody(json.dumps(params, ensure_ascii=False), filename, content_type, handle, size)
            return self._send(self.upload_endpoint, body, body.content_type, body.length, retry=False)

    # -- transport ---------------------------------------------------------
    def _json_call(self, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        return self._send(self.endpoint, data, "application/json", len(data), retry=True)

    def _send(self, url: str, data, content_type: str, length: int, retry: bool) -> dict:
        attempt = 0
        while True:
            if hasattr(data, "read") and attempt:
                raise unknown_outcome()  # a streamed body cannot be replayed
            request = urllib.request.Request(url, data=data, method="POST", headers={
                "Authorization": "Bearer " + self._lease,
                "Content-Type": content_type,
                "Content-Length": str(length),
                "Accept": "application/json",
            })
            status, raw = self._roundtrip(request)
            payload = None
            if raw:
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    payload = None
            if status != 200:
                failure = self._rejection(status, payload if isinstance(payload, dict) else {})
                busy = (failure.code == "runtime_lease_busy" and failure.next_action == "retry_runtime_call"
                        and failure.retryable)
                if retry and busy and attempt < len(self._retry_delays):
                    time.sleep(self._retry_delays[attempt])
                    attempt += 1
                    continue
                raise failure
            if not isinstance(payload, dict):
                raise unknown_outcome()
            if payload.get("status") == "fail" and payload.get("code"):
                raise self._response_error(payload, "Runtime endpoint call failed")
            return redact(payload, self._lease)

    def _roundtrip(self, request) -> tuple:
        try:
            with _OPENER.open(request, timeout=self._timeout) as response:
                status = response.status
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as error:  # non-2xx, including an un-followed redirect
            status = error.code
            try:
                raw = error.read(MAX_RESPONSE_BYTES + 1)
            except Exception:
                raw = b""
        except urllib.error.URLError as error:
            reason = error.reason
            if isinstance(reason, (ConnectionRefusedError, socket.gaierror)):
                raise network_unreachable(self._clean(str(reason)))
            if isinstance(reason, ssl.SSLCertVerificationError):
                raise network_unreachable(self._clean(str(reason)))
            raise unknown_outcome()
        except Exception:
            raise unknown_outcome()
        if len(raw) > MAX_RESPONSE_BYTES:
            raise unknown_outcome()
        return status, raw

    def _clean(self, text: str) -> str:
        text = " ".join(text.replace(self._lease, REDACTED).split())
        return text[:240] + ("…" if len(text) > 240 else "")

    def _rejection(self, status: int, payload: dict) -> RuntimeFailure:
        structured = isinstance(payload.get("error"), dict)
        if structured or (400 <= status < 500 and status != 408):
            return self._response_error(payload, "Runtime endpoint HTTP %d" % status)
        # A 5xx/408/3xx can come from a gateway after the platform already executed the call.
        return unknown_outcome("Runtime endpoint HTTP %d" % status)

    def _response_error(self, payload: dict, fallback: str) -> RuntimeFailure:
        code, message, next_action, retryable = "runtime_lease_endpoint_error", fallback, "create_runtime_lease", True
        error = payload.get("error")
        if isinstance(error, dict):
            code = str(error.get("code") or code)
            message = str(error.get("message") or message)
            next_action = str(error.get("next_action") or next_action)
            retryable = next_action == "create_runtime_lease"
            if isinstance(error.get("retryable"), bool):
                retryable = error["retryable"]
        elif isinstance(payload.get("detail"), str) and payload["detail"]:
            message = payload["detail"]
        elif isinstance(payload.get("message"), str) and payload["message"]:
            message = payload["message"]
        strip = lambda value: value.replace(self._lease, REDACTED)  # noqa: E731
        return RuntimeFailure(strip(code), strip(message), strip(next_action), retryable, exit_code=7)


def open_upload_file(reference: str, workspace_root: str):
    """Resolve a ``__call_platform_api_file:`` reference to a regular file inside the workspace."""
    relative = reference[len(FILE_PREFIX):]
    if relative.startswith("file:"):
        relative = relative[len("file:"):]
    root = os.path.realpath(workspace_root)
    candidate = relative if os.path.isabs(relative) else os.path.join(root, relative)
    resolved = os.path.realpath(candidate)
    if os.path.commonpath([root, resolved]) != root:
        raise invalid("Upload file must be inside workspace")
    if not os.path.isfile(resolved) or os.path.islink(resolved):
        raise invalid("Upload requires regular file (no symlink/FIFO)")
    size = os.path.getsize(resolved)
    if size < 1 or size > MAX_UPLOAD_BYTES:
        raise invalid("Upload requires nonempty regular file, at most 500 MiB")
    kind = mimetypes.guess_type(resolved)[0] or "application/octet-stream"
    return resolved, os.path.basename(resolved), kind


def exec_with_local_files(client: LeaseClient, api_code: str, body: dict, workspace_root: str) -> dict:
    """Plain calls go through unchanged; ``material_upload_proxy.file`` is read here, never on the server."""
    if not has_file_ref(body):
        return client.exec_api(api_code, body)
    reference = body.get("file")
    if api_code != "material_upload_proxy" or not isinstance(reference, str) or not reference.startswith(FILE_PREFIX):
        raise invalid("Local file uploads support material_upload_proxy.file only")
    params = {key: value for key, value in body.items() if key != "file"}
    if has_file_ref(params):
        raise invalid("Only one local upload file is supported")
    path, name, kind = open_upload_file(reference, workspace_root)
    return client.upload(path, name, kind, params)


class BridgeServer:
    """Serves the child's requests one at a time, so a lease is never used concurrently."""

    def __init__(self, client: LeaseClient, workspace_root: str, secret: str, deadline: float):
        self.client = client
        self.workspace_root = workspace_root
        self.secret = secret
        self.deadline = deadline
        self.failure: RuntimeFailure | None = None
        self._stop = threading.Event()
        self._directory = tempfile.mkdtemp(prefix="iwb-")  # short path: AF_UNIX paths are length-limited
        if hasattr(socket, "AF_UNIX") and os.name != "nt":
            self.address = os.path.join(self._directory, "b.sock")
            self._listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._listener.bind(self.address)
            os.chmod(self.address, 0o600)
        else:  # Windows: loopback TCP protected by the one-time secret
            self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._listener.bind(("127.0.0.1", 0))
            self.address = "tcp:127.0.0.1:%d" % self._listener.getsockname()[1]
        self._listener.listen(8)
        self._listener.settimeout(0.2)
        self._thread = threading.Thread(target=self._serve, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)
        try:
            self._listener.close()
        finally:
            shutil.rmtree(self._directory, ignore_errors=True)

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                connection, _ = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            with connection:
                self._handle(connection)

    def _handle(self, connection) -> None:
        connection.settimeout(max(1.0, self.deadline - time.time()))
        response: dict
        try:
            chunks, total = [], 0
            while True:
                chunk = connection.recv(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise invalid("Invalid runtime bridge request")
                chunks.append(chunk)
            request = json.loads(b"".join(chunks).decode("utf-8"))
            if not isinstance(request, dict):
                raise invalid("Invalid runtime bridge JSON")
            if not hmac.compare_digest(str(request.get("secret") or ""), self.secret):
                raise invalid("Runtime bridge authentication failed")
        except RuntimeFailure as failure:
            response = {"transport_error": failure.message}
        except Exception:
            response = {"transport_error": "Invalid runtime bridge request"}
        else:
            try:
                operation = request.get("operation") or "exec_api"
                api_code = str(request.get("api_code") or "")
                body = request.get("body") if isinstance(request.get("body"), dict) else {}
                if not api_code.strip():
                    raise invalid("api_code must not be empty")
                if operation == "query_api_docs":
                    response = {"result": self.client.query_docs(api_code)}
                elif operation == "exec_api":
                    response = {"result": exec_with_local_files(self.client, api_code, body, self.workspace_root)}
                else:
                    raise invalid("Unsupported bridge operation")
            except RuntimeFailure as failure:
                # Only an authenticated request's failure is a control failure of the whole run.
                if self.failure is None:
                    self.failure = failure
                response = {"transport_error": failure.message, "runtime_error": failure.result()}
            except Exception:
                if self.failure is None:
                    self.failure = unknown_outcome()
                response = {"transport_error": "Runtime bridge call failed"}
        try:
            connection.sendall(json.dumps(response).encode("utf-8"))
        except OSError:
            pass


class _BoundedPipe(threading.Thread):
    """Keep draining a child pipe but retain only a bounded prefix, so a noisy script cannot exhaust memory."""

    def __init__(self, pipe, limit_bytes: int):
        super().__init__(daemon=True)
        self._pipe, self._limit = pipe, limit_bytes
        self.data = bytearray()
        self.truncated = False

    def run(self) -> None:
        while True:
            chunk = self._pipe.read(65536)
            if not chunk:
                return
            room = self._limit - len(self.data)
            if room > 0:
                self.data += chunk[:room]
            if len(chunk) > room:
                self.truncated = True

    def text(self) -> str:
        text = bytes(self.data).decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
        if len(text) > MAX_OUTPUT_CHARS:
            return text[:MAX_OUTPUT_CHARS] + "…"
        return text + ("…" if self.truncated else "")


def scrubbed_environment(workspace_root: str, address: str, secret: str) -> dict:
    sensitive = {"IDEASWORK_CONFIG_DIR", "IDEAWORKS_CONFIG_DIR", "IDEASWORK_OAUTH_SESSION_FILE",
                 "IDEAWORKS_OAUTH_SESSION_FILE", "IDEASWORK_TASK_ID", "IDEASWORK_EXPECTED_ENV",
                 "IDEASWORK_RUNTIME_ENDPOINT", "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"}
    env = {}
    for key, value in os.environ.items():
        upper = key.upper()
        if upper in sensitive or "TOKEN" in upper or "LEASE" in upper or "SECRET" in upper \
                or upper.startswith("IDEASWORK_RUNTIME_BRIDGE_"):
            continue
        env[key] = value
    env.update({"IDEASWORK_RUNTIME_WORKDIR": workspace_root,
                "IDEASWORK_RUNTIME_BRIDGE_SOCKET": address,
                "IDEASWORK_RUNTIME_BRIDGE_SECRET": secret,
                "IDEASWORK_RUNTIME_DISABLE_OAUTH_SESSION": "1"})
    return env


def check_interpreter(interpreter: str) -> None:
    if os.path.realpath(interpreter) == os.path.realpath(sys.executable):
        version = sys.version_info[:2]
    else:
        try:
            probe = subprocess.run([interpreter, "-c", "import sys;print('%d.%d' % sys.version_info[:2])"],
                                   capture_output=True, text=True, timeout=20)
            major, minor = probe.stdout.strip().split(".")
            version = (int(major), int(minor))
        except Exception:
            raise RuntimeFailure("python_runtime_missing", "Python is required only for Python Skill execution",
                                 "install_python_or_select_interpreter", exit_code=2)
    if version < MIN_CHILD_PYTHON:
        raise RuntimeFailure(
            "python_version_unsupported",
            "Skill scripts need Python %d.%d+; found %d.%d. Nothing was executed" % (MIN_CHILD_PYTHON + version),
            "install_newer_python_and_pass_python_executable", exit_code=2)


def run_script(client: LeaseClient, workspace: str, script: str, args: list, python_path: list,
               interpreter: str, timeout: float) -> dict:
    root = os.path.realpath(workspace)
    if not os.path.isdir(root):
        raise invalid("Workspace does not exist")
    script_path = script if os.path.isabs(script) else os.path.join(root, script)
    script_path = os.path.realpath(script_path)
    if os.path.commonpath([root, script_path]) != root:
        raise invalid("script_path must be within workspace")
    if not os.path.isfile(script_path):
        raise invalid("Script must be a regular file")
    check_interpreter(interpreter)
    paths = [p if os.path.isabs(p) else os.path.join(root, p) for p in python_path]

    secret = secrets.token_hex(32)
    deadline = time.time() + timeout
    server = BridgeServer(client, root, secret, deadline)
    server.start()
    process = None
    timed_out = False
    try:
        flags = ["-I", "-X", "utf8"] if os.name == "nt" else ["-I"]
        command = [interpreter, *flags, "-c", CHILD_BRIDGE, script_path, json.dumps(args), json.dumps(paths)]
        popen_kwargs = {"start_new_session": True} if os.name != "nt" else {
            "creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
        try:
            process = subprocess.Popen(command, cwd=root, env=scrubbed_environment(root, server.address, secret),
                                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       **popen_kwargs)
        except OSError:
            raise RuntimeFailure("python_launch_failed", "Python process could not be started",
                                 "inspect_python_runtime", exit_code=2)
        out = _BoundedPipe(process.stdout, MAX_OUTPUT_CHARS * 4 + 4)
        err = _BoundedPipe(process.stderr, MAX_OUTPUT_CHARS * 4 + 4)
        out.start()
        err.start()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_group(process)
            process.wait()
        _kill_group(process)  # descendants that outlived the script
        out.join(timeout=2)
        err.join(timeout=2)
    finally:
        if process is not None and process.poll() is None:
            _kill_group(process)
        server.close()

    exit_code = process.returncode if process.returncode is not None else 1
    result = {"success": exit_code == 0, "exit_code": exit_code, "stdout": out.text(), "stderr": err.text()}
    if timed_out:
        result.update({"success": False, "exit_code": -1, "timeout": True,
                       "stderr": result["stderr"] + "\nExecution timed out"})
        return redact(result, client._lease)
    failure = server.failure
    if failure is not None:
        # A caught platform/lease failure must never look like a successful run, even if the script swallowed it.
        result["success"] = False
        if exit_code == 0:
            result["exit_code"] = 1
        result.update(failure.result())
        if not failure.code.startswith("runtime_lease_") and failure.exit_code > 0:
            result["exit_code"] = failure.exit_code
    return redact(result, client._lease)


def _kill_group(process) -> None:
    try:
        if os.name == "nt":
            process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _json_argument(value: str, label: str):
    text = value
    if value.startswith("@"):
        try:
            with open(value[1:], "r", encoding="utf-8") as handle:
                text = handle.read()
        except OSError as error:
            raise invalid("Cannot read %s file: %s" % (label, error.strerror))
    try:
        return json.loads(text)
    except ValueError:
        raise invalid("%s must be JSON (or @file)" % label)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bridge.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--runtime-endpoint", required=True)
    parser.add_argument("--runtime-lease-stdin", action="store_true", required=True,
                        help="read the lease from stdin (the only supported way to pass it)")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--script", required=True)
    parser.add_argument("--args-json", default="[]")
    parser.add_argument("--python-path-json", default="[]")
    parser.add_argument("--python-executable", default="")
    parser.add_argument("--timeout", type=int, default=3600)
    return parser


def main(argv=None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        lease = sys.stdin.read().strip()
        args = _json_argument(arguments.args_json, "--args-json")
        python_path = _json_argument(arguments.python_path_json, "--python-path-json")
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            raise invalid("--args-json must be a JSON array of strings")
        if not isinstance(python_path, list) or not all(isinstance(p, str) for p in python_path):
            raise invalid("--python-path-json must be a JSON array of strings")
        if arguments.timeout < 1:
            raise invalid("Python timeout must be positive")
        client = LeaseClient(arguments.runtime_endpoint, lease)
        result = run_script(client, arguments.workspace, arguments.script, args, python_path,
                            arguments.python_executable or sys.executable, arguments.timeout)
    except RuntimeFailure as failure:
        print(json.dumps(failure.result(), ensure_ascii=False))
        return failure.exit_code
    print(json.dumps(result, ensure_ascii=False))
    if result.get("success"):
        return 0
    if str(result.get("error_code", "")).startswith("runtime_lease_"):
        return 7
    if result.get("error_code") == "runtime_request_outcome_unknown":
        return 6
    return 1


if __name__ == "__main__":
    sys.exit(main())
