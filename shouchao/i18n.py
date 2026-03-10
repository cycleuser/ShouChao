"""
Internationalization for ShouChao.

Supports 10 languages: zh, en, ja, fr, ru, de, it, es, pt, ko.
"""

from shouchao.core.config import CONFIG

LANGUAGES = {
    "zh": "中文",
    "en": "English",
    "ja": "日本語",
    "fr": "Français",
    "ru": "Русский",
    "de": "Deutsch",
    "it": "Italiano",
    "es": "Español",
    "pt": "Português",
    "ko": "한국어",
}

TRANSLATIONS = {
    "app_title": {
        "zh": "手抄 - 网络信息检索辅助工具",
        "en": "ShouChao - Web Information Retrieval Assistant",
        "ja": "ShouChao - ウェブ情報検索アシスタント",
        "fr": "ShouChao - Assistant de recherche d'informations web",
        "ru": "ShouChao - Помощник по поиску информации в сети",
        "de": "ShouChao - Web-Informationsrecherche-Assistent",
        "it": "ShouChao - Assistente per la ricerca di informazioni web",
        "es": "ShouChao - Asistente de recuperación de información web",
        "pt": "ShouChao - Assistente de recuperação de informações web",
        "ko": "ShouChao - 웹 정보 검색 보조 도구",
    },
    "fetch_news": {
        "zh": "获取新闻", "en": "Get News", "ja": "ニュース取得",
        "fr": "Récupérer les nouvelles", "ru": "Получить новости",
        "de": "Nachrichten abrufen", "it": "Recupera notizie",
        "es": "Obtener noticias", "pt": "Buscar notícias", "ko": "뉴스 가져오기",
    },
    "news_briefing": {
        "zh": "新闻简报", "en": "News Briefing", "ja": "ニュースブリーフィング",
        "fr": "Briefing des nouvelles", "ru": "Новостная сводка",
        "de": "Nachrichtenbriefing", "it": "Briefing notizie",
        "es": "Resumen de noticias", "pt": "Resumo de notícias", "ko": "뉴스 브리핑",
    },
    "investment_analysis": {
        "zh": "投资分析", "en": "Investment Analysis", "ja": "投資分析",
        "fr": "Analyse d'investissement", "ru": "Инвестиционный анализ",
        "de": "Investitionsanalyse", "it": "Analisi degli investimenti",
        "es": "Análisis de inversiones", "pt": "Análise de investimentos", "ko": "투자 분석",
    },
    "immigration_analysis": {
        "zh": "移民分析", "en": "Immigration Analysis", "ja": "移民分析",
        "fr": "Analyse de l'immigration", "ru": "Иммиграционный анализ",
        "de": "Einwanderungsanalyse", "it": "Analisi dell'immigrazione",
        "es": "Análisis de inmigración", "pt": "Análise de imigração", "ko": "이민 분석",
    },
    "study_abroad_analysis": {
        "zh": "留学分析", "en": "Study Abroad Analysis", "ja": "留学分析",
        "fr": "Analyse des études à l'étranger", "ru": "Анализ обучения за рубежом",
        "de": "Auslandsstudienanalyse", "it": "Analisi studio all'estero",
        "es": "Análisis de estudios en el extranjero", "pt": "Análise de estudos no exterior",
        "ko": "유학 분석",
    },
    "general_analysis": {
        "zh": "综合分析", "en": "General Analysis", "ja": "総合分析",
        "fr": "Analyse générale", "ru": "Общий анализ",
        "de": "Allgemeine Analyse", "it": "Analisi generale",
        "es": "Análisis general", "pt": "Análise geral", "ko": "종합 분석",
    },
    "settings": {
        "zh": "设置", "en": "Settings", "ja": "設定",
        "fr": "Paramètres", "ru": "Настройки",
        "de": "Einstellungen", "it": "Impostazioni",
        "es": "Configuración", "pt": "Configurações", "ko": "설정",
    },
    "search": {
        "zh": "搜索", "en": "Search", "ja": "検索",
        "fr": "Rechercher", "ru": "Поиск",
        "de": "Suchen", "it": "Cerca",
        "es": "Buscar", "pt": "Pesquisar", "ko": "검색",
    },
    "dashboard": {
        "zh": "仪表板", "en": "Dashboard", "ja": "ダッシュボード",
        "fr": "Tableau de bord", "ru": "Панель управления",
        "de": "Dashboard", "it": "Dashboard",
        "es": "Panel", "pt": "Painel", "ko": "대시보드",
    },
    "sources": {
        "zh": "新闻源", "en": "Sources", "ja": "ニュースソース",
        "fr": "Sources", "ru": "Источники",
        "de": "Quellen", "it": "Fonti",
        "es": "Fuentes", "pt": "Fontes", "ko": "뉴스 소스",
    },
    "daily_briefing": {
        "zh": "每日简报", "en": "Daily Briefing", "ja": "デイリーブリーフィング",
        "fr": "Briefing quotidien", "ru": "Ежедневная сводка",
        "de": "Tägliches Briefing", "it": "Briefing giornaliero",
        "es": "Resumen diario", "pt": "Resumo diário", "ko": "일일 브리핑",
    },
    "weekly_briefing": {
        "zh": "每周简报", "en": "Weekly Briefing", "ja": "ウィークリーブリーフィング",
        "fr": "Briefing hebdomadaire", "ru": "Еженедельная сводка",
        "de": "Wöchentliches Briefing", "it": "Briefing settimanale",
        "es": "Resumen semanal", "pt": "Resumo semanal", "ko": "주간 브리핑",
    },
    "category_politics": {
        "zh": "政治", "en": "Politics", "ja": "政治",
        "fr": "Politique", "ru": "Политика",
        "de": "Politik", "it": "Politica",
        "es": "Política", "pt": "Política", "ko": "정치",
    },
    "category_economy": {
        "zh": "经济", "en": "Economy", "ja": "経済",
        "fr": "Économie", "ru": "Экономика",
        "de": "Wirtschaft", "it": "Economia",
        "es": "Economía", "pt": "Economia", "ko": "경제",
    },
    "category_technology": {
        "zh": "科技", "en": "Technology", "ja": "テクノロジー",
        "fr": "Technologie", "ru": "Технологии",
        "de": "Technologie", "it": "Tecnologia",
        "es": "Tecnología", "pt": "Tecnologia", "ko": "기술",
    },
    "category_science": {
        "zh": "科学", "en": "Science", "ja": "科学",
        "fr": "Science", "ru": "Наука",
        "de": "Wissenschaft", "it": "Scienza",
        "es": "Ciencia", "pt": "Ciência", "ko": "과학",
    },
    "category_health": {
        "zh": "健康", "en": "Health", "ja": "健康",
        "fr": "Santé", "ru": "Здоровье",
        "de": "Gesundheit", "it": "Salute",
        "es": "Salud", "pt": "Saúde", "ko": "건강",
    },
    "category_environment": {
        "zh": "环境", "en": "Environment", "ja": "環境",
        "fr": "Environnement", "ru": "Окружающая среда",
        "de": "Umwelt", "it": "Ambiente",
        "es": "Medio ambiente", "pt": "Meio ambiente", "ko": "환경",
    },
    "category_culture": {
        "zh": "文化", "en": "Culture", "ja": "文化",
        "fr": "Culture", "ru": "Культура",
        "de": "Kultur", "it": "Cultura",
        "es": "Cultura", "pt": "Cultura", "ko": "문화",
    },
    "category_sports": {
        "zh": "体育", "en": "Sports", "ja": "スポーツ",
        "fr": "Sports", "ru": "Спорт",
        "de": "Sport", "it": "Sport",
        "es": "Deportes", "pt": "Esportes", "ko": "스포츠",
    },
    "language_label": {
        "zh": "语言", "en": "Language", "ja": "言語",
        "fr": "Langue", "ru": "Язык",
        "de": "Sprache", "it": "Lingua",
        "es": "Idioma", "pt": "Idioma", "ko": "언어",
    },
    "ollama_url": {
        "zh": "Ollama 地址", "en": "Ollama URL", "ja": "Ollama URL",
        "fr": "URL Ollama", "ru": "URL Ollama",
        "de": "Ollama URL", "it": "URL Ollama",
        "es": "URL de Ollama", "pt": "URL do Ollama", "ko": "Ollama URL",
    },
    "model": {
        "zh": "模型", "en": "Model", "ja": "モデル",
        "fr": "Modèle", "ru": "Модель",
        "de": "Modell", "it": "Modello",
        "es": "Modelo", "pt": "Modelo", "ko": "모델",
    },
    "proxy": {
        "zh": "代理", "en": "Proxy", "ja": "プロキシ",
        "fr": "Proxy", "ru": "Прокси",
        "de": "Proxy", "it": "Proxy",
        "es": "Proxy", "pt": "Proxy", "ko": "프록시",
    },
    "save": {
        "zh": "保存", "en": "Save", "ja": "保存",
        "fr": "Enregistrer", "ru": "Сохранить",
        "de": "Speichern", "it": "Salva",
        "es": "Guardar", "pt": "Salvar", "ko": "저장",
    },
    "cancel": {
        "zh": "取消", "en": "Cancel", "ja": "キャンセル",
        "fr": "Annuler", "ru": "Отмена",
        "de": "Abbrechen", "it": "Annulla",
        "es": "Cancelar", "pt": "Cancelar", "ko": "취소",
    },
    "loading": {
        "zh": "加载中...", "en": "Loading...", "ja": "読み込み中...",
        "fr": "Chargement...", "ru": "Загрузка...",
        "de": "Laden...", "it": "Caricamento...",
        "es": "Cargando...", "pt": "Carregando...", "ko": "로딩 중...",
    },
    "error": {
        "zh": "错误", "en": "Error", "ja": "エラー",
        "fr": "Erreur", "ru": "Ошибка",
        "de": "Fehler", "it": "Errore",
        "es": "Error", "pt": "Erro", "ko": "오류",
    },
    "success": {
        "zh": "成功", "en": "Success", "ja": "成功",
        "fr": "Succès", "ru": "Успех",
        "de": "Erfolg", "it": "Successo",
        "es": "Éxito", "pt": "Sucesso", "ko": "성공",
    },
    "no_results": {
        "zh": "无结果", "en": "No results", "ja": "結果なし",
        "fr": "Aucun résultat", "ru": "Нет результатов",
        "de": "Keine Ergebnisse", "it": "Nessun risultato",
        "es": "Sin resultados", "pt": "Sem resultados", "ko": "결과 없음",
    },
    "total_articles": {
        "zh": "文章总数", "en": "Total Articles", "ja": "記事数合計",
        "fr": "Total des articles", "ru": "Всего статей",
        "de": "Artikel insgesamt", "it": "Articoli totali",
        "es": "Total de artículos", "pt": "Total de artigos", "ko": "총 기사 수",
    },
    "fetching_progress": {
        "zh": "正在获取新闻...", "en": "Getting news...", "ja": "ニュースを取得中...",
        "fr": "Récupération des nouvelles...", "ru": "Получение новостей...",
        "de": "Nachrichten werden abgerufen...", "it": "Recupero notizie...",
        "es": "Obteniendo noticias...", "pt": "Buscando notícias...", "ko": "뉴스 가져오는 중...",
    },
    "analyzing": {
        "zh": "正在分析...", "en": "Analyzing...", "ja": "分析中...",
        "fr": "Analyse en cours...", "ru": "Анализ...",
        "de": "Analyse läuft...", "it": "Analisi in corso...",
        "es": "Analizando...", "pt": "Analisando...", "ko": "분석 중...",
    },
    "generating_briefing": {
        "zh": "正在生成简报...", "en": "Generating briefing...", "ja": "ブリーフィング生成中...",
        "fr": "Génération du briefing...", "ru": "Генерация сводки...",
        "de": "Briefing wird erstellt...", "it": "Generazione briefing...",
        "es": "Generando resumen...", "pt": "Gerando resumo...", "ko": "브리핑 생성 중...",
    },
    "export": {
        "zh": "导出", "en": "Export", "ja": "エクスポート",
        "fr": "Exporter", "ru": "Экспорт",
        "de": "Exportieren", "it": "Esporta",
        "es": "Exportar", "pt": "Exportar", "ko": "내보내기",
    },
    "ready": {
        "zh": "就绪", "en": "Ready", "ja": "準備完了",
        "fr": "Prêt", "ru": "Готово",
        "de": "Bereit", "it": "Pronto",
        "es": "Listo", "pt": "Pronto", "ko": "준비 완료",
    },
}


def t(key: str, lang: str = None) -> str:
    """Translate a key to the specified or configured language."""
    lang = lang or CONFIG.language
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get("en") or key
