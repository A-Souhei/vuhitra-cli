"""UI formatting utilities for vuhitra-cli interactive mode.

This module provides rich console formatting, markdown rendering,
and verbose output utilities.
"""

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.tree import Tree
from rich.table import Table
from rich import box
import json
from datetime import datetime

# Global console instance
console = Console()

# Verbose mode state (set by CLI)
_verbose_mode = False


def set_verbose_mode(enabled: bool):
    """Set the global verbose mode state."""
    global _verbose_mode
    _verbose_mode = enabled


def is_verbose():
    """Check if verbose mode is enabled."""
    return _verbose_mode


def print_banner(model: str):
    """Print the vuhitra-cli banner with styling."""
    banner_text = f"""
# 🚀 vuhitra-cli Interactive Mode

**Model:** `{model}`
**Verbose Mode:** `{'✓ Enabled' if _verbose_mode else '✗ Disabled'}`

Type `exit` or `quit` to leave, or press `Ctrl+C` to interrupt.
    """
    console.print(Markdown(banner_text))
    console.print()


def print_prompt_prefix():
    """Print the styled prompt prefix."""
    console.print("[bold cyan]❯[/bold cyan] ", end="")


def print_user_prompt(prompt: str):
    """Print user prompt with styling (for verbose mode)."""
    if _verbose_mode:
        console.print(Panel(
            prompt,
            title="[bold cyan]👤 User Prompt[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED
        ))


def print_response(response: str):
    """Print LLM response with markdown formatting."""
    console.print()
    console.print("🤖 [bold green]Assistant:[/bold green]")
    console.print()
    console.print(Markdown(response))
    console.print()


def print_verbose_section(title: str, content: str, color: str = "blue"):
    """Print a verbose section with title and content."""
    if not _verbose_mode:
        return

    console.print(f"\n[bold {color}]{'─' * 80}[/bold {color}]")
    console.print(f"[bold {color}]🔍 {title}[/bold {color}]")
    console.print(f"[bold {color}]{'─' * 80}[/bold {color}]")
    console.print(content)
    console.print()


def print_context_verbose(heuristic_data: dict):
    """Pretty print heuristic context in verbose mode."""
    if not _verbose_mode or not heuristic_data:
        return

    console.print("\n[bold magenta]" + "═" * 80 + "[/bold magenta]")
    console.print("[bold magenta]📚 HEURISTIC CONTEXT RETRIEVAL[/bold magenta]")
    console.print("[bold magenta]" + "═" * 80 + "[/bold magenta]\n")

    # Create a tree for hierarchical display
    tree = Tree("🎯 [bold]Matched Heuristic[/bold]")

    # Matched heuristic details
    matched = heuristic_data.get('matched_heuristic', {})
    if matched:
        details_branch = tree.add("📋 [cyan]Details[/cyan]")
        details_branch.add(f"[yellow]ID:[/yellow] {matched.get('_id', 'N/A')}")
        details_branch.add(f"[yellow]Rating:[/yellow] {'⭐' * matched.get('rating', 0)} ({matched.get('rating', 0)}/5)")
        details_branch.add(f"[yellow]Confidence:[/yellow] {heuristic_data.get('confidence_score', 0):.2%}")
        details_branch.add(f"[yellow]Word Count:[/yellow] {matched.get('prompt_word_count', 0)} words")

        # NLP analysis
        nlp_branch = tree.add("🧠 [cyan]NLP Analysis[/cyan]")
        nlp_branch.add(f"[yellow]Sentiment (VADER):[/yellow] {matched.get('prompt_sentiment_vader', 0):.2f}")
        nlp_branch.add(f"[yellow]Keywords:[/yellow] {', '.join(matched.get('prompt_keywords', [])[:5])}")

        # Prompt and response preview
        prompt_preview = matched.get('prompt', '')[:150] + '...' if len(matched.get('prompt', '')) > 150 else matched.get('prompt', '')
        response_preview = matched.get('response', '')[:150] + '...' if len(matched.get('response', '')) > 150 else matched.get('response', '')

        content_branch = tree.add("💬 [cyan]Content Preview[/cyan]")
        content_branch.add(f"[yellow]Prompt:[/yellow] {prompt_preview}")
        content_branch.add(f"[yellow]Response:[/yellow] {response_preview}")

    # Chain information - show ALL chained heuristics in verbose mode
    chain = heuristic_data.get('chain', [])
    if chain:
        chain_branch = tree.add(f"🔗 [cyan]Chain ({len(chain)} parents)[/cyan]")
        for i, parent in enumerate(chain, 1):  # Show ALL parents
            parent_node = chain_branch.add(f"[green]Parent {i}[/green]")
            parent_node.add(f"[yellow]ID:[/yellow] {parent.get('_id', 'N/A')}")
            parent_node.add(f"[yellow]Rating:[/yellow] {'⭐' * parent.get('rating', 0)}")
            parent_node.add(f"[yellow]Depth:[/yellow] {parent.get('chain_depth', 0)}")
            # Add prompt preview for each parent
            parent_prompt = parent.get('prompt', '')[:100] + '...' if len(parent.get('prompt', '')) > 100 else parent.get('prompt', '')
            if parent_prompt:
                parent_node.add(f"[yellow]Prompt:[/yellow] {parent_prompt}")

    # Scoring breakdown
    scoring = heuristic_data.get('scoring_breakdown', {})
    if scoring:
        score_branch = tree.add("📊 [cyan]Scoring Breakdown[/cyan]")
        score_branch.add(f"[yellow]Keyword Score:[/yellow] {scoring.get('keyword_score', 0):.3f}")
        score_branch.add(f"[yellow]Levenshtein Score:[/yellow] {scoring.get('levenshtein_score', 0):.3f}")
        score_branch.add(f"[yellow]Semantic Score:[/yellow] {scoring.get('semantic_score', 0):.3f}")
        score_branch.add(f"[yellow]Final Score:[/yellow] {scoring.get('final_score', 0):.3f}")

    console.print(tree)
    console.print()


def print_context_content_verbose(context: str):
    """Pretty print the actual context content (formatted_insight) in a thin border square."""
    if not _verbose_mode or not context:
        return

    console.print("\n[bold blue]" + "─" * 80 + "[/bold blue]")
    console.print("[bold blue]📄 CONTEXT USED TO ENHANCE PROMPT[/bold blue]")
    console.print("[bold blue]" + "─" * 80 + "[/bold blue]\n")

    # Display context in a thin-bordered panel
    console.print(Panel(
        context,
        border_style="blue",
        box=box.SQUARE,  # Thin border
        padding=(0, 1)
    ))
    console.print()


def print_elasticsearch_verbose(operation: str, data: dict):
    """Pretty print Elasticsearch operations in verbose mode."""
    if not _verbose_mode:
        return

    console.print("\n[bold yellow]" + "═" * 80 + "[/bold yellow]")
    console.print(f"[bold yellow]🗄️  ELASTICSEARCH: {operation.upper()}[/bold yellow]")
    console.print("[bold yellow]" + "═" * 80 + "[/bold yellow]\n")

    # Create table for data
    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("Field", style="cyan", width=30)
    table.add_column("Value", style="yellow")

    for key, value in data.items():
        if isinstance(value, (list, dict)):
            value_str = json.dumps(value, indent=2)
        else:
            value_str = str(value)

        # Truncate long values
        if len(value_str) > 100:
            value_str = value_str[:100] + "..."

        table.add_row(key, value_str)

    console.print(table)
    console.print()


def print_nlp_analysis_verbose(analysis: dict):
    """Pretty print NLP analysis in verbose mode."""
    if not _verbose_mode:
        return

    console.print("\n[bold green]" + "═" * 80 + "[/bold green]")
    console.print("[bold green]🧠 NLP ANALYSIS[/bold green]")
    console.print("[bold green]" + "═" * 80 + "[/bold green]\n")

    # Sentiment analysis
    console.print("[bold cyan]Sentiment Analysis:[/bold cyan]")
    vader_score = analysis.get('sentiment_vader', 0)
    vader_emoji = "😊" if vader_score > 0.2 else "😐" if vader_score > -0.2 else "😞"
    console.print(f"  {vader_emoji} VADER Score: [yellow]{vader_score:.3f}[/yellow]")

    # Keywords
    keywords = analysis.get('keywords', [])
    if keywords:
        console.print("\n[bold cyan]Extracted Keywords:[/bold cyan]")
        console.print(f"  [yellow]{', '.join(keywords[:15])}[/yellow]")

    # Code detection
    is_code = analysis.get('is_code', False)
    code_purpose = analysis.get('code_purpose', '')
    console.print("\n[bold cyan]Code Detection:[/bold cyan]")
    console.print(f"  Is Code: [yellow]{'✓ Yes' if is_code else '✗ No'}[/yellow]")
    if code_purpose:
        console.print(f"  Purpose: [yellow]{code_purpose}[/yellow]")

    # Word count
    word_count = analysis.get('word_count', 0)
    console.print(f"\n[bold cyan]Word Count:[/bold cyan] [yellow]{word_count}[/yellow]")
    console.print()


def print_timing_verbose(operation: str, duration_ms: float):
    """Pretty print timing information in verbose mode."""
    if not _verbose_mode:
        return

    duration_str = f"{duration_ms:.2f}ms" if duration_ms < 1000 else f"{duration_ms/1000:.2f}s"
    console.print(f"[dim]⏱️  {operation}: {duration_str}[/dim]")


def print_error(message: str):
    """Print error message with styling."""
    console.print(f"\n[bold red]❌ ERROR:[/bold red] {message}\n", style="red")


def print_warning(message: str):
    """Print warning message with styling."""
    console.print(f"[bold yellow]⚠️  WARNING:[/bold yellow] {message}", style="yellow")


def print_success(message: str):
    """Print success message with styling."""
    console.print(f"[bold green]✓ {message}[/bold green]")


def print_info(message: str):
    """Print info message with styling."""
    console.print(f"[bold blue]ℹ️  {message}[/bold blue]")


def print_debug(title: str, data: any):
    """Print debug information in verbose mode."""
    if not _verbose_mode:
        return

    console.print(f"\n[dim][DEBUG] {title}:[/dim]")

    if isinstance(data, (dict, list)):
        syntax = Syntax(
            json.dumps(data, indent=2),
            "json",
            theme="monokai",
            line_numbers=True
        )
        console.print(syntax)
    else:
        console.print(f"[dim]{data}[/dim]")
    console.print()


def print_separator():
    """Print a visual separator."""
    console.print("[dim]" + "─" * 80 + "[/dim]")
