"""Bounded continuous dispatch in the frozen job order; retain in-flight failures."""

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait


def provider_blocked(row):
    calls = row.get("audit", {}).get("calls", []) + row.get("result", {}).get("calls", [])
    return any(r.get("http_status") in (401, 402, 403, 429) for r in [row, *calls])


def results(jobs, execute, workers=3):
    pending = iter(enumerate(jobs))
    blocked = False
    with ThreadPoolExecutor(max_workers=workers) as pool:
        running = {}

        def fill():
            while not blocked and len(running) < workers:
                item = next(pending, None)
                if item is None:
                    break
                index, job = item
                running[pool.submit(execute, job)] = index

        fill()
        while running:
            done, _ = wait(running, return_when=FIRST_COMPLETED)
            for future in sorted(done, key=running.get):
                running.pop(future)
                row = future.result()
                blocked = blocked or provider_blocked(row)
                yield row
            # A provider block stops new submissions, but all already-running results are saved.
            fill()
