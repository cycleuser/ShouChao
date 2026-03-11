"""
Tkinter GUI for ShouChao with workflow-based interface.

Steps:
1. Model Settings - Configure Ollama and proxy
2. Fetch News - Select languages and fetch news
3. Content Search - Search local news and web
4. Generate Briefing - AI summarize in any language
5. TTS Playback - Convert briefing to audio
"""

import os
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
    
    sys.excepthook = lambda t, v, tb: logger.error(''.join(traceback.format_exception(t, v, tb)))
    
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox
    
    from shouchao import __version__
    from shouchao.core.config import CONFIG, load_config, save_config, ensure_dirs
    from shouchao.i18n import LANGUAGES

    load_config()
    ensure_dirs()

    root = tk.Tk()
    root.title(f"ShouChao (手抄) v{__version__}")
    root.geometry("1000x700")
    root.minsize(800, 600)

    # Main container
    main_frame = ttk.Frame(root)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Step indicator frame
    steps_frame = ttk.Frame(main_frame)
    steps_frame.pack(fill="x", pady=(0, 10))

    current_step = tk.IntVar(value=1)
    step_names = ["模型设置", "抓取新闻", "内容搜索", "生成简报", "TTS播报"]

    for i, name in enumerate(step_names):
        btn = ttk.Radiobutton(
            steps_frame, text=f"{i+1}. {name}",
            variable=current_step, value=i+1,
            command=lambda s=i+1: show_step(s)
        )
        btn.pack(side="left", padx=10)

    # Content frames
    content_frame = ttk.Frame(main_frame)
    content_frame.pack(fill="both", expand=True)

    step_frames = {}
    
    # ============ Step 1: Model Settings ============
    step1 = ttk.Frame(content_frame)
    step_frames[1] = step1

    # Ollama settings
    ollama_frame = ttk.LabelFrame(step1, text="Ollama 模型设置", padding=10)
    ollama_frame.pack(fill="x", pady=5)

    ttk.Label(ollama_frame, text="服务地址:").grid(row=0, column=0, sticky="w", pady=3)
    ollama_url_var = tk.StringVar(value=CONFIG.ollama_url)
    ttk.Entry(ollama_frame, textvariable=ollama_url_var, width=40).grid(row=0, column=1, padx=5, pady=3)
    ttk.Button(ollama_frame, text="测试连接", command=lambda: test_ollama()).grid(row=0, column=2, padx=5)

    ttk.Label(ollama_frame, text="聊天模型:").grid(row=1, column=0, sticky="w", pady=3)
    chat_model_var = tk.StringVar(value=CONFIG.chat_model)
    chat_model_combo = ttk.Combobox(ollama_frame, textvariable=chat_model_var, width=38)
    chat_model_combo.grid(row=1, column=1, padx=5, pady=3)

    ttk.Label(ollama_frame, text="嵌入模型:").grid(row=2, column=0, sticky="w", pady=3)
    embed_model_var = tk.StringVar(value=CONFIG.embedding_model)
    embed_model_combo = ttk.Combobox(ollama_frame, textvariable=embed_model_var, width=38)
    embed_model_combo.grid(row=2, column=1, padx=5, pady=3)

    ttk.Button(ollama_frame, text="刷新模型", command=lambda: load_models()).grid(row=3, column=1, sticky="w", pady=5)

    # Proxy settings
    proxy_frame = ttk.LabelFrame(step1, text="代理设置", padding=10)
    proxy_frame.pack(fill="x", pady=5)

    ttk.Label(proxy_frame, text="代理模式:").grid(row=0, column=0, sticky="w", pady=3)
    proxy_mode_var = tk.StringVar(value=CONFIG.proxy_mode)
    ttk.Combobox(proxy_frame, textvariable=proxy_mode_var, 
                  values=["none", "system", "manual"], width=15, state="readonly").grid(row=0, column=1, padx=5, pady=3)

    ttk.Label(proxy_frame, text="HTTP代理:").grid(row=1, column=0, sticky="w", pady=3)
    proxy_http_var = tk.StringVar(value=CONFIG.proxy_http)
    ttk.Entry(proxy_frame, textvariable=proxy_http_var, width=20).grid(row=1, column=1, padx=5, pady=3)

    ttk.Label(proxy_frame, text="HTTPS代理:").grid(row=1, column=2, sticky="w", padx=(20, 5))
    proxy_https_var = tk.StringVar(value=CONFIG.proxy_https)
    ttk.Entry(proxy_frame, textvariable=proxy_https_var, width=20).grid(row=1, column=3, padx=5, pady=3)

    # Status
    step1_status = ttk.Label(step1, text="")
    step1_status.pack(fill="x", pady=10)

    ttk.Button(step1, text="保存并继续 →", command=lambda: save_step1()).pack(pady=10)

    # ============ Step 2: Fetch News ============
    step2 = ttk.Frame(content_frame)
    step_frames[2] = step2

    # Language selection
    lang_frame = ttk.LabelFrame(step2, text="选择新闻语言", padding=10)
    lang_frame.pack(fill="x", pady=5)

    lang_vars = {}
    for i, (code, name) in enumerate(LANGUAGES.items()):
        var = tk.BooleanVar()
        lang_vars[code] = var
        cb = ttk.Checkbutton(lang_frame, text=name, variable=var)
        cb.grid(row=i//5, column=i%5, sticky="w", padx=5, pady=3)

    # Fetch settings
    fetch_frame = ttk.LabelFrame(step2, text="抓取设置", padding=10)
    fetch_frame.pack(fill="x", pady=5)

    ttk.Label(fetch_frame, text="每源最大文章:").grid(row=0, column=0, sticky="w")
    max_articles_var = tk.StringVar(value="20")
    ttk.Entry(fetch_frame, textvariable=max_articles_var, width=10).grid(row=0, column=1, padx=5)

    ttk.Label(fetch_frame, text="抓取方式:").grid(row=0, column=2, padx=(20, 5))
    fetcher_var = tk.StringVar(value="requests")
    ttk.Combobox(fetch_frame, textvariable=fetcher_var, 
                  values=["requests", "curl", "browser"], width=12, state="readonly").grid(row=0, column=3)

    # Stats display
    stats_frame = ttk.LabelFrame(step2, text="统计信息", padding=10)
    stats_frame.pack(fill="x", pady=5)

    stats_labels = {}
    for i, (key, label) in enumerate([("total", "总文章"), ("sources", "来源"), ("indexed", "已索引")]):
        ttk.Label(stats_frame, text=f"{label}:").grid(row=0, column=i*2, padx=5)
        stats_labels[key] = ttk.Label(stats_frame, text="0")
        stats_labels[key].grid(row=0, column=i*2+1, padx=5)

    # Fetch log
    fetch_log = scrolledtext.ScrolledText(step2, height=8)
    fetch_log.pack(fill="both", expand=True, pady=5)

    btn_frame2 = ttk.Frame(step2)
    btn_frame2.pack(fill="x", pady=5)
    ttk.Button(btn_frame2, text="← 上一步", command=lambda: show_step(1)).pack(side="left", padx=5)
    ttk.Button(btn_frame2, text="📥 抓取新闻", command=lambda: fetch_news()).pack(side="left", padx=5)
    ttk.Button(btn_frame2, text="🔍 建立索引", command=lambda: index_news()).pack(side="left", padx=5)
    ttk.Button(btn_frame2, text="继续 →", command=lambda: show_step(3)).pack(side="right", padx=5)

    # ============ Step 3: Content Search ============
    step3 = ttk.Frame(content_frame)
    step_frames[3] = step3

    search_frame = ttk.Frame(step3)
    search_frame.pack(fill="x", pady=5)

    ttk.Label(search_frame, text="搜索:").pack(side="left")
    search_query_var = tk.StringVar()
    ttk.Entry(search_frame, textvariable=search_query_var, width=50).pack(side="left", fill="x", expand=True, padx=5)
    ttk.Button(search_frame, text="🔍 搜索", command=lambda: do_search()).pack(side="left")

    # Search options
    search_opts = ttk.Frame(step3)
    search_opts.pack(fill="x", pady=5)
    
    ttk.Label(search_opts, text="类型:").pack(side="left")
    search_type_var = tk.StringVar(value="local")
    ttk.Combobox(search_opts, textvariable=search_type_var, 
                  values=["local", "web", "both"], width=8, state="readonly").pack(side="left", padx=5)

    ttk.Label(search_opts, text="引擎:").pack(side="left", padx=(20, 5))
    search_engine_var = tk.StringVar(value="duckduckgo")
    ttk.Combobox(search_opts, textvariable=search_engine_var,
                  values=["duckduckgo", "google", "bing", "brave"], width=12, state="readonly").pack(side="left")

    # Results list
    results_frame = ttk.LabelFrame(step3, text="搜索结果", padding=10)
    results_frame.pack(fill="both", expand=True, pady=5)

    results_tree = ttk.Treeview(results_frame, columns=("title", "source", "date"), show="headings", height=10)
    results_tree.heading("title", text="标题")
    results_tree.heading("source", text="来源")
    results_tree.heading("date", text="日期")
    results_tree.column("title", width=400)
    results_tree.column("source", width=150)
    results_tree.column("date", width=100)
    results_tree.pack(fill="both", expand=True)

    # Selected content
    selected_frame = ttk.LabelFrame(step3, text="已选内容", padding=10)
    selected_frame.pack(fill="both", expand=True, pady=5)

    selected_items = []
    selected_text = scrolledtext.ScrolledText(selected_frame, height=6)
    selected_text.pack(fill="both", expand=True)

    btn_frame3 = ttk.Frame(step3)
    btn_frame3.pack(fill="x", pady=5)
    ttk.Button(btn_frame3, text="← 上一步", command=lambda: show_step(2)).pack(side="left", padx=5)
    ttk.Button(btn_frame3, text="添加选中", command=lambda: add_selected()).pack(side="left", padx=5)
    ttk.Button(btn_frame3, text="清空", command=lambda: clear_selected()).pack(side="left", padx=5)
    ttk.Button(btn_frame3, text="继续 →", command=lambda: show_step(4)).pack(side="right", padx=5)

    # ============ Step 4: Generate Briefing ============
    step4 = ttk.Frame(content_frame)
    step_frames[4] = step4

    opts_frame4 = ttk.Frame(step4)
    opts_frame4.pack(fill="x", pady=5)

    ttk.Label(opts_frame4, text="输出语言:").pack(side="left")
    output_lang_var = tk.StringVar(value=CONFIG.language)
    ttk.Combobox(opts_frame4, textvariable=output_lang_var,
                  values=list(LANGUAGES.keys()), width=10, state="readonly").pack(side="left", padx=5)

    ttk.Label(opts_frame4, text="风格:").pack(side="left", padx=(20, 5))
    style_var = tk.StringVar(value="story")
    ttk.Combobox(opts_frame4, textvariable=style_var,
                  values=["brief", "detailed", "bullet", "executive", "story"], width=12, state="readonly").pack(side="left")

    briefing_output = scrolledtext.ScrolledText(step4, height=20)
    briefing_output.pack(fill="both", expand=True, pady=5)

    btn_frame4 = ttk.Frame(step4)
    btn_frame4.pack(fill="x", pady=5)
    ttk.Button(btn_frame4, text="← 上一步", command=lambda: show_step(3)).pack(side="left", padx=5)
    ttk.Button(btn_frame4, text="✨ 生成简报", command=lambda: generate_briefing()).pack(side="left", padx=5)
    ttk.Button(btn_frame4, text="继续 →", command=lambda: show_step(5)).pack(side="right", padx=5)

    # ============ Step 5: TTS Playback ============
    step5 = ttk.Frame(content_frame)
    step_frames[5] = step5

    tts_opts = ttk.Frame(step5)
    tts_opts.pack(fill="x", pady=5)

    ttk.Label(tts_opts, text="TTS引擎:").pack(side="left")
    tts_engine_var = tk.StringVar(value="edge-tts")
    ttk.Combobox(tts_opts, textvariable=tts_engine_var,
                  values=["edge-tts", "gtts", "pyttsx3"], width=10, state="readonly").pack(side="left", padx=5)

    ttk.Label(tts_opts, text="语音:").pack(side="left", padx=(20, 5))
    tts_voice_var = tk.StringVar()
    tts_voice_combo = ttk.Combobox(tts_opts, textvariable=tts_voice_var, width=30)
    tts_voice_combo.pack(side="left", padx=5)

    ttk.Label(tts_opts, text="语速:").pack(side="left", padx=(20, 5))
    tts_speed_var = tk.StringVar(value="1.0")
    ttk.Combobox(tts_opts, textvariable=tts_speed_var,
                  values=["0.5", "0.75", "1.0", "1.25", "1.5", "2.0"], width=5, state="readonly").pack(side="left")

    tts_input = scrolledtext.ScrolledText(step5, height=10)
    tts_input.pack(fill="both", expand=True, pady=5)

    btn_frame5 = ttk.Frame(step5)
    btn_frame5.pack(fill="x", pady=5)
    ttk.Button(btn_frame5, text="← 上一步", command=lambda: show_step(4)).pack(side="left", padx=5)
    ttk.Button(btn_frame5, text="🔊 生成音频", command=lambda: generate_audio()).pack(side="left", padx=5)
    ttk.Button(btn_frame5, text="🔄 重新开始", command=lambda: start_over()).pack(side="right", padx=5)

    # ============ Functions ============
    def show_step(step):
        for i, frame in step_frames.items():
            frame.pack_forget()
        step_frames[step].pack(fill="both", expand=True)
        current_step.set(step)
        
        if step == 2:
            update_stats()
        if step == 4:
            update_briefing_input()
        if step == 5:
            load_tts_voices()

    def test_ollama():
        from shouchao.core.ollama_client import OllamaClient
        client = OllamaClient(ollama_url_var.get())
        if client.is_available():
            step1_status.config(text="✓ 连接成功", foreground="green")
        else:
            step1_status.config(text="✗ 连接失败", foreground="red")

    def load_models():
        from shouchao.core.ollama_client import OllamaClient
        client = OllamaClient(ollama_url_var.get())
        chat_model_combo['values'] = client.get_chat_models()
        embed_model_combo['values'] = client.get_embedding_models()

    def save_step1():
        CONFIG.ollama_url = ollama_url_var.get()
        CONFIG.chat_model = chat_model_var.get()
        CONFIG.embedding_model = embed_model_var.get()
        CONFIG.proxy_mode = proxy_mode_var.get()
        CONFIG.proxy_http = proxy_http_var.get()
        CONFIG.proxy_https = proxy_https_var.get()
        save_config()
        show_step(2)

    def update_stats():
        from shouchao.core.storage import ArticleStorage
        from shouchao.core.sources import get_sources
        from shouchao.core.indexer import NewsIndexer
        from shouchao.core.ollama_client import OllamaClient
        
        storage = ArticleStorage()
        counts = storage.count_articles()
        stats_labels["total"].config(text=str(counts.get("total", 0)))
        stats_labels["sources"].config(text=str(len(get_sources())))
        
        try:
            client = OllamaClient(CONFIG.ollama_url)
            indexer = NewsIndexer(client)
            stats_labels["indexed"].config(text=str(indexer.get_document_count()))
        except:
            stats_labels["indexed"].config(text="0")

    def fetch_news():
        langs = [code for code, var in lang_vars.items() if var.get()]
        if not langs:
            messagebox.showwarning("警告", "请至少选择一种语言")
            return

        def _run():
            from shouchao.api import fetch_news
            fetch_log.delete("1.0", "end")
            for lang in langs:
                fetch_log.insert("end", f"正在抓取 {lang}...\n")
                result = fetch_news(
                    language=lang,
                    max_articles=int(max_articles_var.get()),
                    fetcher=fetcher_var.get()
                )
                if result.success:
                    fetch_log.insert("end", f"  抓取了 {result.data.get('fetched', 0)} 篇\n")
                else:
                    fetch_log.insert("end", f"  错误: {result.error}\n")
            root.after(0, update_stats)

        threading.Thread(target=_run, daemon=True).start()

    def index_news():
        def _run():
            from shouchao.api import index_news
            fetch_log.insert("end", "正在建立索引...\n")
            result = index_news()
            if result.success:
                fetch_log.insert("end", f"索引完成: {result.data.get('indexed', 0)} 篇\n")
            root.after(0, update_stats)
        threading.Thread(target=_run, daemon=True).start()

    def do_search():
        query = search_query_var.get()
        if not query:
            return

        def _run():
            results_tree.delete(*results_tree.get_children())
            search_type = search_type_var.get()
            
            if search_type in ["local", "both"]:
                from shouchao.api import search_news
                result = search_news(query=query, top_k=20)
                if result.success:
                    for r in result.data.get("results", []):
                        m = r.get("metadata", {})
                        results_tree.insert("", "end", values=(
                            m.get("title", "")[:60],
                            m.get("website", ""),
                            m.get("date", "")
                        ), tags=("local", r.get("document", "")))
            
            if search_type in ["web", "both"]:
                from shouchao.api import web_search
                result = web_search(query=query, engines=[search_engine_var.get()])
                if result.success:
                    for r in result.data.get("results", []):
                        results_tree.insert("", "end", values=(
                            r.get("title", "")[:60],
                            r.get("source", ""),
                            ""
                        ), tags=("web", r.get("snippet", "")))

        threading.Thread(target=_run, daemon=True).start()

    def add_selected():
        sel = results_tree.selection()
        for item in sel:
            values = results_tree.item(item, "values")
            tags = results_tree.item(item, "tags")
            selected_items.append({
                "title": values[0],
                "source": values[1],
                "content": tags[1] if len(tags) > 1 else ""
            })
        update_selected_text()

    def clear_selected():
        selected_items.clear()
        update_selected_text()

    def update_selected_text():
        selected_text.delete("1.0", "end")
        for i, item in enumerate(selected_items):
            selected_text.insert("end", f"{i+1}. {item['title']}\n")

    def update_briefing_input():
        briefing_output.delete("1.0", "end")
        briefing_output.insert("end", f"已选择 {len(selected_items)} 条内容，点击生成简报...")

    def generate_briefing():
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要总结的内容")
            return

        def _run():
            from shouchao.api import summarize_content
            content = "\n\n".join([f"标题: {i['title']}\n{i['content']}" for i in selected_items])
            result = summarize_content(
                content=content,
                target_language=output_lang_var.get(),
                style=style_var.get()
            )
            if result.success:
                briefing_output.delete("1.0", "end")
                briefing_output.insert("1.0", result.data.get("summary", ""))
                tts_input.delete("1.0", "end")
                tts_input.insert("1.0", result.data.get("summary", ""))

        threading.Thread(target=_run, daemon=True).start()

    def load_tts_voices():
        from shouchao.api import get_tts_voices
        result = get_tts_voices(engine=tts_engine_var.get(), language=output_lang_var.get())
        if result.success:
            voices = result.data.get("voices", [])
            tts_voice_combo['values'] = [f"{v['name']} ({v['language']})" for v in voices]
            if voices:
                tts_voice_combo.current(0)

    def generate_audio():
        text = tts_input.get("1.0", "end").strip()
        if not text:
            return

        def _run():
            from shouchao.api import text_to_speech
            result = text_to_speech(
                text=text,
                engine=tts_engine_var.get(),
                language=output_lang_var.get(),
                rate=float(tts_speed_var.get())
            )
            if result.success:
                messagebox.showinfo("完成", f"音频已保存: {result.data.get('audio_path', '')}")
            else:
                messagebox.showerror("错误", result.error)

        threading.Thread(target=_run, daemon=True).start()

    def start_over():
        selected_items.clear()
        update_selected_text()
        show_step(1)

    # Initialize
    load_models()
    show_step(1)
    root.mainloop()