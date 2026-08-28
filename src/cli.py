import os
import sys
import shutil
import subprocess
import traceback
from datetime import datetime
from typing import Optional

try:
    import termios
    system = "linux"
except ImportError:
    import msvcrt
    system = "windows"

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.completion import WordCompleter

from src.i18n import setup_i18n, _, SUPPORTED_LOCALES
from src.providers import (
    load_presets,
    load_providers_config,
    save_providers_config,
    get_active_provider_info,
    set_active_provider_and_model,
    remove_provider,
    remove_model_from_provider,
    add_model_to_provider,
    fetch_models_from_endpoint
)
from src.graph import app as cv_graph
from src.config import OUTPUT_DIR

app = typer.Typer(help="CV and ATS Agentic Assistant")
console = Console()


def flush_terminal_stdin():
    """Clear any residual text in terminal buffer to prevent bash leaks."""
    try:
        if system == "linux":
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        else:
            while msvcrt.kbhit():
                msvcrt.getch()
    except Exception:
        pass


def get_clipboard_text() -> str:
    """Read from clipboard (Wayland/X11)."""
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


def render_header():
    p = get_active_provider_info()
    console.clear()
    header_text = (
        f"[bold cyan]✦ CVECK (Agentic Pipeline)[/bold cyan]\n"
        f"[dim]{_('Active Provider:')}[/dim] [bold green]{p['name']}[/bold green] ([yellow]{p['model']}[/yellow]) | [dim]Env:[/dim] {p.get('api_key_env') or _('None')}\n"
        f"[dim]{_('Commands:')}[/dim] [magenta]/provider[/magenta] ({_('manage')}) | [magenta]/clean[/magenta] ({_('clean')}) | [magenta]/exit[/magenta]"
    )
    console.print(Panel(header_text, border_style="blue", expand=False))


def interactive_model_selector(models_list: list[str], prompt_text: str = "") -> str:
    prompt_label = prompt_text or _("Select model")
    filter_hint = _("Type to filter with TAB or arrows")
    console.print(f"\n[cyan]{prompt_label}:[/cyan] [dim]({filter_hint})[/dim]")
    completer = WordCompleter(models_list, ignore_case=True, match_middle=True)
    selected = pt_prompt("> ", completer=completer).strip()
    return selected


def format_token_badge(tok_dict: dict) -> str:
    """Format token consumption for CLI display."""
    if not tok_dict or tok_dict.get("total_tokens", 0) == 0:
        return f"[dim](0 tokens - {_('Local')})[/dim]"
    in_tok = tok_dict.get("input_tokens", 0)
    out_tok = tok_dict.get("output_tokens", 0)
    tot = tok_dict.get("total_tokens", 0)
    return f"[dim]({in_tok:,} in / {out_tok:,} out = [bold]{tot:,}[/bold] tokens)[/dim]"


def select_provider_interactively(config: dict, prompt_title: str = "") -> str:
    """Allows selecting a registered provider by number or key."""
    title = prompt_title or _("Select Provider")
    keys = list(config["providers"].keys())
    console.print(f"\n[cyan]{title}:[/cyan]")
    for idx, k in enumerate(keys, 1):
        p_name = config["providers"][k]["name"]
        console.print(f"  [cyan]{idx}[/cyan] - {p_name} [dim]({k})[/dim]")

    choice = Prompt.ask(_("Choose number or enter key"), default="1")
    if choice.isdigit() and 1 <= int(choice) <= len(keys):
        return keys[int(choice) - 1]
    elif choice in config["providers"]:
        return choice
    return ""


def manage_providers_menu():
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
            table.add_row(
                str(idx),
                k,
                p["name"],
                p.get("active_model", "N/A"),
                str(len(p.get("models", []))),
                status
            )

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


class _ProviderMenu:
    @staticmethod
    def press_enter():
        return f"\n{_('Press ENTER to continue...')}"

    @staticmethod
    def _fetch_models(prov):
        base_url = prov.get("base_url")
        api_key_env = prov.get("api_key_env")
        api_key = os.getenv(api_key_env) if api_key_env else None
        if not base_url or not Confirm.ask(_("Fetch online models from provider via API (/models)?"), default=True):
            return []
        try:
            with console.status(f"[green]{_('Fetching models via API...')}[/green]"):
                return fetch_models_from_endpoint(base_url, api_key)
        except Exception as e:
            console.print(f"[yellow]{_('Warning: Fetch failed ({error})').format(error=e)}[/yellow]")
            return []


def _switch_active_provider(config):
    p_key = select_provider_interactively(config, _("Select provider to activate"))
    if p_key:
        prov = config["providers"][p_key]
        models = prov.get("models", [])
        prompt_text = _("Choose model for '{name}'").format(name=prov['name'])
        chosen_model = interactive_model_selector(models, prompt_text) if models else Prompt.ask(_("Enter model name"))
        set_active_provider_and_model(p_key, chosen_model)
        msg = _("✔ Active provider set: {name} -> {model}").format(name=prov['name'], model=chosen_model)
        console.print(f"\n[bold green]{msg}[/bold green]")
    Prompt.ask(_ProviderMenu.press_enter())


def _add_provider(config):
    presets = load_presets()
    available_presets = {k: v for k, v in presets.items() if k not in config["providers"]}
    console.print(f"\n[cyan]{_('Available presets:')}[/cyan]")
    preset_keys = list(available_presets.keys())
    for idx, k in enumerate(preset_keys, 1):
        console.print(f"  [cyan]{idx}[/cyan] - {available_presets[k]['name']} [dim]({k})[/dim]")
    console.print(f"  [cyan]{len(preset_keys)+1}[/cyan] - {_('Custom Provider (Custom OpenAI/Anthropic)')}")

    p_choice = Prompt.ask(_("Choose an option"), default="1")
    if p_choice.isdigit() and 1 <= int(p_choice) <= len(preset_keys):
        _add_provider_from_preset(config, available_presets, preset_keys, int(p_choice))
    elif p_choice == str(len(preset_keys) + 1):
        _add_custom_provider(config)
    Prompt.ask(_ProviderMenu.press_enter())


def _add_provider_from_preset(config, available_presets, preset_keys, choice):
    selected_key = preset_keys[choice - 1]
    p_data = available_presets[selected_key]
    config["providers"][selected_key] = {
        "name": p_data["name"],
        "provider_type": p_data["provider_type"],
        "base_url": p_data["base_url"],
        "api_key_env": p_data["api_key_env"],
        "active_model": p_data["default_models"][0] if p_data.get("default_models") else "default",
        "models": p_data.get("default_models", [])
    }
    save_providers_config(config)
    console.print(f"\n[bold green]{_('✔ Provider \"{name}\" added successfully!').format(name=p_data['name'])}[/bold green]")


def _add_custom_provider(config):
    custom_key = Prompt.ask(_("Unique key/slug (e.g. openrouter, groq, zai)"))
    custom_name = Prompt.ask(_("Display name"))
    custom_type = Prompt.ask(_("Type"), choices=["openai", "anthropic"], default="openai")
    custom_url = Prompt.ask(_("Base URL"))
    custom_env = Prompt.ask(_("Environment variable (.env)"))
    custom_model = Prompt.ask(_("Default initial model"))
    config["providers"][custom_key] = {
        "name": custom_name,
        "provider_type": custom_type,
        "base_url": custom_url,
        "api_key_env": custom_env,
        "active_model": custom_model,
        "models": [custom_model]
    }
    save_providers_config(config)
    console.print(f"\n[bold green]{_('✔ Custom provider \"{name}\" registered!').format(name=custom_name)}[/bold green]")


def _add_model(config):
    p_key = select_provider_interactively(config, _("Add model to which provider?"))
    if p_key:
        prov = config["providers"][p_key]
        fetched = _ProviderMenu._fetch_models(prov)
        new_model = interactive_model_selector(fetched, _("Select model")) if fetched else Prompt.ask(_("Model name"))
        confirm_prompt = _("Set '{model}' as active model for '{name}'?").format(model=new_model, name=prov['name'])
        set_active = Confirm.ask(confirm_prompt, default=True)
        add_model_to_provider(p_key, new_model, set_as_active=set_active)
        console.print(f"\n[bold green]{_('✔ Model \"{model}\" added!').format(model=new_model)}[/bold green]")
    Prompt.ask(_ProviderMenu.press_enter())


def _remove_model(config):
    p_key = select_provider_interactively(config, _("Remove model from which provider?"))
    if p_key:
        prov = config["providers"][p_key]
        models = prov.get("models", [])
        if len(models) <= 1:
            console.print(f"[yellow]{_('The provider must have at least 1 model.')}[/yellow]")
        else:
            for idx, m in enumerate(models, 1):
                console.print(f"  [cyan]{idx}[/cyan] - {m}")
            m_choice = Prompt.ask(_("Model number to remove"))
            if m_choice.isdigit() and 1 <= int(m_choice) <= len(models):
                removed_model = models[int(m_choice) - 1]
                remove_model_from_provider(p_key, removed_model)
                console.print(f"\n[bold green]{_('✔ Model \"{model}\" removed!').format(model=removed_model)}[/bold green]")
    Prompt.ask(_ProviderMenu.press_enter())


def _remove_provider(config):
    p_key = select_provider_interactively(config, _("Which provider to remove?"))
    if p_key and Confirm.ask(_("Remove '{name}'?").format(name=config['providers'][p_key]['name']), default=False):
        remove_provider(p_key)
        console.print(f"\n[bold green]{_('✔ Provider \"{key}\" removed!').format(key=p_key)}[/bold green]")
    Prompt.ask(_ProviderMenu.press_enter())


def _render_term_extractor(out: dict):
    terms_count = len(out.get("job_terms", []))
    title = out.get("job_title", "Developer")
    company = out.get("company_name", "Company")
    lang = out.get("job_lang", "pt")
    toks = format_token_badge(out.get("last_step_tokens", {}))
    console.print(f"  [cyan]✔ [1/6] {_('Job Detected:')}[/cyan] [bold]{title}[/bold] @ [bold]{company}[/bold] [dim]({lang.upper()})[/dim] ({terms_count} keywords) {toks}")


def _render_gap_finder(out: dict):
    gaps = out.get("detected_gaps", [])
    toks = format_token_badge(out.get("last_step_tokens", {}))
    if gaps:
        gap_labels = [g.term if hasattr(g, "term") else g.get("term", "") for g in gaps]
        console.print(f"  [yellow]⚠ [2/6] {_('Identified Gaps:')}[/yellow] {gap_labels} {toks}")
    else:
        console.print(f"  [cyan]✔ [2/6] {_('Gaps:')}[/cyan] {_('No critical gaps found in profile.')} {toks}")


def _render_cv_generator(out: dict):
    toks = format_token_badge(out.get("last_step_tokens", {}))
    console.print(f"  [cyan]✔ [3/6] {_('Typst Generated:')}[/cyan] {_('STAR structure with bold front-loading ready.')} {toks}")


def _render_typst_compiler(out: dict):
    if out.get("typ_error"):
        console.print(f"  [yellow]⚠ [4/6] {_('Typst Compilation:')}[/yellow] {_('Syntax error (triggering auto-repair).')} [dim](0 tokens - Local)[/dim]")
    else:
        console.print(f"  [cyan]✔ [4/6] {_('Typst Compilation:')}[/cyan] {_('PDF generated and text extracted successfully.')} [dim](0 tokens - Local)[/dim]")


def _render_typst_fixer(out: dict):
    toks = format_token_badge(out.get("last_step_tokens", {}))
    console.print(f"  [magenta]🔧 {_('[Auto-Repair] Fixing Typst syntax...')} {toks}[/magenta]")


def _render_ats_validator(out: dict):
    ats = out.get("ats_report")
    approved = out.get("is_approved")
    color = "green" if approved else "yellow"
    status_text = _("APPROVED") if approved else _("REJECTED")
    score_val = getattr(ats, "score", 0) if ats else 0
    console.print(f"  [{color}]✔ [5/6] {_('ATS Score:')}[/{color}] {score_val}/100 - [{color}]{status_text}[/{color}] [dim](0 tokens - Local)[/dim]")


def _render_cv_refiner(out: dict):
    toks = format_token_badge(out.get("last_step_tokens", {}))
    console.print(f"  [magenta]↻ {_('[Reflection] Adjusting CV to cover mandatory terms...')} {toks}[/magenta]")


def _render_committer(out: dict):
    final_summary = out.get("final_summary", "")
    console.print(Panel(final_summary, title=f"[bold green]{_('Final Agent Report')}[/bold green]", expand=False))


_NODE_RENDERERS = {
    "term_extractor": _render_term_extractor,
    "gap_finder": _render_gap_finder,
    "cv_generator": _render_cv_generator,
    "typst_compiler": _render_typst_compiler,
    "typst_fixer": _render_typst_fixer,
    "ats_validator": _render_ats_validator,
    "cv_refiner": _render_cv_refiner,
    "committer": _render_committer,
}


def _render_stream_node(node_name: str, node_output: dict):
    """Render node output in CLI."""
    renderer = _NODE_RENDERERS.get(node_name)
    if renderer:
        renderer(node_output)


def _collect_job_description(command: str) -> tuple[str, str]:
    """Collect job description from clipboard, argument or multi-line input."""
    if len(command) > 50:
        return command, _("Text Pasted in Terminal")

    clipboard_text = get_clipboard_text()
    if clipboard_text and len(clipboard_text) > 50:
        return clipboard_text, _("Clipboard")

    console.print(f"[yellow]{_('Clipboard empty. Paste the job description below and type \"END\" on a new line:')}[/yellow]")
    lines = []
    while True:
        try:
            line = input()
            if line.strip() in ["FIM", "END", "EXIT", "EOF"]:
                break
            lines.append(line)
        except EOFError:
            break
    return "\n".join(lines).strip(), _("Manual Input")


def _run_pipeline(full_jd: str, source_label: str):
    """Run CV generation and refinement pipeline with agentic feedback."""
    num_lines = len(full_jd.splitlines())
    num_chars = len(full_jd)

    render_header()
    card_title = _("Job Description Loaded")
    card_lines_label = _("Lines:")
    card_chars_label = _("Characters:")
    card_status = _("Running AI-powered adaptation pipeline...")

    console.print(Panel(
        f"📄 [bold green]{card_title}[/bold green] [dim]({source_label})[/dim]\n"
        f"[dim]{card_lines_label}[/dim] {num_lines} | [dim]{card_chars_label}[/dim] {num_chars}\n"
        f"[italic cyan]{card_status}[/italic cyan]",
        border_style="green",
        expand=False
    ))

    initial_state = {
        "job_description": full_jd,
        "job_slug": "",
        "job_title": "",
        "company_name": "",
        "job_lang": "",
        "job_date": datetime.now().strftime("%Y-%m-%d"),
        "job_terms": [],
        "detected_gaps": [],
        "typ_content": "",
        "pdf_path": "",
        "txt_content": "",
        "typ_error": "",
        "syntax_error_count": 0,
        "ats_report": None,
        "iteration": 0,
        "is_approved": False,
        "final_summary": "",
        "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "by_node": {}},
        "last_step_tokens": {}
    }

    active_info = get_active_provider_info()
    running_msg = _("⚡ Running Pipeline with [{name} -> {model}]...").format(name=active_info['name'], model=active_info['model'])
    console.print(f"\n[bold cyan]{running_msg}[/bold cyan]")

    status_msg = _("Processing with {model}...").format(model=active_info['model'])

    try:
        with console.status(f"[bold green]{status_msg}[/bold green]", spinner="dots"):
            for event in cv_graph.stream(initial_state):
                for node_name, node_output in event.items():
                    _render_stream_node(node_name, node_output)
    except Exception:
        flush_terminal_stdin()
        error_msg = traceback.format_exc()
        if "401" in error_msg or "authentication" in error_msg.lower():
            p_info = get_active_provider_info()
            auth_title = _("❌ Authentication Error (401)")
            auth_body = _(
                "The API Key for provider [bold]{name}[/bold] is invalid or not configured.\n"
                "Check the [bold yellow]{env}[/bold yellow] variable in your [bold].env[/bold] file."
            ).format(name=p_info['name'], env=p_info['api_key_env'])
            console.print(Panel(f"[bold red]{auth_title}[/bold red]\n\n{auth_body}", border_style="red"))
        else:
            err_title = _("Error during execution:")
            console.print(Panel(f"[bold red]{err_title}[/bold red]\n{error_msg}", border_style="red"))

    flush_terminal_stdin()
    Prompt.ask(f"\n{_('Press [bold]ENTER[/bold] to return to the main menu...')}")


def _clean_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for item in OUTPUT_DIR.glob("*"):
        if item.name in [".gitignore", ".gitkeep"]:
            continue
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    console.print(f"[bold green]{_('✔ output/ folder cleaned!')}[/bold green]")
    Prompt.ask(f"\n{_('Press [bold]ENTER[/bold] to continue...')}")


@app.command(help="Start the interactive CV adaptation pipeline and ATS analysis.")
def main(
    lang: Optional[str] = typer.Option(
        None,
        "--lang",
        "-l",
        help="Language locale code (e.g. en, en_US, en_GB, pt, pt_BR, pt_PT, es, ru, ja, zh)",
    )
):
    """Interactive Mode (Agent Pipeline Chat)."""
    setup_i18n(lang)

    while True:
        flush_terminal_stdin()
        render_header()
        console.print(f"[bold]{_('Options:')}[/bold]")
        key_enter = "[bold cyan]ENTER[/bold cyan]"
        cmd_provider = "[magenta]/provider[/magenta]"
        cmd_lang = "[magenta]/lang[/magenta]"
        cmd_clean = "[magenta]/clean[/magenta]"
        cmd_exit = "[magenta]/exit[/magenta]"

        console.print(f"  • {_('Press {key} to load job description from clipboard').format(key=key_enter)}")
        console.print(f"  • {_('Type {cmd} to change model/provider').format(cmd=cmd_provider)}")
        console.print(f"  • {_('Type {cmd} to change interface language').format(cmd=cmd_lang)}")
        console.print(f"  • {_('Type {cmd1} to clean outputs | {cmd2} to exit').format(cmd1=cmd_clean, cmd2=cmd_exit)}\n")

        command = input("> ").strip()

        if command == "/exit":
            console.print(f"[bold cyan]{_('Goodbye!')}[/bold cyan]")
            break
        elif command in ["/provider", "/providers"]:
            manage_providers_menu()
            continue
        elif command in ["/lang", "/language"]:
            console.print(f"\n[cyan]{_('Available Languages:')}[/cyan]")
            locales_keys = list(SUPPORTED_LOCALES.keys())
            for idx, loc_key in enumerate(locales_keys, 1):
                console.print(f"  [cyan]{idx}[/cyan] - {SUPPORTED_LOCALES[loc_key]} [dim]({loc_key})[/dim]")

            selected_choice = Prompt.ask(
                _("Select language number or locale code"),
                default="1"
            )

            chosen_locale = None
            if selected_choice.isdigit() and 1 <= int(selected_choice) <= len(locales_keys):
                chosen_locale = locales_keys[int(selected_choice) - 1]
            elif selected_choice in SUPPORTED_LOCALES:
                chosen_locale = selected_choice

            if chosen_locale:
                setup_i18n(chosen_locale)
                msg = _("Language changed to:")
                console.print(f"\n[bold green]✔ {msg} {SUPPORTED_LOCALES.get(chosen_locale, chosen_locale)}[/bold green]")
                Prompt.ask(f"\n{_('Press ENTER to continue...')}")
            continue
        elif command == "/clean":
            _clean_output_dir()
            continue

        full_jd, source_label = _collect_job_description(command)

        flush_terminal_stdin()

        if not full_jd or len(full_jd) < 20:
            console.print(f"[red]{_('Job description is too short or empty.')}[/red]")
            Prompt.ask(f"\n{_('Press ENTER to try again...')}")
            continue

        _run_pipeline(full_jd, source_label)


if __name__ == "__main__":
    app()