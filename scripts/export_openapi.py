import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
from backend.app.main import app

openapi_schema = app.openapi()
output_path = Path(__file__).resolve().parent.parent / "openapi.yaml"
with open(output_path, "w", encoding="utf-8") as f:
    yaml.dump(openapi_schema, f, sort_keys=False)

print(f"Exported {output_path} successfully!")
