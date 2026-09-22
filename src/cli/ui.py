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
    """Clears residual keyboard input buffer to prevent command leakage in bash/powershell."""
    try:
        if system == "linux":
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        else:
            while msvcrt.kbhit():
                msvcrt.getch()
    except Exception:
        pass


def get_clipboard_text() -> str:
    """Reads system clipboard with support for Wayland (wl-paste) and X11 (xclip)."""
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
    """Formats step token consumption badge only when real API usage occurred."""
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
    """Interactive dynamic menu for managing LLM providers and models."""
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
        chosen = pt_prompt(f"{_('Choose model for \'{name}\'').format(name=prov['name'])}: ", completer=completer).strip() if models else Prompt.ask(_("Model name"))
        if chosen:
            set_active_provider_and_model(p_key, chosen)
            console.print(f"[bold green]✔ {_('Active provider set: {name} -> {model}').format(name=prov['name'], model=chosen)}[/bold green]")
    Prompt.ask(f"\n{_('Press ENTER to continue...')}")


def _add_provider(config):
    presets = load_presets()
    available = {k: v for k, v in presets.items() if k not in config["providers"]}
    preset_keys = list(available.keys())
    for idx, k in enumerate(preset_keys, 1):
        console.print(f"  [cyan]{idx}[/cyan] - {available[k]['name']}")
    console.print(f"  [cyan]{len(preset_keys)+1}[/cyan] - {_('Custom Provider (Custom OpenAI/Anthropic)')}")

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
        console.print(f"[bold green]✔ {_('Provider \"{name}\" added successfully!').format(name=p_data['name'])}[/bold green]")
    elif choice.isdigit() and int(choice) == len(preset_keys) + 1:
        key = Prompt.ask(_("Unique key/slug (e.g. openrouter, groq, zai)")).strip().lower()
        if not key:
            Prompt.ask(f"\n{_('Press ENTER to continue...')}")
            return
        name = Prompt.ask(_("Display name")).strip() or key.capitalize()
        ptype = Prompt.ask(_("Type"), choices=["openai", "anthropic"], default="openai")
        base_url = Prompt.ask(_("Base URL")).strip()
        api_key_env = Prompt.ask(_("Environment variable (.env)")).strip()
        default_model = Prompt.ask(_("Default initial model")).strip()
        config["providers"][key] = {
            "name": name,
            "provider_type": ptype,
            "base_url": base_url or None,
            "api_key_env": api_key_env or None,
            "active_model": default_model or "default",
            "models": [default_model] if default_model else ["default"]
        }
        save_providers_config(config)
        console.print(f"[bold green]✔ {_('Custom provider \"{name}\" registered!').format(name=name)}[/bold green]")
    Prompt.ask(f"\n{_('Press ENTER to continue...')}")


def _add_model(config):
    keys = list(config["providers"].keys())
    for idx, k in enumerate(keys, 1):
        console.print(f"  [cyan]{idx}[/cyan] - {config['providers'][k]['name']}")
    choice = Prompt.ask(_("Add model to which provider?"), default="1")
    if choice.isdigit() and 1 <= int(choice) <= len(keys):
        p_key = keys[int(choice) - 1]
        new_m = Prompt.ask(_("Model name")).strip()
        if new_m:
            add_model_to_provider(p_key, new_m, set_as_active=True)
            console.print(f"[bold green]✔ {_('Model \"{model}\" added!').format(model=new_m)}[/bold green]")
    Prompt.ask(f"\n{_('Press ENTER to continue...')}")


def _remove_model(config):
    keys = list(config["providers"].keys())
    for idx, k in enumerate(keys, 1):
        console.print(f"  [cyan]{idx}[/cyan] - {config['providers'][k]['name']}")
    choice = Prompt.ask(_("Remove model from which provider?"), default="1")
    if choice.isdigit() and 1 <= int(choice) <= len(keys):
        p_key = keys[int(choice) - 1]
        models = config["providers"][p_key].get("models", [])
        if len(models) <= 1:
            console.print(f"[red]{_('The provider must have at least 1 model.')}[/red]")
            Prompt.ask(f"\n{_('Press ENTER to continue...')}")
            return
        for idx, m in enumerate(models, 1):
            console.print(f"  [cyan]{idx}[/cyan] - {m}")
        m_choice = Prompt.ask(_("Model number to remove"))
        if m_choice.isdigit() and 1 <= int(m_choice) <= len(models):
            removed_m = models[int(m_choice) - 1]
            remove_model_from_provider(p_key, removed_m)
            console.print(f"[bold green]✔ {_('Model \"{model}\" removed!').format(model=removed_m)}[/bold green]")
    Prompt.ask(f"\n{_('Press ENTER to continue...')}")


def _remove_provider(config):
    keys = list(config["providers"].keys())
    if len(keys) <= 1:
        console.print(f"[red]{_('Cannot remove the only registered provider.')}[/red]")
        Prompt.ask(f"\n{_('Press ENTER to continue...')}")
        return
    for idx, k in enumerate(keys, 1):
        console.print(f"  [cyan]{idx}[/cyan] - {config['providers'][k]['name']}")
    choice = Prompt.ask(_("Which provider to remove?"))
    if choice.isdigit() and 1 <= int(choice) <= len(keys):
        p_key = keys[int(choice) - 1]
        p_name = config["providers"][p_key]["name"]
        if Confirm.ask(_("Remove '{name}'?").format(name=p_name), default=False):
            remove_provider(p_key)
            console.print(f"[bold green]✔ {_('Provider \"{key}\" removed!').format(key=p_key)}[/bold green]")
    Prompt.ask(f"\n{_('Press ENTER to continue...')}")


# --- STREAMING NODE RENDERERS ---

def _render_failure_panel(data: dict) -> Panel:
    separator = "=" * 50
    title = data.get("job_title") or _("Software Developer")
    company = data.get("company_name") or _("Company")
    attempts = max(data.get("iteration", 1), 1)
    errors = data.get("syntax_error_count", 0)
    typ_err = data.get("typ_error", "")

    lines = [
        separator,
        f" ⚠ {_('PROCESS HALTED: TYPST SYNTAX FAILURE')}",
        separator,
        f"{_('Job:')} {title} ({company})",
        f"{_('Compilation attempts:')} {attempts} ({errors} {_('syntax errors')})",
        "",
        f"{_('REASON:')}",
        _("The current model repeatedly failed to produce valid Typst code."),
        _("This indicates that this specific model may not have strong mastery of Typst syntax."),
        "",
        f"{_('LAST COMPILER ERROR:')}",
        f"{typ_err[:350]}...",
        "",
        f"{_('SUGGESTION:')}",
        _("Switch to a more robust coding model in the /provider menu"),
        _("(e.g., meta/llama-3.3-70b-instruct, claude-3-5-sonnet, or deepseek-chat).")
    ]
    return Panel("\n".join(lines), title=f"[bold red]{_('Final Agent Report')}[/bold red]", expand=False)


def _render_success_panel(data: dict) -> Panel:
    separator = "=" * 50
    ats = data.get("ats_report")
    title = data.get("job_title") or _("Software Developer")
    company = data.get("company_name") or _("Company")
    status_label = _("Approved") if data.get("is_approved") else _("Rejected")

    missing_req = ", ".join(ats.missing_required) if ats and ats.missing_required else _("None")
    missing_opt = ", ".join(ats.missing_optional) if ats and ats.missing_optional else _("None")

    lines = [
        separator,
        f" {_('ATS TECHNICAL REPORT:')} {title} ({company})",
        separator,
        f"{_('Status:')} {status_label}",
        f"{_('Overall Score:')} {ats.score if ats else 0}/100",
        f"{_('Attempts Made:')} {max(data.get('iteration', 1), 1)}",
        f"{_('Mandatory Requirements Coverage:')} {ats.coverage_required_pct if ats else 0}%",
        f"{_('Overall Keyword Coverage:')} {ats.coverage_pct if ats else 0}%",
        "",
        f"{_('Missing Mandatory:')} {missing_req}",
        f"{_('Missing Optional:')} {missing_opt}",
    ]

    if ats and ats.stuffing_flags:
        lines.append(f"{_('Keyword Stuffing Alert (>2%):')} {ats.stuffing_flags}")

    gaps = data.get("detected_gaps", [])
    if gaps:
        gap_names = [g.term if hasattr(g, "term") else g.get("term", "") for g in gaps]
        lines.append(f"{_('Gaps Added to Backlog (doc/GAPS.md):')} {gap_names}")

    pdf_path = data.get("pdf_path")
    if pdf_path:
        lines.append(f"{_('PDF generated at:')} {pdf_path}")

    tokens_info = data.get("token_usage") or {}
    total_tok = tokens_info.get("total_tokens", 0)
    in_tok = tokens_info.get("input_tokens", 0)
    out_tok = tokens_info.get("output_tokens", 0)
    if total_tok > 0:
        lines.append("")
        lines.append(
            f"{_('Total Token Consumption:')} {total_tok:,} ({_('Prompt:')} {in_tok:,} | {_('Completion:')} {out_tok:,})"
        )

    return Panel("\n".join(lines), title=f"[bold green]{_('Final Agent Report')}[/bold green]", expand=False)


def render_stream_node(node_name: str, node_output: dict | None):
    if not node_output or not isinstance(node_output, dict):
        node_output = {}

    if node_name == "gaps_updater":
        return

    toks = format_token_badge(node_output.get("last_step_tokens", {}))

    if node_name == "term_extractor":
        t_count = len(node_output.get("job_terms", []))
        title = node_output.get("job_title", "Dev")
        company = node_output.get("company_name", "Company")
        lang = node_output.get("job_lang", "en")
        kw_label = _("keywords")
        console.print(f"  [cyan]✔ [1/6] {_('Job Detected:')}[/cyan] [bold]{title}[/bold] @ [bold]{company}[/bold] [dim]({lang.upper()})[/dim] ({t_count} {kw_label}) {toks}")

    elif node_name == "gap_finder":
        gaps = node_output.get("detected_gaps", [])
        if gaps:
            labels = [g.term if hasattr(g, "term") else g.get("term", "") for g in gaps]
            console.print(f"  [yellow]⚠ [2/6] {_('Identified Gaps:')}[/yellow] {labels} {toks}")
        else:
            console.print(f"  [cyan]✔ [2/6] {_('Gaps:')}[/cyan] {_('No critical gaps found in profile.')} {toks}")

    elif node_name == "cv_generator":
        console.print(f"  [cyan]✔ [3/6] {_('Typst Generated:')}[/cyan] {_('STAR structure with bold front-loading ready.')} {toks}")

    elif node_name == "typst_compiler":
        local_label = _("Local")
        if node_output.get("typ_error"):
            console.print(f"  [yellow]⚠ [4/6] {_('Typst Compilation:')}[/yellow] {_('Syntax error (triggering auto-repair).')} [dim](0 tokens - {local_label})[/dim]")
        else:
            console.print(f"  [cyan]✔ [4/6] {_('Typst Compilation:')}[/cyan] {_('PDF generated and text extracted successfully.')} [dim](0 tokens - {local_label})[/dim]")

    elif node_name == "typst_fixer":
        console.print(f"  [magenta]🔧 {_('[Auto-Repair] Fixing Typst syntax...')} {toks}[/magenta]")

    elif node_name == "ats_validator":
        ats = node_output.get("ats_report")
        approved = node_output.get("is_approved")
        color = "green" if approved else "yellow"
        status_text = _("APPROVED") if approved else _("REJECTED")
        score = ats.score if ats else 0
        local_label = _("Local")
        console.print(f"  [{color}]✔ [5/6] {_('ATS Score:')}[/{color}] {score}/100 - [{color}]{status_text}[/{color}] [dim](0 tokens - {local_label})[/dim]")

    elif node_name == "cv_refiner":
        console.print(f"  [magenta]↻ {_('[Reflection] Adjusting CV to cover mandatory terms...')} {toks}[/magenta]")

    elif node_name == "committer":
        if node_output.get("syntax_error_count", 0) >= 3 or (node_output.get("typ_error") and not node_output.get("pdf_path")):
            console.print(_render_failure_panel(node_output))
        else:
            console.print(_render_success_panel(node_output))