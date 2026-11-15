"""
Fixtures for end-to-end (E2E) browser tests.

E2E = test the whole system the way a user does: a real browser clicks
through the real React UI, which calls the real FastAPI backend, which
uses a real (test) Postgres database.

This file starts its OWN backend and frontend on separate ports (8001 and
5174 by default), pointed at the TEST database. So it never touches your
real data, and it works even if you already have the app open on 8000/5173.

The `page` fixture (a fresh browser tab per test) comes from the
pytest-playwright plugin.
"""
import os
import shutil
import socket
import tempfile
import warnings
import subprocess
import sys
import time
from pathlib import Path

import pytest

from support.ui import login_as
from support.db import get_test_database_url, reset_database

APP_ROOT = Path(__file__).resolve().parents[2]
API_PORT = int(os.getenv("E2E_API_PORT", "8001"))
WEB_PORT = int(os.getenv("E2E_WEB_PORT", "5174"))
BASE = f"http://127.0.0.1:{WEB_PORT}"
_procs = {}    # name -> running server process
_restart = {}  # how to restart the frontend + crash count


def _port_open(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _wait_for(port, proc, name, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _port_open(port):
            return
        if proc.poll() is not None:
            raise RuntimeError(f"{name} exited early (code {proc.returncode})")
        time.sleep(0.5)
    raise RuntimeError(f"{name} did not start on port {port} within {timeout}s")


@pytest.fixture(scope="session")
def servers():
    db_url = get_test_database_url()
    for port in (API_PORT, WEB_PORT):
        if _port_open(port):
            pytest.exit(f"Port {port} is already in use; set E2E_API_PORT / E2E_WEB_PORT in .env.test")
    reset_database()

    env = {**os.environ, "DATABASE_URL": db_url, "CORS_ORIGIN": BASE,
           "API_PROXY_TARGET": f"http://127.0.0.1:{API_PORT}"}
    logs = APP_ROOT / "testing" / "reports"
    logs.mkdir(exist_ok=True)
    api_log = open(logs / "e2e-backend.log", "w")
    web_log = open(logs / "e2e-frontend.log", "w")

    # Isolation for the server processes (lesson from a flaky-test hunt):
    #  * stdin=DEVNULL and their own process group, so console signals and
    #    keystrokes meant for pytest/Playwright can never reach them;
    #  * Vite is started with `node` directly, not through the npx.cmd batch
    #    wrapper, which could end silently mid-run and take Vite with it.
    isolate = dict(stdin=subprocess.DEVNULL, env=env, stderr=subprocess.STDOUT)
    if os.name == "nt":
        isolate["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    api = subprocess.Popen(
        # --timeout-keep-alive 75: the server should keep idle connections
        # open LONGER than its client (the Vite proxy, ~5 s), so the client
        # is always the side that closes them.
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(API_PORT),
         "--timeout-keep-alive", "75"],
        cwd=APP_ROOT / "backend", stdout=api_log, **isolate,
    )
    # Test the PRODUCTION build (vite build + vite preview), not the dev
    # server: one bundle instead of dozens of module files per page load,
    # and it's exactly what users would get. vite preview reuses the /api
    # proxy from vite.config.js.
    node = shutil.which("node") or "node"
    vite = str(APP_ROOT / "frontend" / "node_modules" / "vite" / "bin" / "vite.js")
    # Build into the system temp folder, NOT the project: the project sits in
    # OneDrive, and the sync client grabbing freshly built files is a likely
    # trigger for the Node crash described in _restart_frontend_if_dead().
    dist = Path(tempfile.gettempdir()) / "autorisk-e2e-dist"
    build = subprocess.run(
        [node, vite, "build", "--outDir", str(dist), "--emptyOutDir"],
        cwd=APP_ROOT / "frontend", stdout=web_log, **isolate,
    )
    if build.returncode != 0:
        api.kill()
        raise RuntimeError("Frontend build failed (see testing/reports/e2e-frontend.log)")
    def start_frontend():
        return subprocess.Popen(
            [node, vite, "preview", "--outDir", str(dist),
             "--host", "127.0.0.1", "--port", str(WEB_PORT), "--strictPort"],
            cwd=APP_ROOT / "frontend", stdout=web_log, **isolate,
        )

    web = start_frontend()
    _procs.update(backend=api, frontend=web)
    _restart["frontend"] = start_frontend
    try:
        _wait_for(API_PORT, api, "backend (see testing/reports/e2e-backend.log)")
        _wait_for(WEB_PORT, web, "frontend (see testing/reports/e2e-frontend.log)")
        yield BASE
    finally:
        for proc in _procs.values():
            proc.kill()
            proc.wait(timeout=10)
        api_log.close()
        web_log.close()


@pytest.fixture(autouse=True)
def fresh_db(servers):
    _restart_frontend_if_dead()
    backend = _procs["backend"]
    if backend.poll() is not None:  # fail fast with a clear message
        pytest.fail(f"The E2E backend exited (code {backend.returncode}); "
                    "see testing/reports/e2e-backend.log")
    reset_database()


def _restart_frontend_if_dead():
    """Restart `vite preview` if Node crashed (environment issue, not an app bug).

    While fixing the app bugs, ~2 runs in 10 lost the frontend server
    mid-run: Node.js 24 on this Windows machine exited with code 3221226505
    (0xC0000409, a native crash inside the runtime, nothing in our code).
    Every later test then failed with "connection refused" -- 30 false
    failures from one crash. The test harness now restarts it and warns.
    """
    proc = _procs.get("frontend")
    if proc is None or proc.poll() is None:
        return
    code = proc.returncode
    warnings.warn(f"E2E frontend server crashed (exit code {code}); restarted it.")
    new = _restart["frontend"]()
    _procs["frontend"] = new
    _wait_for(WEB_PORT, new, "frontend (restarted)")
    _restart["crashes"] = _restart.get("crashes", 0) + 1


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return {**browser_type_launch_args, "headless": os.getenv("E2E_HEADED", "0") != "1"}


@pytest.fixture(scope="session")  # must match pytest-playwright's own base_url scope
def base_url(servers):
    return servers


@pytest.fixture
def logged_in_page(page, base_url):
    login_as(page, base_url)
    return page
