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
                "sources", "config", "web", "gui", "preprint", "schedule"}


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
            "preprint": cmd_preprint,
            "schedule": cmd_schedule,
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
  preprint    Fetch/search preprints (arXiv, bioRxiv, medRxiv)
  schedule    Manage automatic preprint fetching schedule

Examples:
  shouchao fetch --language en --max 10
  shouchao search "AI regulation"
  shouchao briefing --type daily
  shouchao analyze "EU policy impact" --scenario investment
  shouchao sources --language zh
  shouchao preprint fetch --servers arxiv --categories cs.AI,cs.LG
  shouchao preprint search "large language models" --mode keyword
  shouchao schedule enable --time 06:00 --servers arxiv,biorxiv
  shouchao schedule status
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
    
    # Only setup logging for non-JSON output
    if not args.json_output:
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
    parser.add_argument("--force", "-f", action="store_true",
                        help="Force kill process using the port")
    args = parser.parse_args()
    _apply_data_dir(args)
    _setup_logging(args.verbose, args.quiet)

    from shouchao.core.config import load_config, ensure_dirs
    load_config()
    ensure_dirs()

    # Check if port is in use
    if is_port_in_use(args.port):
        if args.force:
            if not args.quiet:
                print(f"⚠️  Port {args.port} is in use, attempting to free it...")
            kill_process_on_port(args.port)
        else:
            print(f"❌ Port {args.port} is already in use.")
            print(f"   Options:")
            print(f"   1. Use a different port: shouchao web --port 5002")
            print(f"   2. Force kill the process: shouchao web --force")
            print(f"   3. Find and kill manually: lsof -ti:{args.port} | xargs kill -9")
            return

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


def is_port_in_use(port: int) -> bool:
    """Check if a port is in use."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def kill_process_on_port(port: int) -> bool:
    """Kill process using the specified port."""
    import subprocess
    import signal
    import os
    
    try:
        # Find PID using the port
        result = subprocess.run(
            f"lsof -ti:{port}",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                try:
                    pid_int = int(pid)
                    os.kill(pid_int, signal.SIGTERM)
                    print(f"  ✓ Terminated process {pid_int}")
                except (ValueError, OSError) as e:
                    print(f"  ⚠ Could not terminate PID {pid}: {e}")
            return True
        else:
            print(f"  ℹ No process found on port {port}")
            return False
    except Exception as e:
        print(f"  ❌ Error killing process: {e}")
        return False


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


# ---------------------------------------------------------------------------
# preprint
# ---------------------------------------------------------------------------

def cmd_preprint():
    """Handle preprint subcommands: fetch, search, categories, index."""
    if len(sys.argv) < 2 or sys.argv[1] not in ("fetch", "search", "categories", "index"):
        print("Usage: shouchao preprint <subcommand>")
        print("Subcommands: fetch, search, categories, index")
        print()
        print("Examples:")
        print("  shouchao preprint fetch --servers arxiv --categories cs.AI,cs.LG")
        print("  shouchao preprint search 'transformer models' --mode keyword")
        print("  shouchao preprint categories --server arxiv")
        print("  shouchao preprint index")
        return

    subcmd = sys.argv.pop(1)  # Remove "preprint" from argv
    sys.argv.pop(0)  # Remove subcommand from argv

    if subcmd == "fetch":
        cmd_preprint_fetch()
    elif subcmd == "search":
        cmd_preprint_search()
    elif subcmd == "categories":
        cmd_preprint_categories()
    elif subcmd == "index":
        cmd_preprint_index()


def cmd_preprint_fetch():
    parser = argparse.ArgumentParser(prog="shouchao preprint fetch",
                                     description="Fetch preprints from arXiv, bioRxiv, medRxiv")
    _parse_common_flags(parser)
    parser.add_argument("--servers", "-s",
                        help="Comma-separated servers (arxiv,biorxiv,medrxiv)")
    parser.add_argument("--categories", "-c",
                        help="Comma-separated categories (e.g., cs.AI,cs.LG)")
    parser.add_argument("--keywords", "-k",
                        help="Comma-separated keywords to filter")
    parser.add_argument("--max", type=int, default=100, dest="max_results",
                        help="Max results per server")
    parser.add_argument("--date-from", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--date-to", help="End date (YYYY-MM-DD)")
    parser.add_argument("--index", action="store_true",
                        help="Index fetched preprints after fetching")
    args = parser.parse_args()
    _apply_data_dir(args)
    _setup_logging(args.verbose, args.quiet)

    from shouchao.api import fetch_preprints

    servers = args.servers.split(",") if args.servers else None
    categories = args.categories.split(",") if args.categories else None
    keywords = args.keywords.split(",") if args.keywords else None

    if not args.quiet:
        print(f"\nFetching preprints...")
        print(f"  Servers: {servers or 'all'}")
        print(f"  Categories: {categories or 'default'}")
        print(f"  Keywords: {keywords or 'none'}")
        print(f"  Max results: {args.max_results}")

    result = fetch_preprints(
        servers=servers,
        categories=categories,
        keywords=keywords,
        max_results=args.max_results,
        date_from=args.date_from,
        date_to=args.date_to,
    )

    def _print_text():
        if result.success:
            data = result.data
            print(f"\nFetched {data['fetched']} preprints, saved {data['saved']}")
            by_source = data.get('by_source', {})
            for server, count in by_source.items():
                print(f"  {server}: {count}")

            if not args.quiet and data.get('preprints'):
                from rich.console import Console
                from rich.table import Table
                console = Console()
                table = Table(title="Fetched Preprints")
                table.add_column("Source", style="cyan")
                table.add_column("Date")
                table.add_column("Title", style="white")
                table.add_column("Categories", style="dim")
                for p in data['preprints'][:30]:
                    table.add_row(
                        p.get("source", ""),
                        p.get("date", ""),
                        p.get("title", "")[:60],
                        ", ".join(p.get("categories", []))[:30],
                    )
                console.print(table)
        else:
            print(f"Error: {result.error}")

    _output(args, result.to_dict(), _print_text)

    # Index if requested
    if args.index and result.success:
        from shouchao.api import index_preprints
        index_result = index_preprints()
        if index_result.success:
            print(f"\nIndexed {index_result.data['indexed']} preprints")


def cmd_preprint_search():
    parser = argparse.ArgumentParser(prog="shouchao preprint search",
                                     description="Search preprints")
    _parse_common_flags(parser)
    parser.add_argument("query", help="Search query")
    parser.add_argument("--mode", "-m", default="keyword",
                        choices=["keyword", "semantic", "model"],
                        help="Search mode: keyword, semantic, or model")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--date-from", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--date-to", help="End date (YYYY-MM-DD)")
    args = parser.parse_args()
    _apply_data_dir(args)
    _setup_logging(args.verbose, args.quiet)

    from shouchao.api import search_preprints

    result = search_preprints(
        query=args.query,
        mode=args.mode,
        top_k=args.top_k,
        date_from=args.date_from,
        date_to=args.date_to,
    )

    def _print_text():
        if result.success:
            data = result.data
            print(f"\nFound {data['count']} results for: {data['query']}")
            print(f"  Mode: {data['mode']}\n")

            for i, r in enumerate(data['results'], 1):
                print(f"{i}. [{r.get('source', '?')}] {r.get('title', 'Untitled')}")
                print(f"   Date: {r.get('date', '?')} | Score: {r.get('score', 0)}")
                if r.get('authors'):
                    print(f"   Authors: {', '.join(r['authors'][:3])}")
                if r.get('categories'):
                    print(f"   Categories: {', '.join(r['categories'])}")
                abstract = r.get('abstract', '')
                if abstract:
                    print(f"   {abstract[:150]}...")
                print()
        else:
            print(f"Error: {result.error}")

    _output(args, result.to_dict(), _print_text)


def cmd_preprint_categories():
    parser = argparse.ArgumentParser(prog="shouchao preprint categories",
                                     description="List preprint categories")
    _parse_common_flags(parser)
    parser.add_argument("--server", "-s",
                        choices=["arxiv", "biorxiv", "medrxiv"],
                        help="Filter by server")
    args = parser.parse_args()
    _apply_data_dir(args)

    from shouchao.api import get_preprint_categories

    result = get_preprint_categories(server=args.server)

    def _print_text():
        if result.success:
            categories = result.data.get('categories', {})
            for server, cats in categories.items():
                print(f"\n{server}:")
                if isinstance(cats, dict):
                    for group, items in cats.items():
                        print(f"  {group}: {', '.join(items)}")
                else:
                    print(f"  {', '.join(cats)}")
        else:
            print(f"Error: {result.error}")

    _output(args, result.to_dict(), _print_text)


def cmd_preprint_index():
    parser = argparse.ArgumentParser(prog="shouchao preprint index",
                                     description="Index preprints to knowledge base")
    _parse_common_flags(parser)
    parser.add_argument("--directory", "-d", help="Directory to index")
    parser.add_argument("--collection", default="preprints")
    args = parser.parse_args()
    _apply_data_dir(args)
    _setup_logging(args.verbose, args.quiet)

    from shouchao.api import index_preprints

    result = index_preprints(
        directory=args.directory,
        collection=args.collection,
    )

    def _print_text():
        if result.success:
            print(f"Indexed {result.data.get('indexed', 0)} preprints "
                  f"into collection '{result.data.get('collection')}'")
        else:
            print(f"Error: {result.error}")

    _output(args, result.to_dict(), _print_text)


# ---------------------------------------------------------------------------
# schedule
# ---------------------------------------------------------------------------

def cmd_schedule():
    """Handle schedule subcommands: enable, disable, status, run."""
    if len(sys.argv) < 2 or sys.argv[1] not in ("enable", "disable", "status", "run"):
        print("Usage: shouchao schedule <subcommand>")
        print("Subcommands: enable, disable, status, run")
        print()
        print("Examples:")
        print("  shouchao schedule enable --time 06:00 --servers arxiv")
        print("  shouchao schedule status")
        print("  shouchao schedule run")
        return

    subcmd = sys.argv.pop(1)
    sys.argv.pop(0)

    if subcmd == "enable":
        cmd_schedule_enable()
    elif subcmd == "disable":
        cmd_schedule_disable()
    elif subcmd == "status":
        cmd_schedule_status()
    elif subcmd == "run":
        cmd_schedule_run()


def cmd_schedule_enable():
    parser = argparse.ArgumentParser(prog="shouchao schedule enable",
                                     description="Enable automatic preprint fetching")
    _parse_common_flags(parser)
    parser.add_argument("--time", "-t", default="06:00",
                        help="Time to run (HH:MM, 24h format)")
    parser.add_argument("--servers", "-s",
                        help="Comma-separated servers")
    parser.add_argument("--categories", "-c",
                        help="Comma-separated categories")
    parser.add_argument("--keywords", "-k",
                        help="Comma-separated keywords")
    parser.add_argument("--max", type=int, default=200, dest="max_results")
    parser.add_argument("--no-index", action="store_true",
                        help="Disable auto-indexing")
    args = parser.parse_args()
    _apply_data_dir(args)

    from shouchao.core.scheduler import enable_scheduler

    servers = args.servers.split(",") if args.servers else None
    categories = args.categories.split(",") if args.categories else None
    keywords = args.keywords.split(",") if args.keywords else None

    enable_scheduler(
        time=args.time,
        servers=servers,
        categories=categories,
        keywords=keywords,
        max_results=args.max_results,
        auto_index=not args.no_index,
    )

    print(f"Scheduler enabled: daily at {args.time}")


def cmd_schedule_disable():
    from shouchao.core.scheduler import disable_scheduler

    disable_scheduler()
    print("Scheduler disabled")


def cmd_schedule_status():
    parser = argparse.ArgumentParser(prog="shouchao schedule status",
                                     description="Show scheduler status")
    _parse_common_flags(parser)
    args = parser.parse_args()
    _apply_data_dir(args)

    from shouchao.core.scheduler import get_scheduler_status

    status = get_scheduler_status()

    def _print_text():
        print("\nPreprint Scheduler Status:")
        print(f"  Enabled: {status['enabled']}")
        print(f"  Running: {status['running']}")
        print(f"  Time: {status['time']}")
        print(f"  Servers: {', '.join(status['servers'])}")
        print(f"  Categories: {', '.join(status['categories'])}")
        if status.get('last_run'):
            print(f"  Last run: {status['last_run']}")
        if status.get('last_status'):
            ls = status['last_status']
            print(f"  Last status: {'Success' if ls.get('success') else 'Failed'}")
            if ls.get('fetched') is not None:
                print(f"    Fetched: {ls['fetched']}, Saved: {ls['saved']}")
            if ls.get('error'):
                print(f"    Error: {ls['error']}")

    _output(args, status, _print_text)


def cmd_schedule_run():
    parser = argparse.ArgumentParser(prog="shouchao schedule run",
                                     description="Run manual preprint fetch")
    _parse_common_flags(parser)
    parser.add_argument("--servers", "-s",
                        help="Comma-separated servers")
    parser.add_argument("--categories", "-c",
                        help="Comma-separated categories")
    parser.add_argument("--keywords", "-k",
                        help="Comma-separated keywords")
    parser.add_argument("--max", type=int, default=200, dest="max_results")
    parser.add_argument("--no-index", action="store_true",
                        help="Disable auto-indexing")
    args = parser.parse_args()
    _apply_data_dir(args)
    _setup_logging(args.verbose, args.quiet)

    from shouchao.core.scheduler import run_manual_fetch

    servers = args.servers.split(",") if args.servers else None
    categories = args.categories.split(",") if args.categories else None
    keywords = args.keywords.split(",") if args.keywords else None

    print("Running manual fetch...")
    result = run_manual_fetch(
        servers=servers,
        categories=categories,
        keywords=keywords,
        max_results=args.max_results,
        auto_index=not args.no_index,
    )

    print(f"\nFetched {result['fetched']} preprints, saved {result['saved']}")
    if result.get('indexed'):
        print(f"Indexed {result['indexed']} preprints")
    by_source = result.get('by_source', {})
    for server, count in by_source.items():
        print(f"  {server}: {count}")
