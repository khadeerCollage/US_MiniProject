import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "multi-agents")))
from validators import validate_summary, validate_insights, validate_report

def test_empty_summary_fails():
    result = validate_summary("")
    assert not result.passed
    assert result.score == 0
    assert "Summary is empty." in result.errors

def test_good_summary_passes():
    good = "Dataset has 30 rows. Average salary is $180k. 70% remote roles."
    result = validate_summary(good)
    assert result.passed

def test_summary_looks_like_error():
    bad = "I cannot generate a summary for this."
    result = validate_summary(bad)
    assert not result.passed
    assert any("error message" in e for e in result.errors)

def test_empty_insights_fails():
    result = validate_insights("   ")
    assert not result.passed

def test_good_insights_passes():
    good = "1. Focus on Python. You should learn it.\n2. Target remote roles. Consider applying globally."
    result = validate_insights(good)
    assert result.passed

def test_empty_report_fails():
    result = validate_report("")
    assert not result.passed

def test_report_without_headings_fails():
    result = validate_report("Just some text without any markdown structure.")
    assert not result.passed
    assert any("headings" in str(e).lower() for e in result.errors)

def test_good_report_passes():
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
    result = validate_report(good_report)
    assert result.passed
