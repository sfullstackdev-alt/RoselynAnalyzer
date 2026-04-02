"""Code modernization processor using OpenAI."""

import json
import os
from typing import Any

from openai import OpenAI


def get_openai_client() -> OpenAI:
    """Get OpenAI client instance."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)


def add_line_numbers_and_markers(content: str, target_start: int, target_end: int) -> str:
    """Add line numbers and markers to code content.
    
    Args:
        content: The code content.
        target_start: Start line to mark (1-indexed).
        target_end: End line to mark (1-indexed).
        
    Returns:
        Code with line numbers and markers on target lines.
    """
    lines = content.split("\n")
    numbered_lines = []
    
    for i, line in enumerate(lines, 1):
        if target_start <= i <= target_end:
            # Mark target lines with arrow
            numbered_lines.append(f">>> {i:4d} | {line}")
        else:
            numbered_lines.append(f"    {i:4d} | {line}")
    
    return "\n".join(numbered_lines)


def create_modernization_prompt(result: dict[str, Any]) -> str:
    """Create a prompt for code modernization.
    
    Args:
        result: Enriched result with ruleId, message, content, etc.
        
    Returns:
        Prompt string for the LLM.
    """
    rule_id = result.get("ruleId", "")
    message = result.get("message", "")
    content = result.get("content", "")
    properties = result.get("properties", {})
    
    locations = result.get("locations", [])
    file_info = ""
    target_start = 0
    target_end = 0
    file_uri = ""
    
    if locations:
        loc = locations[0].get("resultFile", {})
        file_uri = loc.get("uri", "")
        file_info = f"File: {file_uri}"
        region = loc.get("region", {})
        if region:
            target_start = region.get("startLine", 0)
            target_end = region.get("endLine", target_start)
            file_info += f"\nTarget Lines: {target_start}-{target_end} (marked with >>> below)"
    
    # Add line numbers and markers to the code
    if content and target_start > 0:
        numbered_content = add_line_numbers_and_markers(content, target_start, target_end)
    else:
        numbered_content = content
    
    # Save the marked content to a text file in the solution root
    save_marked_content(numbered_content, rule_id, file_uri)
    
    prompt = f"""You are a .NET code modernization expert. Analyze the following code issue and provide a fix.

## Issue Details
- Rule ID: {rule_id}
- Message: {message}
- {file_info}

## Properties
{json.dumps(properties, indent=2)}

## Current Code (lines marked with >>> need attention)
```
{numbered_content}
```

## Instructions
1. Focus on the lines marked with >>> - these are the specific lines flagged by the analyzer
2. Analyze the issue based on the rule ID and message
3. Provide the complete fixed code for the entire class/file shown above
4. Explain what changes were made and why

## Response Format
Provide your response in the following JSON format:
{{
    "fixed_code": "// Complete fixed C# code (entire class, not just the changed lines)",
    "explanation": "Brief explanation of changes",
    "changes": ["List of specific changes made"]
}}
"""
    return prompt


def save_marked_content(content: str, rule_id: str, file_uri: str) -> None:
    """Save marked content to a text file in the solution root.
    
    Args:
        content: The code content with line numbers and markers.
        rule_id: The rule ID for naming the file.
        file_uri: The source file URI for reference.
    """
    import re
    from pathlib import Path
    
    # Create a safe filename from rule_id
    safe_rule_id = re.sub(r'[^\w\-]', '_', rule_id)
    
    # Extract filename from URI for additional context
    source_filename = ""
    if file_uri:
        source_filename = Path(file_uri.replace("file://", "")).stem
        safe_source = re.sub(r'[^\w\-]', '_', source_filename)
        filename = f"marked_content_{safe_rule_id}_{safe_source}.txt"
    else:
        filename = f"marked_content_{safe_rule_id}.txt"
    
    output_path = Path("/app/repos/CleanArchitecture") / filename
    
    header = f"""# Marked Content for Analysis
# Rule ID: {rule_id}
# Source: {file_uri}
# Lines marked with >>> require attention
# ========================================

"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + content)
    
    print(f"  Saved marked content to: {output_path}")


def modernize_code(result: dict[str, Any], client: OpenAI | None = None) -> dict[str, Any]:
    """Use OpenAI to modernize code based on SARIF result.
    
    Args:
        result: Enriched result with code content.
        client: Optional OpenAI client instance.
        
    Returns:
        Modernization result with fixed code and explanation.
    """
    if client is None:
        client = get_openai_client()
    
    if not result.get("content"):
        return {
            "success": False,
            "error": "No code content available",
            "original": result,
        }
    
    prompt = create_modernization_prompt(result)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a .NET code modernization expert. Always respond with valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        
        response_text = response.choices[0].message.content
        modernization = json.loads(response_text)
        
        return {
            "success": True,
            "ruleId": result.get("ruleId", ""),
            "original_code": result.get("content", ""),
            "fixed_code": modernization.get("fixed_code", ""),
            "explanation": modernization.get("explanation", ""),
            "changes": modernization.get("changes", []),
            "locations": result.get("locations", []),
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "original": result,
        }


def process_enriched_results(
    enriched_results: list[dict[str, Any]],
    client: OpenAI | None = None,
) -> list[dict[str, Any]]:
    """Process a list of enriched results for code modernization.
    
    Args:
        enriched_results: List of enriched SARIF results with code content.
        client: Optional OpenAI client instance.
        
    Returns:
        List of modernization results.
    """
    if client is None:
        client = get_openai_client()
    
    modernization_results = []
    
    for i, result in enumerate(enriched_results):
        print(f"\nProcessing result {i + 1}/{len(enriched_results)}...")
        print(f"  Rule: {result.get('ruleId', 'unknown')}")
        print(f"  Message: {result.get('message', '')[:80]}...")
        
        modernization = modernize_code(result, client)
        modernization_results.append(modernization)
        
        if modernization["success"]:
            print(f"  ✓ Modernization complete")
            print(f"  Explanation: {modernization.get('explanation', '')[:100]}...")
        else:
            print(f"  ✗ Failed: {modernization.get('error', 'Unknown error')}")
    
    return modernization_results


def save_modernization_report(
    results: list[dict[str, Any]],
    output_path: str,
) -> None:
    """Save modernization results to a JSON file.
    
    Args:
        results: List of modernization results.
        output_path: Path to save the report.
    """
    report = {
        "total_processed": len(results),
        "successful": sum(1 for r in results if r.get("success")),
        "failed": sum(1 for r in results if not r.get("success")),
        "results": results,
    }
    
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nModernization report saved to {output_path}")
