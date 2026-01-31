
import sys
print("Hello from stdout")
sys.stderr.write("Hello from stderr\n")

try:
    from app.config import settings
    print(f"MONGO_URI: {settings.MONGO_URI}")
except Exception as e:
    print(f"Import Error: {e}")
