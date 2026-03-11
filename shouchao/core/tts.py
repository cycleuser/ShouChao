"""
Text-to-Speech module for ShouChao.

Supports multiple TTS backends:
- pyttsx3: Cross-platform offline TTS (no internet required)
- edge-tts: Microsoft Edge TTS (high quality, requires internet)
- sherpa-onnx: Neural TTS with local models (offline, high quality)
- gTTS: Google Translate TTS (online)

Provides unified interface for converting text to speech and exporting to audio files.
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
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "language": self.language,
            "gender": self.gender,
            "engine": self.engine,
            "sample_rate": self.sample_rate,
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

    def _ensure_output_path(self, output_path: Optional[str] = None) -> str:
        """Generate output path if not provided."""
        if output_path:
            return output_path
        from shouchao.core.config import DATA_DIR
        audio_dir = DATA_DIR / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        import uuid
        return str(audio_dir / f"{uuid.uuid4().hex}.mp3")


class Pyttsx3TTS(BaseTTS):
    """pyttsx3 TTS engine - cross-platform offline synthesis."""

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

    def _init_engine(self):
        if self._initialized:
            return
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._initialized = True
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
            output_path = self._ensure_output_path(output_path)
            if not output_path.endswith(".mp3"):
                output_path = output_path.rsplit(".", 1)[0] + ".mp3"

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

    Usage:
        tts = TTSEngine()
        result = tts.synthesize("Hello world", engine="edge-tts", language="en")
        if result.success:
            print(f"Audio saved to: {result.audio_path}")
    """

    def __init__(self, preferred_engine: Optional[str] = None):
        self._engines: dict[str, BaseTTS] = {}
        self._preferred = preferred_engine

        self._register_engine("pyttsx3", Pyttsx3TTS())
        self._register_engine("edge-tts", EdgeTTS())
        self._register_engine("sherpa-onnx", SherpaOnnxTTS())
        self._register_engine("gtts", GTTSEngine())

    def _register_engine(self, name: str, engine: BaseTTS):
        if engine.is_available:
            self._engines[name] = engine

    @property
    def available_engines(self) -> list[str]:
        """List available TTS engine names."""
        return list(self._engines.keys())

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