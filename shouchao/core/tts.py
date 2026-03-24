"""
Text-to-Speech module for ShouChao.

Supports multiple TTS backends:
- pyttsx3: Cross-platform offline TTS (uses system voices, no internet required)
- edge-tts: Microsoft Edge TTS (high quality, requires internet)
- kokoro: High-quality neural TTS with local models (offline)
- sherpa-onnx: Neural TTS with local ONNX models (offline)
- gTTS: Google Translate TTS (online)

All offline engines use local models, no internet required after model download.
"""

import asyncio
import json
import logging
import os
import tempfile
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Union

logger = logging.getLogger(__name__)

# Suppress phonemizer warnings at module load
logging.getLogger("phonemizer").setLevel(logging.ERROR)

DEFAULT_TTS_MODEL_DIR = Path.home() / ".shouchao" / "tts_models"

_TTS_INSTANCE: Optional["TTSEngine"] = None


def get_tts_instance(preferred_engine: Optional[str] = None) -> Optional["TTSEngine"]:
    """Get or create the global TTS engine instance."""
    global _TTS_INSTANCE
    if _TTS_INSTANCE is None:
        try:
            _TTS_INSTANCE = TTSEngine(preferred_engine=preferred_engine)
            logger.info(f"TTS engine initialized with engines: {_TTS_INSTANCE.available_engines}")
        except Exception as e:
            logger.error(f"Failed to initialize TTS engine: {e}")
    return _TTS_INSTANCE


def download_tts_models(languages: Optional[list[str]] = None, force: bool = False) -> dict:
    """
    Download TTS models for specified languages.
    
    Args:
        languages: List of language codes ('zh', 'en'). None = download all.
        force: Force re-download even if models exist.
    
    Returns:
        Dict with download status for each engine.
    """
    if languages is None:
        languages = ["zh", "en"]
    
    results = {
        "edge_tts": {"status": "not_needed", "message": "Online engine, no download required"},
        "kokoro": {"status": "skipped", "message": "kokoro not installed"},
        "pyttsx3": {"status": "not_needed", "message": "Uses system voices"},
        "gtts": {"status": "not_needed", "message": "Online engine, no download required"},
    }
    
    # Check and setup Kokoro
    try:
        import kokoro
        results["kokoro"] = _download_kokoro_models(languages, force)
    except ImportError:
        logger.info("kokoro not installed, skipping model download")
    
    return results


def _download_kokoro_models(languages: list[str], force: bool = False) -> dict:
    """Download Kokoro TTS models for specified languages."""
    try:
        from kokoro import KPipeline
        import torch
        
        model_dir = DEFAULT_TTS_MODEL_DIR / "kokoro"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Downloading Kokoro models on {device}")
        
        # Initialize Kokoro - this triggers automatic model download
        pipeline = KPipeline(lang_code='a', device=device)
        
        # Warm up with sample text for each language to ensure models are cached
        warmup_texts = {
            "zh": "你好，这是一个测试。",
            "en": "Hello, this is a test.",
        }
        
        downloaded_voices = []
        for lang in languages:
            if lang in warmup_texts:
                try:
                    # Run a quick synthesis to cache models
                    voice = "zf_xiaoyu" if lang == "zh" else "af_bella"
                    list(pipeline(warmup_texts[lang], voice=voice))
                    downloaded_voices.append(f"{lang}:{voice}")
                    logger.info(f"Kokoro model cached for {lang}")
                except Exception as e:
                    logger.warning(f"Failed to warm up Kokoro for {lang}: {e}")
        
        return {
            "status": "success",
            "message": f"Models downloaded and cached",
            "voices": downloaded_voices,
            "model_dir": str(model_dir),
        }
    except Exception as e:
        logger.error(f"Failed to download Kokoro models: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


def preload_tts_voices(languages: Optional[list[str]] = None) -> dict:
    """
    Preload TTS voices for specified languages.
    
    This downloads voice lists from online engines and caches offline models.
    Call this at startup to ensure smooth first-use experience.
    """
    if languages is None:
        languages = ["zh", "en"]
    
    results = {}
    tts = get_tts_instance()
    
    if not tts:
        return {"error": "Failed to initialize TTS engine"}
    
    # Preload edge-tts voices (they need to be fetched from server)
    if "edge-tts" in tts.available_engines:
        try:
            for lang in languages:
                voices = tts.get_voices(engine="edge-tts", language=lang)
                results[f"edge-tts-{lang}"] = len(voices)
                logger.info(f"Preloaded {len(voices)} edge-tts voices for {lang}")
        except Exception as e:
            results["edge-tts-error"] = str(e)
            logger.error(f"Failed to preload edge-tts voices: {e}")
    
    # Download offline models
    download_results = download_tts_models(languages)
    results["download"] = download_results
    
    return results


@dataclass
class TTSResult:
    """Result of TTS synthesis."""
    success: bool
    audio_path: Optional[str] = None
    duration: float = 0.0
    engine: str = ""
    voice: str = ""
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "audio_path": self.audio_path,
            "duration": self.duration,
            "engine": self.engine,
            "voice": self.voice,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class VoiceInfo:
    """Information about a TTS voice."""
    id: str
    name: str
    language: str
    gender: str = "neutral"
    engine: str = ""
    sample_rate: int = 22050
    offline: bool = True
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "language": self.language,
            "gender": self.gender,
            "engine": self.engine,
            "sample_rate": self.sample_rate,
            "offline": self.offline,
            "metadata": self.metadata,
        }


class BaseTTS(ABC):
    """Abstract base for TTS engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name identifier."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the engine is available."""
        pass

    @property
    @abstractmethod
    def is_offline(self) -> bool:
        """Check if engine works offline."""
        pass

    @abstractmethod
    def get_voices(self, language: Optional[str] = None) -> list[VoiceInfo]:
        """Get available voices."""
        pass

    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice: Optional[str] = None,
        rate: float = 1.0,
        pitch: float = 1.0,
    ) -> TTSResult:
        """Synthesize text to speech."""
        pass

    def _ensure_output_path(self, output_path: Optional[str] = None, ext: str = ".mp3") -> str:
        """Generate output path if not provided."""
        if output_path:
            return output_path
        from shouchao.core.config import DATA_DIR
        audio_dir = DATA_DIR / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        import uuid
        return str(audio_dir / f"{uuid.uuid4().hex}{ext}")


class Pyttsx3TTS(BaseTTS):
    """pyttsx3 TTS engine - cross-platform offline synthesis using system voices."""

    def __init__(self):
        self._engine = None
        self._initialized = False

    @property
    def name(self) -> str:
        return "pyttsx3"

    @property
    def is_available(self) -> bool:
        try:
            import pyttsx3
            return True
        except ImportError:
            return False

    @property
    def is_offline(self) -> bool:
        return True

    def _init_engine(self):
        if self._initialized:
            return
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._initialized = True
            logger.info("pyttsx3 initialized with system voices")
        except Exception as e:
            logger.error(f"Failed to initialize pyttsx3: {e}")

    def get_voices(self, language: Optional[str] = None) -> list[VoiceInfo]:
        self._init_engine()
        if not self._engine:
            return []

        voices = []
        for v in self._engine.getProperty("voices"):
            lang = self._extract_language(v)
            if language and not lang.startswith(language):
                continue
            voices.append(VoiceInfo(
                id=v.id,
                name=v.name,
                language=lang,
                gender=self._extract_gender(v),
                engine=self.name,
                offline=True,
            ))
        return voices

    def synthesize(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice: Optional[str] = None,
        rate: float = 1.0,
        pitch: float = 1.0,
    ) -> TTSResult:
        self._init_engine()
        if not self._engine:
            return TTSResult(
                success=False,
                engine=self.name,
                error="pyttsx3 not initialized. Install with: pip install pyttsx3",
            )

        try:
            output_path = self._ensure_output_path(output_path, ".mp3")

            if voice:
                self._engine.setProperty("voice", voice)

            rate_val = int(self._engine.getProperty("rate") * rate)
            self._engine.setProperty("rate", rate_val)

            self._engine.save_to_file(text, output_path)
            self._engine.runAndWait()

            duration = self._get_audio_duration(output_path)

            return TTSResult(
                success=True,
                audio_path=output_path,
                duration=duration,
                engine=self.name,
                voice=voice or "default",
            )
        except Exception as e:
            logger.error(f"pyttsx3 synthesis error: {e}")
            return TTSResult(success=False, engine=self.name, error=str(e))

    def _extract_language(self, voice) -> str:
        try:
            for attr in ["languages", "language"]:
                if hasattr(voice, attr):
                    langs = getattr(voice, attr)
                    if langs:
                        if isinstance(langs, list):
                            return langs[0] if langs else "unknown"
                        return str(langs)
        except Exception:
            pass
        return "unknown"

    def _extract_gender(self, voice) -> str:
        name = voice.name.lower() if voice.name else ""
        if "female" in name or "woman" in name:
            return "female"
        if "male" in name or "man" in name:
            return "male"
        return "neutral"

    def _get_audio_duration(self, path: str) -> float:
        try:
            import mutagen
            audio = mutagen.File(path)
            if audio:
                return audio.info.length
        except Exception:
            pass
        return 0.0


class KokoroTTS(BaseTTS):
    """Kokoro TTS - high-quality offline neural synthesis.
    
    Uses local models from:
    - https://huggingface.co/hexgrad/Kokoro-82M
    
    Install: pip install kokoro
    Models are downloaded automatically or can be placed in ~/.shouchao/tts_models/kokoro/
    
    Note: Kokoro v0.7+ uses different voice names. Available voices:
    - English: af_bella, af_sarah, am_adam, am_michael
    - Chinese voices may not be available in all versions
    """

    VOICE_MAP = {
        "zh": ["af_bella"],  # Use English voice for Chinese (multilingual)
        "en": ["af_bella", "af_sarah", "am_adam", "am_michael"],
        "ja": ["af_bella"],
    }
    
    # Default voice for each language
    DEFAULT_VOICE = {
        "zh": "af_bella",
        "en": "af_bella",
        "ja": "af_bella",
    }

    def __init__(self, model_dir: Optional[str] = None):
        self._model_dir = model_dir or str(DEFAULT_TTS_MODEL_DIR / "kokoro")
        self._tts = None
        self._initialized = False
        self._pipelines = {}

    @property
    def name(self) -> str:
        return "kokoro"

    @property
    def is_available(self) -> bool:
        try:
            import kokoro
            return True
        except ImportError:
            return False

    @property
    def is_offline(self) -> bool:
        return True

    def _suppress_phonemizer_warnings(self):
        """Suppress phonemizer warnings that appear during Chinese synthesis."""
        import logging
        phonemizer_logger = logging.getLogger("phonemizer")
        phonemizer_logger.setLevel(logging.ERROR)

    def _init_tts(self):
        if self._initialized:
            return
        try:
            import torch
            
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Initializing Kokoro TTS on {device}")
            
            self._suppress_phonemizer_warnings()
            self._initialized = True
            logger.info("Kokoro TTS initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kokoro TTS: {e}")

    def _get_pipeline(self, voice: str):
        """Get or create pipeline for specific voice language."""
        if voice in self._pipelines:
            return self._pipelines[voice]
        
        try:
            from kokoro import KPipeline
            import torch
            
            device = "cuda" if torch.cuda.is_available() else "cpu"
            # Use 'a' for all voices (Kokoro's multilingual mode)
            pipeline = KPipeline(lang_code='a', device=device)
            self._pipelines[voice] = pipeline
            return pipeline
        except Exception as e:
            logger.error(f"Failed to create pipeline for voice {voice}: {e}")
            return None
    
    def get_voices(self, language: Optional[str] = None) -> list[VoiceInfo]:
        if not self.is_available:
            return []
        
        voices = []
        # Kokoro v0.7+ standard voices
        kokoro_voices = [
            ("af_bella", "Bella (Female)", "en", "female"),
            ("af_sarah", "Sarah (Female)", "en", "female"),
            ("am_adam", "Adam (Male)", "en", "male"),
            ("am_michael", "Michael (Male)", "en", "male"),
        ]
        
        for vid, vname, vlang, vgender in kokoro_voices:
            if language and vlang != language:
                continue
            voices.append(VoiceInfo(
                id=vid,
                name=vname,
                language=vlang,
                gender=vgender,
                engine=self.name,
                offline=True,
            ))
        return voices

    def synthesize(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice: Optional[str] = None,
        rate: float = 1.0,
        pitch: float = 1.0,
    ) -> TTSResult:
        if not self.is_available:
            return TTSResult(
                success=False,
                engine=self.name,
                error="kokoro not installed. Install with: pip install kokoro",
            )
        
        self._init_tts()
        
        if not voice:
            voice = "af_bella"
        
        pipeline = self._get_pipeline(voice)
        if not pipeline:
            return TTSResult(
                success=False,
                engine=self.name,
                error="Failed to create TTS pipeline",
            )

        try:
            self._suppress_phonemizer_warnings()
            output_path = self._ensure_output_path(output_path, ".wav")
            
            # Clean text: remove markdown formatting
            import re
            clean_text = text
            clean_text = re.sub(r'#+\s*', '', clean_text)  # Remove headings
            clean_text = re.sub(r'\*\*(.+?)\*\*', r'\1', clean_text)  # Remove bold
            clean_text = re.sub(r'\*(.+?)\*', r'\1', clean_text)  # Remove italic
            clean_text = re.sub(r'`(.+?)`', r'\1', clean_text)  # Remove code
            clean_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean_text)  # Remove links
            clean_text = re.sub(r'^\s*[-*]\s*', '', clean_text, flags=re.MULTILINE)  # Remove list markers
            clean_text = re.sub(r'\n+', ' ', clean_text)  # Replace newlines with space
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()  # Normalize whitespace
            
            speed = 1.0 / rate if rate > 0 else 1.0
            
            audio_segments = []
            for _, _, audio in pipeline(clean_text, voice=voice, speed=speed):
                audio_segments.append(audio)
            
            if not audio_segments:
                return TTSResult(
                    success=False,
                    engine=self.name,
                    error="No audio generated",
                    voice=voice,
                )
            
            import numpy as np
            combined = np.concatenate(audio_segments)
            
            import soundfile as sf
            sf.write(output_path, combined, samplerate=24000)
            
            duration = len(combined) / 24000

            return TTSResult(
                success=True,
                audio_path=output_path,
                duration=duration,
                engine=self.name,
                voice=voice,
            )
        except Exception as e:
            logger.error(f"Kokoro TTS synthesis error: {e}")
            return TTSResult(success=False, engine=self.name, error=str(e), voice=voice or "default")


class MeloTTS(BaseTTS):
    """MeloTTS - high-quality offline TTS by MyShell.
    
    Supports multiple languages with local models.
    
    Install: pip install melo-tts
    """

    LANGUAGE_MAP = {
        "zh": "ZH",
        "en": "EN",
        "ja": "JP",
        "ko": "KR",
        "es": "ES",
        "fr": "FR",
        "de": "DE",
        "ru": "RU",
    }

    def __init__(self):
        self._tts = {}
        self._initialized_langs = set()

    @property
    def name(self) -> str:
        return "melo"

    @property
    def is_available(self) -> bool:
        try:
            from melo_tts import MeloTTS as MTTS
            return True
        except ImportError:
            return False

    @property
    def is_offline(self) -> bool:
        return True

    def _init_tts(self, language: str):
        if language in self._initialized_langs:
            return True
        
        try:
            from melo_tts import MeloTTS as MTTS
            
            lang_code = self.LANGUAGE_MAP.get(language, "EN")
            self._tts[language] = MTTS(language=lang_code, device="auto")
            self._initialized_langs.add(language)
            logger.info(f"MeloTTS initialized for {language}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize MeloTTS for {language}: {e}")
            return False

    def get_voices(self, language: Optional[str] = None) -> list[VoiceInfo]:
        if not self.is_available:
            return []
        
        voices = []
        for lang in self.LANGUAGE_MAP.keys():
            if language and not lang.startswith(language):
                continue
            voices.append(VoiceInfo(
                id=f"{lang}_default",
                name=f"{lang.upper()} Default",
                language=lang,
                engine=self.name,
                offline=True,
            ))
        return voices

    def synthesize(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice: Optional[str] = None,
        rate: float = 1.0,
        pitch: float = 1.0,
    ) -> TTSResult:
        if not self.is_available:
            return TTSResult(
                success=False,
                engine=self.name,
                error="melo-tts not installed. Install with: pip install melo-tts",
            )
        
        language = "en"
        if voice and "_" in voice:
            language = voice.split("_")[0]
        
        if not self._init_tts(language):
            return TTSResult(
                success=False,
                engine=self.name,
                error=f"Failed to initialize MeloTTS for {language}",
            )

        try:
            output_path = self._ensure_output_path(output_path, ".wav")
            
            speed = 1.0 / rate if rate > 0 else 1.0
            
            self._tts[language].tts_to_file(text, output_path, speed=speed)
            
            duration = self._get_wav_duration(output_path)

            return TTSResult(
                success=True,
                audio_path=output_path,
                duration=duration,
                engine=self.name,
                voice=voice or f"{language}_default",
            )
        except Exception as e:
            logger.error(f"MeloTTS synthesis error: {e}")
            return TTSResult(success=False, engine=self.name, error=str(e))

    def _get_wav_duration(self, path: str) -> float:
        try:
            with wave.open(path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                return frames / float(rate)
        except Exception:
            return 0.0


class EdgeTTS(BaseTTS):
    """Microsoft Edge TTS - high quality online synthesis."""

    DEFAULT_VOICES = {
        "zh": "zh-CN-XiaoxiaoNeural",
        "en": "en-US-JennyNeural",
        "ja": "ja-JP-NanamiNeural",
        "ko": "ko-KR-SunHiNeural",
        "fr": "fr-FR-DeniseNeural",
        "de": "de-DE-KatjaNeural",
        "es": "es-ES-ElviraNeural",
        "pt": "pt-BR-FranciscaNeural",
        "it": "it-IT-ElsaNeural",
        "ru": "ru-RU-DariyaNeural",
    }

    def __init__(self):
        self._voices_cache: Optional[list[VoiceInfo]] = None

    @property
    def name(self) -> str:
        return "edge-tts"

    @property
    def is_available(self) -> bool:
        try:
            import edge_tts
            return True
        except ImportError:
            return False

    @property
    def is_offline(self) -> bool:
        return False

    async def _list_voices_async(self) -> list[VoiceInfo]:
        try:
            import edge_tts
            voices = await edge_tts.list_voices()
            result = []
            for v in voices:
                locale = v.get("Locale", "")
                result.append(VoiceInfo(
                    id=v.get("ShortName", ""),
                    name=v.get("FriendlyName", ""),
                    language=locale,
                    gender=v.get("Gender", "Neutral").lower(),
                    engine=self.name,
                    offline=False,
                    metadata={
                        "locale": locale,
                        "suggested_codec": v.get("SuggestedCodec", ""),
                    },
                ))
            return result
        except Exception as e:
            logger.error(f"Failed to list Edge TTS voices: {e}")
            return []

    def get_voices(self, language: Optional[str] = None) -> list[VoiceInfo]:
        if not self.is_available:
            return []

        if self._voices_cache is None:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._voices_cache = loop.run_until_complete(self._list_voices_async())
                loop.close()
            except Exception as e:
                logger.error(f"Failed to get Edge TTS voices: {e}")
                self._voices_cache = []

        if language:
            return [v for v in self._voices_cache if v.language.startswith(language)]
        return self._voices_cache

    async def _synthesize_async(
        self,
        text: str,
        output_path: str,
        voice: str,
        rate: float,
    ) -> TTSResult:
        try:
            import edge_tts

            if rate == 1.0:
                rate_str = "+0%"
            elif rate > 1:
                rate_str = f"+{int((rate - 1) * 100)}%"
            else:
                rate_str = f"{int((rate - 1) * 100)}%"

            communicate = edge_tts.Communicate(text, voice, rate=rate_str)
            await communicate.save(output_path)

            duration = self._get_duration_mp3(output_path)

            return TTSResult(
                success=True,
                audio_path=output_path,
                duration=duration,
                engine=self.name,
                voice=voice,
            )
        except Exception as e:
            return TTSResult(success=False, engine=self.name, error=str(e))

    def synthesize(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice: Optional[str] = None,
        rate: float = 1.0,
        pitch: float = 1.0,
    ) -> TTSResult:
        if not self.is_available:
            return TTSResult(
                success=False,
                engine=self.name,
                error="edge-tts not installed. Run: pip install edge-tts",
            )

        output_path = self._ensure_output_path(output_path)
        if not output_path.endswith(".mp3"):
            output_path = output_path.rsplit(".", 1)[0] + ".mp3"

        if not voice:
            from shouchao.core.config import CONFIG
            lang = CONFIG.language
            voice = self.DEFAULT_VOICES.get(lang, "en-US-JennyNeural")

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self._synthesize_async(text, output_path, voice, rate)
            )
            loop.close()
            return result
        except Exception as e:
            logger.error(f"Edge TTS synthesis error: {e}")
            return TTSResult(success=False, engine=self.name, error=str(e))

    def _get_duration_mp3(self, path: str) -> float:
        try:
            from mutagen.mp3 import MP3
            audio = MP3(path)
            return audio.info.length
        except Exception:
            pass
        return 0.0


class SherpaOnnxTTS(BaseTTS):
    """Sherpa-ONNX TTS - offline neural synthesis."""

    def __init__(self, model_dir: Optional[str] = None):
        self._model_dir = model_dir
        self._tts = None
        self._initialized = False

    @property
    def name(self) -> str:
        return "sherpa-onnx"

    @property
    def is_available(self) -> bool:
        try:
            import sherpa_onnx
            return True
        except ImportError:
            return False

    @property
    def is_offline(self) -> bool:
        return True

    def _init_tts(self, model_path: Optional[str] = None):
        if self._initialized:
            return

        try:
            import sherpa_onnx

            if not model_path and not self._model_dir:
                return

            model_dir = Path(model_path or self._model_dir)
            if not model_dir.exists():
                return

            self._tts = sherpa_onnx.OfflineTts(
                provider="cpu",
                model_num_threads=4,
                debug=False,
                tokens=str(model_dir / "tokens.txt"),
                data_dir=str(model_dir),
            )
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Sherpa-ONNX TTS: {e}")

    def get_voices(self, language: Optional[str] = None) -> list[VoiceInfo]:
        if not self.is_available:
            return []
        return [
            VoiceInfo(
                id="default",
                name="Default Sherpa Voice",
                language="multi",
                engine=self.name,
            )
        ]

    def synthesize(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice: Optional[str] = None,
        rate: float = 1.0,
        pitch: float = 1.0,
    ) -> TTSResult:
        self._init_tts()
        if not self._tts:
            return TTSResult(
                success=False,
                engine=self.name,
                error="Sherpa-ONNX TTS not initialized. "
                      "Install with: pip install sherpa-onnx, and download TTS models.",
            )

        try:
            output_path = self._ensure_output_path(output_path)
            if not output_path.endswith(".wav"):
                output_path = output_path.rsplit(".", 1)[0] + ".wav"

            speaker_id = 0
            speed = 1.0 / rate

            audio = self._tts.generate(text, sid=speaker_id, speed=speed)

            with wave.open(output_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self._tts.sample_rate)
                wf.writeframes(audio.samples)

            duration = len(audio.samples) / (self._tts.sample_rate * 2)

            return TTSResult(
                success=True,
                audio_path=output_path,
                duration=duration,
                engine=self.name,
                voice="default",
            )
        except Exception as e:
            logger.error(f"Sherpa-ONNX synthesis error: {e}")
            return TTSResult(success=False, engine=self.name, error=str(e))


class GTTSEngine(BaseTTS):
    """Google Translate TTS - simple online synthesis."""

    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "gtts"

    @property
    def is_available(self) -> bool:
        try:
            from gtts import gTTS
            return True
        except ImportError:
            return False

    @property
    def is_offline(self) -> bool:
        return False

    def get_voices(self, language: Optional[str] = None) -> list[VoiceInfo]:
        from gtts import lang

        voices = []
        try:
            langs = lang.tts_langs()
            for code, name in langs.items():
                if language and not code.startswith(language):
                    continue
                voices.append(VoiceInfo(
                    id=code,
                    name=name,
                    language=code,
                    engine=self.name,
                    offline=False,
                ))
        except Exception:
            pass
        return voices

    def synthesize(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice: Optional[str] = None,
        rate: float = 1.0,
        pitch: float = 1.0,
    ) -> TTSResult:
        if not self.is_available:
            return TTSResult(
                success=False,
                engine=self.name,
                error="gTTS not installed. Run: pip install gtts",
            )

        try:
            from gtts import gTTS

            output_path = self._ensure_output_path(output_path)
            if not output_path.endswith(".mp3"):
                output_path = output_path.rsplit(".", 1)[0] + ".mp3"

            lang = voice or "en"

            tts = gTTS(text=text, lang=lang, slow=rate < 0.8)
            tts.save(output_path)

            duration = self._get_duration(output_path)

            return TTSResult(
                success=True,
                audio_path=output_path,
                duration=duration,
                engine=self.name,
                voice=lang,
            )
        except Exception as e:
            logger.error(f"gTTS synthesis error: {e}")
            return TTSResult(success=False, engine=self.name, error=str(e))

    def _get_duration(self, path: str) -> float:
        try:
            from mutagen.mp3 import MP3
            audio = MP3(path)
            return audio.info.length
        except Exception:
            pass
        return 0.0


class TTSEngine:
    """
    Unified TTS interface supporting multiple backends.
    
    Supported engines:
    - pyttsx3: Offline, uses system voices (pip install pyttsx3)
    - kokoro: Offline, high-quality neural TTS (pip install kokoro)
    - melo: Offline, multi-language TTS (pip install melo-tts)
    - sherpa-onnx: Offline, ONNX-based TTS (pip install sherpa-onnx)
    - edge-tts: Online, Microsoft Edge TTS (pip install edge-tts)
    - gtts: Online, Google Translate TTS (pip install gtts)

    Usage:
        tts = TTSEngine()
        result = tts.synthesize("Hello world", engine="pyttsx3", language="en")
        if result.success:
            print(f"Audio saved to: {result.audio_path}")
    """

    def __init__(self, preferred_engine: Optional[str] = None):
        self._engines: dict[str, BaseTTS] = {}
        self._preferred = preferred_engine

        # Register offline engines first (preferred)
        self._register_engine("pyttsx3", Pyttsx3TTS())
        self._register_engine("kokoro", KokoroTTS())
        self._register_engine("melo", MeloTTS())
        self._register_engine("sherpa-onnx", SherpaOnnxTTS())
        # Online engines
        self._register_engine("edge-tts", EdgeTTS())
        self._register_engine("gtts", GTTSEngine())

    def _register_engine(self, name: str, engine: BaseTTS):
        if engine.is_available:
            self._engines[name] = engine
            logger.info(f"Registered TTS engine: {name} (offline={engine.is_offline})")

    @property
    def available_engines(self) -> list[str]:
        """List available TTS engine names."""
        return list(self._engines.keys())

    @property
    def offline_engines(self) -> list[str]:
        """List offline TTS engine names."""
        return [name for name, eng in self._engines.items() if eng.is_offline]

    def get_voices(
        self,
        engine: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list[VoiceInfo]:
        """Get available voices for an engine."""
        engine_name = engine or self._get_default_engine()
        if engine_name not in self._engines:
            return []
        return self._engines[engine_name].get_voices(language)

    def synthesize(
        self,
        text: str,
        output_path: Optional[str] = None,
        engine: Optional[str] = None,
        voice: Optional[str] = None,
        language: Optional[str] = None,
        rate: float = 1.0,
        pitch: float = 1.0,
    ) -> TTSResult:
        """
        Synthesize text to speech.

        Args:
            text: Text to synthesize.
            output_path: Output audio file path (auto-generated if None).
            engine: TTS engine to use (edge-tts, pyttsx3, gtts, sherpa-onnx).
            voice: Voice ID to use.
            language: Language code for voice selection.
            rate: Speech rate multiplier (1.0 = normal).
            pitch: Pitch multiplier (not all engines support this).

        Returns:
            TTSResult with audio path and metadata.
        """
        engine_name = engine or self._get_default_engine()

        if engine_name not in self._engines:
            return TTSResult(
                success=False,
                engine=engine_name,
                error=f"Engine '{engine_name}' not available. "
                      f"Available: {self.available_engines}",
            )

        if not voice and language:
            voices = self._engines[engine_name].get_voices(language)
            if voices:
                voice = voices[0].id

        return self._engines[engine_name].synthesize(
            text=text,
            output_path=output_path,
            voice=voice,
            rate=rate,
            pitch=pitch,
        )

    def synthesize_long(
        self,
        text: str,
        output_path: Optional[str] = None,
        engine: Optional[str] = None,
        voice: Optional[str] = None,
        language: Optional[str] = None,
        rate: float = 1.0,
        chunk_size: int = 5000,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> TTSResult:
        """
        Synthesize long text by chunking.

        Args:
            text: Long text to synthesize.
            output_path: Output audio file path.
            engine: TTS engine to use.
            voice: Voice ID.
            language: Language code.
            rate: Speech rate multiplier.
            chunk_size: Maximum characters per chunk.
            on_progress: Callback for progress updates.

        Returns:
            TTSResult with combined audio.
        """
        chunks = self._split_text(text, chunk_size)
        if not chunks:
            return TTSResult(success=False, error="No text to synthesize")

        engine_name = engine or self._get_default_engine()
        if engine_name not in self._engines:
            return TTSResult(
                success=False,
                error=f"Engine '{engine_name}' not available",
            )

        temp_files = []
        total_duration = 0.0

        for i, chunk in enumerate(chunks):
            if on_progress:
                on_progress(i + 1, len(chunks))

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name

            result = self.synthesize(
                text=chunk,
                output_path=tmp_path,
                engine=engine_name,
                voice=voice,
                language=language,
                rate=rate,
            )

            if not result.success:
                for f in temp_files:
                    try:
                        os.unlink(f)
                    except Exception:
                        pass
                return result

            temp_files.append(result.audio_path)
            total_duration += result.duration

        output_path = self._ensure_output_path(output_path)

        combined_result = self._concatenate_audio(temp_files, output_path)

        for f in temp_files:
            try:
                os.unlink(f)
            except Exception:
                pass

        if combined_result:
            return TTSResult(
                success=True,
                audio_path=output_path,
                duration=total_duration,
                engine=engine_name,
                voice=voice or "default",
            )
        else:
            return TTSResult(
                success=False,
                error="Failed to concatenate audio chunks",
            )

    def _get_default_engine(self) -> str:
        if self._preferred and self._preferred in self._engines:
            return self._preferred

        for name in ["edge-tts", "pyttsx3", "gtts"]:
            if name in self._engines:
                return name

        return list(self._engines.keys())[0] if self._engines else ""

    def _ensure_output_path(self, output_path: Optional[str] = None) -> str:
        if output_path:
            return output_path
        from shouchao.core.config import DATA_DIR
        audio_dir = DATA_DIR / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        import uuid
        return str(audio_dir / f"{uuid.uuid4().hex}.mp3")

    def _split_text(self, text: str, chunk_size: int) -> list[str]:
        """Split text into chunks at sentence boundaries."""
        import re

        sentences = re.split(r"(?<=[.!?。！？])\s*", text)
        chunks = []
        current = ""

        for sentence in sentences:
            if not sentence:
                continue
            if len(current) + len(sentence) <= chunk_size:
                current += sentence + " "
            else:
                if current:
                    chunks.append(current.strip())
                current = sentence + " "

        if current:
            chunks.append(current.strip())

        return chunks

    def _concatenate_audio(self, files: list[str], output: str) -> bool:
        """Concatenate multiple audio files."""
        try:
            from pydub import AudioSegment

            combined = AudioSegment.empty()
            for f in files:
                audio = AudioSegment.from_mp3(f)
                combined += audio

            combined.export(output, format="mp3")
            return True
        except ImportError:
            logger.warning("pydub not installed, cannot concatenate audio chunks")
            if files:
                import shutil
                shutil.copy(files[0], output)
                return True
            return False
        except Exception as e:
            logger.error(f"Error concatenating audio: {e}")
            return False


def text_to_speech(
    text: str,
    output_path: Optional[str] = None,
    engine: Optional[str] = None,
    language: Optional[str] = None,
) -> TTSResult:
    """
    Convenience function for text-to-speech synthesis.

    Args:
        text: Text to synthesize.
        output_path: Output file path.
        engine: TTS engine (edge-tts, pyttsx3, gtts).
        language: Language code.

    Returns:
        TTSResult with audio path.
    """
    tts = TTSEngine()
    return tts.synthesize(
        text=text,
        output_path=output_path,
        engine=engine,
        language=language,
    )