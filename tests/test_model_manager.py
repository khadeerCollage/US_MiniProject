import pytest
from unittest.mock import MagicMock
from model_manager import ModelManager, TaskComplexity

def test_long_context_routes_to_gemini():
    """Test that a LONG_CONTEXT task is routed to the Gemini provider when available."""
    mgr = ModelManager()
    
    # Mock availability to force testing the routing logic
    mgr.gemini.is_available = MagicMock(return_value=True)
    mgr.groq.is_available = MagicMock(return_value=True)
    
    provider = mgr._select_provider(TaskComplexity.LONG_CONTEXT, prefer=None)
    assert provider == mgr.gemini, "LONG_CONTEXT should route to Gemini"

def test_critical_routes_to_anthropic_when_paid():
    """Test that CRITICAL tasks route to Anthropic when prefer_free is False."""
    mgr = ModelManager(prefer_free=False)
    
    # Mock availability
    mgr.anthropic.is_available = MagicMock(return_value=True)
    mgr.groq.is_available = MagicMock(return_value=True)
    
    provider = mgr._select_provider(TaskComplexity.CRITICAL, prefer=None)
    assert provider == mgr.anthropic, "CRITICAL tasks should route to Anthropic when not preferring free models"

def test_fallback_routing():
    """Test that if preferred or designated provider is unavailable, it falls back to others."""
    mgr = ModelManager()
    
    # Gemini unavailable, Groq available
    mgr.gemini.is_available = MagicMock(return_value=False)
    mgr.groq.is_available = MagicMock(return_value=True)
    
    provider = mgr._select_provider(TaskComplexity.LONG_CONTEXT, prefer=None)
    assert provider == mgr.groq, "Should fall back to Groq if Gemini is unavailable for LONG_CONTEXT"
