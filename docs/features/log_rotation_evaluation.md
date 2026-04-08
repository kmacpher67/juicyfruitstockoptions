# Log Rotation Evaluation

## Context
Currently, the application logs are written dynamically to `logs/stock_portal_debug.log` using standard Python `logging.FileHandler` defined in `app/utils/logging_config.py`. As the system runs continuously via Docker or local processes (especially with scheduler sync jobs), this file will grow unbounded, consuming disk space and making log analysis slow.

**Requirement:** `- [ ] **Logging:** Implement daily log rotation for log files`

## Options Evaluated

### Option 1: Python `TimedRotatingFileHandler` (Application Level)
**How:** Replace the `FileHandler` in `app/utils/logging_config.py` with `logging.handlers.TimedRotatingFileHandler`. 
```python
from logging.handlers import TimedRotatingFileHandler

handler = TimedRotatingFileHandler("logs/stock_portal_debug.log", when="midnight", interval=1, backupCount=7)
```
**Pros:** 
- Extremely easy to implement (native standard library).
- Cross-platform out of the box (works on Windows/Ubuntu development environments instantly).
- Cleans up its own old logs automatically via `backupCount`.

**Cons:** 
- **Concurrency Risks:** If Uvicorn runs with multiple worker processes (`--workers 4`), Python's default rotating file handlers can corrupt the file or fail to rotate safely because all processes attempt to lock/rename the same file simultaneously. 
- *Mitigation:* We can use third-party packages like `concurrent-log-handler` if multiple workers are used, or just strictly run Uvicorn as a single worker.

### Option 2: Docker Native Logging + stdout (Platform Level)
**How:** Remove `logging.FileHandler` entirely so Python only pushes logs to `stdout` (`StreamHandler`). Let Docker's daemon handle rotation natively via `docker-compose.yml`.
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "5"
```
**Pros:**
- "Cloud Native" / 12-factor app best practice. 
- Completely immune to Python concurrency/multiprocessing locking issues. 

**Cons:**
- Removes the local `logs/stock_portal_debug.log` file from the host directory. Developers would need to use `docker logs -f juicy_backend` instead of `tail -f logs/stock_portal_debug.log` or opening the file in Notepad++/VSCode. This may disrupt the workflow if the user expects plain text files on disk.

### Option 3: `logrotate` (OS Level)
**How:** Keep the `FileHandler` as-is. Configure a `/etc/logrotate.d/juicyfruit` definition on the Ubuntu prod host to rotate the file nightly, using `copytruncate`.
**Pros:**
- Safe concurrency.
**Cons:**
- Tightly couples the log rotation to Ubuntu ops requirements. Doesn't rotate the files correctly when running locally on Windows. Adds operational maintenance overhead.

## Recommendation

**Proceed with Option 1: `TimedRotatingFileHandler`**
Since the Juicy Fruit project emphasizes native standard library solutions where possible and needs to comfortably run both on Windows 11 and Ubuntu (as per the tech stack), dropping in `TimedRotatingFileHandler` is the path of least resistance. 
*Constraint Note:* As long as FastAPI is being run with a single worker under Uvicorn (`workers=1` which is the typical default for basic setups), this will be highly stable and requires the least ops effort.

To implement this, you simply modify `setup_logging` in `app/utils/logging_config.py` and optionally create a `logs/.gitignore` exclusion to ensure rotated logs aren't accidentally committed.
