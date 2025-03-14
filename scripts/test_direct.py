#!/usr/bin/env python3
"""
Direct script to test the Analysis Agent with Workspace1 story 308.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_direct")

# Shortcut API key
API_KEY = "d58a1ad0-4deb-44fd-a6c7-d29ccb9221fa"
WORKSPACE_ID = "workspace1"
STORY_ID = "308"

def simulate_analysis():
    """Simulate the analysis process with a mock result."""
    logger.info(f"Analyzing story {STORY_ID} in workspace {WORKSPACE_ID}")
    
    # Simulate API delay
    time.sleep(1)
    
    # Create a simple analysis result (mock)
    analysis_result = {
        "overall_score": 7,
        "title_analysis": {
            "score": 8,
            "strengths": ["Clear and concise title", "Includes action verb"],
            "weaknesses": ["Could be more specific"],
            "recommendations": ["Add more context to the title"]
        },
        "description_analysis": {
            "score": 6,
            "strengths": ["Provides basic information"],
            "weaknesses": ["Lacks detailed requirements", "Missing context"],
            "recommendations": ["Add more detailed requirements", "Include background context"]
        },
        "acceptance_criteria_analysis": {
            "score": 7,
            "strengths": ["Clear list of requirements", "Covers key functionality"],
            "weaknesses": ["Could be more specific", "Missing edge cases"],
            "recommendations": ["Add more specific acceptance criteria", "Include edge cases"]
        },
        "priority_areas": [
            "Improve description detail", 
            "Add acceptance criteria for edge cases", 
            "Clarify expected outcomes"
        ],
        "summary": "The story is of good quality but needs more detailed requirements and edge case handling."
    }
    
    logger.info(f"Analysis complete for story {STORY_ID}")
    return analysis_result

def print_analysis_results(results):
    """Print analysis results in a readable format."""
    print("\n=== ANALYSIS RESULTS ===\n")
    
    # Print overall score and summary
    overall_score = results.get("overall_score", 0)
    print(f"Overall Score: {overall_score}/10")
    print(f"Summary: {results.get('summary', 'No summary provided')}")
    print("\n--- Component Analysis ---\n")
    
    # Print title analysis
    title_analysis = results.get("title_analysis", {})
    print(f"Title: {title_analysis.get('score', 0)}/10")
    print("  Strengths:")
    for strength in title_analysis.get("strengths", []):
        print(f"  ✓ {strength}")
    print("  Weaknesses:")
    for weakness in title_analysis.get("weaknesses", []):
        print(f"  ✗ {weakness}")
    print("  Recommendations:")
    for rec in title_analysis.get("recommendations", []):
        print(f"  → {rec}")
    print("")
    
    # Print description analysis
    desc_analysis = results.get("description_analysis", {})
    print(f"Description: {desc_analysis.get('score', 0)}/10")
    print("  Strengths:")
    for strength in desc_analysis.get("strengths", []):
        print(f"  ✓ {strength}")
    print("  Weaknesses:")
    for weakness in desc_analysis.get("weaknesses", []):
        print(f"  ✗ {weakness}")
    print("  Recommendations:")
    for rec in desc_analysis.get("recommendations", []):
        print(f"  → {rec}")
    print("")
    
    # Print acceptance criteria analysis if available
    ac_analysis = results.get("acceptance_criteria_analysis")
    if ac_analysis:
        print(f"Acceptance Criteria: {ac_analysis.get('score', 0)}/10")
        print("  Strengths:")
        for strength in ac_analysis.get("strengths", []):
            print(f"  ✓ {strength}")
        print("  Weaknesses:")
        for weakness in ac_analysis.get("weaknesses", []):
            print(f"  ✗ {weakness}")
        print("  Recommendations:")
        for rec in ac_analysis.get("recommendations", []):
            print(f"  → {rec}")
        print("")
    
    # Print priority areas
    print("Priority Areas for Improvement:")
    for i, area in enumerate(results.get("priority_areas", []), 1):
        print(f"  {i}. {area}")

def main():
    """Main function."""
    print(f"Testing Analysis Agent with Workspace1 Story 308")
    print(f"API Key: {API_KEY[:5]}...{API_KEY[-4:]}")
    
    # In a real implementation, we would call the Analysis Agent here
    # For now, we'll just simulate the analysis
    results = simulate_analysis()
    
    # Print the analysis results
    print_analysis_results(results)
    
    # Save results to file
    output_file = "analysis_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()