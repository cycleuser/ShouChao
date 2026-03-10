"""
Tkinter GUI for ShouChao.

Provides a tabbed interface for news browsing, briefings, analysis,
search, and fetching configuration.
"""

import sys
import threading
import logging
import traceback
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def launch_gui():
    """Launch the ShouChao GUI application."""
    logger.info("Initializing GUI...")
    
    # Set up global exception handler for GUI
    def gui_excepthook(exc_type, exc_value, exc_traceback):
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.error(f"GUI Exception:\n{error_msg}")
        import tkinter as tk
        from tkinter import messagebox
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Error", f"An error occurred:\n{exc_value}")
        except Exception:
            pass
    
    sys.excepthook = gui_excepthook
    
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox, filedialog

    from shouchao import __version__
    from shouchao.core.config import CONFIG, load_config, save_config, ensure_dirs
    from shouchao.i18n import t, LANGUAGES

    load_config()
    ensure_dirs()

    root = tk.Tk()
    root.title(f"ShouChao (手抄) v{__version__}")
    root.geometry("1100x750")
    root.minsize(800, 600)

    # Try to set a reasonable font for CJK
    default_font = ("TkDefaultFont", 10)
    mono_font = ("Courier", 10)
    for family in ("Noto Sans CJK", "Microsoft YaHei", "PingFang SC",
                   "Hiragino Sans", "WenQuanYi Micro Hei", "Arial Unicode MS"):
        try:
            tk.font.Font(family=family)
            default_font = (family, 10)
            break
        except Exception:
            continue
    for family in ("Noto Sans Mono CJK", "Consolas", "DejaVu Sans Mono",
                   "Courier New"):
        try:
            tk.font.Font(family=family)
            mono_font = (family, 10)
            break
        except Exception:
            continue

    # Status bar
    status_var = tk.StringVar(value=t("ready"))
    status_bar = ttk.Label(root, textvariable=status_var, relief="sunken",
                           anchor="w", padding=5)
    status_bar.pack(side="bottom", fill="x")

    def set_status(msg):
        status_var.set(msg)
        root.update_idletasks()

    # Notebook
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=5, pady=5)

    # ===== Tab 1: News Feed =====
    news_frame = ttk.Frame(notebook)
    notebook.add(news_frame, text=f" {t('fetch_news')} ")

    # Filter bar
    filter_frame = ttk.Frame(news_frame)
    filter_frame.pack(fill="x", padx=5, pady=5)

    ttk.Label(filter_frame, text=t("language_label") + ":").pack(side="left")
    lang_var = tk.StringVar(value="all")
    lang_combo = ttk.Combobox(filter_frame, textvariable=lang_var,
                               values=["all"] + list(LANGUAGES.keys()),
                               width=8, state="readonly")
    lang_combo.pack(side="left", padx=5)

    ttk.Label(filter_frame, text="Date:").pack(side="left", padx=(10, 0))
    date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
    date_entry = ttk.Entry(filter_frame, textvariable=date_var, width=12)
    date_entry.pack(side="left", padx=5)

    refresh_btn = ttk.Button(filter_frame, text=t("search"))
    refresh_btn.pack(side="left", padx=10)

    # Paned: tree + viewer
    news_paned = ttk.PanedWindow(news_frame, orient="horizontal")
    news_paned.pack(fill="both", expand=True, padx=5, pady=5)

    tree_frame = ttk.Frame(news_paned)
    news_tree = ttk.Treeview(tree_frame,
                              columns=("date", "source", "lang", "title"),
                              show="headings", height=20)
    news_tree.heading("date", text="Date")
    news_tree.heading("source", text="Source")
    news_tree.heading("lang", text="Lang")
    news_tree.heading("title", text="Title")
    news_tree.column("date", width=90)
    news_tree.column("source", width=100)
    news_tree.column("lang", width=40)
    news_tree.column("title", width=300)
    tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical",
                                 command=news_tree.yview)
    news_tree.configure(yscrollcommand=tree_scroll.set)
    news_tree.pack(side="left", fill="both", expand=True)
    tree_scroll.pack(side="right", fill="y")
    news_paned.add(tree_frame, weight=1)

    viewer_frame = ttk.Frame(news_paned)
    article_viewer = scrolledtext.ScrolledText(
        viewer_frame, wrap="word", font=mono_font, state="disabled",
    )
    article_viewer.pack(fill="both", expand=True)
    news_paned.add(viewer_frame, weight=1)

    def _load_articles():
        lang = lang_var.get()
        lang_filter = None if lang == "all" else lang
        logger.debug(f"GUI: Loading articles (lang={lang_filter})")
        from shouchao.core.storage import ArticleStorage
        storage = ArticleStorage()
        articles = storage.list_articles(language=lang_filter)
        logger.debug(f"GUI: Loaded {len(articles)} articles")
        news_tree.delete(*news_tree.get_children())
        for a in articles[:500]:
            news_tree.insert("", "end", values=(
                a.get("date", ""), a.get("website", ""),
                a.get("language", ""), a.get("title", ""),
            ), tags=(a.get("path", ""),))

    def _on_article_select(event):
        sel = news_tree.selection()
        if not sel:
            return
        tags = news_tree.item(sel[0], "tags")
        if tags:
            path = tags[0]
            try:
                content = Path(path).read_text(encoding="utf-8")
                article_viewer.config(state="normal")
                article_viewer.delete("1.0", "end")
                article_viewer.insert("1.0", content)
                article_viewer.config(state="disabled")
            except Exception as e:
                set_status(f"Error: {e}")

    news_tree.bind("<<TreeviewSelect>>", _on_article_select)
    refresh_btn.config(command=_load_articles)

    # ===== Tab 2: Briefing =====
    briefing_frame = ttk.Frame(notebook)
    notebook.add(briefing_frame, text=f" {t('news_briefing')} ")

    brief_ctrl = ttk.Frame(briefing_frame)
    brief_ctrl.pack(fill="x", padx=5, pady=5)

    brief_type_var = tk.StringVar(value="daily")
    ttk.Radiobutton(brief_ctrl, text=t("daily_briefing"),
                     variable=brief_type_var, value="daily").pack(side="left")
    ttk.Radiobutton(brief_ctrl, text=t("weekly_briefing"),
                     variable=brief_type_var, value="weekly").pack(side="left", padx=10)

    brief_lang_var = tk.StringVar(value=CONFIG.language)
    ttk.Label(brief_ctrl, text=t("language_label") + ":").pack(side="left", padx=(20, 5))
    ttk.Combobox(brief_ctrl, textvariable=brief_lang_var,
                  values=list(LANGUAGES.keys()), width=6,
                  state="readonly").pack(side="left")

    gen_brief_btn = ttk.Button(brief_ctrl, text=t("generating_briefing").replace("...", ""))
    gen_brief_btn.pack(side="left", padx=20)

    export_brief_btn = ttk.Button(brief_ctrl, text=t("export"))
    export_brief_btn.pack(side="left")

    brief_text = scrolledtext.ScrolledText(briefing_frame, wrap="word",
                                            font=mono_font)
    brief_text.pack(fill="both", expand=True, padx=5, pady=5)

    def _generate_briefing():
        set_status(t("generating_briefing"))
        gen_brief_btn.config(state="disabled")
        brief_text.delete("1.0", "end")

        def _run():
            try:
                from shouchao.api import generate_briefing
                result = generate_briefing(
                    briefing_type=brief_type_var.get(),
                    language=brief_lang_var.get(),
                )
                content = result.data.get("content", "") if result.success else f"Error: {result.error}"
                root.after(0, lambda: brief_text.insert("1.0", content))
            except Exception as e:
                root.after(0, lambda: brief_text.insert("1.0", f"Error: {e}"))
            finally:
                root.after(0, lambda: gen_brief_btn.config(state="normal"))
                root.after(0, lambda: set_status(t("ready")))

        threading.Thread(target=_run, daemon=True).start()

    gen_brief_btn.config(command=_generate_briefing)

    def _export_briefing():
        content = brief_text.get("1.0", "end").strip()
        if not content:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("All files", "*.*")],
        )
        if path:
            Path(path).write_text(content, encoding="utf-8")
            set_status(f"Exported to {path}")

    export_brief_btn.config(command=_export_briefing)

    # ===== Tab 3: Analysis =====
    analysis_frame = ttk.Frame(notebook)
    notebook.add(analysis_frame, text=f" {t('general_analysis')} ")

    analysis_ctrl = ttk.Frame(analysis_frame)
    analysis_ctrl.pack(fill="x", padx=5, pady=5)

    scenario_var = tk.StringVar(value="general")
    for scenario, label_key in [("general", "general_analysis"),
                                 ("investment", "investment_analysis"),
                                 ("immigration", "immigration_analysis"),
                                 ("study_abroad", "study_abroad_analysis")]:
        ttk.Radiobutton(analysis_ctrl, text=t(label_key),
                         variable=scenario_var, value=scenario).pack(side="left", padx=5)

    query_frame = ttk.Frame(analysis_frame)
    query_frame.pack(fill="x", padx=5, pady=5)
    ttk.Label(query_frame, text="Query:").pack(side="left")
    query_var = tk.StringVar()
    query_entry = ttk.Entry(query_frame, textvariable=query_var)
    query_entry.pack(side="left", fill="x", expand=True, padx=5)

    analyze_btn = ttk.Button(query_frame, text=t("analyzing").replace("...", ""))
    analyze_btn.pack(side="left")

    analysis_text = scrolledtext.ScrolledText(analysis_frame, wrap="word",
                                               font=mono_font)
    analysis_text.pack(fill="both", expand=True, padx=5, pady=5)

    def _run_analysis():
        query = query_var.get().strip()
        if not query:
            messagebox.showwarning("Warning", "Enter a query first")
            return
        set_status(t("analyzing"))
        analyze_btn.config(state="disabled")
        analysis_text.delete("1.0", "end")

        def _run():
            try:
                from shouchao.api import analyze_news
                result = analyze_news(
                    query=query,
                    scenario=scenario_var.get(),
                )
                content = result.data.get("content", "") if result.success else f"Error: {result.error}"
                root.after(0, lambda: analysis_text.insert("1.0", content))
            except Exception as e:
                root.after(0, lambda: analysis_text.insert("1.0", f"Error: {e}"))
            finally:
                root.after(0, lambda: analyze_btn.config(state="normal"))
                root.after(0, lambda: set_status(t("ready")))

        threading.Thread(target=_run, daemon=True).start()

    analyze_btn.config(command=_run_analysis)
    query_entry.bind("<Return>", lambda e: _run_analysis())

    # ===== Tab 4: Search =====
    search_frame = ttk.Frame(notebook)
    notebook.add(search_frame, text=f" {t('search')} ")

    search_ctrl = ttk.Frame(search_frame)
    search_ctrl.pack(fill="x", padx=5, pady=5)
    ttk.Label(search_ctrl, text=t("search") + ":").pack(side="left")
    search_var = tk.StringVar()
    search_entry = ttk.Entry(search_ctrl, textvariable=search_var)
    search_entry.pack(side="left", fill="x", expand=True, padx=5)
    search_btn = ttk.Button(search_ctrl, text=t("search"))
    search_btn.pack(side="left")

    search_paned = ttk.PanedWindow(search_frame, orient="horizontal")
    search_paned.pack(fill="both", expand=True, padx=5, pady=5)

    search_results_frame = ttk.Frame(search_paned)
    search_tree = ttk.Treeview(
        search_results_frame,
        columns=("score", "source", "title"),
        show="headings", height=15,
    )
    search_tree.heading("score", text="Score")
    search_tree.heading("source", text="Source")
    search_tree.heading("title", text="Title")
    search_tree.column("score", width=60)
    search_tree.column("source", width=100)
    search_tree.column("title", width=300)
    search_tree.pack(fill="both", expand=True)
    search_paned.add(search_results_frame, weight=1)

    search_preview = scrolledtext.ScrolledText(search_paned, wrap="word",
                                                font=mono_font, state="disabled")
    search_paned.add(search_preview, weight=1)

    _search_results = []

    def _do_search():
        nonlocal _search_results
        query = search_var.get().strip()
        if not query:
            return
        set_status(t("search") + "...")
        search_btn.config(state="disabled")
        search_tree.delete(*search_tree.get_children())

        def _run():
            nonlocal _search_results
            from shouchao.api import search_news
            result = search_news(query=query, top_k=20)
            _search_results = result.data.get("results", []) if result.success else []

            def _update():
                for r in _search_results:
                    meta = r.get("metadata", {})
                    dist = r.get("distance", 0)
                    score = f"{1 - dist:.2f}" if dist < 2 else "0.00"
                    search_tree.insert("", "end", values=(
                        score, meta.get("website", ""),
                        meta.get("title", ""),
                    ))
                search_btn.config(state="normal")
                set_status(f"Found {len(_search_results)} results")

            root.after(0, _update)

        threading.Thread(target=_run, daemon=True).start()

    search_btn.config(command=_do_search)
    search_entry.bind("<Return>", lambda e: _do_search())

    def _on_search_select(event):
        sel = search_tree.selection()
        if not sel:
            return
        idx = search_tree.index(sel[0])
        if idx < len(_search_results):
            doc = _search_results[idx].get("document", "")
            search_preview.config(state="normal")
            search_preview.delete("1.0", "end")
            search_preview.insert("1.0", doc)
            search_preview.config(state="disabled")

    search_tree.bind("<<TreeviewSelect>>", _on_search_select)

    # ===== Tab 5: Fetch =====
    fetch_frame = ttk.Frame(notebook)
    notebook.add(fetch_frame, text=f" {t('fetching_progress').split('...')[0]} ")

    fetch_ctrl = ttk.Frame(fetch_frame)
    fetch_ctrl.pack(fill="x", padx=5, pady=5)

    ttk.Label(fetch_ctrl, text=t("language_label") + ":").pack(side="left")
    fetch_lang_var = tk.StringVar(value="en")
    ttk.Combobox(fetch_ctrl, textvariable=fetch_lang_var,
                  values=list(LANGUAGES.keys()), width=6,
                  state="readonly").pack(side="left", padx=5)

    ttk.Label(fetch_ctrl, text="Max:").pack(side="left", padx=(10, 5))
    fetch_max_var = tk.StringVar(value="10")
    ttk.Entry(fetch_ctrl, textvariable=fetch_max_var, width=5).pack(side="left")

    ttk.Label(fetch_ctrl, text="Fetcher:").pack(side="left", padx=(10, 5))
    fetch_type_var = tk.StringVar(value="requests")
    ttk.Combobox(fetch_ctrl, textvariable=fetch_type_var,
                  values=["requests", "curl", "browser", "playwright"],
                  width=10, state="readonly").pack(side="left")

    fetch_btn = ttk.Button(fetch_ctrl, text=t("fetch_news"))
    fetch_btn.pack(side="left", padx=20)

    fetch_progress = ttk.Progressbar(fetch_frame, mode="indeterminate")
    fetch_progress.pack(fill="x", padx=5, pady=5)

    fetch_log = scrolledtext.ScrolledText(fetch_frame, wrap="word",
                                           font=mono_font, height=20)
    fetch_log.pack(fill="both", expand=True, padx=5, pady=5)

    def _do_fetch():
        set_status(t("fetching_progress"))
        fetch_btn.config(state="disabled")
        fetch_progress.start()
        fetch_log.delete("1.0", "end")

        def _run():
            try:
                from shouchao.api import fetch_news
                result = fetch_news(
                    language=fetch_lang_var.get(),
                    max_articles=int(fetch_max_var.get()),
                    fetcher=fetch_type_var.get(),
                )
                if result.success:
                    articles = result.data.get("articles", [])
                    msg = f"Fetched {len(articles)} articles\n\n"
                    for a in articles:
                        msg += f"[{a.get('language')}] {a.get('source')}: {a.get('title', '')}\n"
                else:
                    msg = f"Error: {result.error}\n"
                root.after(0, lambda: fetch_log.insert("1.0", msg))
            except Exception as e:
                root.after(0, lambda: fetch_log.insert("1.0", f"Error: {e}\n"))
            finally:
                root.after(0, lambda: fetch_progress.stop())
                root.after(0, lambda: fetch_btn.config(state="normal"))
                root.after(0, lambda: set_status(t("ready")))

        threading.Thread(target=_run, daemon=True).start()

    fetch_btn.config(command=_do_fetch)

    # ===== Settings menu (top menu bar) =====
    menubar = tk.Menu(root)
    root.config(menu=menubar)

    settings_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label=t("settings"), menu=settings_menu)

    def _open_settings():
        win = tk.Toplevel(root)
        win.title(t("settings"))
        win.geometry("500x450")
        win.transient(root)

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill="both", expand=True)

        entries = {}
        row = 0

        # --- Ollama URL (text entry) ---
        ttk.Label(frame, text=t("ollama_url") + ":").grid(row=row, column=0, sticky="w", pady=3)
        var_ollama_url = tk.StringVar(value=str(CONFIG.ollama_url))
        ttk.Entry(frame, textvariable=var_ollama_url, width=35).grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        entries["ollama_url"] = var_ollama_url
        row += 1

        # --- Chat Model (combobox, dynamically populated) ---
        ttk.Label(frame, text=t("model") + " (Chat):").grid(row=row, column=0, sticky="w", pady=3)
        var_chat_model = tk.StringVar(value=str(CONFIG.chat_model))
        chat_combo = ttk.Combobox(frame, textvariable=var_chat_model, width=33)
        chat_combo.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        entries["chat_model"] = var_chat_model
        row += 1

        # --- Embedding Model (combobox, dynamically populated) ---
        ttk.Label(frame, text=t("model") + " (Embed):").grid(row=row, column=0, sticky="w", pady=3)
        var_embed_model = tk.StringVar(value=str(CONFIG.embedding_model))
        embed_combo = ttk.Combobox(frame, textvariable=var_embed_model, width=33)
        embed_combo.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        entries["embedding_model"] = var_embed_model
        row += 1

        # --- Refresh Models button ---
        def _refresh_models():
            def _fetch():
                try:
                    from shouchao.core.ollama_client import OllamaClient
                    client = OllamaClient(var_ollama_url.get())
                    chat_models = client.get_chat_models()
                    embed_models = client.get_embedding_models()
                    root.after(0, lambda: chat_combo.config(values=chat_models))
                    root.after(0, lambda: embed_combo.config(values=embed_models))
                    root.after(0, lambda: set_status(f"Found {len(chat_models)} chat, {len(embed_models)} embedding models"))
                except Exception as e:
                    root.after(0, lambda: set_status(f"Failed to fetch models: {e}"))
            threading.Thread(target=_fetch, daemon=True).start()

        ttk.Button(frame, text="Refresh Models", command=_refresh_models).grid(row=row, column=1, sticky="w", padx=5, pady=3)
        row += 1

        # --- Language (readonly combobox) ---
        ttk.Label(frame, text=t("language_label") + ":").grid(row=row, column=0, sticky="w", pady=3)
        var_language = tk.StringVar(value=str(CONFIG.language))
        ttk.Combobox(frame, textvariable=var_language, values=list(LANGUAGES.keys()),
                      width=33, state="readonly").grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        entries["language"] = var_language
        row += 1

        # --- Fetch Delay (text entry) ---
        ttk.Label(frame, text="Fetch Delay (s):").grid(row=row, column=0, sticky="w", pady=3)
        var_fetch_delay = tk.StringVar(value=str(CONFIG.fetch_delay))
        ttk.Entry(frame, textvariable=var_fetch_delay, width=35).grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        entries["fetch_delay"] = var_fetch_delay
        row += 1

        # --- Default Fetcher (readonly combobox) ---
        ttk.Label(frame, text="Default Fetcher:").grid(row=row, column=0, sticky="w", pady=3)
        var_fetcher = tk.StringVar(value=str(CONFIG.default_fetcher))
        ttk.Combobox(frame, textvariable=var_fetcher,
                      values=["requests", "curl", "browser", "playwright"],
                      width=33, state="readonly").grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        entries["default_fetcher"] = var_fetcher
        row += 1

        # --- Proxy Mode (readonly combobox) ---
        ttk.Label(frame, text=t("proxy") + " Mode:").grid(row=row, column=0, sticky="w", pady=3)
        var_proxy_mode = tk.StringVar(value=str(CONFIG.proxy_mode))
        ttk.Combobox(frame, textvariable=var_proxy_mode,
                      values=["none", "system", "manual"],
                      width=33, state="readonly").grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        entries["proxy_mode"] = var_proxy_mode
        row += 1

        # --- Proxy HTTP (text entry) ---
        ttk.Label(frame, text=t("proxy") + " HTTP:").grid(row=row, column=0, sticky="w", pady=3)
        var_proxy_http = tk.StringVar(value=str(CONFIG.proxy_http))
        ttk.Entry(frame, textvariable=var_proxy_http, width=35).grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        entries["proxy_http"] = var_proxy_http
        row += 1

        # --- Proxy HTTPS (text entry) ---
        ttk.Label(frame, text=t("proxy") + " HTTPS:").grid(row=row, column=0, sticky="w", pady=3)
        var_proxy_https = tk.StringVar(value=str(CONFIG.proxy_https))
        ttk.Entry(frame, textvariable=var_proxy_https, width=35).grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        entries["proxy_https"] = var_proxy_https
        row += 1

        frame.columnconfigure(1, weight=1)

        # Auto-fetch models on dialog open
        _refresh_models()

        def _save():
            for field, var in entries.items():
                val = var.get()
                current = getattr(CONFIG, field, "")
                if isinstance(current, float):
                    val = float(val)
                elif isinstance(current, int):
                    val = int(val)
                setattr(CONFIG, field, val)
            save_config()
            set_status("Settings saved")
            win.destroy()

        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill="x", padx=10, pady=10)
        ttk.Button(btn_frame, text=t("save"), command=_save).pack(side="right", padx=5)
        ttk.Button(btn_frame, text=t("cancel"), command=win.destroy).pack(side="right")

    settings_menu.add_command(label=t("settings") + "...", command=_open_settings)

    # Load articles on startup
    root.after(100, _load_articles)

    root.mainloop()
