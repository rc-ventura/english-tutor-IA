import unittest
from unittest.mock import patch, MagicMock, ANY
import base64

from src.core.speaking_tutor import SpeakingTutor
from src.services.openai_service import OpenAIService
from src.core.base_tutor import BaseTutor  # For tutor_parent


class TestSpeakingTutorIntegration(unittest.TestCase):
    def setUp(self):
        """Set up for test methods."""
        # Mock the BaseTutor parent for SpeakingTutor initialization
        self.mock_tutor_parent = MagicMock(spec=BaseTutor)
        self.mock_tutor_parent.level = "B1"  # Example level
        self.mock_tutor_parent.language = "en"  # Example language
        self.mock_tutor_parent.config = MagicMock()
        self.mock_tutor_parent.config.get.return_value = "gpt-4o-audio-preview"  # Example model
        self.mock_tutor_parent.get_system_message = MagicMock(
            return_value="Fake system prompt for testing"
        )  # Mock this method

        # Create a mock for OpenAIService and pass it to the constructor
        self.mock_openai_service_instance = MagicMock(spec=OpenAIService)
        self.speaking_tutor = SpeakingTutor(
            tutor_parent=self.mock_tutor_parent, openai_service=self.mock_openai_service_instance
        )

        # The self.speaking_tutor.openai_service is now self.mock_openai_service_instance

    @patch("src.core.speaking_tutor.play_audio", return_value=None)  # Correct patch target
    def test_process_input_successful_multimodal_flow(self, mock_play_audio):
        """Test successful multimodal flow from audio input to audio output and history update."""
        user_audio_path = "/fake/path/user_audio.wav"
        initial_history = []
        user_transcribed_text = "Hello, this is a test."
        bot_response_text = "Understood. This is a test response."
        bot_response_audio_bytes = b"fake_bot_audio_data"

        # Mock OpenAIService.transcribe_audio
        self.speaking_tutor.openai_service.transcribe_audio.return_value = user_transcribed_text

        # Mock OpenAIService.chat_multimodal response
        # The chat_multimodal method in OpenAIService returns the raw OpenAI SDK response object.
        # SpeakingTutor then uses extract_text_from_response and extract_audio_from_response on this.
        sdk_style_response = MagicMock()
        sdk_style_response.choices = [MagicMock()]
        sdk_style_response.choices[0].message = MagicMock()
        sdk_style_response.choices[0].message.content = bot_response_text  # Text part

        # Audio part: Simulate the structure for extract_audio_from_response
        # extract_audio_from_response expects response.choices[0].message.audio.data (base64 encoded)
        mock_audio_object = MagicMock()
        mock_audio_object.data = base64.b64encode(bot_response_audio_bytes).decode("utf-8")
        sdk_style_response.choices[0].message.audio = mock_audio_object

        self.speaking_tutor.openai_service.chat_multimodal.return_value = sdk_style_response

        # Call the method under test
        # process_input is a generator, so we need to iterate through it to get the final result
        final_history = None
        for history_update in self.speaking_tutor.process_input(user_audio_path, initial_history):
            final_history = history_update

        # Assertions
        self.speaking_tutor.openai_service.transcribe_audio.assert_called_once_with(user_audio_path)

        expected_messages_for_llm = [
            {"role": "system", "content": ANY},  # System prompt can vary
            {"role": "user", "content": user_transcribed_text},
        ]
        self.speaking_tutor.openai_service.chat_multimodal.assert_called_once_with(
            messages=expected_messages_for_llm,
        )

        mock_play_audio.assert_called_once_with(bot_response_audio_bytes)

        self.assertIsNotNone(final_history, "The yielded result (tuple) should not be None")
        self.assertIsInstance(final_history, tuple, "process_input should yield a tuple")
        self.assertEqual(len(final_history), 2, "The yielded tuple should have two elements")

        actual_chat_history_list = final_history[0]
        self.assertIsInstance(
            actual_chat_history_list, list, "The first element of the tuple should be the history list"
        )

        self.assertEqual(len(actual_chat_history_list), 2, "History list should contain two messages")
        self.assertEqual(actual_chat_history_list[0], {"role": "user", "content": user_transcribed_text})
        self.assertEqual(actual_chat_history_list[1], {"role": "assistant", "content": bot_response_text})


if __name__ == "__main__":
    unittest.main()
