"""Roslyn analyzer for .NET solutions."""

import json
import subprocess
from pathlib import Path
from typing import Any


def find_solution(repo_path: Path) -> Path | None:
    """Find the .sln file in the repository."""
    solutions = list(repo_path.glob("*.sln"))
    if solutions:
        return solutions[0]
    # Check subdirectories
    solutions = list(repo_path.glob("**/*.sln"))
    return solutions[0] if solutions else None


def run_roslyn_analysis(repo_path: Path, output_dir: Path | None = None) -> dict[str, Any]:
    """Run Roslyn analysis on a .NET solution.
    
    Args:
        repo_path: Path to the repository containing the solution.
        output_dir: Directory to save the report. Defaults to repo_path.
        
    Returns:
        Analysis results as a dictionary.
    """
    if output_dir is None:
        output_dir = repo_path
    
    solution_path = find_solution(repo_path)
    if not solution_path:
        raise FileNotFoundError(f"No .sln file found in {repo_path}")
    
    print(f"Found solution: {solution_path}")
    
    # SARIF output file (Roslyn's native format, which is JSON)
    sarif_path = output_dir / "analysis_report.sarif"
    
    print(f"Running Roslyn analysis on {solution_path}...")
    
    # Run dotnet build with analyzer output
    result = subprocess.run(
        [
            "dotnet", "build",
            str(solution_path),
            "--no-incremental",
            f"/p:ErrorLog={sarif_path},version=2.1",
            "/p:ReportAnalyzer=true",
        ],
        capture_output=True,
        text=True,
        cwd=repo_path,
    )
    
    # Parse SARIF and convert to simplified JSON
    analysis_result = {
        "solution": str(solution_path),
        "build_success": result.returncode == 0,
        "build_output": result.stdout,
        "build_errors": result.stderr,
        "diagnostics": [],
    }
    
    # Parse SARIF file if it exists
    if sarif_path.exists():
        with open(sarif_path) as f:
            sarif_data = json.load(f)
        
        # Extract diagnostics from SARIF
        for run in sarif_data.get("runs", []):
            for sarif_result in run.get("results", []):
                message = sarif_result.get("message", "")
                if isinstance(message, dict):
                    message_text = message.get("text", "")
                else:
                    message_text = str(message)
                
                diagnostic = {
                    "rule_id": sarif_result.get("ruleId", ""),
                    "message": message_text,
                    "level": sarif_result.get("level", "warning"),
                    "properties": sarif_result.get("properties", {}),
                    "locations": [],
                }
                
                for location in sarif_result.get("locations", []):
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
                    
                    diagnostic["locations"].append({
                        "file": uri,
                        "start_line": region.get("startLine", 0),
                        "end_line": region.get("endLine", 0),
                        "start_column": region.get("startColumn", 0),
                        "end_column": region.get("endColumn", 0),
                    })
                
                analysis_result["diagnostics"].append(diagnostic)
    
    # Save JSON report
    json_report_path = output_dir / "analysis_report.json"
    with open(json_report_path, "w") as f:
        json.dump(analysis_result, f, indent=2)
    
    print(f"Analysis complete. Report saved to {json_report_path}")
    print(f"Found {len(analysis_result['diagnostics'])} diagnostics")
    
    return analysis_result


def analyze_clean_architecture(output_dir: Path | None = None) -> dict[str, Any]:
    """Analyze the CleanArchitecture repository.
    
    Args:
        output_dir: Directory to save the report. Defaults to /app.
        
    Returns:
        Analysis results as a dictionary.
    """
    repo_path = Path("/app/repos/CleanArchitecture")
    
    if not repo_path.exists():
        raise FileNotFoundError(
            f"Repository not found at {repo_path}. "
            "Run clone_repository() first."
        )
    
    return run_roslyn_analysis(repo_path, output_dir)
