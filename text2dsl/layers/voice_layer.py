"""
Voice Layer - Warstwa konwersji głos <-> tekst

Obsługuje:
- STT (Speech-to-Text) przez różne backendy
- TTS (Text-to-Speech) przez różne backendy
- Streaming audio
- Wake word detection
- Wielojęzyczność (PL, DE, EN)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict, Any, Generator
from enum import Enum, auto
import threading
import queue
import time
import os
import contextlib
import io


class VoiceBackend(Enum):
    """Dostępne backendy głosowe"""

    # STT
    WHISPER = auto()  # OpenAI Whisper (lokalnie)
    WHISPER_API = auto()  # OpenAI Whisper API
    GOOGLE_STT = auto()  # Google Speech-to-Text
    VOSK = auto()  # Vosk (offline)

    # TTS
    PYTTSX3 = auto()  # pyttsx3 (offline)
    GTTS = auto()  # Google TTS
    ELEVENLABS = auto()  # ElevenLabs
    ESPEAK = auto()  # eSpeak (offline)
    EDGE_TTS = auto()  # Microsoft Edge TTS


class Language(Enum):
    """Obsługiwane języki"""

    POLISH = "pl"
    GERMAN = "de"
    ENGLISH = "en"

    @classmethod
    def from_code(cls, code: str) -> "Language":
        """Tworzy Language z kodu języka"""
        code = code.lower()[:2]
        for lang in cls:
            if lang.value == code:
                return lang
        return cls.ENGLISH  # domyślny


@dataclass
class LanguageConfig:
    """Konfiguracja dla konkretnego języka"""

    code: str
    name: str
    whisper_code: str
    edge_tts_voice: str
    pyttsx3_voice_pattern: str
    espeak_voice: str
    wake_words: List[str]

    # Komunikaty systemowe
    messages: Dict[str, str] = field(default_factory=dict)


# Konfiguracje dla wszystkich języków
LANGUAGE_CONFIGS: Dict[str, LanguageConfig] = {
    "pl": LanguageConfig(
        code="pl",
        name="Polski",
        whisper_code="pl",
        edge_tts_voice="pl-PL-MarekNeural",
        pyttsx3_voice_pattern="polish",
        espeak_voice="pl",
        wake_words=["hej asystent", "słuchaj", "komenda"],
        messages={
            "welcome": "Witaj! Jak mogę pomóc?",
            "goodbye": "Do widzenia!",
            "listening": "Słucham...",
            "processing": "Przetwarzam...",
            "error": "Wystąpił błąd",
            "success": "Wykonano pomyślnie",
            "confirm": "Czy potwierdzasz?",
            "cancelled": "Anulowano",
            "no_suggestions": "Brak sugestii",
            "available_options": "Dostępne opcje",
            "next_step": "Następny krok",
            "repeat": "Powtórz",
            "help": "Pomoc",
        },
    ),
    "de": LanguageConfig(
        code="de",
        name="Deutsch",
        whisper_code="de",
        edge_tts_voice="de-DE-ConradNeural",
        pyttsx3_voice_pattern="german",
        espeak_voice="de",
        wake_words=["hey assistent", "höre", "befehl"],
        messages={
            "welcome": "Willkommen! Wie kann ich helfen?",
            "goodbye": "Auf Wiedersehen!",
            "listening": "Ich höre...",
            "processing": "Verarbeite...",
            "error": "Ein Fehler ist aufgetreten",
            "success": "Erfolgreich ausgeführt",
            "confirm": "Bestätigen Sie?",
            "cancelled": "Abgebrochen",
            "no_suggestions": "Keine Vorschläge",
            "available_options": "Verfügbare Optionen",
            "next_step": "Nächster Schritt",
            "repeat": "Wiederholen",
            "help": "Hilfe",
        },
    ),
    "en": LanguageConfig(
        code="en",
        name="English",
        whisper_code="en",
        edge_tts_voice="en-US-GuyNeural",
        pyttsx3_voice_pattern="english",
        espeak_voice="en",
        wake_words=["hey assistant", "listen", "command"],
        messages={
            "welcome": "Welcome! How can I help?",
            "goodbye": "Goodbye!",
            "listening": "Listening...",
            "processing": "Processing...",
            "error": "An error occurred",
            "success": "Completed successfully",
            "confirm": "Do you confirm?",
            "cancelled": "Cancelled",
            "no_suggestions": "No suggestions",
            "available_options": "Available options",
            "next_step": "Next step",
            "repeat": "Repeat",
            "help": "Help",
        },
    ),
}


def get_language_config(lang_code: str) -> LanguageConfig:
    """Pobiera konfigurację dla języka"""
    code = lang_code.lower()[:2]
    return LANGUAGE_CONFIGS.get(code, LANGUAGE_CONFIGS["en"])


@dataclass
class VoiceConfig:
    """Konfiguracja warstwy głosowej"""

    stt_backend: VoiceBackend = VoiceBackend.WHISPER
    tts_backend: VoiceBackend = VoiceBackend.EDGE_TTS
    language: str = "pl"
    debug: bool = False
    sample_rate: int = 16000
    wake_word: Optional[str] = None  # np. "hej asystent"
    voice_name: Optional[str] = None
    speech_rate: int = 150  # słów na minutę
    volume: float = 1.0
    silence_threshold: float = 0.03
    silence_duration: float = 1.0  # sekundy ciszy = koniec mowy
    auto_detect_language: bool = False  # automatyczne wykrywanie języka

    def get_lang_config(self) -> LanguageConfig:
        """Pobiera konfigurację dla aktualnego języka"""
        return get_language_config(self.language)

    def get_message(self, key: str) -> str:
        """Pobiera przetłumaczony komunikat"""
        return self.get_lang_config().messages.get(key, key)


@dataclass
class TranscriptionResult:
    """Wynik transkrypcji"""

    text: str
    confidence: float = 1.0
    language: str = "pl"
    duration_ms: int = 0
    is_final: bool = True
    alternatives: List[str] = field(default_factory=list)


class STTProvider(ABC):
    """Abstrakcyjny provider STT"""

    @abstractmethod
    def transcribe(self, audio_data: bytes) -> TranscriptionResult:
        """Transkrybuje audio na tekst"""
        pass

    @abstractmethod
    def start_streaming(self, callback: Callable[[TranscriptionResult], None]):
        """Rozpoczyna transkrypcję strumieniową"""
        pass

    @abstractmethod
    def stop_streaming(self):
        """Zatrzymuje transkrypcję strumieniową"""
        pass


class TTSProvider(ABC):
    """Abstrakcyjny provider TTS"""

    @abstractmethod
    def synthesize(self, text: str) -> bytes:
        """Syntezuje tekst na audio"""
        pass

    @abstractmethod
    def speak(self, text: str):
        """Odtwarza tekst jako mowę"""
        pass

    @abstractmethod
    def stop(self):
        """Zatrzymuje odtwarzanie"""
        pass


class WhisperSTT(STTProvider):
    """Provider STT używający Whisper z obsługą wielu języków"""

    def __init__(self, config: VoiceConfig):
        self.config = config
        self.model = None
        self._streaming = False
        self._stream_thread: Optional[threading.Thread] = None
        self.lang_config = config.get_lang_config()

    def _ensure_model(self):
        """Ładuje model Whisper jeśli nie załadowany"""
        if self.model is None:
            try:
                import whisper

                # Użyj mniejszego modelu dla szybkości
                model_name = os.getenv("WHISPER_MODEL", "base")
                if getattr(self.config, "debug", False):
                    print(
                        f"[text2dsl][voice][debug] stt.whisper.load_model {{'model': '{model_name}'}}"
                    )
                self.model = whisper.load_model(model_name)
            except ImportError:
                raise ImportError("Zainstaluj whisper: pip install openai-whisper")

    def _check_streaming_deps(self):
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                import pyaudio  # noqa: F401
            import numpy  # noqa: F401
        except Exception as e:
            msg = str(e)
            hint = ""
            if "GLIBCXX_" in msg or "libstdc++" in msg:
                hint = (
                    "\nWygląda na konflikt libstdc++ (np. Conda vs system). "
                    "Spróbuj uruchomić w czystym venv (bez aktywnego conda 'base') "
                    "albo zaktualizować libstdc++ w środowisku."
                )
            raise ImportError(
                "PyAudio nie działa w tym środowisku. "
                "Wymagane jest działające pyaudio + portaudio. "
                f"Szczegóły: {msg}{hint}"
            )

    def transcribe(self, audio_data: bytes) -> TranscriptionResult:
        """Transkrybuje audio z wykrywaniem języka"""
        self._ensure_model()

        # Zapisz tymczasowo audio
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            # Konfiguracja transkrypcji
            transcribe_opts = {
                "fp16": False,
            }

            # Automatyczne wykrywanie języka lub użycie skonfigurowanego
            if self.config.auto_detect_language:
                transcribe_opts["task"] = "transcribe"
            else:
                transcribe_opts["language"] = self.lang_config.whisper_code

            result = self.model.transcribe(temp_path, **transcribe_opts)

            detected_lang = result.get("language", self.config.language)

            return TranscriptionResult(
                text=result["text"].strip(), language=detected_lang, confidence=0.9
            )
        finally:
            os.unlink(temp_path)

    def start_streaming(self, callback: Callable[[TranscriptionResult], None]):
        """Rozpoczyna transkrypcję strumieniową"""
        self._check_streaming_deps()
        if getattr(self.config, "debug", False):
            print("[text2dsl][voice][debug] stt.streaming.start {}")
        self._streaming = True
        self._stream_thread = threading.Thread(
            target=self._stream_loop, args=(callback,), daemon=True
        )
        self._stream_thread.start()

    def stop_streaming(self):
        """Zatrzymuje transkrypcję strumieniową"""
        if getattr(self.config, "debug", False):
            print("[text2dsl][voice][debug] stt.streaming.stop {}")
        self._streaming = False
        if self._stream_thread:
            self._stream_thread.join(timeout=2.0)

    def _stream_loop(self, callback: Callable[[TranscriptionResult], None]):
        """Pętla transkrypcji strumieniowej"""
        try:
            import pyaudio
            import numpy as np

            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=1024,
            )

            audio_buffer = []
            silence_frames = 0

            while self._streaming:
                data = stream.read(1024, exception_on_overflow=False)
                audio_np = np.frombuffer(data, dtype=np.float32)

                # Wykryj ciszę
                volume = np.abs(audio_np).mean()
                if volume < self.config.silence_threshold:
                    silence_frames += 1
                else:
                    silence_frames = 0
                    audio_buffer.append(data)

                # Po ciszy - przetwórz bufor
                silence_limit = int(self.config.silence_duration * self.config.sample_rate / 1024)
                if silence_frames > silence_limit and audio_buffer:
                    # Konwertuj i transkrybuj
                    audio_bytes = b"".join(audio_buffer)
                    result = self.transcribe(audio_bytes)
                    if result.text:
                        callback(result)
                    audio_buffer = []

            stream.stop_stream()
            stream.close()
            p.terminate()

        except Exception as e:
            if getattr(self.config, "debug", False):
                print(f"[text2dsl][voice][debug] stt.streaming.error {{'error': '{str(e)}'}}")
            else:
                print(f"Błąd audio/STT: {e}")
            self._streaming = False
            return


class Pyttsx3TTS(TTSProvider):
    """Provider TTS używający pyttsx3 z obsługą wielu języków"""

    def __init__(self, config: VoiceConfig):
        self.config = config
        self._engine = None
        self._lock = threading.Lock()
        self.lang_config = config.get_lang_config()

    def _ensure_engine(self):
        """Inicjalizuje silnik TTS"""
        if self._engine is None:
            try:
                import pyttsx3

                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", self.config.speech_rate)
                self._engine.setProperty("volume", self.config.volume)

                # Wybierz głos dla języka
                self._set_voice_for_language(self.config.language)
            except ImportError:
                raise ImportError("Zainstaluj pyttsx3: pip install pyttsx3")

    def _set_voice_for_language(self, lang_code: str):
        """Ustawia głos dla podanego języka"""
        if self._engine is None:
            return

        lang_config = get_language_config(lang_code)
        pattern = lang_config.pyttsx3_voice_pattern.lower()

        voices = self._engine.getProperty("voices")
        for voice in voices:
            voice_name = voice.name.lower()
            voice_id = voice.id.lower()

            if pattern in voice_name or pattern in voice_id or lang_code in voice_id:
                self._engine.setProperty("voice", voice.id)
                return

    def set_language(self, lang_code: str):
        """Zmienia język"""
        self._ensure_engine()
        self._set_voice_for_language(lang_code)
        self.lang_config = get_language_config(lang_code)

    def synthesize(self, text: str) -> bytes:
        """Syntezuje tekst na audio (zwraca bajty)"""
        self._ensure_engine()

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            with self._lock:
                self._engine.save_to_file(text, temp_path)
                self._engine.runAndWait()

            with open(temp_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def speak(self, text: str):
        """Odtwarza tekst jako mowę"""
        self._ensure_engine()
        with self._lock:
            self._engine.say(text)
            self._engine.runAndWait()

    def stop(self):
        """Zatrzymuje odtwarzanie"""
        if self._engine:
            with self._lock:
                self._engine.stop()


class EdgeTTS(TTSProvider):
    """Provider TTS używający Microsoft Edge TTS (darmowy, online) z obsługą wielu języków"""

    # Mapowanie głosów dla różnych języków
    VOICES = {
        "pl": {
            "male": "pl-PL-MarekNeural",
            "female": "pl-PL-ZofiaNeural",
        },
        "de": {
            "male": "de-DE-ConradNeural",
            "female": "de-DE-KatjaNeural",
        },
        "en": {
            "male": "en-US-GuyNeural",
            "female": "en-US-JennyNeural",
        },
        "en-gb": {
            "male": "en-GB-RyanNeural",
            "female": "en-GB-SoniaNeural",
        },
    }

    def __init__(self, config: VoiceConfig):
        self.config = config
        self.lang_config = config.get_lang_config()

        # Wybierz głos
        if config.voice_name:
            self.voice = config.voice_name
        else:
            self.voice = self.lang_config.edge_tts_voice

    def set_language(self, lang_code: str, gender: str = "male"):
        """Zmienia język i głos"""
        lang_code = lang_code.lower()[:2]
        if lang_code in self.VOICES:
            self.voice = self.VOICES[lang_code].get(gender, self.VOICES[lang_code]["male"])
            self.lang_config = get_language_config(lang_code)

    def synthesize(self, text: str) -> bytes:
        """Syntezuje tekst na audio"""
        try:
            import edge_tts
            import asyncio

            async def _synthesize():
                communicate = edge_tts.Communicate(text, self.voice)
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                return audio_data

            return asyncio.run(_synthesize())
        except ImportError:
            raise ImportError("Zainstaluj edge-tts: pip install edge-tts")

    def speak(self, text: str):
        """Odtwarza tekst jako mowę"""
        audio_data = self.synthesize(text)

        # Odtwórz audio
        try:
            import pygame
            import io

            pygame.mixer.init()
            sound = pygame.mixer.Sound(io.BytesIO(audio_data))
            sound.play()
            while pygame.mixer.get_busy():
                time.sleep(0.1)
        except ImportError:
            # Fallback - zapisz i odtwórz przez system
            import subprocess
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name

            try:
                subprocess.run(
                    ["mpv", "--no-video", temp_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except FileNotFoundError:
                subprocess.run(
                    ["aplay", temp_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            finally:
                os.unlink(temp_path)

    def stop(self):
        """Zatrzymuje odtwarzanie"""
        try:
            import pygame

            pygame.mixer.stop()
        except Exception:
            pass


class VoiceLayer:
    """
    Główna warstwa głosowa - koordynuje STT i TTS
    Obsługuje języki: polski, niemiecki, angielski

    Użycie:
        voice = VoiceLayer(VoiceConfig(language="pl"))
        voice.speak("Witaj!")

        # Zmiana języka
        voice.set_language("de")
        voice.speak("Hallo!")

        # Nasłuchiwanie
        def on_speech(text):
            print(f"Usłyszano: {text}")

        voice.start_listening(on_speech)
    """

    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        self.stt: Optional[STTProvider] = None
        self.tts: Optional[TTSProvider] = None
        self._listening = False
        self._on_speech: Optional[Callable[[str], None]] = None
        self.lang_config = self.config.get_lang_config()

        self._init_providers()

    def _init_providers(self):
        """Inicjalizuje providery STT i TTS"""
        if self.config.debug:
            print(
                f"[text2dsl][voice][debug] init {{'stt_backend': '{self.config.stt_backend.name}', 'tts_backend': '{self.config.tts_backend.name}', 'lang': '{self.config.language}'}}"
            )
        # STT
        if self.config.stt_backend == VoiceBackend.WHISPER:
            self.stt = WhisperSTT(self.config)
        else:
            self.stt = WhisperSTT(self.config)

        # TTS
        if self.config.tts_backend == VoiceBackend.EDGE_TTS:
            self.tts = EdgeTTS(self.config)
        elif self.config.tts_backend == VoiceBackend.PYTTSX3:
            self.tts = Pyttsx3TTS(self.config)
        else:
            self.tts = EdgeTTS(self.config)  # Domyślnie edge-tts dla lepszej jakości

    def set_language(self, lang_code: str, gender: str = "male"):
        """
        Zmienia język dla TTS i STT

        Args:
            lang_code: Kod języka (pl, de, en)
            gender: Płeć głosu (male, female)
        """
        self.config.language = lang_code
        self.lang_config = get_language_config(lang_code)

        # Zaktualizuj TTS
        if hasattr(self.tts, "set_language"):
            self.tts.set_language(lang_code, gender)

        # Zaktualizuj STT
        if hasattr(self.stt, "lang_config"):
            self.stt.lang_config = self.lang_config

        if self.config.debug:
            print(
                f"[text2dsl][voice][debug] set_language {{'lang': '{lang_code}', 'gender': '{gender}'}}"
            )

    def get_message(self, key: str) -> str:
        """Pobiera przetłumaczony komunikat systemowy"""
        return self.lang_config.messages.get(key, key)

    def speak(self, text: str, wait: bool = True):
        """
        Wymawia tekst w aktualnym języku

        Args:
            text: Tekst do wymówienia
            wait: Czy czekać na zakończenie
        """
        if self.tts:
            if wait:
                self.tts.speak(text)
            else:
                threading.Thread(target=self.tts.speak, args=(text,), daemon=True).start()

    def speak_message(self, key: str, wait: bool = True):
        """Wymawia przetłumaczony komunikat systemowy"""
        message = self.get_message(key)
        self.speak(message, wait)

    def listen(self, timeout: float = 5.0) -> Optional[str]:
        """
        Nasłuchuje i zwraca transkrypcję

        Args:
            timeout: Maksymalny czas nasłuchiwania w sekundach

        Returns:
            Rozpoznany tekst lub None
        """
        if not self.stt:
            return None

        result_queue: queue.Queue = queue.Queue()

        def callback(result: TranscriptionResult):
            result_queue.put(result.text)

        self.stt.start_streaming(callback)

        try:
            text = result_queue.get(timeout=timeout)
            return text
        except queue.Empty:
            return None
        finally:
            self.stt.stop_streaming()

    def start_listening(self, callback: Callable[[str], None]):
        """
        Rozpoczyna ciągłe nasłuchiwanie

        Args:
            callback: Funkcja wywoływana przy rozpoznaniu mowy
        """
        if not self.stt:
            return

        self._on_speech = callback

        def internal_callback(result: TranscriptionResult):
            if self.config.debug:
                print(
                    f"[text2dsl][voice][debug] stt.result {{'text': '{result.text}', 'lang': '{result.language}', 'confidence': {result.confidence}}}"
                )
            if self._on_speech and result.text:
                self._on_speech(result.text)

        try:
            self.stt.start_streaming(internal_callback)
        except ImportError as e:
            self._listening = False
            if self.config.debug:
                print(f"[text2dsl][voice][debug] listening.error {{'error': '{str(e)}'}}")
            else:
                print(f"Błąd voice/STT: {e}")
            return

        self._listening = True
        if self.config.debug:
            print("[text2dsl][voice][debug] listening.start {}")

    def stop_listening(self):
        """Zatrzymuje nasłuchiwanie"""
        if self.config.debug:
            print("[text2dsl][voice][debug] listening.stop {}")
        self._listening = False
        if self.stt:
            self.stt.stop_streaming()

    def stop_speaking(self):
        """Zatrzymuje mówienie"""
        if self.tts:
            self.tts.stop()

    def transcribe_audio(self, audio_data: bytes) -> str:
        """Transkrybuje dane audio"""
        if self.stt:
            result = self.stt.transcribe(audio_data)
            return result.text
        return ""

    def synthesize_audio(self, text: str) -> bytes:
        """Syntezuje tekst na audio"""
        if self.tts:
            return self.tts.synthesize(text)
        return b""

    @property
    def is_listening(self) -> bool:
        """Czy aktualnie nasłuchuje"""
        return self._listening

    @property
    def current_language(self) -> str:
        """Aktualny język"""
        return self.config.language

    @property
    def available_languages(self) -> List[str]:
        """Lista dostępnych języków"""
        return list(LANGUAGE_CONFIGS.keys())


class MockVoiceLayer(VoiceLayer):
    """Warstwa głosowa do testów (bez prawdziwego audio)"""

    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        self.stt = None
        self.tts = None
        self._listening = False
        self.spoken_texts: List[str] = []
        self.mock_input_queue: queue.Queue = queue.Queue()
        self.lang_config = self.config.get_lang_config()

    def speak(self, text: str, wait: bool = True):
        """Zapisuje tekst zamiast mówić"""
        self.spoken_texts.append(text)

    def listen(self, timeout: float = 5.0) -> Optional[str]:
        """Zwraca tekst z kolejki mock"""
        try:
            return self.mock_input_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def mock_speech(self, text: str):
        """Symuluje mowę użytkownika"""
        self.mock_input_queue.put(text)

    def set_language(self, lang_code: str, gender: str = "male"):
        """Zmienia język (mock)"""
        self.config.language = lang_code
        self.lang_config = get_language_config(lang_code)


# Export dodatkowych klas dla wielojęzyczności
__all__ = [
    "VoiceLayer",
    "VoiceConfig",
    "VoiceBackend",
    "MockVoiceLayer",
    "Language",
    "LanguageConfig",
    "LANGUAGE_CONFIGS",
    "get_language_config",
]
