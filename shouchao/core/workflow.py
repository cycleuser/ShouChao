"""
Enhanced Model Configuration and Workflow Management.

Implements agent patterns from Skills:
- master-architect: Requirement analysis and task decomposition
- software-planner: Complete development workflow
- iteration-manager: Iterative improvement
- official-document-writer: Document generation
- academic-writer: Academic writing
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Enhanced model configuration."""
    ollama_url: str = "http://localhost:11434"
    chat_model: str = "gemma3:1b"
    embedding_model: str = "nomic-embed-text"
    
    # Multi-model support
    analysis_model: str = "gemma3:1b"  # For analysis
    writing_model: str = "gemma3:1b"   # For writing
    coding_model: str = "gemma3:1b"    # For code
    
    # Proxy settings (only for web requests)
    proxy_mode: str = "none"  # none, system, manual
    proxy_http: str = ""
    proxy_https: str = ""
    proxy_socks5: str = ""
    proxy_username: str = ""
    proxy_password: str = ""
    
    # Language
    language: str = "zh"
    
    # Output settings
    output_format: str = "markdown"  # markdown, html, docx
    include_references: bool = True
    include_code_examples: bool = True
    
    # Quality settings
    max_iterations: int = 3
    quality_threshold: float = 0.8
    
    # Workflow settings
    auto_save: bool = True
    auto_index: bool = True


@dataclass
class WorkflowStep:
    """Workflow step definition."""
    name: str
    description: str
    required: bool = True
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    model: str = ""  # Which model to use
    timeout: int = 300  # seconds
    optional: bool = False


@dataclass 
class Workflow:
    """Complete workflow definition."""
    name: str
    description: str
    steps: list[WorkflowStep] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    results: dict = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class WorkflowManager:
    """
    Manage complex workflows with multiple steps.
    
    Implements patterns from:
    - master-architect: Task decomposition
    - iteration-manager: Iterative improvement
    - power-iterate: Autonomous iteration
    """
    
    # Predefined workflows
    WORKFLOWS = {
        "news_briefing": {
            "name": "News Briefing Generation",
            "description": "Generate news briefing from fetched articles",
            "steps": [
                WorkflowStep(
                    name="fetch_news",
                    description="Fetch news from sources",
                    outputs=["articles"],
                    timeout=600,
                ),
                WorkflowStep(
                    name="index_articles",
                    description="Index articles to ChromaDB",
                    inputs=["articles"],
                    timeout=300,
                ),
                WorkflowStep(
                    name="select_articles",
                    description="Select relevant articles",
                    inputs=["articles"],
                    outputs=["selected"],
                ),
                WorkflowStep(
                    name="generate_briefing",
                    description="Generate AI briefing",
                    inputs=["selected"],
                    outputs=["briefing"],
                    model="chat",
                ),
                WorkflowStep(
                    name="generate_audio",
                    description="Convert to speech",
                    inputs=["briefing"],
                    outputs=["audio"],
                    optional=True,
                ),
            ]
        },
        "github_article": {
            "name": "GitHub Trending Article",
            "description": "Generate WeChat article from GitHub trends",
            "steps": [
                WorkflowStep(
                    name="fetch_trending",
                    description="Fetch GitHub trending repos",
                    outputs=["repos"],
                    timeout=120,
                ),
                WorkflowStep(
                    name="analyze_repos",
                    description="Analyze selected repositories",
                    inputs=["repos"],
                    outputs=["analyses"],
                    model="chat",
                ),
                WorkflowStep(
                    name="generate_article",
                    description="Generate WeChat article",
                    inputs=["repos", "analyses"],
                    outputs=["article"],
                    model="writing",
                ),
                WorkflowStep(
                    name="review_article",
                    description="Review and improve article",
                    inputs=["article"],
                    outputs=["reviewed"],
                    model="chat",
                    optional=True,
                ),
            ]
        },
        "academic_paper": {
            "name": "Academic Paper Writing",
            "description": "Write academic paper section",
            "steps": [
                WorkflowStep(
                    name="literature_search",
                    description="Search relevant literature",
                    outputs=["references"],
                    timeout=300,
                ),
                WorkflowStep(
                    name="outline_generation",
                    description="Generate paper outline",
                    inputs=["topic"],
                    outputs=["outline"],
                    model="writing",
                ),
                WorkflowStep(
                    name="section_writing",
                    description="Write paper section",
                    inputs=["outline", "references"],
                    outputs=["draft"],
                    model="academic",
                ),
                WorkflowStep(
                    name="citation_formatting",
                    description="Format citations",
                    inputs=["draft"],
                    outputs=["formatted"],
                    model="writing",
                ),
                WorkflowStep(
                    name="quality_review",
                    description="Review for quality",
                    inputs=["formatted"],
                    outputs=["final"],
                    model="chat",
                ),
            ]
        },
        "official_document": {
            "name": "Official Document Writing",
            "description": "Write official document (公文)",
            "steps": [
                WorkflowStep(
                    name="determine_type",
                    description="Determine document type",
                    inputs=["purpose"],
                    outputs=["doc_type"],
                ),
                WorkflowStep(
                    name="gather_info",
                    description="Gather required information",
                    outputs=["info"],
                ),
                WorkflowStep(
                    name="draft_content",
                    description="Draft document content",
                    inputs=["info", "doc_type"],
                    outputs=["draft"],
                    model="official",
                ),
                WorkflowStep(
                    name="format_check",
                    description="Check formatting compliance",
                    inputs=["draft"],
                    outputs=["checked"],
                    model="chat",
                ),
            ]
        },
    }
    
    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig()
        self._workflows: dict[str, Workflow] = {}
    
    def create_workflow(self, workflow_type: str, **kwargs) -> Workflow:
        """Create a new workflow instance."""
        if workflow_type not in self.WORKFLOWS:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
        
        template = self.WORKFLOWS[workflow_type]
        
        workflow = Workflow(
            name=template["name"],
            description=template["description"],
            steps=template["steps"].copy(),
            context=kwargs,
        )
        
        self._workflows[workflow.name] = workflow
        return workflow
    
    async def execute_workflow(self, workflow: Workflow) -> dict:
        """
        Execute workflow step by step.
        
        Returns:
            Results dictionary
        """
        workflow.status = "running"
        results = {}
        
        for i, step in enumerate(workflow.steps):
            try:
                logger.info(f"Executing step {i+1}/{len(workflow.steps)}: {step.name}")
                
                # Gather inputs
                inputs = {}
                for input_name in step.inputs:
                    if input_name in results:
                        inputs[input_name] = results[input_name]
                    elif input_name in workflow.context:
                        inputs[input_name] = workflow.context[input_name]
                
                # Execute step
                result = await self._execute_step(step, inputs, workflow.context)
                results[step.outputs[0] if step.outputs else f"result_{i}"] = result
                
                workflow.updated_at = datetime.now().isoformat()
                
            except Exception as e:
                if step.required:
                    workflow.status = "failed"
                    raise
                else:
                    logger.warning(f"Optional step {step.name} failed: {e}")
        
        workflow.status = "completed"
        workflow.results = results
        return results
    
    async def _execute_step(
        self,
        step: WorkflowStep,
        inputs: dict,
        context: dict,
    ) -> Any:
        """Execute a single workflow step."""
        # Dispatch based on step name
        if step.name == "fetch_news":
            return await self._fetch_news(inputs, context)
        elif step.name == "index_articles":
            return await self._index_articles(inputs, context)
        elif step.name == "generate_briefing":
            return await self._generate_briefing(inputs, context)
        elif step.name == "fetch_trending":
            return await self._fetch_trending(inputs, context)
        elif step.name == "analyze_repos":
            return await self._analyze_repos(inputs, context)
        elif step.name == "generate_article":
            return await self._generate_article(inputs, context)
        else:
            # Generic execution via model
            return await self._execute_with_model(step, inputs, context)
    
    async def _fetch_news(self, inputs: dict, context: dict) -> Any:
        """Fetch news step."""
        from shouchao.api import fetch_news
        
        language = context.get("language", self.config.language)
        max_articles = context.get("max_articles", 50)
        
        result = fetch_news(language=language, max_articles=max_articles)
        return result.data if result.success else None
    
    async def _index_articles(self, inputs: dict, context: dict) -> Any:
        """Index articles step."""
        from shouchao.api import index_news
        
        result = index_news()
        return result.data if result.success else None
    
    async def _generate_briefing(self, inputs: dict, context: dict) -> Any:
        """Generate briefing step."""
        from shouchao.api import generate_briefing
        
        language = context.get("language", self.config.language)
        style = context.get("style", "detailed")
        
        result = generate_briefing(language=language, style=style)
        return result.data if result.success else None
    
    async def _fetch_trending(self, inputs: dict, context: dict) -> Any:
        """Fetch GitHub trending step."""
        from shouchao.core.github_trends import fetch_github_trending
        
        since = context.get("since", "daily")
        language = context.get("language")
        limit = context.get("limit", 25)
        
        repos = fetch_github_trending(since=since, language=language, limit=limit)
        return [r.__dict__ for r in repos]
    
    async def _analyze_repos(self, inputs: dict, context: dict) -> Any:
        """Analyze repositories step."""
        from shouchao.core.github_trends import analyze_github_repo
        
        repos = inputs.get("repos", [])
        analyses = {}
        
        for repo in repos[:5]:  # Limit to 5
            repo_name = repo.get("name") if isinstance(repo, dict) else str(repo)
            analysis = analyze_github_repo(repo_name)
            analyses[repo_name] = analysis.__dict__
        
        return analyses
    
    async def _generate_article(self, inputs: dict, context: dict) -> Any:
        """Generate article step."""
        from shouchao.core.wechat_generator import generate_trending_roundup_article
        from shouchao.core.github_trends import RepoTrend
        
        repos_data = inputs.get("repos", [])
        analyses_data = inputs.get("analyses", {})
        
        # Convert to objects
        repos = [RepoTrend(**r) if isinstance(r, dict) else r for r in repos_data]
        analyses = analyses_data
        
        article = generate_trending_roundup_article(
            repos, analyses, 
            author=context.get("author", "ShouChao"),
            period=context.get("period", "今日"),
        )
        
        return article.to_dict()
    
    async def _execute_with_model(self, step: WorkflowStep, inputs: dict, context: dict) -> Any:
        """Execute step using AI model."""
        from shouchao.core.ollama_client import OllamaClient
        
        client = OllamaClient(self.config.ollama_url)
        
        # Build prompt
        prompt = self._build_prompt(step, inputs, context)
        
        # Select model
        model = step.model or self.config.chat_model
        if model == "writing":
            model = self.config.writing_model
        elif model == "academic":
            model = self.config.analysis_model
        elif model == "official":
            model = self.config.writing_model
        
        # Generate response
        response = client.generate(
            model=model,
            prompt=prompt,
        )
        
        return response
    
    def _build_prompt(self, step: WorkflowStep, inputs: dict, context: dict) -> str:
        """Build prompt for AI model."""
        prompt_parts = []
        
        # System instruction
        prompt_parts.append(f"You are assisting with: {step.description}")
        prompt_parts.append("")
        
        # Context
        if context:
            prompt_parts.append("## Context")
            for key, value in context.items():
                if isinstance(value, str):
                    prompt_parts.append(f"{key}: {value}")
            prompt_parts.append("")
        
        # Inputs
        if inputs:
            prompt_parts.append("## Input Data")
            for key, value in inputs.items():
                if isinstance(value, str):
                    prompt_parts.append(f"{key}: {value[:500]}")  # Truncate
            prompt_parts.append("")
        
        # Task
        prompt_parts.append(f"## Task")
        prompt_parts.append(step.description)
        prompt_parts.append("")
        
        # Output format
        if step.outputs:
            prompt_parts.append(f"## Expected Output")
            prompt_parts.append(f"Provide: {', '.join(step.outputs)}")
        
        return "\n".join(prompt_parts)
    
    def get_workflow_status(self, workflow_name: str) -> dict:
        """Get workflow status."""
        workflow = self._workflows.get(workflow_name)
        if not workflow:
            return {"error": "Workflow not found"}
        
        return {
            "name": workflow.name,
            "status": workflow.status,
            "steps": len(workflow.steps),
            "created_at": workflow.created_at,
            "updated_at": workflow.updated_at,
            "results": list(workflow.results.keys()),
        }


# Singleton
_manager: Optional[WorkflowManager] = None


def get_workflow_manager(config: Optional[ModelConfig] = None) -> WorkflowManager:
    """Get workflow manager singleton."""
    global _manager
    if _manager is None:
        _manager = WorkflowManager(config)
    return _manager


def run_workflow(
    workflow_type: str,
    **kwargs,
) -> dict:
    """
    Run a workflow synchronously.
    
    Args:
        workflow_type: Type of workflow to run
        **kwargs: Workflow parameters
        
    Returns:
        Results dictionary
    """
    import asyncio
    
    manager = get_workflow_manager()
    workflow = manager.create_workflow(workflow_type, **kwargs)
    
    return asyncio.run(manager.execute_workflow(workflow))
