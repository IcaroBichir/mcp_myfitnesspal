from __future__ import annotations

import click


@click.group()
def cli() -> None:
    """MyFitnessPal MCP server — connect Claude to your MFP diary and measurements."""


@cli.command()
def auth() -> None:
    """Read Chrome cookies and warm the local cache (~/.config/mfp-mcp/cookies.json)."""
    from .auth import COOKIE_CACHE, load_cookiejar

    try:
        load_cookiejar()
        click.echo(f"Auth OK — cookies cached at: {COOKIE_CACHE}")
    except Exception as exc:
        click.echo(f"Auth failed: {exc}", err=True)
        raise SystemExit(1)


@cli.command()
def serve() -> None:
    """Start the MCP server (stdio transport for Claude)."""
    from .server import mcp
    mcp.run()


if __name__ == "__main__":
    cli()
