from pathlib import Path
from typing import Annotated

import typer

from tech_translator.config import load_config
from tech_translator.llm.api_health import APIHealthResult, check_api
from tech_translator.utils.errors import diagnostic
from tech_translator.utils.logging import configure_logging

app = typer.Typer(no_args_is_help=True)
ConfigOption = Annotated[Path | None, typer.Option("--config", help="YAML configuration path")]


@app.command("test-api")
def test_api(config: ConfigOption = None, model: str | None = None,
             json_output: Annotated[bool, typer.Option("--json")] = False):
    try:
        settings = load_config(config, model)
        configure_logging(settings)
    except Exception:
        result = APIHealthResult(error="Invalid configuration. Check the YAML file and environment values.")
        typer.echo(result.model_dump_json() if json_output else result.error)
        raise typer.Exit(1)
    result = check_api(settings)
    if json_output:
        typer.echo(result.model_dump_json())
    else:
        availability = {True: "OK", False: "NOT LISTED", None: "UNKNOWN"}[result.model_available]
        typer.echo(f"LLM API Connection Test\n-----------------------------\n"
                   f"Endpoint: {settings.llm.base_url}\nModel: {settings.llm.model}\n\n"
                   f"Connection:          {'OK' if result.connected else 'FAILED'}\n"
                   f"Model availability:  {availability}\n"
                   f"Generation:          {'OK' if result.generation_success else 'FAILED'}\n"
                   f"Response time:       {result.response_time_ms} ms")
        if result.test_response:
            typer.echo(f"\nTest response:\n{result.test_response}")
        if result.error:
            typer.echo(f"\nError: {result.error}")
        typer.echo(f"\nResult: {'SUCCESS' if result.generation_success else 'FAILURE'}")
    if not result.generation_success:
        raise typer.Exit(1)


@app.command()
def translate(input_path: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
              output: Annotated[Path, typer.Option("--output", "-o")],
              config: ConfigOption = None, model: str | None = None,
              force: Annotated[bool, typer.Option(help="Replace an existing output")] = False):
    """Translate a TXT, Markdown, or DOCX document."""
    from tech_translator.core.pipeline import translate_document
    try:
        settings = load_config(config, model)
        configure_logging(settings)
    except Exception:
        typer.echo("Invalid configuration. Check the YAML file and environment values.", err=True)
        raise typer.Exit(1)
    try:
        translate_document(input_path, output, settings, force=force)
    except Exception as error:
        # Validation failures are local and safe; remote bodies are never printed.
        text = str(error) if isinstance(error, (ValueError, FileExistsError, FileNotFoundError)) else diagnostic(error)
        typer.echo(f"Translation failed: {text}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Saved translation: {output}")


if __name__ == "__main__":
    app()
