# Future Improvements

This document tracks planned architectural, performance, and robustness improvements for the CodeAtlas project.

## GitHub Synchronization (`src/github/sync_github.py`)

1. **Multi-Threading / Concurrency**
   - **Current State**: Repositories are processed sequentially in a synchronous loop.
   - **Improvement**: Wrap the `sync_single_repo` call in a `concurrent.futures.ThreadPoolExecutor` to clone and pull multiple repositories simultaneously.

2. **Logging Infrastructure**
   - **Current State**: The pipeline heavily relies on standard `print()` statements for visibility.
   - **Improvement**: Transition to Python's built-in `logging` module. This will allow configurable log levels, proper timestamping, and persisting logs to a `sync.log` file (critical for background/cron execution).

3. **"Read-Only" Git Hard Resets**
   - **Current State**: The pipeline uses `git pull`, which can crash with merge conflicts if the remote repository is force-pushed or local files are accidentally modified.
   - **Improvement**: Change the git update strategy to `git fetch origin` followed by `git reset --hard origin/<branch>` to guarantee the local mirror perfectly matches the remote state without conflicts.

4. **GitHub Authentication & Rate Limits**
   - **Current State**: `fetch_github_repos()` pings the public API unauthenticated.
   - **Improvement**: Pass a `GITHUB_TOKEN` in the `Authorization` header to increase the rate limit from 60/hr to 5000/hr, and add retry/backoff logic for `403 Rate Limit Exceeded` responses.
