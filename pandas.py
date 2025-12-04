diff --git a/pandas.py b/pandas.py
new file mode 100644
index 0000000000000000000000000000000000000000..38a21defec2bea4f05df1551f3603a4dca1ceb53
--- /dev/null
+++ b/pandas.py
@@ -0,0 +1,74 @@
+"""Minimal pandas-like stub for offline testing.
+
+This implementation provides just enough of the pandas DataFrame API
+used inside the project (construction from a list of dictionaries,
+`.empty`, `.iterrows()`, `.sort_values()`, and `.reset_index()`). It is
+not a full replacement for pandas but allows running the application and
+its tests in environments where installing external dependencies is not
+possible.
+"""
+from __future__ import annotations
+
+from copy import deepcopy
+from typing import Iterable, List, Dict, Any, Tuple
+
+
+class DataFrame:
+    def __init__(self, data: Iterable[Dict[str, Any]] | None = None, columns: List[str] | None = None):
+        self._data: List[Dict[str, Any]] = []
+        self.columns: List[str] = columns[:] if columns else []
+
+        if data is None:
+            return
+
+        if not isinstance(data, Iterable):
+            raise TypeError("DataFrame data must be an iterable of dict rows")
+
+        for row in data:
+            if not isinstance(row, dict):
+                raise TypeError("Each row must be a dictionary")
+            self._data.append(dict(row))
+            if not self.columns:
+                self.columns = list(row.keys())
+            else:
+                for key in row.keys():
+                    if key not in self.columns:
+                        self.columns.append(key)
+
+    @property
+    def empty(self) -> bool:
+        return len(self._data) == 0
+
+    def iterrows(self) -> Iterable[Tuple[int, Dict[str, Any]]]:
+        for idx, row in enumerate(self._data):
+            yield idx, row
+
+    def sort_values(self, by: str, ascending: bool = True) -> "DataFrame":
+        def sort_key(r: Dict[str, Any]):
+            val = r.get(by)
+            return (val is None, val)
+
+        sorted_rows = sorted(self._data, key=sort_key, reverse=not ascending)
+        return DataFrame(sorted_rows, columns=self.columns)
+
+    def reset_index(self, drop: bool = False) -> "DataFrame":
+        if drop:
+            return DataFrame(deepcopy(self._data), columns=self.columns)
+        rows = []
+        for idx, row in enumerate(self._data):
+            r = {"index": idx}
+            r.update(row)
+            rows.append(r)
+        cols = ["index"] + [c for c in self.columns if c != "index"]
+        return DataFrame(rows, columns=cols)
+
+    def __repr__(self) -> str:
+        return f"DataFrame({self._data!r})"
+
+
+def DataFrame_from_dict(data: Dict[str, Any]) -> DataFrame:
+    """Helper to mimic a minimal pandas API surface."""
+    return DataFrame([data])
+
+
+__all__ = ["DataFrame", "DataFrame_from_dict"]
