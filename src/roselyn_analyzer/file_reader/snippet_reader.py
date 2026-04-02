"""File reading utilities for extracting code snippets."""

from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


def uri_to_path(uri: str) -> Path:
    """Convert a file URI to a Path.
    
    Args:
        uri: File URI (e.g., file:///app/repos/CleanArchitecture/src/File.cs)
        
    Returns:
        Path object.
    """
    if uri.startswith("file://"):
        parsed = urlparse(uri)
        return Path(unquote(parsed.path))
    return Path(uri)


def read_lines_from_file(file_path: Path, start_line: int, end_line: int) -> str | None:
    """Read specific lines from a file.
    
    Args:
        file_path: Path to the source file.
        start_line: Starting line number (1-indexed).
        end_line: Ending line number (1-indexed).
        
    Returns:
        Content string or None if file not found.
    """
    if not file_path.exists():
        return None
    
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    
    # Adjust for 0-indexed array
    actual_start = max(0, start_line - 1)
    actual_end = min(len(lines), end_line)
    
    return "".join(lines[actual_start:actual_end])


def read_entire_file(file_path: Path) -> str | None:
    """Read the entire contents of a file.
    
    Args:
        file_path: Path to the source file.
        
    Returns:
        File content string or None if file not found.
    """
    if not file_path.exists():
        return None
    
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def extract_class_content(file_content: str, target_line: int) -> str:
    """Extract the class containing the target line from C# file content.
    
    Args:
        file_content: Full file content.
        target_line: The line number we're interested in (1-indexed).
        
    Returns:
        The class content containing the target line, or full file if not found.
    """
    lines = file_content.split("\n")
    
    if target_line <= 0 or target_line > len(lines):
        return file_content
    
    # Find class/struct/record boundaries
    class_start = None
    brace_count = 0
    in_class = False
    class_end = None
    
    # Look backwards from target line to find class start
    for i in range(target_line - 1, -1, -1):
        line = lines[i].strip()
        
        # Check for class/struct/record declaration
        if any(keyword in line for keyword in ["class ", "struct ", "record "]):
            # Count braces from this point to verify it contains target line
            temp_brace = 0
            for j in range(i, len(lines)):
                temp_line = lines[j]
                temp_brace += temp_line.count("{") - temp_line.count("}")
                
                if j == target_line - 1:
                    if temp_brace > 0:
                        class_start = i
                        break
                    else:
                        break
                
                if temp_brace <= 0 and j > i:
                    break
            
            if class_start is not None:
                break
    
    if class_start is None:
        return file_content
    
    # Find class end by counting braces
    brace_count = 0
    started = False
    for i in range(class_start, len(lines)):
        line = lines[i]
        brace_count += line.count("{") - line.count("}")
        
        if "{" in line:
            started = True
        
        if started and brace_count <= 0:
            class_end = i + 1
            break
    
    if class_end is None:
        class_end = len(lines)
    
    # Include using statements and namespace from the beginning
    header_lines = []
    for i in range(class_start):
        line = lines[i].strip()
        if line.startswith("using ") or line.startswith("namespace ") or line == "" or line.startswith("//") or line.startswith("["):
            header_lines.append(lines[i])
        elif "{" in line and "namespace" not in lines[i-1] if i > 0 else True:
            header_lines.append(lines[i])
    
    class_lines = lines[class_start:class_end]
    
    return "\n".join(header_lines + class_lines)


def create_enriched_result(sarif_result: dict[str, Any]) -> dict[str, Any]:
    """Create an enriched result object with code content.
    
    Reads the entire class containing the flagged code for better context.
    
    Args:
        sarif_result: Parsed SARIF result dictionary.
        
    Returns:
        Enriched result with content field added.
    """
    # Extract content from the first location
    content = None
    full_file_content = None
    locations = sarif_result.get("locations", [])
    
    if locations:
        location = locations[0]
        file_uri = location.get("file", "")
        start_line = location.get("start_line", 0)
        
        if file_uri and start_line > 0:
            file_path = uri_to_path(file_uri)
            full_file_content = read_entire_file(file_path)
            
            if full_file_content:
                # Extract the class containing the target line
                content = extract_class_content(full_file_content, start_line)
    
    # Build the enriched result object
    enriched = {
        "ruleId": sarif_result.get("rule_id", ""),
        "level": sarif_result.get("level", "warning"),
        "message": sarif_result.get("message", ""),
        "content": content,
        "locations": [
            {
                "resultFile": {
                    "uri": loc.get("file", ""),
                    "region": {
                        "startLine": loc.get("start_line", 0),
                        "startColumn": loc.get("start_column", 0),
                        "endLine": loc.get("end_line", 0),
                        "endColumn": loc.get("end_column", 0),
                    }
                }
            }
            for loc in locations
        ],
        "properties": sarif_result.get("properties", {}),
    }
    
    return enriched


def create_enriched_results(sarif_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create enriched result objects for a list of SARIF results.
    
    Args:
        sarif_results: List of parsed SARIF results.
        
    Returns:
        List of enriched results with content fields.
    """
    return [create_enriched_result(result) for result in sarif_results]


def read_code_snippet(file_path: Path, start_line: int, end_line: int, context_lines: int = 2) -> dict[str, Any]:
    """Read a code snippet from a file.
    
    Args:
        file_path: Path to the source file.
        start_line: Starting line number (1-indexed).
        end_line: Ending line number (1-indexed).
        context_lines: Number of context lines before/after the snippet.
        
    Returns:
        Dictionary with snippet details.
    """
    if not file_path.exists():
        return {
            "error": f"File not found: {file_path}",
            "file": str(file_path),
            "snippet": None,
        }
    
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    
    total_lines = len(lines)
    
    # Adjust for 0-indexed array, add context
    actual_start = max(0, start_line - 1 - context_lines)
    actual_end = min(total_lines, end_line + context_lines)
    
    snippet_lines = lines[actual_start:actual_end]
    
    return {
        "file": str(file_path),
        "start_line": actual_start + 1,
        "end_line": actual_end,
        "target_start": start_line,
        "target_end": end_line,
        "snippet": "".join(snippet_lines),
        "lines": [
            {"line_number": actual_start + 1 + i, "content": line.rstrip()}
            for i, line in enumerate(snippet_lines)
        ],
    }


def extract_snippets_from_results(results: list[dict[str, Any]], context_lines: int = 2) -> list[dict[str, Any]]:
    """Extract code snippets for a list of SARIF results.
    
    Args:
        results: List of parsed SARIF results with locations.
        context_lines: Number of context lines before/after each snippet.
        
    Returns:
        List of results with code snippets attached.
    """
    enriched_results = []
    
    for result in results:
        enriched = result.copy()
        enriched["snippets"] = []
        
        for location in result.get("locations", []):
            file_uri = location.get("file", "")
            start_line = location.get("start_line", 0)
            end_line = location.get("end_line", start_line)
            
            if not file_uri or start_line == 0:
                continue
            
            file_path = uri_to_path(file_uri)
            snippet = read_code_snippet(file_path, start_line, end_line, context_lines)
            enriched["snippets"].append(snippet)
        
        enriched_results.append(enriched)
    
    return enriched_results


def print_result_with_snippet(result: dict[str, Any]) -> None:
    """Print a result with its code snippet.
    
    Args:
        result: Enriched result with snippets.
    """
    print(f"\n{'='*60}")
    print(f"Rule: {result.get('rule_id', 'unknown')}")
    print(f"Level: {result.get('level', 'unknown')}")
    print(f"Message: {result.get('message', '')}")
    
    for snippet in result.get("snippets", []):
        if snippet.get("error"):
            print(f"  Error: {snippet['error']}")
            continue
        
        print(f"\nFile: {snippet['file']}")
        print(f"Lines {snippet['target_start']}-{snippet['target_end']}:")
        print("-" * 40)
        
        for line_info in snippet.get("lines", []):
            line_num = line_info["line_number"]
            content = line_info["content"]
            
            # Mark target lines with arrow
            if snippet["target_start"] <= line_num <= snippet["target_end"]:
                print(f">>> {line_num:4d} | {content}")
            else:
                print(f"    {line_num:4d} | {content}")
        
        print("-" * 40)
