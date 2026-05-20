"""
Prompt templates for document migration analysis.
Keeping prompts in a dedicated file makes them easy to tune.
"""

SYSTEM_PROMPT = """You are a senior documentation specialist and migration expert.
Your job is to analyse documentation and determine its readiness for migration
into a knowledge base platform like Document360.

Always respond ONLY with valid JSON — no markdown fences, no extra text.
"""

CHAT_SYSTEM_PROMPT = """You are a helpful document migration assistant.
Answer using only the provided document metrics and AI analysis.
Be concise, practical, and do not invent details that are not present in the context.
If the answer is not available in the context, say so clearly.
"""

ANALYSIS_PROMPT_TEMPLATE = """Analyse the following document excerpt and its metrics.
Provide a comprehensive migration readiness assessment.

=== DOCUMENT METADATA ===
Title: {title}
File type: {file_type}

=== METRICS ===
{metrics_text}

=== DOCUMENT EXCERPT (first 1500 chars) ===
{excerpt}

=== TASK ===
Return a JSON object with EXACTLY these keys:

{{
  "readability_level": "Easy | Medium | Complex",
  "readability_reason": "one sentence explaining the readability score",

  "content_clarity": "High | Medium | Low",
  "clarity_notes": "brief explanation",

  "structural_quality": "Well-organized | Fragmented | Needs improvement",
  "structure_notes": "brief explanation of heading/section usage",

  "migration_readiness": "Ready | Needs Minor Fixes | Needs Major Restructuring",
  "readiness_score": <integer 0-100>,
  "readiness_reason": "one-sentence summary",

  "strengths": ["list", "of", "1-3", "document", "strengths"],
  "issues": ["list", "of", "identified", "problems"],
  "suggestions": ["list", "of", "3-5", "actionable", "improvement", "suggestions"],

  "estimated_migration_effort": "Low | Medium | High",
  "recommended_actions_before_migration": ["action1", "action2"]
}}
"""


def build_analysis_prompt(title, file_type, metrics, excerpt) -> str:
    metrics_text = "\n".join(
        f"  {k}: {v}" for k, v in metrics.items()
        if not isinstance(v, dict)
    )
    # Add heading distribution separately
    if "heading_distribution" in metrics:
        metrics_text += "\n  heading_distribution: " + str(metrics["heading_distribution"])

    return ANALYSIS_PROMPT_TEMPLATE.format(
        title=title or "(untitled)",
        file_type=file_type.upper(),
        metrics_text=metrics_text,
        excerpt=excerpt[:1500],
    )


CHAT_PROMPT_TEMPLATE = """Document title: {title}
File type: {file_type}

Metrics:
{metrics_text}

AI analysis:
{analysis_text}

User question:
{question}

Answer in 1-3 short paragraphs. Use plain English and refer to the document data above.
"""


def build_chat_prompt(title, file_type, metrics, ai_analysis, question) -> str:
    metrics_text = "\n".join(
        f"  {k}: {v}" for k, v in metrics.items()
        if not isinstance(v, dict)
    )
    if "heading_distribution" in metrics:
        metrics_text += "\n  heading_distribution: " + str(metrics["heading_distribution"])

    analysis_text = "\n".join(f"  {k}: {v}" for k, v in ai_analysis.items())

    return CHAT_PROMPT_TEMPLATE.format(
        title=title or "(untitled)",
        file_type=file_type.upper(),
        metrics_text=metrics_text,
        analysis_text=analysis_text,
        question=question.strip(),
    )
