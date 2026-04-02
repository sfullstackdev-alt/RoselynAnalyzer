"""SARIF report reader utilities."""

import json
from pathlib import Path
from typing import Any


def parse_sarif_result(result: dict[str, Any]) -> dict[str, Any]:
    """Parse a single SARIF result into a simplified format.
    
    Args:
        result: Raw SARIF result dictionary.
        
    Returns:
        Parsed result with extracted fields.
    """
    message = result.get("message", "")
    if isinstance(message, dict):
        message = message.get("text", "")
    
    locations = []
    for location in result.get("locations", []):
        # Handle both SARIF formats: resultFile or physicalLocation
        result_file = location.get("resultFile", {})
        physical = location.get("physicalLocation", {})
        
        if result_file:
            uri = result_file.get("uri", "")
            region = result_file.get("region", {})
        else:
            artifact = physical.get("artifactLocation", {})
            uri = artifact.get("uri", "")
            region = physical.get("region", {})
        
        locations.append({
            "file": uri,
            "start_line": region.get("startLine", 0),
            "end_line": region.get("endLine", 0),
            "start_column": region.get("startColumn", 0),
            "end_column": region.get("endColumn", 0),
        })
    
    return {
        "rule_id": result.get("ruleId", ""),
        "level": result.get("level", "warning"),
        "message": message,
        "locations": locations,
        "properties": result.get("properties", {}),
    }


def read_sarif_results(repo_path: Path) -> dict[str, Any]:
    """Read SARIF report and extract first and last results.
    
    Args:
        repo_path: Path to the repository containing analysis_report.sarif.
        
    Returns:
        Dictionary with first_result and last_result.
    """
    sarif_path = repo_path / "analysis_report.sarif"
    
    if not sarif_path.exists():
        raise FileNotFoundError(f"SARIF report not found at {sarif_path}")
    
    with open(sarif_path) as f:
        sarif_data = json.load(f)
    
    # Navigate to runs/results
    runs = sarif_data.get("runs", [])
    if not runs:
        print("No runs found in SARIF report")
        return {"first_result": None, "last_result": None}
    
    # Get results from first run
    results = runs[0].get("results", [])
    
    if not results:
        print("No results found in SARIF report")
        return {"first_result": None, "last_result": None}
    
    first_result = parse_sarif_result(results[0])
    last_result = parse_sarif_result(results[-1])
    
    print("=== First Result ===")
    print(f"Rule ID: {first_result['rule_id']}")
    print(f"Level: {first_result['level']}")
    print(f"Message: {first_result['message']}")
    if first_result['locations']:
        loc = first_result['locations'][0]
        print(f"File: {loc['file']}")
        print(f"Line: {loc['start_line']}-{loc['end_line']}")
    if first_result['properties']:
        print(f"Properties: {json.dumps(first_result['properties'], indent=2)}")
    
    print("\n=== Last Result ===")
    print(f"Rule ID: {last_result['rule_id']}")
    print(f"Level: {last_result['level']}")
    print(f"Message: {last_result['message']}")
    if last_result['locations']:
        loc = last_result['locations'][0]
        print(f"File: {loc['file']}")
        print(f"Line: {loc['start_line']}-{loc['end_line']}")
    if last_result['properties']:
        print(f"Properties: {json.dumps(last_result['properties'], indent=2)}")
    
    print(f"\nTotal results: {len(results)}")
    
    return {
        "first_result": first_result,
        "last_result": last_result,
        "total_count": len(results),
    }
