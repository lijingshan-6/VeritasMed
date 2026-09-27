"""Wait for the owned local API before presenting the frontend startup URL."""
import socket
import time


def wait_for_api(process, port: int, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while process.poll() is None and time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError(f"The local API did not start on port {port}; see its output above.")
