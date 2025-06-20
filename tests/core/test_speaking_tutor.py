import base64
import unittest
from unittest.mock import patch, MagicMock, call
from typing import List, Dict, Any, Generator, Tuple

from src.core.speaking_tutor import SpeakingTutor
from src.services.openai_service import OpenAIService

# Assuming BaseTutor and other necessary parent classes/structures are importable
# For simplicity, we might need to mock TutorParent or provide a minimal version.


class MockTutorParent:
    def get_system_message(self, mode: str, level: str) -> str:
        return f"System prompt for {mode} at {level} level."


class TestSpeakingTutor(unittest.TestCase):
    def setUp(self):
        self.mock_openai_service = MagicMock(spec=OpenAIService)
        self.mock_tutor_parent = MockTutorParent()

        self.tutor = SpeakingTutor(openai_service=self.mock_openai_service, tutor_parent=self.mock_tutor_parent)
        # self.tutor.tutor_parent = self.mock_tutor_parent # No longer needed as it's passed in constructor

    def _run_process_input_and_collect(
        self, *args, **kwargs
    ) -> List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]]:
        results = []
        generator = self.tutor.process_input(*args, **kwargs)
        for item in generator:
            results.append(item)
        return results

    @patch("src.core.speaking_tutor.play_audio")
    def test_process_input_happy_path(self, mock_play_audio):
        audio_file_path = "/fake/path/audio.wav"
        initial_history = []
        level = "B1"

        transcribed_text = "Hello, how are you?"
        self.mock_openai_service.transcribe_audio.return_value = transcribed_text

        mock_message = MagicMock()
        mock_message.content = "I am fine, thank you!"  # Align with extract_text_from_response
        mock_message.audio = MagicMock()
        mock_message.audio.data = base64.b64encode(b"fake_audio_bytes").decode("utf-8")

        mock_llm_response = MagicMock()
        mock_llm_response.choices = [MagicMock()]
        mock_llm_response.choices[0].message = mock_message
        self.mock_openai_service.chat_multimodal.return_value = mock_llm_response

        results = self._run_process_input_and_collect(audio_file_path, initial_history, level)

        self.assertEqual(len(results), 1)  # Should yield only once with final history
        final_history, _ = results[0]

        self.mock_openai_service.transcribe_audio.assert_called_once_with(audio_file_path)

        expected_system_prompt = self.mock_tutor_parent.get_system_message("speaking", level)
        expected_messages_for_llm = [
            {"role": "system", "content": expected_system_prompt},
            {"role": "user", "content": transcribed_text},
        ]
        self.mock_openai_service.chat_multimodal.assert_called_once_with(
            messages=expected_messages_for_llm, input_audio_path=None
        )
        mock_play_audio.assert_called_once_with(b"fake_audio_bytes")

        self.assertEqual(len(final_history), 2)
        self.assertEqual(final_history[0], {"role": "user", "content": transcribed_text})
        self.assertEqual(final_history[1], {"role": "assistant", "content": "I am fine, thank you!"})

    def test_process_input_no_audio_file(self):
        results = self._run_process_input_and_collect(None, [], "B1")
        self.assertEqual(len(results), 1)
        final_history, _ = results[0]
        self.assertEqual(len(final_history), 1)
        self.assertIn("No audio input received", final_history[0]["content"])
        self.mock_openai_service.transcribe_audio.assert_not_called()

    @patch("src.core.speaking_tutor.play_audio")
    def test_process_input_transcription_fails(self, mock_play_audio):
        audio_file_path = "/fake/path/audio.wav"
        self.mock_openai_service.transcribe_audio.side_effect = Exception("Transcription Error")

        results = self._run_process_input_and_collect(audio_file_path, [], "B1")
        self.assertEqual(len(results), 1)
        final_history, _ = results[0]
        self.assertEqual(len(final_history), 1)
        self.assertIn("couldn't transcribe your audio", final_history[0]["content"])
        self.assertIn("Transcription Error", final_history[0]["content"])
        mock_play_audio.assert_not_called()

    @patch("src.core.speaking_tutor.play_audio")
    def test_process_input_transcription_empty(self, mock_play_audio):
        audio_file_path = "/fake/path/audio.wav"
        self.mock_openai_service.transcribe_audio.return_value = " "  # Empty or whitespace

        mock_llm_response = MagicMock()
        mock_llm_response.choices = [MagicMock()]
        mock_llm_response.choices[0].message.text = "Bot response"
        mock_llm_response.choices[0].message.audio.data = base64.b64encode(b"audio").decode("utf-8")
        self.mock_openai_service.chat_multimodal.return_value = mock_llm_response

        results = self._run_process_input_and_collect(audio_file_path, [], "B1")
        final_history, _ = results[0]

        self.assertEqual(final_history[0]["content"], "[Audio not clear or empty]")
        mock_play_audio.assert_called_once()

    @patch("src.core.speaking_tutor.play_audio")
    def test_process_input_llm_call_fails(self, mock_play_audio):
        audio_file_path = "/fake/path/audio.wav"
        transcribed_text = "User speech"
        self.mock_openai_service.transcribe_audio.return_value = transcribed_text
        self.mock_openai_service.chat_multimodal.side_effect = Exception("LLM Error")

        results = self._run_process_input_and_collect(audio_file_path, [], "B1")
        self.assertEqual(len(results), 1)
        final_history, _ = results[0]
        self.assertEqual(len(final_history), 2)  # User message + error message
        self.assertEqual(final_history[0]["content"], transcribed_text)
        self.assertIn("encountered an error getting a response", final_history[1]["content"])
        self.assertIn("LLM Error", final_history[1]["content"])
        mock_play_audio.assert_not_called()

    @patch("src.core.speaking_tutor.play_audio")
    def test_process_input_llm_response_no_audio(self, mock_play_audio):
        audio_file_path = "/fake/path/audio.wav"
        transcribed_text = "User speech"
        self.mock_openai_service.transcribe_audio.return_value = transcribed_text

        mock_message_no_audio = MagicMock()
        mock_message_no_audio.content = "Bot text only"  # Align with extract_text_from_response
        # To simulate no audio, we ensure the 'audio' attribute either doesn't exist
        # or doesn't evaluate to true in a way that extract_text_from_response or play_audio would use it.
        # For MagicMock, if 'audio' is accessed and not set, it returns a new MagicMock.
        # If `hasattr` is used, this new MagicMock means `hasattr` is true.
        # To truly simulate its absence for hasattr, we can make it raise AttributeError or set it to None.
        # Let's try setting it to None, as `speaking_tutor.py` checks `hasattr(response.choices[0].message, "audio") and response.choices[0].message.audio`
        mock_message_no_audio.audio = None

        mock_llm_response = MagicMock()
        mock_llm_response.choices = [MagicMock()]
        mock_llm_response.choices[0].message = mock_message_no_audio
        self.mock_openai_service.chat_multimodal.return_value = mock_llm_response

        results = self._run_process_input_and_collect(audio_file_path, [], "B1")
        final_history, _ = results[0]

        mock_play_audio.assert_not_called()
        self.assertEqual(final_history[1]["content"], "Bot text only")

    @patch("src.core.speaking_tutor.play_audio")
    def test_process_input_play_audio_fails(self, mock_play_audio):
        audio_file_path = "/fake/path/audio.wav"
        transcribed_text = "User speech"
        self.mock_openai_service.transcribe_audio.return_value = transcribed_text

        mock_llm_response = MagicMock()
        mock_llm_response.choices = [MagicMock()]
        mock_llm_response.choices[0].message.text = "Bot text"
        mock_llm_response.choices[0].message.audio.data = base64.b64encode(b"audio").decode("utf-8")
        self.mock_openai_service.chat_multimodal.return_value = mock_llm_response

        mock_play_audio.side_effect = Exception("Playback Error")

        results = self._run_process_input_and_collect(audio_file_path, [], "B1")
        final_history, _ = results[0]

        mock_play_audio.assert_called_once()
        self.assertIn("(Error playing audio response)", final_history[1]["content"])


if __name__ == "__main__":
    unittest.main()
