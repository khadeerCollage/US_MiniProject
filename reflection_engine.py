# =============================================================================
# reflection_engine.py  -  Self-Reflection Quality Booster
# =============================================================================
#
# THE BIG IDEA:
#   This is the single most powerful technique to boost free model quality.
#   Instead of accepting the first output, you ask the model to:
#     1. Generate initial answer
#     2. Critique that answer ("What's wrong with this?")
#     3. Improve based on the critique
#     4. Validate the final result
#
#   Research shows this improves output quality by 20-40% for complex tasks.
#   A Llama-70B with reflection often matches Claude on structured tasks.
#
# THE REFLECTION LOOP:
#
#   1. Initial Output
#   2. [CRITIC] "What's weak? What's missing?"
#   3. Quality Score (1-10)
#      - If Score >= 7: Return output
#      - If Score < 7: [IMPROVER] Fix issues
#   4. Improved output (loops max 2x)
#
# =============================================================================

import re
from model_manager import ModelManager, TaskComplexity, ModelResponse


class ReflectionEngine:
    """
    Wraps any model call with a self-reflection quality loop.
    Use this for any output where quality matters.
    """

    def __init__(self, model_manager: ModelManager, max_reflections: int = 2):
        self.mgr = model_manager
        self.max_reflections = max_reflections

    # -- CRITIC PROMPT ---------------------------------------------------------
    CRITIC_SYSTEM = """
You are a rigorous quality critic. Your job is to identify weaknesses in AI-generated content.
Be harsh but fair. Focus on what would make the output more useful and accurate.
"""

    CRITIC_TEMPLATE = """
Review this AI-generated output for the task: "{task_description}"

OUTPUT TO REVIEW:
---
{output}
---

Evaluate on these dimensions:
1. ACCURACY: Is everything factually correct? Any hallucinations?
2. COMPLETENESS: What important points are missing?
3. STRUCTURE: Is it well-organized and easy to read?
4. ACTIONABILITY: Does it give the reader clear next steps?
5. SPECIFICITY: Are there vague claims that should be specific?

Respond in this EXACT format:
QUALITY_SCORE: [1-10]
CRITICAL_ISSUES: [list the 2-3 most important problems]
IMPROVEMENT_INSTRUCTIONS: [specific instructions to fix each issue]
VERDICT: [ACCEPT if score >= 7, IMPROVE if score < 7]
"""

    # -- IMPROVER PROMPT -------------------------------------------------------
    IMPROVER_SYSTEM = """
You are an expert editor and writer. You take AI-generated content and improve it
based on specific critique feedback. Make targeted improvements, not a complete rewrite.
"""

    IMPROVER_TEMPLATE = """
You must improve this output based on the critique below.

ORIGINAL TASK: {task_description}

CURRENT OUTPUT:
---
{output}
---

CRITIQUE:
{critique}

Instructions:
- Fix the specific issues mentioned in CRITICAL_ISSUES
- Follow the IMPROVEMENT_INSTRUCTIONS exactly
- Keep everything that was working well
- Do NOT add information you don't have evidence for
- Output the improved version directly (no meta-commentary)
"""

    def critique(self, output: str, task_description: str) -> dict:
        """
        Ask the model to critique an output.
        Returns: {"score": int, "issues": str, "instructions": str, "verdict": str}
        """
        user_msg = self.CRITIC_TEMPLATE.format(
            task_description=task_description,
            output=output
        )

        response = self.mgr.call(
            system=self.CRITIC_SYSTEM,
            user=user_msg,
            complexity=TaskComplexity.MEDIUM,
            max_tokens=512,
            task_label="Reflection-Critique"
        )

        text = response.text

        # Parse the structured critique
        # Handle "8/10", "8 out of 10", "8.5", etc.
        score_match  = re.search(r"QUALITY_SCORE:?\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        issues_match = re.search(r"CRITICAL_ISSUES:\s*(.*?)(?=IMPROVEMENT|$)", text, re.DOTALL)
        instruct_match = re.search(r"IMPROVEMENT_INSTRUCTIONS:\s*(.*?)(?=VERDICT|$)", text, re.DOTALL)
        verdict_match = re.search(r"VERDICT:\s*(ACCEPT|IMPROVE)", text)

        score   = int(score_match.group(1)) if score_match else 5
        issues  = issues_match.group(1).strip() if issues_match else text[:200]
        instructions = instruct_match.group(1).strip() if instruct_match else ""
        verdict = verdict_match.group(1) if verdict_match else ("ACCEPT" if score >= 7 else "IMPROVE")

        return {
            "score":        score,
            "issues":       issues,
            "instructions": instructions,
            "verdict":      verdict,
            "full_text":    text
        }

    def improve(self, output: str, critique: dict, task_description: str,
                original_system: str, original_user: str) -> str:
        """
        Ask the model to improve its output based on the critique.
        """
        user_msg = self.IMPROVER_TEMPLATE.format(
            task_description=task_description,
            output=output,
            critique=f"Issues: {critique['issues']}\nInstructions: {critique['instructions']}"
        )

        response = self.mgr.call(
            system=self.IMPROVER_SYSTEM,
            user=user_msg,
            complexity=TaskComplexity.COMPLEX,
            max_tokens=2048,
            task_label="Reflection-Improve"
        )

        return response.text

    def generate_with_reflection(
        self,
        system: str,
        user: str,
        task_description: str,
        complexity: TaskComplexity = TaskComplexity.MEDIUM,
        max_tokens: int = 1500,
        task_label: str = "",
        verbose: bool = True
    ) -> tuple:
        """
        The main method: generate → critique → improve (up to max_reflections times).

        Returns: (final_text, quality_score, reflection_count)
        """
        if verbose:
            print(f"\n    [{task_label}] Generating initial output...")

        # Step 1: Initial generation
        initial_response = self.mgr.call(
            system=system, user=user,
            complexity=complexity, max_tokens=max_tokens,
            task_label=f"{task_label}-Draft"
        )
        current_output = initial_response.text
        final_score    = 5   # default
        reflections    = 0

        # Step 2: Reflection loop
        for i in range(self.max_reflections):
            if verbose:
                print(f"    [{task_label}] Running reflection {i+1}/{self.max_reflections}...")

            critique = self.critique(current_output, task_description)
            final_score = critique["score"]

            if verbose:
                print(f"      Quality score: {critique['score']}/10 | Verdict: {critique['verdict']}")
                if critique["issues"]:
                    issue_preview = critique["issues"][:120].replace("\n", " ")
                    print(f"      Issues: {issue_preview}...")

            if critique["verdict"] == "ACCEPT" or critique["score"] >= 7:
                if verbose:
                    print(f"    [{task_label}] Quality accepted at score {critique['score']}/10")
                break

            # Improve
            if verbose:
                print(f"     [{task_label}] Improving output...")

            improved = self.improve(current_output, critique, task_description, system, user)
            current_output = improved
            reflections += 1

        return current_output, final_score, reflections

    # =========================================================================
    # ASYNC versions  -  use inside 'async def' nodes and asyncio.gather()
    # =========================================================================

    async def critique_async(self, output: str, task_description: str) -> dict:
        """
        Async version of critique() -- non-blocking.
        Yields control to the event loop while awaiting the API response.
        """
        user_msg = self.CRITIC_TEMPLATE.format(
            task_description=task_description,
            output=output
        )
        response = await self.mgr.async_call(
            system=self.CRITIC_SYSTEM,
            user=user_msg,
            complexity=TaskComplexity.MEDIUM,
            max_tokens=512,
            task_label="Reflection-Critique"
        )
        text           = response.text
        # Handle "8/10", "8 out of 10", "8.5", etc.
        score_match    = re.search(r"QUALITY_SCORE:?\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        issues_match   = re.search(r"CRITICAL_ISSUES:\s*(.*?)(?=IMPROVEMENT|$)", text, re.DOTALL)
        instruct_match = re.search(r"IMPROVEMENT_INSTRUCTIONS:\s*(.*?)(?=VERDICT|$)", text, re.DOTALL)
        verdict_match  = re.search(r"VERDICT:\s*(ACCEPT|IMPROVE)", text)

        score        = int(score_match.group(1)) if score_match else 5
        issues       = issues_match.group(1).strip() if issues_match else text[:200]
        instructions = instruct_match.group(1).strip() if instruct_match else ""
        verdict      = verdict_match.group(1) if verdict_match else ("ACCEPT" if score >= 7 else "IMPROVE")

        return {
            "score":        score,
            "issues":       issues,
            "instructions": instructions,
            "verdict":      verdict,
            "full_text":    text,
        }

    async def improve_async(self, output: str, critique: dict, task_description: str,
                            original_system: str, original_user: str) -> str:
        """
        Async version of improve() -- non-blocking.
        """
        user_msg = self.IMPROVER_TEMPLATE.format(
            task_description=task_description,
            output=output,
            critique=f"Issues: {critique['issues']}\nInstructions: {critique['instructions']}"
        )
        response = await self.mgr.async_call(
            system=self.IMPROVER_SYSTEM,
            user=user_msg,
            complexity=TaskComplexity.COMPLEX,
            max_tokens=2048,
            task_label="Reflection-Improve"
        )
        return response.text

    async def generate_with_reflection_async(
        self,
        system: str,
        user: str,
        task_description: str,
        complexity: TaskComplexity = TaskComplexity.MEDIUM,
        max_tokens: int = 1500,
        task_label: str = "",
        verbose: bool = True
    ) -> tuple:
        """
        Async generate -> critique -> improve loop.

        Use this inside async def nodes or with asyncio.gather() to run
        multiple agents concurrently:

            summary, insights = await asyncio.gather(
                engine.generate_with_reflection_async(sys_a, user_a, ...),
                engine.generate_with_reflection_async(sys_b, user_b, ...),
            )

        Returns: (final_text, quality_score, reflection_count)
        """
        if verbose:
            print(f"\n    [{task_label}] Generating initial output (async)...")

        # Step 1: Initial generation
        initial_response = await self.mgr.async_call(
            system=system, user=user,
            complexity=complexity, max_tokens=max_tokens,
            task_label=f"{task_label}-Draft"
        )
        current_output = initial_response.text
        final_score    = 5
        reflections    = 0

        # Step 2: Async reflection loop
        for i in range(self.max_reflections):
            if verbose:
                print(f"    [{task_label}] Running reflection {i+1}/{self.max_reflections} (async)...")

            critique    = await self.critique_async(current_output, task_description)
            final_score = critique["score"]

            if verbose:
                print(f"      Quality score: {critique['score']}/10 | Verdict: {critique['verdict']}")
                if critique["issues"]:
                    preview = critique["issues"][:120].replace("\n", " ")
                    print(f"      Issues: {preview}...")

            if critique["verdict"] == "ACCEPT" or critique["score"] >= 7:
                if verbose:
                    print(f"    [{task_label}] Quality accepted at score {critique['score']}/10")
                break

            if verbose:
                print(f"     [{task_label}] Improving output (async)...")

            current_output = await self.improve_async(
                current_output, critique, task_description, system, user
            )
            reflections += 1

        return current_output, final_score, reflections


# Quick test
if __name__ == "__main__":
    from model_manager import ModelManager, TaskComplexity

    mgr = ModelManager()
    available = mgr.get_available_providers()

    if not available:
        print("Set GROQ_API_KEY or GEMINI_API_KEY to test")
    else:
        engine = ReflectionEngine(mgr, max_reflections=1)
        output, score, reflections = engine.generate_with_reflection(
            system="You are a data analyst.",
            user="Write a 3-bullet summary of why Python is popular for AI.",
            task_description="3-bullet Python AI popularity summary",
            complexity=TaskComplexity.SIMPLE,
            task_label="Test",
            verbose=True
        )
        print(f"\nFinal output (score {score}/10, {reflections} reflections):")
        print(output)
