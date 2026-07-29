"""System/investigation prompt placeholders for the future agent loop.

Kept as plain string constants, not f-strings or templates, until the agent
loop that consumes them exists — content and templating approach (e.g.
str.format, Jinja) will be decided alongside that implementation.
"""

# Establishes the agent's role, evidence-discipline rules (FACT/INFERENCE/
# CONTRADICTION/GAP/UNVERIFIED labeling per PROJECT_PLAN.md Part D §20), and
# citation requirements. Placeholder pending the agent loop implementation.
SYSTEM_PROMPT = """
You are an evidence investigation assistant for construction claims.
(placeholder — full instructions pending agent loop implementation)
"""

# Frames a single investigation question for the agent, ahead of it entering
# the plan -> search -> read -> follow-references loop (Part C step 7).
INVESTIGATION_PROMPT = """
Investigation question: {query}
(placeholder — full prompt pending agent loop implementation)
"""
