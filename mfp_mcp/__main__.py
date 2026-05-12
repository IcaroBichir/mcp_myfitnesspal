from __future__ import annotations

import click


@click.group()
def cli() -> None:
    """MyFitnessPal MCP server — connect Claude to your MFP diary and measurements."""


@cli.command()
def auth() -> None:
    """Read Chrome cookies, resolve MFP username, and warm the local cache."""
    from .auth import COOKIE_CACHE, load_auth

    try:
        _, username = load_auth()
        click.echo(f"Auth OK — logged in as: {username}")
        click.echo(f"Cache saved to: {COOKIE_CACHE}")
    except Exception as exc:
        click.echo(f"Auth failed: {exc}", err=True)
        raise SystemExit(1)


@cli.command()
def serve() -> None:
    """Start the MCP server (stdio transport for Claude)."""
    from .server import mcp
    mcp.run()


@cli.group()
def cache() -> None:
    """Manage the local SQLite response cache."""


@cache.command("stats")
def cache_stats() -> None:
    """Show cache statistics."""
    from .cache import CacheStore
    stats = CacheStore().stats()
    click.echo(f"DB:      {stats['db']}")
    click.echo(f"Entries: {stats['total_entries']} total, {stats['valid']} valid, {stats['expired']} expired")


@cache.command("clear")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
def cache_clear(yes: bool) -> None:
    """Delete all cached data."""
    from .cache import CacheStore
    if not yes:
        click.confirm("Clear all cached MFP data?", abort=True)
    CacheStore().clear()
    click.echo("Cache cleared.")


if __name__ == "__main__":
    cli()
