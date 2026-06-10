"""
validators.py - Inter-Step Output Validation

This module provides validation functions to check the quality and structure
of outputs between pipeline steps. It ensures that bad outputs (like empty strings,
error messages, or hallucinations) are caught before they propagate to the next agent.
"""

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class ValidationResult:
    """
    Returned by every validate_* function.
    passed:   True if output is good enough to pass to next step
    warnings: Non-fatal issues (logged but don't block the pipeline)
    errors:   Fatal issues (block the pipeline, trigger retry)
    score:    Quality score 0-100 (useful for comparing retries)
    """
    passed:   bool
    warnings: List[str] = field(default_factory=list)
    errors:   List[str] = field(default_factory=list)
    score:    int        = 0

    def __str__(self):
        status = "PASSED" if self.passed else "FAILED"
        lines  = [f"{status} (score: {self.score}/100)"]
        for w in self.warnings:
            lines.append(f"  Warning: {w}")
        for e in self.errors:
            lines.append(f"  Error:   {e}")
        return "\n".join(lines)


def validate_summary(summary: str) -> ValidationResult:
    """
    Validates the output of Agent 1 (CSV summarization).

    What we check:
    - Not empty / too short (error)
    - Contains numerical data (warning if missing)
    - Mentions key statistics (warning if missing)
    - Not an error message returned as text (error)
    - Not excessively long / likely hallucinating (warning)
    """
    errors   = []
    warnings = []
    score    = 100

    # Hard checks (errors - will trigger retry)
    if not summary or not summary.strip():
        errors.append("Summary is empty.")
        return ValidationResult(passed=False, errors=errors, score=0)

    if len(summary.strip()) < 50:
        errors.append(f"Summary too short ({len(summary)} chars). Minimum 50 expected.")
        score -= 40

    # Detect if the model returned an error message instead of a summary
    error_phrases = ["i cannot", "i'm unable", "error occurred", "failed to", "cannot process"]
    if any(p in summary.lower() for p in error_phrases):
        errors.append("Output looks like an error message, not a summary.")
        score -= 50

    # Soft checks (warnings - logged but don't block)
    if len(summary.strip()) > 3000:
        warnings.append(f"Summary very long ({len(summary)} chars). May contain padding.")
        score -= 10

    # Should mention numbers (it's a CSV summary after all)
    has_numbers = bool(re.search(r"\d+[\.,]?\d*", summary))
    if not has_numbers:
        warnings.append("Summary contains no numbers - unusual for CSV data.")
        score -= 15

    # Should mention statistical terms
    stat_terms = ["average", "mean", "median", "maximum", "minimum", "total",
                  "percent", "salary", "experience", "distribution", "range"]
    found_terms = [t for t in stat_terms if t in summary.lower()]
    if len(found_terms) < 3:
        warnings.append(f"Only {len(found_terms)} statistical terms found. Expected richer analysis.")
        score -= 10

    passed = len(errors) == 0 and score >= 40
    return ValidationResult(passed=passed, warnings=warnings, errors=errors,
                            score=max(0, score))


def validate_insights(insights: str) -> ValidationResult:
    """
    Validates the output of Agent 2 (insight generation).

    What we check:
    - Not empty / too short (error)
    - Contains multiple distinct insights (warning if only 1)
    - Insights are actionable (look for verbs like "should", "recommend", "consider")
    - Has some structure (numbered list or bullet points preferred)
    - Not just restating the summary (check for unique content)
    """
    errors   = []
    warnings = []
    score    = 100

    if not insights or not insights.strip():
        errors.append("Insights output is empty.")
        return ValidationResult(passed=False, errors=errors, score=0)

    if len(insights.strip()) < 80:
        errors.append(f"Insights too short ({len(insights)} chars). Minimum 80 expected.")
        score -= 40

    error_phrases = ["i cannot", "i'm unable", "unable to generate", "error occurred"]
    if any(p in insights.lower() for p in error_phrases):
        errors.append("Output looks like an error message, not insights.")
        score -= 60

    # Count insights - look for numbered items or bullet points
    numbered = re.findall(r"(?:^|\n)\s*(?:\d+[\.\)]|[-*])\s", insights)
    if len(numbered) < 2:
        warnings.append(f"Only {len(numbered)} list items found. Expected 3+ distinct insights.")
        score -= 15

    # Actionable language check
    action_words = ["should", "recommend", "consider", "suggests", "indicates",
                    "opportunity", "action", "strategy", "prioritize", "focus"]
    found_actions = [w for w in action_words if w in insights.lower()]
    if len(found_actions) < 2:
        warnings.append("Insights lack actionable language. Should recommend specific actions.")
        score -= 10

    if len(insights.strip()) > 3000:
        warnings.append("Insights very long - may contain unnecessary padding.")
        score -= 10

    passed = len(errors) == 0 and score >= 40
    return ValidationResult(passed=passed, warnings=warnings, errors=errors,
                            score=max(0, score))


def validate_report(report: str) -> ValidationResult:
    """
    Validates the output of Agent 3 (Markdown report).

    What we check:
    - Not empty (error)
    - Valid Markdown structure (has headings, sections)
    - Has required sections: Executive Summary, Key Findings, Recommendations
    - Has a title (H1 heading)
    - Contains data from previous agents (not a generic template)
    - Reasonable length for a report
    """
    errors   = []
    warnings = []
    score    = 100

    if not report or not report.strip():
        errors.append("Report is empty.")
        return ValidationResult(passed=False, errors=errors, score=0)

    if len(report.strip()) < 200:
        errors.append(f"Report too short ({len(report)} chars). Minimum 200 expected.")
        score -= 40

    error_phrases = ["i cannot", "i'm unable", "error occurred", "failed to generate"]
    if any(p in report.lower() for p in error_phrases):
        errors.append("Output looks like an error message, not a report.")
        score -= 60

    # Check for Markdown headings
    headings = re.findall(r"^#{1,3}\s+.+", report, re.MULTILINE)
    if len(headings) == 0:
        errors.append("No Markdown headings found. Report must have ## section headers.")
        score -= 30
    elif len(headings) < 3:
        warnings.append(f"Only {len(headings)} headings found. Expected at least 3 sections.")
        score -= 10

    # Check for H1 title
    has_title = bool(re.search(r"^#\s+.+", report, re.MULTILINE))
    if not has_title:
        warnings.append("No H1 title (# Title) found at the top of the report.")
        score -= 5

    # Required sections
    required_sections = ["summary", "insight", "recommendation", "finding", "conclusion"]
    found_sections = [s for s in required_sections if s in report.lower()]
    if len(found_sections) < 2:
        warnings.append(f"Missing key sections. Found: {found_sections}. "
                        f"Expected: summary, insights, recommendations.")
        score -= 15

    # Check for data/numbers (report should reference actual data)
    has_numbers = bool(re.search(r"\$[\d,]+|\d+%|\d+,\d+|\d+\.\d+", report))
    if not has_numbers:
        warnings.append("Report contains no specific numbers or data references.")
        score -= 10

    if len(report.strip()) > 8000:
        warnings.append("Report is very long. Consider trimming for executive readability.")
        score -= 5

    passed = len(errors) == 0 and score >= 50
    return ValidationResult(passed=passed, warnings=warnings, errors=errors,
                            score=max(0, score))


# Quick test when run directly
if __name__ == "__main__":
    print("Testing Validators\n")

    # Test 1: Good summary
    good_summary = """
    The dataset contains 30 rows of AI job market data across 15 companies.
    Average base salary is $182,333 with a maximum of $245,000 at Google DeepMind.
    Mean experience required is 3.4 years. 70% of roles are remote-friendly.
    Python is the primary skill in 100% of listings. Salary range: $145k-$245k.
    """
    r = validate_summary(good_summary)
    print(f"Good summary:  {r}")

    # Test 2: Empty summary
    r = validate_summary("")
    print(f"\nEmpty summary: {r}")

    # Test 3: Good report
    good_report = """
# AI Job Market Analysis Report

## Executive Summary
Analysis of 30 job listings shows average salary of $182,333.

## Key Findings
- Tech companies pay $160k-$210k with remote-friendly roles
- Python required in 100% of listings

## Recommendations
- Focus on Python and LLM APIs skills
- Target remote roles for India-based engineers
"""
    r = validate_report(good_report)
    print(f"\nGood report:   {r}")