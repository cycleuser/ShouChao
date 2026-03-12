"""
Tkinter GUI for ShouChao with 5-step workflow.
"""

import logging
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

logger = logging.getLogger(__name__)


def launch_gui():
    """Launch the ShouChao GUI application."""
    from shouchao import __version__
    from shouchao.core.config import CONFIG, load_config, save_config, ensure_dirs
    from shouchao.i18n import LANGUAGES

    load_config()
    ensure_dirs()

    root = tk.Tk()
    root.title(f"ShouChao (手抄) v{__version__}")
    root.geometry("1000x700")
    root.minsize(800, 600)

    # State variables (must be defined before functions)
    selected_articles = []
    current_briefing = [""]
    current_audio_path = [""]
    current_page = [1]
    total_pages = [1]

    # Tkinter variables
    ollama_url_var = tk.StringVar(value=CONFIG.ollama_url)
    chat_model_var = tk.StringVar(value=CONFIG.chat_model)
    embed_model_var = tk.StringVar(value=CONFIG.embedding_model)
    proxy_mode_var = tk.StringVar(value=CONFIG.proxy_mode)
    proxy_http_var = tk.StringVar(value=CONFIG.proxy_http)
    max_articles_var = tk.StringVar(value="20")
    date_from_var = tk.StringVar(value=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"))
    date_to_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
    filter_lang_var = tk.StringVar()
    output_lang_var = tk.StringVar(value=CONFIG.language)
    briefing_style_var = tk.StringVar(value="story")
    show_source_var = tk.BooleanVar(value=True)
    tts_engine_var = tk.StringVar(value="edge-tts")
    tts_speed_var = tk.StringVar(value="1.0")
    tts_voice_var = tk.StringVar()
    current_step = tk.IntVar(value=1)
    lang_vars = {}
    tts_engine_combo = [None]

    # Widget references (will be set after creating widgets)
    ollama_status_label = [None]
    chat_model_combo = [None]
    embed_model_combo = [None]
    proxy_http_entry = [None]
    stat_labels = {}
    fetch_log_widget = [None]
    article_listbox = [None]
    page_label = [None]
    selected_label = [None]
    next_to_briefing_btn = [None]
    articles_info_label = [None]
    briefing_output_widget = [None]
    tts_input_widget = [None]
    audio_status_label_widget = [None]

    # ============ Define all callback functions FIRST ============

    def show_step(step):
        for s in step_frames.values():
            s.pack_forget()
        step_frames[step].pack(fill="both", expand=True)
        
        if step == 2:
            update_stats()
        elif step == 3:
            load_articles()
        elif step == 4:
            if articles_info_label[0]:
                articles_info_label[0].config(text=f"{len(selected_articles)} 篇文章")
        elif step == 5:
            if tts_input_widget[0]:
                tts_input_widget[0].delete("1.0", "end")
                tts_input_widget[0].insert("1.0", current_briefing[0])
            load_tts_engines()

    def test_ollama():
        from shouchao.core.ollama_client import OllamaClient
        client = OllamaClient(ollama_url_var.get())
        if ollama_status_label[0]:
            ollama_status_label[0].config(text="✓ 连接成功" if client.is_available() else "✗ 连接失败")

    def load_models():
        from shouchao.core.ollama_client import OllamaClient
        client = OllamaClient(ollama_url_var.get())
        if chat_model_combo[0]:
            chat_model_combo[0]['values'] = client.get_chat_models()
        if embed_model_combo[0]:
            embed_model_combo[0]['values'] = client.get_embedding_models()

    def update_proxy_fields():
        if proxy_http_entry[0]:
            proxy_http_entry[0].config(state="normal" if proxy_mode_var.get() == "manual" else "disabled")

    def save_step1():
        CONFIG.ollama_url = ollama_url_var.get()
        CONFIG.chat_model = chat_model_var.get()
        CONFIG.embedding_model = embed_model_var.get()
        CONFIG.proxy_mode = proxy_mode_var.get()
        CONFIG.proxy_http = proxy_http_var.get()
        save_config()
        show_step(2)

    def select_all_langs(select):
        for var in lang_vars.values():
            var.set(select)

    def update_stats():
        from shouchao.core.storage import ArticleStorage
        from shouchao.core.sources import get_sources
        storage = ArticleStorage()
        counts = storage.count_articles()
        if "total" in stat_labels:
            stat_labels["total"].config(text=str(counts.get("total", 0)))
        if "sources" in stat_labels:
            stat_labels["sources"].config(text=str(len(get_sources())))

    def fetch_news():
        langs = [code for code, var in lang_vars.items() if var.get()]
        if not langs:
            messagebox.showwarning("警告", "请至少选择一种语言")
            return

        def _run():
            from shouchao.api import fetch_news, index_news
            if fetch_log_widget[0]:
                fetch_log_widget[0].delete("1.0", "end")
                
                for lang in langs:
                    fetch_log_widget[0].insert("end", f"[{lang}] 抓取中...\n")
                    result = fetch_news(language=lang, max_articles=int(max_articles_var.get()))
                    fetch_log_widget[0].insert("end", f"  {result.data.get('fetched', 0)} 篇\n" if result.success else f"  失败\n")
                
                fetch_log_widget[0].insert("end", "\n建立索引...\n")
                result = index_news()
                fetch_log_widget[0].insert("end", f"完成: {result.data.get('indexed', 0)} 篇已索引\n")
            root.after(0, update_stats)

        threading.Thread(target=_run, daemon=True).start()

    def load_articles(page=1):
        if page < 1:
            page = 1
        current_page[0] = page

        from shouchao.core.storage import ArticleStorage
        storage = ArticleStorage()
        
        lang_filter = filter_lang_var.get()
        date_from = date_from_var.get()
        date_to = date_to_var.get()
        
        articles = storage.list_articles(
            language=lang_filter if lang_filter else None,
            date_from=date_from if date_from else None,
            date_to=date_to if date_to else None,
        )
        
        per_page = 50
        total = len(articles)
        total_pages[0] = max(1, (total + per_page - 1) // per_page)
        
        start = (page - 1) * per_page
        page_articles = articles[start:start + per_page]

        if article_listbox[0]:
            article_listbox[0].delete(0, tk.END)
            article_listbox[0].page_articles = page_articles
            
            for a in page_articles:
                article_listbox[0].insert(tk.END, f"{a.get('title', 'Untitled')} [{a.get('website', '')} {a.get('date', '')}]")

        if page_label[0]:
            page_label[0].config(text=f"第 {page}/{total_pages[0]} 页，共 {total} 篇")
        update_selected_count()

    def select_all_articles():
        if article_listbox[0]:
            article_listbox[0].select_set(0, tk.END)
            update_selected_articles()

    def clear_article_selection():
        if article_listbox[0]:
            article_listbox[0].selection_clear(0, tk.END)
        selected_articles.clear()
        update_selected_count()

    def update_selected_articles():
        if not article_listbox[0]:
            return
        sel_indices = article_listbox[0].curselection()
        articles = getattr(article_listbox[0], 'page_articles', [])
        
        for i in sel_indices:
            if i < len(articles):
                path = articles[i].get('path')
                if path and path not in selected_articles:
                    selected_articles.append(path)
        
        update_selected_count()

    def update_selected_count():
        if selected_label[0]:
            selected_label[0].config(text=f"已选: {len(selected_articles)} 篇")
        if next_to_briefing_btn[0]:
            next_to_briefing_btn[0].config(text=f"已选 {len(selected_articles)} 篇，继续")
            next_to_briefing_btn[0].config(state="normal" if selected_articles else "disabled")

    def generate_briefing():
        if not selected_articles:
            messagebox.showwarning("警告", "请先选择文章")
            return

        def _run():
            if briefing_output_widget[0]:
                briefing_output_widget[0].delete("1.0", "end")
                briefing_output_widget[0].insert("1.0", "生成中...")

            from shouchao.api import generate_briefing_from_articles
            result = generate_briefing_from_articles(
                article_paths=selected_articles,
                language=output_lang_var.get(),
                show_source=show_source_var.get()
            )

            if briefing_output_widget[0]:
                if result.success:
                    current_briefing[0] = result.data.get("content", "")
                    briefing_output_widget[0].delete("1.0", "end")
                    briefing_output_widget[0].insert("1.0", current_briefing[0])
                else:
                    briefing_output_widget[0].delete("1.0", "end")
                    briefing_output_widget[0].insert("1.0", f"错误: {result.error}")

        threading.Thread(target=_run, daemon=True).start()

    def export_briefing():
        if not current_briefing[0]:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md")],
            initialfile=f"briefing_{datetime.now().strftime('%Y%m%d')}.md"
        )
        if path:
            Path(path).write_text(current_briefing[0], encoding="utf-8")
            messagebox.showinfo("导出成功", f"已保存到: {path}")

    def generate_audio():
        text = tts_input_widget[0].get("1.0", "end").strip() if tts_input_widget[0] else ""
        if not text:
            return

        def _run():
            if audio_status_label_widget[0]:
                audio_status_label_widget[0].config(text="生成中...")
            from shouchao.api import text_to_speech
            result = text_to_speech(
                text=text,
                engine=tts_engine_var.get(),
                language=output_lang_var.get(),
                rate=float(tts_speed_var.get())
            )
            if audio_status_label_widget[0]:
                if result.success:
                    current_audio_path[0] = result.data.get('audio_path', '')
                    audio_status_label_widget[0].config(text="音频已生成")
                else:
                    audio_status_label_widget[0].config(text=f"失败: {result.error}")

        threading.Thread(target=_run, daemon=True).start()

    def play_audio():
        if not current_audio_path[0]:
            messagebox.showwarning("提示", "请先生成音频")
            return
        
        import platform
        try:
            if platform.system() == "Darwin":
                subprocess.run(["afplay", current_audio_path[0]])
            elif platform.system() == "Windows":
                import webbrowser
                webbrowser.open(current_audio_path[0])
            else:
                subprocess.run(["xdg-open", current_audio_path[0]])
        except Exception as e:
            messagebox.showerror("播放失败", str(e))

    def save_audio():
        if not current_audio_path[0]:
            messagebox.showwarning("提示", "请先生成音频")
            return
        
        dest_path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3 Audio", "*.mp3")],
            initialfile=f"briefing_{datetime.now().strftime('%Y%m%d')}.mp3"
        )
        if dest_path:
            import shutil
            shutil.copy(current_audio_path[0], dest_path)
            messagebox.showinfo("保存成功", f"已保存到: {dest_path}")

    def start_over():
        selected_articles.clear()
        current_briefing[0] = ""
        current_audio_path[0] = ""
        if briefing_output_widget[0]:
            briefing_output_widget[0].delete("1.0", "end")
        if tts_input_widget[0]:
            tts_input_widget[0].delete("1.0", "end")
        show_step(1)

    def load_tts_engines():
        from shouchao.core.tts import TTSEngine
        tts = TTSEngine()
        engines = []
        for name in tts.available_engines:
            engines.append(name)
        if tts_engine_combo[0]:
            tts_engine_combo[0]['values'] = engines
            if engines and not tts_engine_var.get():
                tts_engine_var.set(engines[0])

    # ============ Now build the UI ============

    main_frame = ttk.Frame(root, padding=10)
    main_frame.pack(fill="both", expand=True)

    steps_frame = ttk.Frame(main_frame)
    steps_frame.pack(fill="x", pady=(0, 10))

    step_names = ["1.模型设置", "2.抓取新闻", "3.选择新闻", "4.生成简报", "5.TTS播报"]
    for name in step_names:
        ttk.Radiobutton(
            steps_frame, text=name,
            variable=current_step, value=int(name[0]),
            command=lambda: show_step(current_step.get())
        ).pack(side="left", padx=10)

    content_frame = ttk.Frame(main_frame)
    content_frame.pack(fill="both", expand=True)

    step_frames = {}

    # Step 1
    step1 = ttk.Frame(content_frame)
    step_frames[1] = step1

    ollama_lf = ttk.LabelFrame(step1, text="Ollama 配置 (本地服务，无需代理)", padding=10)
    ollama_lf.pack(fill="x", pady=5)

    ttk.Label(ollama_lf, text="服务地址:").grid(row=0, column=0, sticky="w", pady=3)
    ttk.Entry(ollama_lf, textvariable=ollama_url_var, width=45).grid(row=0, column=1, padx=5)
    ttk.Button(ollama_lf, text="测试", command=test_ollama).grid(row=0, column=2, padx=5)
    lbl = ttk.Label(ollama_lf, text="")
    lbl.grid(row=0, column=3, padx=5)
    ollama_status_label[0] = lbl

    ttk.Label(ollama_lf, text="聊天模型:").grid(row=1, column=0, sticky="w", pady=3)
    cb1 = ttk.Combobox(ollama_lf, textvariable=chat_model_var, width=43)
    cb1.grid(row=1, column=1, columnspan=2, padx=5, sticky="w")
    chat_model_combo[0] = cb1

    ttk.Label(ollama_lf, text="嵌入模型:").grid(row=2, column=0, sticky="w", pady=3)
    cb2 = ttk.Combobox(ollama_lf, textvariable=embed_model_var, width=43)
    cb2.grid(row=2, column=1, columnspan=2, padx=5, sticky="w")
    embed_model_combo[0] = cb2

    ttk.Button(ollama_lf, text="刷新模型", command=load_models).grid(row=3, column=1, sticky="w", pady=5)

    proxy_lf = ttk.LabelFrame(step1, text="代理设置 (仅用于网络获取)", padding=10)
    proxy_lf.pack(fill="x", pady=5)

    ttk.Label(proxy_lf, text="模式:").grid(row=0, column=0, sticky="w")
    proxy_mode_combo = ttk.Combobox(proxy_lf, textvariable=proxy_mode_var, values=["none", "system", "manual"], width=12, state="readonly")
    proxy_mode_combo.grid(row=0, column=1, padx=5)
    proxy_mode_combo.bind("<<ComboboxSelected>>", lambda e: update_proxy_fields())

    ttk.Label(proxy_lf, text="HTTP:").grid(row=0, column=2, padx=(20, 5))
    entry = ttk.Entry(proxy_lf, textvariable=proxy_http_var, width=18)
    entry.grid(row=0, column=3, padx=5)
    proxy_http_entry[0] = entry

    ttk.Button(step1, text="保存并继续", command=save_step1).pack(pady=15)

    # Step 2
    step2 = ttk.Frame(content_frame)
    step_frames[2] = step2

    lang_lf = ttk.LabelFrame(step2, text="选择语言 (可多选)", padding=10)
    lang_lf.pack(fill="x", pady=5)

    for i, (code, name) in enumerate(LANGUAGES.items()):
        var = tk.BooleanVar()
        lang_vars[code] = var
        ttk.Checkbutton(lang_lf, text=name, variable=var).grid(row=i//5, column=i%5, sticky="w", padx=10, pady=3)

    btn_row = ttk.Frame(lang_lf)
    btn_row.grid(row=2, column=0, columnspan=5, pady=5)
    ttk.Button(btn_row, text="全选", command=lambda: select_all_langs(True)).pack(side="left", padx=5)
    ttk.Button(btn_row, text="清除", command=lambda: select_all_langs(False)).pack(side="left", padx=5)

    settings_lf = ttk.LabelFrame(step2, text="抓取设置", padding=10)
    settings_lf.pack(fill="x", pady=5)
    ttk.Label(settings_lf, text="每源最大文章:").grid(row=0, column=0, sticky="w")
    ttk.Entry(settings_lf, textvariable=max_articles_var, width=8).grid(row=0, column=1, padx=5)

    stats_lf = ttk.LabelFrame(step2, text="当前状态", padding=10)
    stats_lf.pack(fill="x", pady=5)

    stats_frame = ttk.Frame(stats_lf)
    stats_frame.pack()
    for i, (key, label) in enumerate([("total", "文章"), ("sources", "来源")]):
        ttk.Label(stats_frame, text=f"{label}:").grid(row=0, column=i*2, padx=5)
        lbl = ttk.Label(stats_frame, text="0", font=("", 12, "bold"))
        lbl.grid(row=0, column=i*2+1, padx=5)
        stat_labels[key] = lbl

    log = scrolledtext.ScrolledText(step2, height=6)
    log.pack(fill="both", expand=True, pady=5)
    fetch_log_widget[0] = log

    btn_frame2 = ttk.Frame(step2)
    btn_frame2.pack(fill="x", pady=5)
    ttk.Button(btn_frame2, text="上一步", command=lambda: show_step(1)).pack(side="left", padx=5)
    ttk.Button(btn_frame2, text="开始抓取", command=fetch_news).pack(side="left", padx=5)
    ttk.Button(btn_frame2, text="跳过，使用已有新闻", command=lambda: show_step(3)).pack(side="right", padx=5)

    # Step 3
    step3 = ttk.Frame(content_frame)
    step_frames[3] = step3

    filter_lf = ttk.LabelFrame(step3, text="筛选条件", padding=10)
    filter_lf.pack(fill="x", pady=5)

    ttk.Label(filter_lf, text="开始日期:").grid(row=0, column=0, sticky="w")
    ttk.Entry(filter_lf, textvariable=date_from_var, width=12).grid(row=0, column=1, padx=5)

    ttk.Label(filter_lf, text="结束日期:").grid(row=0, column=2, padx=(10, 5))
    ttk.Entry(filter_lf, textvariable=date_to_var, width=12).grid(row=0, column=3, padx=5)

    ttk.Label(filter_lf, text="语言:").grid(row=0, column=4, padx=(10, 5))
    ttk.Combobox(filter_lf, textvariable=filter_lang_var, values=[""] + list(LANGUAGES.keys()), width=8).grid(row=0, column=5, padx=5)

    ttk.Button(filter_lf, text="筛选", command=lambda: load_articles(1)).grid(row=0, column=6, padx=10)

    list_lf = ttk.LabelFrame(step3, text="新闻列表", padding=10)
    list_lf.pack(fill="both", expand=True, pady=5)

    list_frame = ttk.Frame(list_lf)
    list_frame.pack(fill="both", expand=True)

    lb = tk.Listbox(list_frame, selectmode="extended", height=15)
    lb.pack(side="left", fill="both", expand=True)
    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=lb.yview)
    scrollbar.pack(side="right", fill="y")
    lb.config(yscrollcommand=scrollbar.set)
    article_listbox[0] = lb
    lb.bind('<<ListboxSelect>>', lambda e: update_selected_articles())

    sel_frame = ttk.Frame(step3)
    sel_frame.pack(fill="x", pady=5)
    ttk.Button(sel_frame, text="全选当前页", command=select_all_articles).pack(side="left", padx=5)
    ttk.Button(sel_frame, text="清除选择", command=clear_article_selection).pack(side="left", padx=5)
    lbl = ttk.Label(sel_frame, text="已选: 0 篇")
    lbl.pack(side="left", padx=20)
    selected_label[0] = lbl

    page_frame = ttk.Frame(step3)
    page_frame.pack(fill="x", pady=5)
    ttk.Button(page_frame, text="上一页", command=lambda: load_articles(current_page[0] - 1)).pack(side="left", padx=5)
    lbl = ttk.Label(page_frame, text="第 1 页")
    lbl.pack(side="left", padx=10)
    page_label[0] = lbl
    ttk.Button(page_frame, text="下一页", command=lambda: load_articles(current_page[0] + 1)).pack(side="left", padx=5)

    btn_frame3 = ttk.Frame(step3)
    btn_frame3.pack(fill="x", pady=5)
    ttk.Button(btn_frame3, text="上一步", command=lambda: show_step(2)).pack(side="left", padx=5)
    btn = ttk.Button(btn_frame3, text="已选 0 篇，继续", command=lambda: show_step(4))
    btn.pack(side="right", padx=5)
    next_to_briefing_btn[0] = btn

    # Step 4
    step4 = ttk.Frame(content_frame)
    step_frames[4] = step4

    opts_lf = ttk.LabelFrame(step4, text="简报设置", padding=10)
    opts_lf.pack(fill="x", pady=5)

    ttk.Label(opts_lf, text="输出语言:").grid(row=0, column=0, sticky="w")
    ttk.Combobox(opts_lf, textvariable=output_lang_var, values=list(LANGUAGES.keys()), width=8, state="readonly").grid(row=0, column=1, padx=5)

    ttk.Label(opts_lf, text="风格:").grid(row=0, column=2, padx=(20, 5))
    ttk.Combobox(opts_lf, textvariable=briefing_style_var, values=["story", "detailed", "brief", "bullet"], width=12, state="readonly").grid(row=0, column=3, padx=5)

    ttk.Checkbutton(opts_lf, text="显示信息出处", variable=show_source_var).grid(row=1, column=0, columnspan=4, sticky="w", pady=5)

    info_lf = ttk.LabelFrame(step4, text="选中的文章", padding=10)
    info_lf.pack(fill="x", pady=5)
    lbl = ttk.Label(info_lf, text="0 篇文章")
    lbl.pack()
    articles_info_label[0] = lbl

    output_lf = ttk.LabelFrame(step4, text="生成的简报", padding=10)
    output_lf.pack(fill="both", expand=True, pady=5)

    out = scrolledtext.ScrolledText(output_lf, wrap="word")
    out.pack(fill="both", expand=True)
    briefing_output_widget[0] = out

    btn_frame4 = ttk.Frame(step4)
    btn_frame4.pack(fill="x", pady=5)
    ttk.Button(btn_frame4, text="上一步", command=lambda: show_step(3)).pack(side="left", padx=5)
    ttk.Button(btn_frame4, text="生成简报", command=generate_briefing).pack(side="left", padx=5)
    ttk.Button(btn_frame4, text="导出", command=export_briefing).pack(side="left", padx=5)
    ttk.Button(btn_frame4, text="TTS播报", command=lambda: show_step(5)).pack(side="right", padx=5)

    # Step 5
    step5 = ttk.Frame(content_frame)
    step_frames[5] = step5

    tts_lf = ttk.LabelFrame(step5, text="语音设置", padding=10)
    tts_lf.pack(fill="x", pady=5)

    ttk.Label(tts_lf, text="引擎:").grid(row=0, column=0, sticky="w")
    cb = ttk.Combobox(tts_lf, textvariable=tts_engine_var, values=[], width=12, state="readonly")
    cb.grid(row=0, column=1, padx=5)
    tts_engine_combo[0] = cb

    ttk.Label(tts_lf, text="语速:").grid(row=0, column=2, padx=(20, 5))
    ttk.Combobox(tts_lf, textvariable=tts_speed_var, values=["0.8", "1.0", "1.2"], width=5, state="readonly").grid(row=0, column=3, padx=5)

    content_lf = ttk.LabelFrame(step5, text="播报内容", padding=10)
    content_lf.pack(fill="both", expand=True, pady=5)

    tin = scrolledtext.ScrolledText(content_lf, wrap="word", height=8)
    tin.pack(fill="both", expand=True)
    tts_input_widget[0] = tin

    lbl = ttk.Label(step5, text="")
    lbl.pack()
    audio_status_label_widget[0] = lbl

    btn_frame5 = ttk.Frame(step5)
    btn_frame5.pack(fill="x", pady=5)
    ttk.Button(btn_frame5, text="上一步", command=lambda: show_step(4)).pack(side="left", padx=5)
    ttk.Button(btn_frame5, text="生成音频", command=generate_audio).pack(side="left", padx=5)
    ttk.Button(btn_frame5, text="播放", command=play_audio).pack(side="left", padx=5)
    ttk.Button(btn_frame5, text="另存为", command=save_audio).pack(side="left", padx=5)
    ttk.Button(btn_frame5, text="重新开始", command=start_over).pack(side="right", padx=5)

    # Initialize
    load_models()
    update_proxy_fields()
    show_step(1)
    root.mainloop()