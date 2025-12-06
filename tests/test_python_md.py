#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.9"
# dependencies = ["pytest", "markdown-it-py"]
# ///
"""Tests for python-md script."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

# Load python-md as a module (it has no .py extension)
SCRIPT_PATH = Path(__file__).parent.parent.parent / "bin" / "python-md"
spec = importlib.util.spec_from_loader("python_md", loader=None, origin=str(SCRIPT_PATH))
python_md = importlib.util.module_from_spec(spec)
exec(SCRIPT_PATH.read_text(), python_md.__dict__)


# =============================================================================
# Unit Tests
# =============================================================================


class TestFindFirstCodeBlock:
    """Unit tests for find_first_code_block function."""

    def test_extracts_python_block(self):
        markdown = """
# Example

```python
print("hello")
```
"""
        result = python_md.find_first_code_block(markdown)
        assert result == 'print("hello")\n'

    def test_returns_first_python_block_only(self):
        markdown = """
```python
first()
```

```python
second()
```
"""
        result = python_md.find_first_code_block(markdown)
        assert result == "first()\n"

    def test_ignores_other_languages(self):
        markdown = """
```javascript
console.log("js");
```

```python
print("python")
```
"""
        result = python_md.find_first_code_block(markdown)
        assert result == 'print("python")\n'

    def test_returns_none_when_no_python_block(self):
        markdown = """
# Just text

```bash
echo "not python"
```
"""
        result = python_md.find_first_code_block(markdown)
        assert result is None

    def test_returns_none_for_empty_markdown(self):
        result = python_md.find_first_code_block("")
        assert result is None

    def test_case_insensitive_language(self):
        markdown = """
```Python
print("upper")
```
"""
        result = python_md.find_first_code_block(markdown)
        assert result == 'print("upper")\n'

    def test_custom_language(self):
        markdown = """
```rust
fn main() {}
```

```python
print("py")
```
"""
        result = python_md.find_first_code_block(markdown, language="rust")
        assert result == "fn main() {}\n"

    def test_multiline_code_block(self):
        markdown = """
```python
def foo():
    return 42

print(foo())
```
"""
        result = python_md.find_first_code_block(markdown)
        assert "def foo():" in result
        assert "return 42" in result
        assert "print(foo())" in result


class TestFetchGithubContent:
    """Unit tests for URL parsing in fetch_github_content."""

    def test_rejects_invalid_url(self):
        with pytest.raises(ValueError, match="Unrecognized GitHub URL format"):
            python_md.fetch_github_content("https://example.com/foo")

    def test_rejects_non_issue_github_url(self):
        with pytest.raises(ValueError, match="Unrecognized GitHub URL format"):
            python_md.fetch_github_content("https://github.com/owner/repo/pulls/1")


# =============================================================================
# Functional Tests (hits GitHub for real)
# =============================================================================


@pytest.mark.functional
class TestGitHubIntegration:
    """Functional tests that actually hit GitHub API."""

    ISSUE_URL = "https://github.com/dandavison/log-interviewing/issues/1"
    COMMENT_URL = f"{ISSUE_URL}#issuecomment-3620612919"

    def test_fetch_from_issue_comment(self):
        """Fetch code from a specific GitHub issue comment."""
        code = python_md.fetch_github_content(self.COMMENT_URL)
        assert code is not None
        assert "bfs" in code.lower() or "dfs" in code.lower()

    def test_fetch_from_issue_searches_comments(self):
        """Fetch code from issue URL (should search body then comments)."""
        code = python_md.fetch_github_content(self.ISSUE_URL)
        assert code is not None
        assert "bfs" in code.lower() or "dfs" in code.lower()

    def test_full_script_execution(self, tmp_path, capsys):
        """Run the actual script via subprocess."""
        result = subprocess.run(
            [str(SCRIPT_PATH), self.COMMENT_URL],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # The BFS/DFS script prints output
        assert "bfs" in result.stdout.lower() or "dfs" in result.stdout.lower()

    def test_local_file_execution(self, tmp_path, capsys):
        """Run script with a local markdown file."""
        md_file = tmp_path / "test.md"
        md_file.write_text("""
# Test

```python
print("test output")
```
""")
        result = subprocess.run(
            [str(SCRIPT_PATH), str(md_file)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "test output" in result.stdout

    def test_code_block_with_uv_script_dependencies(self, tmp_path):
        """Run code block that itself has uv script dependency headers."""
        md_file = tmp_path / "test_with_deps.md"
        # Code block contains a uv script with its own dependencies
        md_file.write_text('''
# Script with dependencies

```python
# /// script
# requires-python = ">=3.9"
# dependencies = ["cowsay"]
# ///
import cowsay
cowsay.cow("moo from python-md")
```
''')
        result = subprocess.run(
            [str(SCRIPT_PATH), str(md_file)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "moo from python-md" in result.stdout


if __name__ == "__main__":
    # Run with: ./test_python_md.py
    # Or: uv run pytest tools/tests/test_python_md.py
    sys.exit(pytest.main([__file__, "-v"]))

