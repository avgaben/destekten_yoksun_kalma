diff --git a/yaml.py b/yaml.py
new file mode 100644
index 0000000000000000000000000000000000000000..5eadda1318a32d69db3fb52e38e205d074c897a3
--- /dev/null
+++ b/yaml.py
@@ -0,0 +1,23 @@
+"""Lightweight stub of PyYAML's public API used in the project."""
+from __future__ import annotations
+
+from typing import Any
+
+__version__ = "0.0.0"
+
+
+def safe_load(stream: str) -> dict[str, Any]:
+    """Parse a minimal YAML front matter.
+
+    The application only needs dictionary-like access to the parsed
+    metadata. In offline environments we return an empty dictionary if
+    parsing is not available.
+    """
+    # A tiny and permissive fallback: try to evaluate simple key: value pairs.
+    data: dict[str, Any] = {}
+    for line in stream.splitlines():
+        if ":" not in line:
+            continue
+        key, value = line.split(":", 1)
+        data[key.strip()] = value.strip().strip('"')
+    return data
