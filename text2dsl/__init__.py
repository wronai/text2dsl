"""
text2dsl - Framework do głosowej nawigacji i kontekstowego wsparcia CLI

Architektura warstw:
1. TTS/STT Layer - Konwersja mowa <-> tekst (PL/DE/EN)
2. text2DSL Layer - Parser i router DSL
3. Executor Layers - text2make, text2shell, text2git, text2docker, text2python
"""

__version__ = "0.2.0"
__author__ = "Softreck"

from .core.dsl_parser import DSLParser
from .core.context_manager import ContextManager
from .core.suggestion_engine import SuggestionEngine

from .layers.voice_layer import (
    VoiceLayer,
    VoiceConfig,
    VoiceBackend,
    Language,
    LanguageConfig,
    LANGUAGE_CONFIGS,
    get_language_config,
)
from .layers.text2make import Text2Make
from .layers.text2shell import Text2Shell
from .layers.text2git import Text2Git
from .layers.text2docker import Text2Docker
from .layers.text2python import Text2Python

from .orchestrator import Text2DSLOrchestrator, OrchestratorConfig, ExecutionResponse

from .utils.archive import ArchiveManager, ExportResult, create_project_archive

__all__ = [
    # Core
    "DSLParser",
    "ContextManager",
    "SuggestionEngine",
    # Voice
    "VoiceLayer",
    "VoiceConfig",
    "VoiceBackend",
    "Language",
    "LanguageConfig",
    "LANGUAGE_CONFIGS",
    "get_language_config",
    # Layers
    "Text2Make",
    "Text2Shell",
    "Text2Git",
    "Text2Docker",
    "Text2Python",
    # Orchestrator
    "Text2DSLOrchestrator",
    "OrchestratorConfig",
    "ExecutionResponse",
    # Utils
    "ArchiveManager",
    "ExportResult",
    "create_project_archive",
]
