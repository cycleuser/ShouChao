"""
Command-line interface for ShouChao.

Provides subcommands for getting, searching, briefing, analysis,
indexing, source management, configuration, and launching GUI/Web.
"""

import sys
import argparse
import json
import logging

from shouchao import __version__

logger = logging.getLogger(__name__)

CLI_COMMANDS = {"fetch", "search", "briefing", "analyze", "index",
                "sources", "config", "web", "gui"}


def main():
    """Main CLI entry point with subcommand routing."""
    # Quick check for subcommand routing
    if len(sys.argv) > 1 and sys.argv[1] in CLI_COMMANDS:
        cmd = sys.argv[1]
        sys.argv = [sys.argv[0]] + sys.argv[2:]  # Strip subcommand
        handlers = {
            "fetch": cmd_fetch,
            "search": cmd_search,
            "briefing": cmd_briefing,
            "analyze": cmd_analyze,
            "index": cmd_index,
            "sources": cmd_sources,
            "config": cmd_config,
            "web": cmd_web,
            "gui": cmd_gui,
        }
        return handlers[cmd]()

    # Default: show help
    parser = _build_main_parser()
    args = parser.parse_args()

    if args.json_output:
        print(json.dumps({"version": __version__}))
    else:
        parser.print_help()


def _build_main_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shouchao",
        description="ShouChao (手抄) - Web Information Retrieval Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Subcommands:
  fetch       Get news from sources
  search      Search indexed news
  briefing    Generate news briefings
  analyze     Analyze news for scenarios (investment/immigration/study)
  index       Index articles into knowledge base
  sources     List/manage news sources
  config      View/update configuration
  web         Start web server
  gui         Launch GUI

Examples:
  shouchao fetch --language en --max 10
  shouchao search "AI regulation"
  shouchao briefing --type daily
  shouchao analyze "EU policy impact" --scenario investment
  shouchao sources --language zh
  shouchao web --port 5001
""",
    )
    parser.add_argument(
        "-V", "--version", action="version",
        version=f"shouchao {__version__}",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output results as JSON",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="Suppress non-essential output",
    )
    parser.add_argument(
        "--data-dir", help="Custom data directory",
    )
    return parser


def _setup_logging(verbose=False, quiet=False):
    """Configure DEBUG level logging, output to both stdout and file."""
    from shouchao.core.config import LOGS_DIR, ensure_dirs
    
    ensure_dirs()
    
    # Always use DEBUG level for maximum logging
    level = logging.DEBUG if verbose else (logging.WARNING if quiet else logging.DEBUG)
    
    # Unified format: [时间][线程][模块:行号][级别]消息
    fmt = "[%(asctime)s][%(threadName)s][%(name)s:%(lineno)d][%(levelname)s] %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=date_fmt)
    
    root = logging.getLogger()
    # Clear existing handlers to avoid duplicates
    for h in root.handlers[:]:
        root.removeHandler(h)
    
    # StreamHandler bound to stdout for real-time CLI output
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)
    
    # Also log to file for persistence
    log_file = LOGS_DIR / "shouchao.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    
    root.setLevel(level)
    
    # Suppress noisy third-party libraries
    for lib in ("urllib3", "requests", "chroma", "chromadb", "feedparser", "bs4", "html2text"):
        logging.getLogger(lib).setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.INFO)
    logging.getLogger("flask").setLevel(logging.INFO)
    
    logging.info(f"Logging initialized: level={logging.getLevelName(level)}, file={log_file}")


def _parse_common_flags(parser):
    """Add common flags to any subcommand parser."""
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("--data-dir", help="Custom data directory")


def _apply_data_dir(args):
    """Apply custom data dir if specified."""
    if hasattr(args, "data_dir") and args.data_dir:
        import os
        os.environ["SHOUCHAO_DATA_DIR"] = args.data_dir


def _output(args, data, text_func):
    """Output as JSON or formatted text."""
    if args.json_output:
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    else:
        text_func()


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------

def cmd_fetch():
    parser = argparse.ArgumentParser(prog="shouchao fetch",
                                     description="Get news from sources")
    _parse_common_flags(parser)
    parser.add_argument("--language", "-l", help="Language code(s), comma-separated")
    parser.add_argument("--category", "-c", help="Category filter")
    parser.add_argument("--source", "-s", help="Specific source name")
    parser.add_argument("--max", type=int, default=20, dest="max_articles",
                        help="Max articles per source (default: 20)")
    parser.add_argument("--fetcher", default="requests",
                        choices=["requests", "curl", "browser", "playwright"])
    args = parser.parse_args()
    _apply_data_dir(args)
    _setup_logging(args.verbose, args.quiet)

    from shouchao.api import fetch_news

    try:
        from rich.console import Console
        from rich.progress import Progress, SpinnerColumn, TextColumn
        console = Console()
        has_rich = True
    except ImportError:
        has_rich = False

    languages = args.language.split(",") if args.language else [None]

    all_results = []
    for lang in languages:
        result = fetch_news(
            language=lang,
            source=args.source,
            max_articles=args.max_articles,
            fetcher=args.fetcher,
        )
        if result.success and result.data:
            all_results.extend(result.data.get("articles", []))

    total = len(all_results)

    def _print_text():
        if has_rich:
            console.print(f"\n[bold green]Got {total} articles[/bold green]\n")
            if total > 0 and not args.quiet:
                from rich.table import Table
                table = Table(title="Retrieved Articles")
                table.add_column("Source", style="cyan")
                table.add_column("Language", style="magenta")
                table.add_column("Date")
                table.add_column("Title", style="white")
                for a in all_results[:50]:
                    table.add_row(
                        a.get("source", ""),
                        a.get("language", ""),
                        a.get("date", ""),
                        a.get("title", "")[:60],
                    )
                console.print(table)
        else:
            print(f"Got {total} articles")
            for a in all_results[:20]:
                print(f"  [{a.get('language')}] {a.get('source')}: {a.get('title', '')[:60]}")

    _output(args, {"fetched": total, "articles": all_results}, _print_text)


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

def cmd_search():
    parser = argparse.ArgumentParser(prog="shouchao search",
                                     description="Search indexed news")
    _parse_common_flags(parser)
    parser.add_argument("query", help="Search query")
    parser.add_argument("--language", "-l", help="Filter language")
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()
    _apply_data_dir(args)
    _setup_logging(args.verbose, args.quiet)

    from shouchao.api import search_news
    result = search_news(query=args.query, language=args.language, top_k=args.top_k)

    def _print_text():
        if result.success:
            results = result.data.get("results", [])
            print(f"\nFound {len(results)} results for: {args.query}\n")
            for i, r in enumerate(results, 1):
                meta = r.get("metadata", {})
                print(f"{i}. [{meta.get('website', '?')}] {meta.get('title', 'Untitled')}")
                print(f"   Language: {meta.get('language', '?')} | "
                      f"Date: {meta.get('date', '?')} | "
                      f"Distance: {r.get('distance', 0):.3f}")
                doc = r.get("document", "")[:150]
                print(f"   {doc}...")
                print()
        else:
            print(f"Error: {result.error}")

    _output(args, result.to_dict(), _print_text)


# ---------------------------------------------------------------------------
# briefing
# ---------------------------------------------------------------------------

def cmd_briefing():
    parser = argparse.ArgumentParser(prog="shouchao briefing",
                                     description="Generate news briefings")
    _parse_common_flags(parser)
    parser.add_argument("--type", default="daily",
                        choices=["daily", "weekly", "domain"],
                        dest="briefing_type")
    parser.add_argument("--date", help="Target date (YYYY-MM-DD)")
    parser.add_argument("--language", "-l", help="Output language")
    parser.add_argument("--category", "-c", help="Category filter (for domain type)")
    parser.add_argument("-o", "--output", help="Output file path")
    args = parser.parse_args()
    _apply_data_dir(args)
    _setup_logging(args.verbose, args.quiet)

    from shouchao.api import generate_briefing
    categories = [args.category] if args.category else None
    result = generate_briefing(
        briefing_type=args.briefing_type,
        language=args.language,
        categories=categories,
        date=args.date,
    )

    def _print_text():
        if result.success:
            content = result.data.get("content", "")
            if args.output:
                from pathlib import Path
                Path(args.output).write_text(content, encoding="utf-8")
                print(f"Briefing saved to: {args.output}")
            else:
                print(content)
        else:
            print(f"Error: {result.error}")

    _output(args, result.to_dict(), _print_text)


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------

def cmd_analyze():
    parser = argparse.ArgumentParser(prog="shouchao analyze",
                                     description="Analyze news for scenarios")
    _parse_common_flags(parser)
    parser.add_argument("query", help="Analysis query")
    parser.add_argument("--scenario", "-s", default="general",
                        choices=["investment", "immigration", "study_abroad", "general"])
    parser.add_argument("--language", "-l", help="Output language")
    args = parser.parse_args()
    _apply_data_dir(args)
    _setup_logging(args.verbose, args.quiet)

    from shouchao.api import analyze_news
    result = analyze_news(
        query=args.query,
        scenario=args.scenario,
        language=args.language,
    )

    def _print_text():
        if result.success:
            print(result.data.get("content", ""))
        else:
            print(f"Error: {result.error}")

    _output(args, result.to_dict(), _print_text)


# ---------------------------------------------------------------------------
# index
# ---------------------------------------------------------------------------

def cmd_index():
    parser = argparse.ArgumentParser(prog="shouchao index",
                                     description="Index articles to knowledge base")
    _parse_common_flags(parser)
    parser.add_argument("--directory", "-d", help="Directory to index")
    parser.add_argument("--collection", default="shouchao_news")
    args = parser.parse_args()
    _apply_data_dir(args)
    _setup_logging(args.verbose, args.quiet)

    from shouchao.api import index_news
    result = index_news(directory=args.directory, collection=args.collection)

    def _print_text():
        if result.success:
            print(f"Indexed {result.data.get('indexed', 0)} articles "
                  f"into collection '{result.data.get('collection')}'")
        else:
            print(f"Error: {result.error}")

    _output(args, result.to_dict(), _print_text)


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------

def cmd_sources():
    parser = argparse.ArgumentParser(prog="shouchao sources",
                                     description="List/manage news sources")
    _parse_common_flags(parser)
    parser.add_argument("--language", "-l", help="Filter by language")
    parser.add_argument("--type", "-t", choices=["rss", "web"],
                        dest="source_type", help="Filter by type")
    args = parser.parse_args()
    _apply_data_dir(args)
    _setup_logging(args.verbose, args.quiet)

    from shouchao.api import list_sources
    result = list_sources(language=args.language, source_type=args.source_type)

    def _print_text():
        if result.success:
            sources = result.data.get("sources", [])
            print(f"\n{len(sources)} news sources\n")
            try:
                from rich.console import Console
                from rich.table import Table
                console = Console()
                table = Table(title="News Sources")
                table.add_column("Name", style="cyan")
                table.add_column("Language", style="magenta")
                table.add_column("Type", style="green")
                table.add_column("Categories")
                table.add_column("URL", style="dim")
                for s in sources:
                    table.add_row(
                        s["name"], s["language"], s["source_type"],
                        ", ".join(s.get("category", [])),
                        s["url"][:50],
                    )
                console.print(table)
            except ImportError:
                for s in sources:
                    print(f"  [{s['language']}] {s['name']} ({s['source_type']}) "
                          f"- {', '.join(s.get('category', []))}")
        else:
            print(f"Error: {result.error}")

    _output(args, result.to_dict(), _print_text)


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

def cmd_config():
    parser = argparse.ArgumentParser(prog="shouchao config",
                                     description="View/update configuration")
    _parse_common_flags(parser)
    parser.add_argument("action", nargs="?", default="show",
                        choices=["show", "get", "set"],
                        help="Action: show, get <key>, set <key> <value>")
    parser.add_argument("key", nargs="?", help="Config key")
    parser.add_argument("value", nargs="?", help="Config value")
    args = parser.parse_args()
    _apply_data_dir(args)
    _setup_logging(args.verbose, args.quiet)

    from shouchao.core.config import CONFIG, load_config, save_config
    from dataclasses import asdict
    load_config()

    if args.action == "show" or (args.action == "get" and not args.key):
        data = asdict(CONFIG)
        if args.json_output:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print("\nShouChao Configuration:\n")
            for k, v in data.items():
                print(f"  {k}: {v}")
    elif args.action == "get" and args.key:
        if hasattr(CONFIG, args.key):
            val = getattr(CONFIG, args.key)
            if args.json_output:
                print(json.dumps({args.key: val}))
            else:
                print(f"{args.key}: {val}")
        else:
            print(f"Unknown config key: {args.key}")
            sys.exit(1)
    elif args.action == "set" and args.key and args.value is not None:
        if not hasattr(CONFIG, args.key):
            print(f"Unknown config key: {args.key}")
            sys.exit(1)
        current = getattr(CONFIG, args.key)
        # Type conversion
        if isinstance(current, bool):
            val = args.value.lower() in ("true", "1", "yes")
        elif isinstance(current, int):
            val = int(args.value)
        elif isinstance(current, float):
            val = float(args.value)
        else:
            val = args.value
        setattr(CONFIG, args.key, val)
        save_config()
        print(f"Set {args.key} = {val}")
    else:
        parser.print_help()


# ---------------------------------------------------------------------------
# web
# ---------------------------------------------------------------------------

def cmd_web():
    parser = argparse.ArgumentParser(prog="shouchao web",
                                     description="Start web server")
    _parse_common_flags(parser)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    _apply_data_dir(args)
    _setup_logging(args.verbose, args.quiet)

    from shouchao.core.config import load_config, ensure_dirs
    load_config()
    ensure_dirs()

    banner = f"""
    ╔═══════════════════════════════════════════╗
    ║   ShouChao (手抄) v{__version__:<24s} ║
    ║   Web Information Retrieval Assistant     ║
    ╠═══════════════════════════════════════════╣
    ║   Web: http://{args.host}:{args.port:<21d} ║
    ╚═══════════════════════════════════════════╝
    """
    if not args.quiet:
        print(banner)

    from shouchao.app import create_app
    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)


# ---------------------------------------------------------------------------
# gui
# ---------------------------------------------------------------------------

def cmd_gui():
    parser = argparse.ArgumentParser(prog="shouchao gui",
                                     description="Launch GUI")
    _parse_common_flags(parser)
    args = parser.parse_args()
    _apply_data_dir(args)
    _setup_logging(args.verbose, args.quiet)

    from shouchao.core.config import load_config, ensure_dirs
    load_config()
    ensure_dirs()

    from shouchao.gui import launch_gui
    launch_gui()
