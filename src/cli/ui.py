import os
import sys
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.completion import WordCompleter

from src.cli.i18n import _
from src.adapters.langgraph.providers.registry import (
    load_presets,
    load_providers_config,
    save_providers_config,
    get_active_provider_info,
    NoProviderConfiguredError,
    set_active_provider_and_model,
    remove_provider,
    remove_model_from_provider,
    add_model_to_provider,
    fetch_models_from_endpoint
)

console = Console()

try:
    import termios
    system = "linux"
except ImportError:
    import msvcrt
    system = "windows"


def flush_terminal_stdin():
    """Limpa buffer residual do teclado para evitar vazamento de comandos no bash/powershell."""
    try:
        if system == "linux":
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        else:
            while msvcrt.kbhit():
                msvcrt.getch()
    except Exception:
        pass


def get_clipboard_text() -> str:
    """Lê do clipboard do sistema com suporte a Wayland (wl-paste) e X11 (xclip)."""
    try:
        res = subprocess.run(["wl-paste"], capture_output=True, text=True, timeout=1)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass

    try:
        res = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True, timeout=1)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass

    return ""


def format_token_badge(tok_dict: dict) -> str:
    """Formata consumo de tokens do passo apenas se houver consumo real de API."""
    if not tok_dict or tok_dict.get("total_tokens", 0) == 0:
        return ""
    in_tok = tok_dict.get("input_tokens", 0)
    out_tok = tok_dict.get("output_tokens", 0)
    tot = tok_dict.get("total_tokens", 0)
    return f"[dim]({in_tok:,} in / {out_tok:,} out = [bold]{tot:,}[/bold] tokens)[/dim]"


def render_header():
    console.clear()
    try:
        p = get_active_provider_info()
        provider_line = (
            f"[dim]{_('Active Provider:')}[/dim] [bold green]{p['name']}[/bold green] "
            f"([yellow]{p['model']}[/yellow]) | [dim]Env:[/dim] {p.get('api_key_env') or _('None')}"
        )
    except NoProviderConfiguredError:
        provider_line = f"[bold red]{_('No provider configured — use /provider to add one')}[/bold red]"

    header_text = (
        f"[bold cyan]✦ CVECK 2.0 (Agentic Architecture)[/bold cyan]\n"
        f"{provider_line}\n"
        f"[dim]{_('Commands:')}[/dim] [magenta]/provider[/magenta] ({_('manage')}) | [magenta]/clean[/magenta] ({_('clean')}) | [magenta]/exit[/magenta]"
    )
    console.print(Panel(header_text, border_style="blue", expand=False))


def manage_providers_menu():
    """Menu dinâmico interativo para gerenciar provedores e modelos LLM."""
    while True:
        flush_terminal_stdin()
        console.clear()
        config = load_providers_config()
        active_p = config.get("active_provider")

        table = Table(title=_("Provider & Model Manager"), border_style="cyan")
        table.add_column("#", style="dim")
        table.add_column(_("Key"), style="cyan")
        table.add_column(_("Name"), style="white")
        table.add_column(_("Active Model"), style="yellow")
        table.add_column(_("Total Models"), style="magenta")
        table.add_column(_("Status"), style="green")

        provider_keys = list(config["providers"].keys())
        for idx, k in enumerate(provider_keys, 1):
            p = config["providers"][k]
            status = f"[bold green]{_('● ACTIVE')}[/bold green]" if k == active_p else ""
            table.add_row(str(idx), k, p["name"], p.get("active_model", "N/A"), str(len(p.get("models", []))), status)

        console.print(table)
        console.print(f"\n[bold]{_('Available actions:')}[/bold]")
        console.print(f"  [cyan]1[/cyan] - {_('Switch Active Provider / Model')}")
        console.print(f"  [cyan]2[/cyan] - {_('Add New Provider (from Presets or Custom)')}")
        console.print(f"  [cyan]3[/cyan] - {_('Add Model to a Provider')}")
        console.print(f"  [cyan]4[/cyan] - {_('Remove Model from a Provider')}")
        console.print(f"  [cyan]5[/cyan] - {_('Remove a Provider')}")
        console.print(f"  [cyan]0[/cyan] - {_('Return to Main Chat')}\n")

        opt = Prompt.ask(_("Choose an option"), choices=["0", "1", "2", "3", "4", "5"], default="0")

        if opt == "0":
            break
        elif opt == "1":
            _switch_active_provider(config)
        elif opt == "2":
            _add_provider(config)
        elif opt == "3":
            _add_model(config)
        elif opt == "4":
            _remove_model(config)
        elif opt == "5":
            _remove_provider(config)


def _switch_active_provider(config):
    keys = list(config["providers"].keys())
    for idx, k in enumerate(keys, 1):
        console.print(f"  [cyan]{idx}[/cyan] - {config['providers'][k]['name']}")
    choice = Prompt.ask(_("Select provider to activate"), default="1")
    if choice.isdigit() and 1 <= int(choice) <= len(keys):
        p_key = keys[int(choice) - 1]
        prov = config["providers"][p_key]
        models = prov.get("models", [])
        completer = WordCompleter(models, ignore_case=True)
        chosen = pt_prompt(f"{_('Choose model for')} '{prov['name']}': ", completer=completer).strip() if models else Prompt.ask(_("Model name"))
        set_active_provider_and_model(p_key, chosen)
        console.print(f"[bold green]✔ {prov['name']} -> {chosen}[/bold green]")
    Prompt.ask(f"\n{_('Press ENTER to continue...')}")


def _add_provider(config):
    presets = load_presets()
    available = {k: v for k, v in presets.items() if k not in config["providers"]}
    preset_keys = list(available.keys())
    for idx, k in enumerate(preset_keys, 1):
        console.print(f"  [cyan]{idx}[/cyan] - {available[k]['name']}")
    console.print(f"  [cyan]{len(preset_keys)+1}[/cyan] - {_('Custom Provider')}")

    choice = Prompt.ask(_("Choose an option"), default="1")
    if choice.isdigit() and 1 <= int(choice) <= len(preset_keys):
        k = preset_keys[int(choice) - 1]
        p_data = available[k]
        config["providers"][k] = {
            "name": p_data["name"], "provider_type": p_data["provider_type"],
            "base_url": p_data["base_url"], "api_key_env": p_data["api_key_env"],
            "active_model": p_data["default_models"][0], "models": p_data["default_models"]
        }
        save_providers_config(config)
        console.print(f"[bold green]✔ {_('Provider added!')}[/bold green]")
    Prompt.ask(f"\n{_('Press ENTER to continue...')}")


def _add_model(config):
    keys = list(config["providers"].keys())
    for idx, k in enumerate(keys, 1):
        console.print(f"  [cyan]{idx}[/cyan] - {config['providers'][k]['name']}")
    choice = Prompt.ask(_("Add model to which provider?"), default="1")
    if choice.isdigit() and 1 <= int(choice) <= len(keys):
        p_key = keys[int(choice) - 1]
        new_m = Prompt.ask(_("Model name"))
        add_model_to_provider(p_key, new_m, set_as_active=True)
        console.print(f"[bold green]✔ {_('Model added!')}[/bold green]")
    Prompt.ask(f"\n{_('Press ENTER to continue...')}")


def _remove_model(config):
    keys = list(config["providers"].keys())
    for idx, k in enumerate(keys, 1):
        console.print(f"  [cyan]{idx}[/cyan] - {config['providers'][k]['name']}")
    choice = Prompt.ask(_("Remove model from which provider?"), default="1")
    if choice.isdigit() and 1 <= int(choice) <= len(keys):
        p_key = keys[int(choice) - 1]
        models = config["providers"][p_key].get("models", [])
        for idx, m in enumerate(models, 1):
            console.print(f"  [cyan]{idx}[/cyan] - {m}")
        m_choice = Prompt.ask(_("Model number to remove"))
        if m_choice.isdigit() and 1 <= int(m_choice) <= len(models):
            remove_model_from_provider(p_key, models[int(m_choice) - 1])
            console.print(f"[bold green]✔ {_('Model removed!')}[/bold green]")
    Prompt.ask(f"\n{_('Press ENTER to continue...')}")


def _remove_provider(config):
    keys = list(config["providers"].keys())
    for idx, k in enumerate(keys, 1):
        console.print(f"  [cyan]{idx}[/cyan] - {config['providers'][k]['name']}")
    choice = Prompt.ask(_("Which provider to remove?"))
    if choice.isdigit() and 1 <= int(choice) <= len(keys):
        p_key = keys[int(choice) - 1]
        if Confirm.ask(f"{_('Remove')} '{config['providers'][p_key]['name']}'?", default=False):
            remove_provider(p_key)
            console.print(f"[bold green]✔ {_('Provider removed!')}[/bold green]")
    Prompt.ask(f"\n{_('Press ENTER to continue...')}")


# --- STREAMING NODE RENDERERS ---

def render_stream_node(node_name: str, node_output: dict | None):
    # 1. Guarda contra eventos sem mutação de estado (None)
    if not node_output or not isinstance(node_output, dict):
        node_output = {}

    # 2. Ignora nós internos silenciosos que não geram log visual no terminal
    if node_name == "gaps_updater":
        return

    toks = format_token_badge(node_output.get("last_step_tokens", {}))

    if node_name == "term_extractor":
        t_count = len(node_output.get("job_terms", []))
        title = node_output.get("job_title", "Dev")
        company = node_output.get("company_name", "Company")
        lang = node_output.get("job_lang", "en")
        console.print(f"  [cyan]✔ [1/6] {_('Job Detected:')}[/cyan] [bold]{title}[/bold] @ [bold]{company}[/bold] [dim]({lang.upper()})[/dim] ({t_count} keywords) {toks}")

    elif node_name == "gap_finder":
        gaps = node_output.get("detected_gaps", [])
        if gaps:
            labels = [g.term if hasattr(g, "term") else g.get("term", "") for g in gaps]
            console.print(f"  [yellow]⚠ [2/6] {_('Identified Gaps:')}[/yellow] {labels} {toks}")
        else:
            console.print(f"  [cyan]✔ [2/6] {_('Gaps:')}[/cyan] {_('No critical gaps found.')} {toks}")

    elif node_name == "cv_generator":
        console.print(f"  [cyan]✔ [3/6] {_('Typst Generated:')}[/cyan] {_('STAR structure ready.')} {toks}")

    elif node_name == "typst_compiler":
        if node_output.get("typ_error"):
            console.print(f"  [yellow]⚠ [4/6] {_('Typst Compilation:')}[/yellow] {_('Syntax error (triggering auto-repair).')} [dim](0 tokens - Local)[/dim]")
        else:
            console.print(f"  [cyan]✔ [4/6] {_('Typst Compilation:')}[/cyan] {_('PDF generated successfully.')} [dim](0 tokens - Local)[/dim]")

    elif node_name == "typst_fixer":
        console.print(f"  [magenta]🔧 {_('[Auto-Repair] Fixing Typst syntax...')} {toks}[/magenta]")

    elif node_name == "ats_validator":
        ats = node_output.get("ats_report")
        approved = node_output.get("is_approved")
        color = "green" if approved else "yellow"
        status_text = _("APPROVED") if approved else _("REJECTED")
        score = ats.score if ats else 0
        console.print(f"  [{color}]✔ [5/6] {_('ATS Score:')}[/{color}] {score}/100 - [{color}]{status_text}[/{color}] [dim](0 tokens - Local)[/dim]")

    elif node_name == "cv_refiner":
        console.print(f"  [magenta]↻ {_('[Reflection] Adjusting CV to cover mandatory terms...')} {toks}[/magenta]")

    elif node_name == "committer":
        summary = node_output.get("final_summary", "")
        if summary:
            console.print(Panel(summary, title=f"[bold green]{_('Final Agent Report')}[/bold green]", expand=False))
        else:
            console.print(Panel(f"✔ {_('Artifacts committed to output/ successfully!')}", title=f"[bold green]{_('Final Agent Report')}[/bold green]", expand=False))