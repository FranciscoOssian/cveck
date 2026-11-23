from dotenv import load_dotenv

load_dotenv()

import shutil
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from src.core.paths import OUTPUT_DIR

from src.cli.i18n import setup_i18n, _, SUPPORTED_LOCALES
from src.cli.ui import (
    render_header,
    flush_terminal_stdin,
    get_clipboard_text,
    manage_providers_menu,
    render_stream_node,
    console
)
from src.adapters.langgraph.providers.registry import get_active_provider_info, NoProviderConfiguredError
from src.adapters.langgraph.builder import app as langgraph_pipeline
from src.core.models.state import DomainState

app = typer.Typer(
    help="✦ CVECK 2.0: Autonomous Agentic Resume Tailoring & ATS Scoring Engine",
    add_completion=False
)

def _clean_output():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for item in OUTPUT_DIR.glob("*"):
        if item.name in [".gitignore", ".gitkeep"]:
            continue
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    console.print(f"[bold green]✔ {_('output/ folder cleaned!')}[/bold green]")
    Prompt.ask(f"\n{_('Press ENTER to continue...')}")


def _run_pipeline(full_jd: str, source_label: str):
    num_lines = len(full_jd.splitlines())
    render_header()

    console.print(Panel(
        f"📄 [bold green]{_('Job Description Loaded')}[/bold green] [dim]({source_label})[/dim]\n"
        f"[dim]{_('Lines:')}[/dim] {num_lines} | [dim]{_('Characters:')}[/dim] {len(full_jd)}\n"
        f"[italic cyan]{_('Running AI-powered adaptation pipeline...')}[/italic cyan]",
        border_style="green",
        expand=False
    ))

    try:
        active_info = get_active_provider_info()
    except NoProviderConfiguredError:
        console.print(Panel(
            f"[bold red]{_('No provider configured.')}[/bold red]\n"
            f"{_('Use /provider to add one.')}",
            border_style="red"
        ))
        Prompt.ask(f"\n{_('Press ENTER to continue...')}")
        return

    console.print(f"\n[bold cyan]{_('⚡ Running Pipeline with [{name} -> {model}]...').format(name=active_info['name'], model=active_info['model'])}[/bold cyan]")

    initial_state = DomainState(
        job_description=full_jd,
        job_date=datetime.now().strftime("%Y-%m-%d")
    ).model_dump()

    try:
        with console.status(f"[bold green]{_('Processing with {model}...').format(model=active_info['model'])}[/bold green]", spinner="dots"):
            for event in langgraph_pipeline.stream(initial_state):
                for node_name, node_output in event.items():
                    render_stream_node(node_name, node_output)
    except Exception:
        flush_terminal_stdin()
        err = traceback.format_exc()
        if "401" in err or "authentication" in err.lower():
            p_info = get_active_provider_info()
            console.print(Panel(
                f"[bold red]❌ {_('Authentication Error (401)')}[/bold red]\n\n"
                f"{_('The API Key for provider [bold]{name}[/bold] is invalid or not configured.\nCheck the [bold yellow]{env}[/bold yellow] variable in your [bold].env[/bold] file.').format(name=p_info['name'], env=p_info.get('api_key_env', ''))}",
                border_style="red"
            ))
        else:
            console.print(Panel(f"[bold red]{_('Error during execution:')}[/bold red]\n{err}", border_style="red"))

    flush_terminal_stdin()
    Prompt.ask(f"\n{_('Press ENTER to return to the main menu...')}")


def run(lang: Optional[str] = None):
    """Start the interactive CVECK CLI (LangGraph Adapter)."""
    setup_i18n(lang)

    while True:
        flush_terminal_stdin()
        render_header()
        console.print(f"[bold]{_('Options:')}[/bold]")
        console.print(f"  • {_('Press {key} to load job description from clipboard').format(key='[bold cyan]ENTER[/bold cyan]')}")
        console.print(f"  • {_('Type {cmd} to change model/provider').format(cmd='[magenta]/provider[/magenta]')}")
        console.print(f"  • {_('Type {cmd} to change interface language').format(cmd='[magenta]/lang[/magenta]')}")
        console.print(f"  • {_('Type {cmd1} to clean outputs | {cmd2} to exit').format(cmd1='[magenta]/clean[/magenta]', cmd2='[magenta]/exit[/magenta]')}\n")

        cmd = input("> ").strip()

        if cmd == "/exit":
            console.print(f"[bold cyan]{_('Goodbye!')}[/bold cyan]")
            break
        elif cmd in ["/provider", "/providers"]:
            manage_providers_menu()
            continue
        elif cmd in ["/lang", "/language"]:
            console.print(f"\n[cyan]{_('Available Languages:')}[/cyan]")
            keys = list(SUPPORTED_LOCALES.keys())
            for idx, k in enumerate(keys, 1):
                console.print(f"  [cyan]{idx}[/cyan] - {SUPPORTED_LOCALES[k]} [dim]({k})[/dim]")
            sel = Prompt.ask(_("Select language number or locale code"), default="1")
            chosen = keys[int(sel) - 1] if sel.isdigit() and 1 <= int(sel) <= len(keys) else sel
            if chosen in SUPPORTED_LOCALES:
                setup_i18n(chosen)
                console.print(f"[bold green]✔ {_('Language changed to:')} {SUPPORTED_LOCALES[chosen]}[/bold green]")
                Prompt.ask(f"\n{_('Press ENTER to continue...')}")
            continue
        elif cmd == "/clean":
            _clean_output()
            continue

        # Capture text (Clipboard or Terminal)
        if len(cmd) > 50:
            full_jd, source = cmd, _("Text Pasted in Terminal")
        else:
            clip = get_clipboard_text()
            if clip and len(clip) > 50:
                full_jd, source = clip, _("Clipboard")
            else:
                console.print(f"[yellow]{_('Clipboard empty. Paste the job description below and type \"END\" on a new line:')}[/yellow]")
                lines = []
                while True:
                    try:
                        line = input()
                        if line.strip().upper() in ["END", "FIM", "EXIT", "EOF"]:
                            break
                        lines.append(line)
                    except EOFError:
                        break
                full_jd, source = "\n".join(lines).strip(), _("Manual Input")

        if not full_jd or len(full_jd) < 20:
            console.print(f"[red]{_('Job description is too short or empty.')}[/red]")
            Prompt.ask(f"\n{_('Press ENTER to try again...')}")
            continue

        _run_pipeline(full_jd, source)


@app.command()
def mcp():
    """Start the official MCP (Model Context Protocol) server via stdio."""
    from src.adapters.mcp.server import run_mcp_server
    run_mcp_server()


@app.callback(invoke_without_command=True)
def default_entrypoint(
    ctx: typer.Context,
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Language code (en, pt_BR, zh). Default: system language.")
):
    """Default: if the user only types `cveck`, runs the interactive CLI."""
    if ctx.invoked_subcommand is None:
        run(lang=lang)


if __name__ == "__main__":
    app()