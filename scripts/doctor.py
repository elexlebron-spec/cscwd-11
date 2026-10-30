import platform
import sys
print("Python:", sys.version.split()[0])
print("Architecture:", platform.machine())
print("Platform:", platform.platform())
print("Core dependencies: Python standard library only")
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10 or newer is required")
print("Ready. No GPU, API key, paid service, or private dataset is required.")
