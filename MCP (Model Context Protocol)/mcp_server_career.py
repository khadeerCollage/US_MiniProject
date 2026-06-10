"""
mcp_server_career.py - Custom MCP Server

This module defines a FastMCP server that exposes career research tools via the
Model Context Protocol. The tools can be used by any MCP-compatible client.

Usage:
    # Mode 1 - stdio (for local clients):
    python mcp_server_career.py

    # Mode 2 - SSE/HTTP (for API or HTTP clients):
    python mcp_server_career.py --sse
"""

import sys
import json
from datetime import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="ai-career-research",
    instructions=(
        "You are connected to an AI career research server. "
        "Use these tools to help engineers research AI companies, "
        "identify skill gaps, understand compensation, and prepare for interviews. "
        "Combine multiple tools for comprehensive research."
    )
)


@mcp.tool()
def search_ai_jobs(role: str, company: str = "", remote_only: bool = False) -> str:
    """
    Search for AI engineering job listings.

    Args:
        role:        Job role to search (e.g., 'AI Engineer', 'ML Engineer')
        company:     Optional company name to filter (e.g., 'TechCorp')
        remote_only: If True, only show remote-friendly positions

    Returns:
        Formatted list of matching job listings with key details.
    """
    JOBS_DB = [
        {
            "id": "TC-001", "company": "TechCorp", "role": "AI Applications Engineer",
            "level": "Mid", "salary": "$160k-$210k", "remote": True,
            "skills": ["Python", "LLM APIs", "System Design"],
            "apply": "careers.techcorp.com", "posted": "3 days ago"
        },
        {
            "id": "TC-002", "company": "TechCorp", "role": "Research Engineer",
            "level": "Senior", "salary": "$180k-$240k", "remote": True,
            "skills": ["Python", "PyTorch", "ML Research", "Transformers"],
            "apply": "careers.techcorp.com", "posted": "1 week ago"
        },
        {
            "id": "OAI-001", "company": "OpenAI", "role": "AI Engineer",
            "level": "Mid", "salary": "$170k-$220k", "remote": False,
            "skills": ["Python", "GPT APIs", "System Design", "APIs"],
            "apply": "openai.com/careers", "posted": "5 days ago"
        },
        {
            "id": "OAI-002", "company": "OpenAI", "role": "ML Engineer",
            "level": "Senior", "salary": "$195k-$260k", "remote": False,
            "skills": ["Python", "PyTorch", "Distributed Systems"],
            "apply": "openai.com/careers", "posted": "2 days ago"
        },
        {
            "id": "GDM-001", "company": "Google DeepMind", "role": "Research Engineer",
            "level": "Senior", "salary": "$200k-$280k", "remote": False,
            "skills": ["Python", "JAX", "ML Research", "Publications"],
            "apply": "deepmind.google/careers", "posted": "1 week ago"
        },
        {
            "id": "MET-001", "company": "Meta AI", "role": "AI Engineer",
            "level": "Mid", "salary": "$160k-$200k", "remote": True,
            "skills": ["Python", "PyTorch", "LLaMA", "Open Source"],
            "apply": "metacareers.com", "posted": "4 days ago"
        },
        {
            "id": "COH-001", "company": "Cohere", "role": "AI Engineer",
            "level": "Entry/Mid", "salary": "$140k-$175k", "remote": True,
            "skills": ["Python", "LLM APIs", "NLP", "APIs"],
            "apply": "cohere.com/careers", "posted": "2 days ago"
        },
        {
            "id": "HUG-001", "company": "Hugging Face", "role": "ML Engineer",
            "level": "Mid", "salary": "$145k-$175k", "remote": True,
            "skills": ["Python", "Transformers", "Open Source", "HF Hub"],
            "apply": "huggingface.co/jobs", "posted": "6 days ago"
        },
        {
            "id": "PER-001", "company": "Perplexity AI", "role": "AI Engineer",
            "level": "Mid", "salary": "$155k-$190k", "remote": True,
            "skills": ["Python", "RAG", "LLM APIs", "Search"],
            "apply": "perplexity.ai/careers", "posted": "1 day ago"
        },
        {
            "id": "TOG-001", "company": "Together AI", "role": "ML Engineer",
            "level": "Mid", "salary": "$155k-$185k", "remote": True,
            "skills": ["Python", "LLMs", "Inference Optimization"],
            "apply": "together.ai/careers", "posted": "3 days ago"
        },
    ]

    role_lower    = role.lower()
    company_lower = company.lower()

    results = [
        j for j in JOBS_DB
        if (role_lower in j["role"].lower() or role_lower in " ".join(j["skills"]).lower())
        and (not company_lower or company_lower in j["company"].lower())
        and (not remote_only or j["remote"])
    ]

    if not results:
        return (
            f"No listings found for role='{role}'"
            + (f", company='{company}'" if company else "")
            + (", remote only" if remote_only else "")
            + ".\nTry broader terms: 'AI Engineer', 'ML Engineer', 'Research Engineer'"
        )

    lines = [f"[JOB SEARCH: '{role}'"
             + (f" at {company}" if company else "")
             + (f" | remote only" if remote_only else "")
             + f"] - {len(results)} results\n"]

    for j in results:
        remote_tag = "Remote" if j["remote"] else "On-site"
        skills_str = ", ".join(j["skills"][:3])
        lines.append(
            f"--------------------------------------------------\n"
            f"  [{j['id']}] {j['company']} - {j['role']} ({j['level']})\n"
            f"  Salary: {j['salary']} | {remote_tag} | Posted: {j['posted']}\n"
            f"  Key skills: {skills_str}\n"
            f"  Apply: {j['apply']}"
        )

    return "\n".join(lines)


@mcp.tool()
def get_skill_gap(current_skills: str, target_role: str, target_company: str = "") -> str:
    """
    Analyze the skill gap between current skills and a target AI role.

    Args:
        current_skills:  Comma-separated skills you currently have
                         e.g., "Python, REST APIs, SQL, React"
        target_role:     Role you want to get  e.g., "AI Engineer"
        target_company:  Optional company  e.g., "TechCorp"

    Returns:
        Skills you have, skills you need, priority learning list.
    """
    ROLE_REQUIREMENTS = {
        "ai engineer": {
            "required": ["Python", "LLM APIs", "REST APIs", "System Design", "Git"],
            "preferred": ["Groq API / OpenAI API", "Prompt Engineering", "RAG", "Tool Use", "MCP"],
            "bonus":     ["Agentic Frameworks", "Docker", "Cloud (AWS/GCP)", "TypeScript"]
        },
        "ml engineer": {
            "required": ["Python", "PyTorch or TensorFlow", "ML Fundamentals", "Git", "Linux"],
            "preferred": ["Transformers", "Distributed Training", "CUDA", "MLOps", "Docker"],
            "bonus":     ["JAX", "FSDP", "vLLM", "Kubernetes", "Papers implementation"]
        },
        "research engineer": {
            "required": ["Python", "PyTorch", "ML Research Papers", "Math (Linear Algebra, Statistics)"],
            "preferred": ["Published work or open-source", "JAX", "Experiment tracking", "HPC"],
            "bonus":     ["PhD preferred", "Conference papers", "GitHub projects with 100+ stars"]
        },
        "llm engineer": {
            "required": ["Python", "LLM APIs", "Prompt Engineering", "RAG", "Vector DBs"],
            "preferred": ["Tool Use / Function Calling", "MCP", "LangChain or similar", "Evals"],
            "bonus":     ["Fine-tuning", "RLHF basics", "Agentic Systems", "Observability"]
        }
    }

    COMPANY_EXTRA = {
        "techcorp": ["LLM architecture understanding", "Groq API expertise", "Safety awareness"],
        "openai":    ["GPT API mastery", "OpenAI Evals", "Python async"],
        "google deepmind": ["JAX", "Research papers", "Publications preferred"],
        "meta ai":   ["PyTorch", "Open source contributions", "LLaMA experience"]
    }

    # Find best matching role
    target_lower = target_role.lower()
    requirements = None
    matched_role = ""
    for role_key, reqs in ROLE_REQUIREMENTS.items():
        if role_key in target_lower or any(w in target_lower for w in role_key.split()):
            requirements = reqs
            matched_role = role_key.title()
            break

    if not requirements:
        requirements = ROLE_REQUIREMENTS["ai engineer"]
        matched_role = "AI Engineer (default)"

    # Parse current skills
    your_skills = [s.strip().lower() for s in current_skills.split(",") if s.strip()]
    all_required = requirements["required"] + requirements["preferred"]

    have     = [r for r in all_required if any(y in r.lower() or r.lower() in y for y in your_skills)]
    missing  = [r for r in requirements["required"]  if r not in have]
    learn_next = [r for r in requirements["preferred"] if r not in have]

    # Company extras
    company_gaps = []
    if target_company:
        extras = COMPANY_EXTRA.get(target_company.lower(), [])
        company_gaps = [e for e in extras if not any(y in e.lower() for y in your_skills)]

    lines = [
        f"SKILL GAP ANALYSIS: {matched_role}" +
        (f" at {target_company.title()}" if target_company else "") +
        f"\n--------------------------------------------------",
        f"\nYOU HAVE ({len(have)} skills matched):",
        *([f"    - {s}" for s in have] or ["    - (none matched - be more specific)"]),
        f"\nMISSING - REQUIRED ({len(missing)} gaps):",
        *([f"    - {s}  <- HIGH PRIORITY" for s in missing] or ["    - None! Excellent."]),
        f"\nLEARN NEXT - Preferred ({len(learn_next)}):",
        *[f"    - {s}" for s in learn_next[:5]],
    ]

    if company_gaps:
        lines += [
            f"\n{target_company.title()}-SPECIFIC GAPS:",
            *[f"    - {g}" for g in company_gaps]
        ]

    # Priority action
    priority = missing[0] if missing else (learn_next[0] if learn_next else "You're well-prepared!")
    lines += [
        f"\n--------------------------------------------------",
        f"PRIORITY RIGHT NOW: {priority}"
    ]

    return "\n".join(lines)


@mcp.tool()
def calculate_salary(
    years_experience: int,
    role: str,
    location: str = "remote",
    company_tier: str = "mid"
) -> str:
    """
    Calculate expected salary range for AI engineering roles.

    Args:
        years_experience: Years of relevant experience (0-15)
        role:             Job role (e.g., 'AI Engineer', 'ML Engineer')
        location:         'remote', 'sf' (San Francisco), 'nyc', 'seattle', or city name
        company_tier:     'top' (TechCorp/OpenAI/Google), 'mid' (Cohere/HuggingFace), 'startup'

    Returns:
        Detailed salary breakdown with base, equity, and total comp estimates.
    """
    # Base salary ranges by experience tier (remote, USD)
    EXPERIENCE_TIERS = {
        range(0, 2):   {"label": "Entry",   "remote_base": (110_000, 145_000)},
        range(2, 5):   {"label": "Mid",     "remote_base": (145_000, 190_000)},
        range(5, 9):   {"label": "Senior",  "remote_base": (190_000, 250_000)},
        range(9, 20):  {"label": "Staff+",  "remote_base": (250_000, 380_000)},
    }

    # Location multipliers (relative to remote)
    LOCATION_MULT = {
        "remote":  1.00,
        "sf":      1.35,  "san francisco": 1.35,
        "nyc":     1.25,  "new york":      1.25,
        "seattle": 1.20,
        "austin":  1.05,
        "india":   0.55,  "remote india":  0.55,  # Remote from India (USD)
    }

    # Company tier multipliers
    COMPANY_MULT = {
        "top":     1.30,   # TechCorp, OpenAI, Google DeepMind
        "mid":     1.00,   # Cohere, HuggingFace, Perplexity
        "startup": 0.85,   # Early-stage startups (higher equity)
    }

    # Find experience tier
    tier_info = None
    for exp_range, info in EXPERIENCE_TIERS.items():
        if years_experience in exp_range:
            tier_info = info
            break
    if not tier_info:
        tier_info = {"label": "Staff+", "remote_base": (250_000, 380_000)}

    loc_key  = location.lower().strip()
    loc_mult = LOCATION_MULT.get(loc_key, 1.0)
    co_mult  = COMPANY_MULT.get(company_tier.lower(), 1.0)

    base_low, base_high = tier_info["remote_base"]
    adj_low  = int(base_low  * loc_mult * co_mult)
    adj_high = int(base_high * loc_mult * co_mult)

    # Equity estimate (% of base, annualized over 4-year vest)
    equity_pct = {"top": 0.30, "mid": 0.20, "startup": 0.50}.get(company_tier.lower(), 0.20)
    eq_low     = int(adj_low  * equity_pct)
    eq_high    = int(adj_high * equity_pct)

    total_low  = adj_low  + eq_low  + 20_000   # ~20k bonus
    total_high = adj_high + eq_high + 40_000

    loc_label = location.title() if location != "remote" else "Remote (Global)"
    co_label  = {"top": "Top Lab (TechCorp/OpenAI/Google)", "mid": "Mid-tier AI Co.", "startup": "Startup"}.get(company_tier.lower(), company_tier)

    return f"""
SALARY ESTIMATE: {tier_info['label']} {role}
--------------------------------------------------
  Experience:   {years_experience} years  ({tier_info['label']} level)
  Location:     {loc_label}  (multiplier: {loc_mult:.0%})
  Company tier: {co_label}

  BASE SALARY:   ${adj_low:,} - ${adj_high:,} / year
  EQUITY:        ~${eq_low:,} - ${eq_high:,} / year (annualized, 4-yr vest)
  BONUS:         ~$20,000 - $40,000 / year
                 -----------------------------------
  TOTAL COMP:    ${total_low:,} - ${total_high:,} / year

  Note: For remote from India, multiply base by 0.55 for USD offers
  ({int(adj_low*0.55):,} - {int(adj_high*0.55):,} USD base is realistic for remote India roles)
""".strip()


@mcp.tool()
def get_company_profile(company_name: str) -> str:
    """
    Get a detailed profile of a top AI company including hiring info,
    interview process, tech stack, and career growth path.

    Args:
        company_name: Company name (TechCorp, OpenAI, Google DeepMind, Meta AI,
                      Cohere, Hugging Face, Perplexity AI, Together AI)
    """
    PROFILES = {
        "techcorp": {
            "name":        "TechCorp",
            "founded":     "2021",
            "hq":          "San Francisco, CA",
            "size":        "~800 employees (growing fast)",
            "focus":       "AI infrastructure and enterprise models",
            "models":      "Enterprise-grade proprietary models",
            "funding":     "$7.3B+",
            "remote":      "Yes - remote-friendly, hires globally",
            "interview":   "1 recruiter screen -> 2 tech rounds (Python + system design) -> values/mission round",
            "tech_stack":  "Python, JAX, internal tooling, AWS",
            "what_they_want": "Engineers who SHIP things. Portfolio projects > credentials. API experience valued.",
            "differentiator": "Mission-driven. Values clean code and scalable architecture.",
            "apply":       "careers.techcorp.com",
            "tip":         "Building with modern LLM APIs is the strongest signal. Have a strong GitHub portfolio."
        },
        "openai": {
            "name":        "OpenAI",
            "founded":     "2015",
            "hq":          "San Francisco, CA",
            "size":        "~3,000 employees",
            "focus":       "AGI research, GPT models, safety, consumer products",
            "models":      "GPT-4o, o1, Sora, DALL-E, Whisper",
            "funding":     "$11B+ total",
            "remote":      "Hybrid - prefers SF presence for most engineering roles",
            "interview":   "5 rounds: recruiter -> coding -> ML fundamentals -> system design -> behavioral",
            "tech_stack":  "Python, PyTorch, Kubernetes, Azure",
            "what_they_want": "Deep ML fundamentals + product sense. Can you improve GPT?",
            "differentiator": "Product-oriented. They want engineers who think about users.",
            "apply":       "openai.com/careers",
            "tip":         "Build something with the Assistants API or fine-tuning. Show creative use cases."
        },
        "google deepmind": {
            "name":        "Google DeepMind",
            "founded":     "2010 (DeepMind) - merged with Google Brain in 2023",
            "hq":          "London, UK + Mountain View, CA",
            "size":        "~3,500 researchers and engineers",
            "focus":       "Gemini models, AlphaFold, Robotics, AGI research",
            "models":      "Gemini Ultra/Pro/Nano/Flash, Imagen, AlphaFold",
            "funding":     "Google subsidiary - unlimited resources",
            "remote":      "Limited - mostly London and Mountain View",
            "interview":   "Research-heavy: coding + ML theory + research discussion + paper review",
            "tech_stack":  "Python, JAX (not PyTorch), internal TPU infrastructure",
            "what_they_want": "Research publications strongly preferred. PhD common but not required.",
            "differentiator": "Hardest to get into. Best for those aiming at research careers.",
            "apply":       "deepmind.google/careers",
            "tip":         "Read and implement a recent Gemini/AlphaFold paper. Discuss it in the interview."
        },
        "meta ai": {
            "name":        "Meta AI (FAIR + GenAI)",
            "founded":     "2013 (FAIR founded), GenAI team 2023",
            "hq":          "Menlo Park, CA",
            "size":        "~2,000 AI researchers + engineers",
            "focus":       "Open-source AI, LLaMA models, AR/VR AI, infrastructure",
            "models":      "LLaMA 3/3.1/3.2, Llama Guard, Code Llama, SAM",
            "funding":     "Meta subsidiary - $40B+ AI investment planned",
            "remote":      "Hybrid - some remote roles exist",
            "interview":   "Classic Facebook loop: E5 coding (2 rounds) + system design + behavioral",
            "tech_stack":  "Python, PyTorch (Meta invented it), internal infra",
            "what_they_want": "Strong Python + PyTorch. Open source contributions a HUGE plus.",
            "differentiator": "They open-source everything. Contribute to LLaMA or Transformers.",
            "apply":       "metacareers.com",
            "tip":         "Fine-tune LLaMA 3 on a custom dataset. Put it on GitHub. It works."
        },
        "cohere": {
            "name":        "Cohere",
            "founded":     "2019",
            "hq":          "Toronto, Canada (remote-first)",
            "size":        "~500 employees",
            "focus":       "Enterprise LLMs, Command models, RAG, fine-tuning",
            "models":      "Command R, Command R+, Embed, Rerank",
            "funding":     "$445M+",
            "remote":      "Yes - fully remote-friendly",
            "interview":   "3-4 rounds: recruiter + technical (Python/LLMs) + system design",
            "tech_stack":  "Python, JAX, internal tooling",
            "what_they_want": "LLM API experience, enterprise mindset, strong Python",
            "differentiator": "Enterprise-focused. Less competitive than OpenAI/TechCorp.",
            "apply":       "cohere.com/careers",
            "tip":         "Great first target. Remote-friendly for global candidates."
        },
    }

    key = company_name.lower().strip()
    profile = PROFILES.get(key)

    if not profile:
        for db_key in PROFILES:
            if key in db_key or any(w in db_key for w in key.split()):
                profile = PROFILES[db_key]
                break

    if not profile:
        available = ", ".join(PROFILES.keys())
        return f"Profile for '{company_name}' not found.\nAvailable: {available}"

    lines = [f"-------------------------------------------------------", f"  {profile['name']}", f"-------------------------------------------------------"]
    for field, value in profile.items():
        if field != "name":
            label = field.upper().replace("_", " ")
            lines.append(f"\n  {label:18}: {value}")

    return "\n".join(lines)


@mcp.tool()
def get_interview_prep(company: str, role: str, interview_round: str = "all") -> str:
    """
    Get specific interview preparation tips for a company and role.

    Args:
        company:          Target company (TechCorp, OpenAI, Google DeepMind, Meta AI, Cohere)
        role:             Target role (AI Engineer, ML Engineer, Research Engineer)
        interview_round:  'all', 'coding', 'system_design', 'behavioral', 'ml_fundamentals'

    Returns:
        Targeted interview prep guide with example questions and study tips.
    """
    PREP_GUIDES = {
        "techcorp": {
            "overview": "TechCorp interviews are practical. They want to see you BUILD things.",
            "coding": [
                "Python-heavy. Expect questions about async/await, generators, type hints.",
                "API design patterns - how would you structure a tool-use agent?",
                "Data structures & algorithms - LeetCode medium level.",
                "Example: 'Implement a retry mechanism with exponential backoff'",
            ],
            "system_design": [
                "Design a multi-agent research pipeline",
                "How would you build a production chatbot that scales to 10M users?",
                "Design a prompt evaluation system for comparing prompt quality.",
                "Key: discuss observability, retry logic, cost management.",
            ],
            "behavioral": [
                "Why TechCorp specifically?",
                "Tell me about a project where you had to learn fast.",
                "How do you think about responsible AI development?",
            ],
            "tip": "Show your GitHub. Mention you built a multi-agent pipeline."
        },
        "openai": {
            "overview": "OpenAI expects strong fundamentals + product intuition.",
            "coding": [
                "LeetCode medium-hard. Arrays, graphs, dynamic programming.",
                "Python proficiency: decorators, context managers, async.",
                "Example: 'Design a token counter and context window manager for a chatbot'",
            ],
            "system_design": [
                "Design the GPT Assistant API backend.",
                "How would you implement function calling / tool use?",
                "Design a system that routes user queries to appropriate AI models.",
                "Focus on scalability, latency, and cost.",
            ],
            "ml_fundamentals": [
                "How does attention mechanism work? Explain self-attention.",
                "What is RLHF? How is it used to align language models?",
                "Explain the difference between temperature and top-p sampling.",
                "What causes hallucination in LLMs and how do you reduce it?",
            ],
            "behavioral": [
                "Tell me about a time you improved a system's performance.",
                "How do you balance speed vs. quality in your work?",
                "OpenAI wants product thinkers - discuss how you'd improve ChatGPT.",
            ],
            "tip": "Study transformer architecture. Read 'Attention Is All You Need'."
        },
    }

    company_lower = company.lower().strip()
    guide = PREP_GUIDES.get(company_lower)

    if not guide:
        for key in PREP_GUIDES:
            if key in company_lower or company_lower in key:
                guide = PREP_GUIDES[key]
                break

    if not guide:
        # Generic guide
        guide = {
            "overview": f"General AI engineering interview prep for {company} + {role}",
            "coding":   ["Python proficiency", "Data structures", "API design"],
            "system_design": ["Agentic pipeline design", "Scalability", "Reliability"],
            "behavioral": ["Why this company?", "Your best project", "Learning fast"],
            "ml_fundamentals": ["Transformer architecture", "LLM APIs", "Prompt engineering"],
            "tip": "Show your GitHub portfolio with working AI projects."
        }

    rounds_to_show = []
    if interview_round == "all":
        rounds_to_show = ["coding", "system_design", "behavioral", "ml_fundamentals"]
    else:
        rounds_to_show = [interview_round]

    lines = [
        f"INTERVIEW PREP: {company.title()} - {role}",
        f"-------------------------------------------------------",
        f"Overview: {guide.get('overview', '')}",
    ]

    for rnd in rounds_to_show:
        items = guide.get(rnd, [])
        if items:
            label = rnd.upper().replace("_", " ")
            lines.append(f"\n[{label}]")
            for item in items:
                lines.append(f"  - {item}")

    tip = guide.get("tip", "")
    if tip:
        lines.append(f"\nKEY TIP: {tip}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    # Check run mode from command line
    if "--sse" in sys.argv or "--http" in sys.argv:
        # SSE/HTTP mode - for HTTP clients
        # Server starts at http://localhost:8000
        print("Starting MCP server in SSE/HTTP mode...")
        print("Endpoint: http://localhost:8000/sse")
        print("Press Ctrl+C to stop.\n")
        mcp.run(transport="sse")
    else:
        # stdio mode - for local desktop clients
        mcp.run(transport="stdio")