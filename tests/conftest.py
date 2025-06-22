import sys
import types

# Provide a minimal stub of the `openai` package used in the code
class _FakeChat:
    def __init__(self):
        self.completions = types.SimpleNamespace(create=lambda *a, **k: None)

class _FakeAudio:
    def __init__(self):
        self.transcriptions = types.SimpleNamespace(create=lambda *a, **k: None)
        self.speech = types.SimpleNamespace(create=lambda *a, **k: types.SimpleNamespace(content=b""))

class _FakeModels:
    def list(self):
        return []

class OpenAI:
    def __init__(self, *a, **k):
        self.chat = _FakeChat()
        self.audio = _FakeAudio()
        self.models = _FakeModels()

class AuthenticationError(Exception):
    pass

# Provide minimal types namespace for hints
class ChatCompletion:  # pragma: no cover - only for import satisfaction
    pass

pkg = types.ModuleType("openai")
pkg.OpenAI = OpenAI
pkg.AuthenticationError = AuthenticationError

types_pkg = types.ModuleType("openai.types")
chat_pkg = types.ModuleType("openai.types.chat")
chat_pkg.ChatCompletion = ChatCompletion
types_pkg.chat = chat_pkg
pkg.types = types_pkg

sys.modules.setdefault("openai", pkg)
sys.modules.setdefault("openai.types", types_pkg)
sys.modules.setdefault("openai.types.chat", chat_pkg)
