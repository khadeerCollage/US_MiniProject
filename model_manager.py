# =============================================================================
# model_manager.py  -  Multi-Provider Model Manager  (Sync + Async)
# =============================================================================
#
# THE CORE STRATEGY: Free Models + Smart Orchestration = Near-Claude Quality
#
# Why this works:
#   Claude is powerful. But "quality" comes from TWO places:
#     1. Raw model capability    (Claude wins here - we can't change this)
#     2. How you USE the model   (Orchestration - WE control this 100%)
#
#   By maximizing #2, we can close most of the gap with free models.
#
# FREE MODELS AVAILABLE:
#   +----------------------------------------------------------+
#   |  Provider    Model                 Free Tier Limit       |
#   |  ----------- ------------------- ---------------------  |
#   |  Groq        llama-3.3-70b        14,400 req/day       |
#   |  Groq        llama-3.1-8b         (blocked by org)     |
#   |  Groq        mixtral-8x7b         14,400 req/day       |
#   |  Gemini      gemini-1.5-flash     1,500 req/day        |
#   |  Gemini      gemini-1.5-pro       50 req/day           |
#   |  Anthropic   claude-sonnet-4-6    $5 credit            |
#   +----------------------------------------------------------+
#
# SMART ROUTING STRATEGY:
#   Simple task   -> Groq llama-3.3-70b   (fastest, saves quota)
#   Medium task   -> Groq llama-3.3-70b   (strong free model)
#   Long context  -> Gemini 1.5 Flash     (1M context window, free)
#   Critical task -> Anthropic            (only when really needed)
#
# ASYNC / PARALLEL SUPPORT (NEW):
#   Use manager.async_call() in async contexts.
#   Use asyncio.gather() to run multiple agents concurrently.
#
#   Example - 3 agents in parallel:
#     a, b, c = await asyncio.gather(
#         mgr.async_call(sys, prompt_a, task_label="Agent-A"),
#         mgr.async_call(sys, prompt_b, task_label="Agent-B"),
#         mgr.async_call(sys, prompt_c, task_label="Agent-C"),
#     )
#
# SETUP:
#   pip install groq google-generativeai anthropic
#   export GROQ_API_KEY="gsk_..."
#   export GEMINI_API_KEY="AI..."
#   export ANTHROPIC_API_KEY="sk-..."
# =============================================================================

import os
import time
import asyncio
from enum import Enum
from typing import Optional
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass


class TaskComplexity(Enum):
    """How complex is this task? Determines which model to use."""
    SIMPLE    = "simple"     # Short output, clear structure    -> fast cheap model
    MEDIUM    = "medium"     # Multi-paragraph, some reasoning  -> mid-tier model
    COMPLEX   = "complex"    # Deep analysis, long output       -> best available model
    LONG_CONTEXT = "long_context" # Large documents            -> Gemini 1.5 Flash (1M tokens)
    CRITICAL  = "critical"   # High stakes, must be excellent   -> Anthropic


@dataclass
class ModelResponse:
    """Standard response object - same format regardless of provider."""
    text:           str
    model_used:     str
    provider:       str
    input_tokens:   int
    output_tokens:  int
    latency_ms:     float
    cost_usd:       float   # Estimated cost (free models = $0.0)


# =============================================================================
# SYNC PROVIDERS
# =============================================================================

class GroqProvider:
    """
    Groq runs open-source models (Llama, Mixtral) at blazing speed.
    Free tier: 14,400 requests/day.
    """
    MODELS = {
        TaskComplexity.SIMPLE:   "llama-3.3-70b-versatile",  # 8b blocked by org
        TaskComplexity.MEDIUM:   "llama-3.3-70b-versatile",
        TaskComplexity.COMPLEX:  "llama-3.3-70b-versatile",
        TaskComplexity.LONG_CONTEXT: "llama-3.3-70b-versatile", # Fallback if Gemini fails
        TaskComplexity.CRITICAL: "llama-3.3-70b-versatile",
    }

    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        self._client = None

    def _get_client(self):
        if not self._client:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                raise ImportError("Run: pip install groq")
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key)

    def call(self, system: str, user: str,
             complexity: TaskComplexity = TaskComplexity.MEDIUM,
             max_tokens: int = 2048) -> ModelResponse:
        model  = self.MODELS[complexity]
        client = self._get_client()
        start  = time.time()
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user}
            ]
        )
        latency = (time.time() - start) * 1000
        return ModelResponse(
            text=response.choices[0].message.content,
            model_used=model,
            provider="Groq (Free)",
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            latency_ms=round(latency, 1),
            cost_usd=0.0
        )


class GeminiProvider:
    """Google Gemini 1.5 Flash: free tier, 1M token context window."""
    MODELS = {
        TaskComplexity.SIMPLE:   "gemini-1.5-flash",
        TaskComplexity.MEDIUM:   "gemini-1.5-flash",
        TaskComplexity.COMPLEX:  "gemini-1.5-pro",
        TaskComplexity.LONG_CONTEXT: "gemini-1.5-flash",
        TaskComplexity.CRITICAL: "gemini-1.5-pro",
    }

    def __init__(self):
        self.api_key     = os.environ.get("GEMINI_API_KEY", "")
        self._configured = False

    def _ensure_configured(self):
        if not self._configured:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._configured = True
            except ImportError:
                raise ImportError("Run: pip install google-generativeai")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def call(self, system: str, user: str,
             complexity: TaskComplexity = TaskComplexity.MEDIUM,
             max_tokens: int = 2048) -> ModelResponse:
        import google.generativeai as genai
        self._ensure_configured()
        model_name = self.MODELS[complexity]
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system,
            generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens)
        )
        start    = time.time()
        response = model.generate_content(user)
        latency  = (time.time() - start) * 1000
        return ModelResponse(
            text=response.text,
            model_used=model_name,
            provider="Google Gemini (Free)",
            input_tokens=response.usage_metadata.prompt_token_count,
            output_tokens=response.usage_metadata.candidates_token_count,
            latency_ms=round(latency, 1),
            cost_usd=0.0
        )


class AnthropicProvider:
    """Claude - use only when quality is non-negotiable."""
    MODEL = "claude-sonnet-4-6"

    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = None

    def _get_client(self):
        if not self._client:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key)

    def call(self, system: str, user: str,
             complexity: TaskComplexity = TaskComplexity.CRITICAL,
             max_tokens: int = 2048) -> ModelResponse:
        client   = self._get_client()
        start    = time.time()
        response = client.messages.create(
            model=self.MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}]
        )
        latency = (time.time() - start) * 1000
        cost = (response.usage.input_tokens  / 1_000_000 * 3.0 +
                response.usage.output_tokens / 1_000_000 * 15.0)
        return ModelResponse(
            text=response.content[0].text,
            model_used=self.MODEL,
            provider="Anthropic (Paid)",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=round(latency, 1),
            cost_usd=round(cost, 5)
        )


# =============================================================================
# ASYNC PROVIDERS  -  Non-blocking API calls for parallel / concurrent execution
# =============================================================================

class AsyncGroqProvider:
    """
    Async Groq using groq.AsyncGroq (official native async client).
    Enables multiple agents to fire API calls simultaneously with no blocking.

    Internally uses asyncio - no threads, pure cooperative concurrency.
    """
    MODELS = {
        TaskComplexity.SIMPLE:   "llama-3.3-70b-versatile",
        TaskComplexity.MEDIUM:   "llama-3.3-70b-versatile",
        TaskComplexity.COMPLEX:  "llama-3.3-70b-versatile",
        TaskComplexity.LONG_CONTEXT: "llama-3.3-70b-versatile", # Fallback
        TaskComplexity.CRITICAL: "llama-3.3-70b-versatile",
    }

    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        self._client = None

    def _get_client(self):
        if not self._client:
            try:
                from groq import AsyncGroq
                self._client = AsyncGroq(api_key=self.api_key)
            except ImportError:
                raise ImportError("Run: pip install groq")
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def call(self, system: str, user: str,
                   complexity: TaskComplexity = TaskComplexity.MEDIUM,
                   max_tokens: int = 2048) -> ModelResponse:
        model  = self.MODELS[complexity]
        client = self._get_client()
        start  = time.time()
        response = await client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user}
            ]
        )
        latency = (time.time() - start) * 1000
        return ModelResponse(
            text=response.choices[0].message.content,
            model_used=model,
            provider="Groq (Free) [async]",
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            latency_ms=round(latency, 1),
            cost_usd=0.0
        )


class AsyncGeminiProvider:
    """
    Async Gemini via asyncio.to_thread().
    Google's SDK has no native async client. asyncio.to_thread() is the
    correct pattern: each call runs in a thread-pool worker, releasing the
    event loop so other coroutines can proceed during the blocking HTTP call.
    """

    def __init__(self):
        self._sync = GeminiProvider()   # delegate to sync provider

    def is_available(self) -> bool:
        return self._sync.is_available()

    async def call(self, system: str, user: str,
                   complexity: TaskComplexity = TaskComplexity.MEDIUM,
                   max_tokens: int = 2048) -> ModelResponse:
        return await asyncio.to_thread(
            self._sync.call, system, user, complexity, max_tokens
        )


class AsyncAnthropicProvider:
    """
    Async Anthropic using anthropic.AsyncAnthropic (official native async client).
    Zero thread overhead - pure async HTTP via httpx.
    """
    MODEL = "claude-sonnet-4-6"

    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = None

    def _get_client(self):
        if not self._client:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("Run: pip install anthropic")
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def call(self, system: str, user: str,
                   complexity: TaskComplexity = TaskComplexity.CRITICAL,
                   max_tokens: int = 2048) -> ModelResponse:
        client   = self._get_client()
        start    = time.time()
        response = await client.messages.create(
            model=self.MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}]
        )
        latency = (time.time() - start) * 1000
        cost = (response.usage.input_tokens  / 1_000_000 * 3.0 +
                response.usage.output_tokens / 1_000_000 * 15.0)
        return ModelResponse(
            text=response.content[0].text,
            model_used=self.MODEL,
            provider="Anthropic (Paid) [async]",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=round(latency, 1),
            cost_usd=round(cost, 5)
        )


# =============================================================================
# SMART MODEL MANAGER  -  Sync + Async routing to the best available provider
# =============================================================================

class ModelManager:
    """
    Routes every call to the best available provider automatically.

    SYNC  (sequential/blocking):
        response = manager.call(system, user, complexity=TaskComplexity.MEDIUM)

    ASYNC (concurrent/non-blocking):
        response = await manager.async_call(system, user, ...)

    PARALLEL (fire multiple calls at once):
        a, b, c = await asyncio.gather(
            manager.async_call(sys, p1, task_label="Agent-A"),
            manager.async_call(sys, p2, task_label="Agent-B"),
            manager.async_call(sys, p3, task_label="Agent-C"),
        )

    Provider priority: Groq (free+fast) -> Gemini (free+smart) -> Anthropic (paid+best)
    Override with: manager.call(..., prefer="gemini")
    """

    def __init__(self, prefer_free: bool = True):
        # Sync providers
        self.groq      = GroqProvider()
        self.gemini    = GeminiProvider()
        self.anthropic = AnthropicProvider()
        # Async providers (same API keys, non-blocking HTTP clients)
        self.async_groq      = AsyncGroqProvider()
        self.async_gemini    = AsyncGeminiProvider()
        self.async_anthropic = AsyncAnthropicProvider()

        self.prefer_free = prefer_free

        # Usage tracking - shared across sync + async (asyncio is single-threaded,
        # so list.append() and float += are safe from concurrent coroutines)
        self.call_log   = []
        self.total_cost = 0.0

    def get_available_providers(self) -> list:
        available = []
        if self.groq.is_available():      available.append("groq")
        if self.gemini.is_available():    available.append("gemini")
        if self.anthropic.is_available(): available.append("anthropic")
        return available

    # -------------------------------------------------------------------------
    # SYNC call  -  blocking, sequential
    # -------------------------------------------------------------------------

    def call(self, system: str, user: str,
             complexity: TaskComplexity = TaskComplexity.MEDIUM,
             max_tokens: int = 2048,
             prefer: Optional[str] = None,
             task_label: str = "") -> ModelResponse:
        """
        Blocking call. Routes to best sync provider.
        Use in regular (non-async) code or LangGraph sync nodes.
        """
        provider = self._select_provider(complexity, prefer)
        response = provider.call(system, user, complexity, max_tokens)
        self._log(response, task_label)
        return response

    def _select_provider(self, complexity: TaskComplexity, prefer: Optional[str]):
        """Route to the best available sync provider."""
        if prefer:
            mapping = {"groq": self.groq, "gemini": self.gemini, "anthropic": self.anthropic}
            p = mapping.get(prefer.lower())
            if p and p.is_available():
                return p

        if complexity == TaskComplexity.CRITICAL and not self.prefer_free:
            if self.anthropic.is_available():
                return self.anthropic

        if complexity == TaskComplexity.LONG_CONTEXT and self.gemini.is_available():
            return self.gemini

        if self.groq.is_available():      return self.groq
        if self.gemini.is_available():    return self.gemini
        if self.anthropic.is_available(): return self.anthropic

        raise RuntimeError(
            "No model providers configured!\n"
            "Set at least one API key:\n"
            "  GROQ_API_KEY     - free: console.groq.com\n"
            "  GEMINI_API_KEY   - free: aistudio.google.com\n"
            "  ANTHROPIC_API_KEY - paid"
        )

    # -------------------------------------------------------------------------
    # ASYNC call  -  non-blocking, use with asyncio.gather() for parallelism
    # -------------------------------------------------------------------------

    async def async_call(self, system: str, user: str,
                         complexity: TaskComplexity = TaskComplexity.MEDIUM,
                         max_tokens: int = 2048,
                         prefer: Optional[str] = None,
                         task_label: str = "",
                         _retries: int = 2) -> ModelResponse:
        """
        Non-blocking async call with automatic retry on transient timeouts.

        Retries up to _retries times with exponential backoff on:
        - groq.APITimeoutError
        - httpx.ConnectTimeout

        Multiple async_call()s can run simultaneously with asyncio.gather():
            results = await asyncio.gather(
                mgr.async_call(sys, prompt_a, task_label="A"),
                mgr.async_call(sys, prompt_b, task_label="B"),
            )
        """
        provider = self._select_async_provider(complexity, prefer)
        last_err = None

        for attempt in range(_retries + 1):
            try:
                response = await provider.call(system, user, complexity, max_tokens)
                self._log(response, task_label)
                return response
            except Exception as e:
                err_name = type(e).__name__
                is_timeout = ("Timeout" in err_name or "ConnectTimeout" in err_name
                              or "APITimeout" in err_name)
                if is_timeout and attempt < _retries:
                    wait = 2 ** attempt   # 1s, 2s, ...
                    print(f"    [{task_label}] Timeout (attempt {attempt+1}/{_retries+1}), retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    last_err = e
                else:
                    raise

        raise last_err  # should not reach here


    def _select_async_provider(self, complexity: TaskComplexity, prefer: Optional[str]):
        """Route to the best available async provider."""
        if prefer:
            mapping = {
                "groq":      self.async_groq,
                "gemini":    self.async_gemini,
                "anthropic": self.async_anthropic,
            }
            p = mapping.get(prefer.lower())
            if p and p.is_available():
                return p

        if complexity == TaskComplexity.CRITICAL and not self.prefer_free:
            if self.async_anthropic.is_available():
                return self.async_anthropic

        if complexity == TaskComplexity.LONG_CONTEXT and self.async_gemini.is_available():
            return self.async_gemini

        if self.async_groq.is_available():      return self.async_groq
        if self.async_gemini.is_available():    return self.async_gemini
        if self.async_anthropic.is_available(): return self.async_anthropic

        raise RuntimeError(
            "No async model providers configured!\n"
            "Set at least one API key:\n"
            "  GROQ_API_KEY     - free: console.groq.com\n"
            "  GEMINI_API_KEY   - free: aistudio.google.com\n"
            "  ANTHROPIC_API_KEY - paid"
        )

    # -------------------------------------------------------------------------
    # Internal logging (shared by sync + async)
    # -------------------------------------------------------------------------

    def _log(self, response: ModelResponse, task_label: str):
        """Append call to log and accumulate cost. Safe from async coroutines."""
        self.total_cost += response.cost_usd
        self.call_log.append({
            "task":     task_label or "unnamed",
            "provider": response.provider,
            "model":    response.model_used,
            "in_tok":   response.input_tokens,
            "out_tok":  response.output_tokens,
            "latency":  response.latency_ms,
            "cost":     response.cost_usd,
        })

    # -------------------------------------------------------------------------
    # Usage reporting
    # -------------------------------------------------------------------------

    def print_usage_report(self):
        """Print a summary of all API calls made this session."""
        if not self.call_log:
            print("  No calls made yet.")
            return

        print(f"\n  {'Task':<28} {'Provider':<25} {'In':>6} {'Out':>6} {'ms':>6} {'$':>8}")
        print("  " + "-" * 82)
        for e in self.call_log:
            print(f"  {e['task']:<28} {e['provider']:<25} "
                  f"{e['in_tok']:>5}t {e['out_tok']:>5}t "
                  f"{e['latency']:>5.0f} ${e['cost']:>7.5f}")
        print("  " + "-" * 82)
        print(f"  {'TOTAL':<28} {'':<25} {'':>6} {'':>6} {'':>6} ${self.total_cost:>7.5f}")
        free_calls = sum(1 for e in self.call_log if e["cost"] == 0.0)
        print(f"\n  Free calls: {free_calls}/{len(self.call_log)} "
              f"({int(free_calls / len(self.call_log) * 100)}% free)")


# =============================================================================
# Quick self-test
# =============================================================================

if __name__ == "__main__":
    print("\n=== Model Manager - Provider Status ===\n")
    mgr = ModelManager()
    available = mgr.get_available_providers()
    print(f"  Available providers: {available or ['none configured']}")
    print()

    for name, prov in [("Groq", mgr.groq), ("Gemini", mgr.gemini), ("Anthropic", mgr.anthropic)]:
        status = "Available" if prov.is_available() else "Not configured"
        print(f"  {name:12}: {status}")

    if not available:
        print("\n  Set GROQ_API_KEY or GEMINI_API_KEY to test.")
    else:
        print("\n  [Sync] Running test call...")
        r = mgr.call(
            system="You are a helpful assistant. Be very brief.",
            user="Say exactly: 'Sync Model Manager working!'",
            complexity=TaskComplexity.SIMPLE,
            task_label="Test-Sync"
        )
        print(f"  Response: {r.text.strip()}")
        print(f"  Provider: {r.provider} | Latency: {r.latency_ms}ms")

        async def _test_async():
            print("\n  [Async] Running parallel async test calls...")
            r1, r2 = await asyncio.gather(
                mgr.async_call(
                    system="Be very brief.",
                    user="Say: 'Async call 1 done!'",
                    complexity=TaskComplexity.SIMPLE,
                    task_label="Test-Async-1"
                ),
                mgr.async_call(
                    system="Be very brief.",
                    user="Say: 'Async call 2 done!'",
                    complexity=TaskComplexity.SIMPLE,
                    task_label="Test-Async-2"
                ),
            )
            print(f"  Response 1: {r1.text.strip()}")
            print(f"  Response 2: {r2.text.strip()}")
            print(f"  Both fired in parallel!")

        asyncio.run(_test_async())
        print()
        mgr.print_usage_report()
