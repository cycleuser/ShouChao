"""
Tests for TTS (Text-to-Speech) module.
"""

import pytest
from unittest.mock import patch, MagicMock
from tempfile import NamedTemporaryFile
import os


class TestTTSResult:
    def test_tts_result_creation(self):
        from shouchao.core.tts import TTSResult
        result = TTSResult(
            success=True,
            audio_path="/tmp/test.mp3",
            duration=5.5,
            engine="edge-tts",
            voice="en-US-JennyNeural",
        )
        assert result.success is True
        assert result.audio_path == "/tmp/test.mp3"
        assert result.duration == 5.5
        assert result.engine == "edge-tts"

    def test_tts_result_to_dict(self):
        from shouchao.core.tts import TTSResult
        result = TTSResult(
            success=False,
            error="Something went wrong",
            engine="gtts",
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] == "Something went wrong"
        assert d["engine"] == "gtts"

    def test_tts_result_defaults(self):
        from shouchao.core.tts import TTSResult
        result = TTSResult(success=True)
        assert result.audio_path is None
        assert result.duration == 0.0
        assert result.error is None
        assert result.metadata == {}


class TestVoiceInfo:
    def test_voice_info_creation(self):
        from shouchao.core.tts import VoiceInfo
        voice = VoiceInfo(
            id="en-US-JennyNeural",
            name="Jenny",
            language="en-US",
            gender="female",
            engine="edge-tts",
        )
        assert voice.id == "en-US-JennyNeural"
        assert voice.name == "Jenny"
        assert voice.language == "en-US"
        assert voice.gender == "female"

    def test_voice_info_to_dict(self):
        from shouchao.core.tts import VoiceInfo
        voice = VoiceInfo(
            id="test-voice",
            name="Test Voice",
            language="en",
            engine="pyttsx3",
        )
        d = voice.to_dict()
        assert d["id"] == "test-voice"
        assert d["name"] == "Test Voice"
        assert d["language"] == "en"
        assert d["engine"] == "pyttsx3"


class TestPyttsx3TTS:
    def test_engine_name(self):
        from shouchao.core.tts import Pyttsx3TTS
        engine = Pyttsx3TTS()
        assert engine.name == "pyttsx3"

    def test_is_available_without_package(self):
        from shouchao.core.tts import Pyttsx3TTS
        engine = Pyttsx3TTS()
        with patch.dict("sys.modules", {"pyttsx3": None}):
            available = engine.is_available
            assert available is False

    def test_get_voices_empty_without_init(self):
        from shouchao.core.tts import Pyttsx3TTS
        engine = Pyttsx3TTS()
        voices = engine.get_voices()
        assert isinstance(voices, list)


class TestEdgeTTS:
    def test_engine_name(self):
        from shouchao.core.tts import EdgeTTS
        engine = EdgeTTS()
        assert engine.name == "edge-tts"

    def test_is_available_without_package(self):
        from shouchao.core.tts import EdgeTTS
        engine = EdgeTTS()
        with patch.dict("sys.modules", {"edge_tts": None}):
            available = engine.is_available
            assert available is False

    def test_default_voices(self):
        from shouchao.core.tts import EdgeTTS
        assert "zh" in EdgeTTS.DEFAULT_VOICES
        assert "en" in EdgeTTS.DEFAULT_VOICES
        assert EdgeTTS.DEFAULT_VOICES["zh"] == "zh-CN-XiaoxiaoNeural"


class TestGTTSEngine:
    def test_engine_name(self):
        from shouchao.core.tts import GTTSEngine
        engine = GTTSEngine()
        assert engine.name == "gtts"

    def test_is_available_without_package(self):
        from shouchao.core.tts import GTTSEngine
        engine = GTTSEngine()
        with patch.dict("sys.modules", {"gtts": None}):
            available = engine.is_available
            assert available is False


class TestSherpaOnnxTTS:
    def test_engine_name(self):
        from shouchao.core.tts import SherpaOnnxTTS
        engine = SherpaOnnxTTS()
        assert engine.name == "sherpa-onnx"

    def test_is_available_without_package(self):
        from shouchao.core.tts import SherpaOnnxTTS
        engine = SherpaOnnxTTS()
        with patch.dict("sys.modules", {"sherpa_onnx": None}):
            available = engine.is_available
            assert available is False


class TestTTSEngine:
    def test_available_engines(self):
        from shouchao.core.tts import TTSEngine
        tts = TTSEngine()
        engines = tts.available_engines
        assert isinstance(engines, list)

    def test_synthesize_with_unavailable_engine(self):
        from shouchao.core.tts import TTSEngine
        tts = TTSEngine()
        result = tts.synthesize(
            text="Hello",
            engine="nonexistent_engine",
        )
        assert result.success is False
        assert "not available" in result.error

    def test_get_voices_for_engine(self):
        from shouchao.core.tts import TTSEngine
        tts = TTSEngine()
        voices = tts.get_voices(engine="gtts", language="en")
        assert isinstance(voices, list)

    def test_split_text(self):
        from shouchao.core.tts import TTSEngine
        tts = TTSEngine()
        text = "First sentence. Second sentence. Third sentence."
        chunks = tts._split_text(text, chunk_size=20)
        assert len(chunks) >= 1

    def test_split_text_preserves_sentences(self):
        from shouchao.core.tts import TTSEngine
        tts = TTSEngine()
        text = "This is sentence one. This is sentence two."
        chunks = tts._split_text(text, chunk_size=100)
        full_text = " ".join(chunks)
        assert "sentence one" in full_text
        assert "sentence two" in full_text


class TestTextToSpeechFunction:
    def test_function_exists(self):
        from shouchao.core.tts import text_to_speech
        assert callable(text_to_speech)

    def test_function_returns_tts_result(self):
        from shouchao.core.tts import text_to_speech, TTSResult
        with patch("shouchao.core.tts.TTSEngine.synthesize") as mock_synthesize:
            mock_synthesize.return_value = TTSResult(
                success=True,
                audio_path="/tmp/test.mp3",
                engine="edge-tts",
            )
            result = text_to_speech(text="Test")
            assert isinstance(result, TTSResult)


class TestTTSErrorHandling:
    def test_synthesize_handles_exceptions(self):
        from shouchao.core.tts import TTSEngine
        tts = TTSEngine()
        result = tts.synthesize(
            text="Test text",
            engine="invalid_engine_name",
        )
        assert result.success is False
        assert result.error is not None

    def test_long_text_synthesize_handles_errors(self):
        from shouchao.core.tts import TTSEngine
        tts = TTSEngine()
        result = tts.synthesize_long(
            text="",
            engine="edge-tts",
        )
        assert result.success is False