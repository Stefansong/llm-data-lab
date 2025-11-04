from textwrap import dedent
from typing import Optional


def build_analysis_prompt(
    *,
    task_description: str,
    task_type: str = "analysis",
    dataset_context: Optional[str] = None,
) -> str:
    """Craft a detailed system prompt for code generation."""
    intent_guidance = {
        "strategy": dedent(
            """
            Focus on producing a detailed analysis plan:
            - Load the dataset, inspect schema, and identify variable types and clinical relevance.
            - Outline recommended preprocessing, statistical tests, modeling approaches, and visualizations without executing heavy computations.
            - Provide rationale for each suggested step, referencing potential clinical insights.
            - Summarize the plan in a structured format (bulleted or Markdown sections) so researchers can follow along.
            - If helpful, include lightweight exploratory statistics to justify the recommendations.
            """
        ).strip(),
        "analysis": dedent(
            """
            Focus on executing quantitative analysis end-to-end:
            - Perform data cleaning and descriptive statistics (mean, std, counts).
            - Run appropriate hypothesis tests or regression models based on the data characteristics.
            - Produce at least two complementary visualizations (e.g., distribution plot and relationship plot), save each figure as a PNG with `plt.tight_layout()` and close it afterward.
            - For every chart, emit a short textual interpretation in stdout, followed by an overall summary highlighting clinical or scientific insights.
            - Organize code into reusable functions with clear docstrings.
            """
        ).strip(),
    }

    intent_text = intent_guidance.get(task_type, intent_guidance["analysis"])

    sections = [
        "You are a senior research data scientist and Python expert.",
        "Write executable Python 3 code that uses pandas and other scientific libraries.",
        "Follow these constraints:",
        "- Do not include explanatory prose outside of comments (except for designated summary output).",
        "- Prefer functions with docstrings.",
        "- If the environment variable DATASET_PATH is set, use it as the primary dataset source.",
        f"The requested task is: {task_description}",
        f"Primary intent: {task_type}.",
        "Guidance for this intent:",
        intent_text,
    ]
    if dataset_context:
        sections.append("Dataset context:\n" + dataset_context)

    sections.append(
        dedent(
            """
            Return the final answer as a JSON object with keys:
            - "code": Python source string.
            - "reasoning": Short explanation of analysis strategy.
            """
        ).strip()
    )

    return "\n\n".join(sections)
