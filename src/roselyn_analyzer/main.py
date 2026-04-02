"""Main entry point for Roselyn Analyzer."""

from pathlib import Path

from roselyn_analyzer.clone_and_build import clone_repository
from roselyn_analyzer.analyzer import analyze_clean_architecture
from roselyn_analyzer.resolver import read_sarif_results
from roselyn_analyzer.file_reader import create_enriched_results
from roselyn_analyzer.processor import process_enriched_results, save_modernization_report


def main() -> None:
    """Run the Roselyn Analyzer."""
    print("Welcome to Roselyn Analyzer!")
    
    # Clone the repository from GIT_REPO env var
    clone_path = clone_repository()
    print(f"Repository cloned to: {clone_path}")
    
    # Run Roslyn analysis
    print("\nStarting Roslyn analysis...")
    results = analyze_clean_architecture()
    
    print(f"\nBuild successful: {results['build_success']}")
    print(f"Total diagnostics: {len(results['diagnostics'])}")
    
    # Read and display SARIF results
    print("\n--- SARIF Results Summary ---")
    sarif_results = read_sarif_results(Path("/app/repos/CleanArchitecture"))
    
    # Get first and last results for processing
    results_to_process = []
    if sarif_results["first_result"]:
        results_to_process.append(sarif_results["first_result"])
    if sarif_results["last_result"] and sarif_results["total_count"] > 1:
        results_to_process.append(sarif_results["last_result"])
    
    # Create enriched results with full class content
    print("\n--- Creating Enriched Results ---")
    enriched = create_enriched_results(results_to_process)
    
    # Process through OpenAI for modernization
    print("\n--- Processing with LLM ---")
    modernization_results = process_enriched_results(enriched)
    
    # Print the results
    print("\n--- LLM Modernization Results ---")
    for i, result in enumerate(modernization_results):
        print(f"\n{'='*60}")
        print(f"Result {i + 1}:")
        if result["success"]:
            print(f"  Rule: {result['ruleId']}")
            print(f"  Explanation: {result['explanation']}")
            print(f"  Changes:")
            for change in result.get('changes', []):
                print(f"    - {change}")
            print(f"\n  Fixed Code:")
            print("-" * 40)
            print(result['fixed_code'])
            print("-" * 40)
        else:
            print(f"  Failed: {result.get('error', 'Unknown error')}")
    
    # Save the report
    save_modernization_report(
        modernization_results,
        "/app/repos/CleanArchitecture/modernization_report.json"
    )


if __name__ == "__main__":
    main()
