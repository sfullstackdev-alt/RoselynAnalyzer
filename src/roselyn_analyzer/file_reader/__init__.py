"""FileReader - File reading utilities."""

from .snippet_reader import (
    create_enriched_result,
    create_enriched_results,
    extract_class_content,
    extract_snippets_from_results,
    print_result_with_snippet,
    read_code_snippet,
    read_entire_file,
    read_lines_from_file,
    uri_to_path,
)

__all__ = [
    "create_enriched_result",
    "create_enriched_results",
    "extract_class_content",
    "extract_snippets_from_results",
    "print_result_with_snippet",
    "read_code_snippet",
    "read_entire_file",
    "read_lines_from_file",
    "uri_to_path",
]
