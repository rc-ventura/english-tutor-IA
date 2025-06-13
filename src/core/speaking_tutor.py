
from typing import List, Dict, Optional
from src.core.base_tutor import BaseTutor
from src.utils.audio import talker
import logging

class SpeakingTutor(BaseTutor):
    


    def transcribe_audio_only(self, audio_file_path: Optional[str], history: List[Dict]) -> tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """Transcribes the audio and appends user message to history."""
        if not audio_file_path:
            return history + [{"role": "user", "content": "[No audio provided]"}], history

        try:
            transcription = self.openai_service.transcribe_audio(audio_file_path)
            if not transcription or not transcription.strip():
                transcription = "I couldn't understand the audio. Could you say it again?"
        except Exception as e:
            transcription = f"[Transcription error: {str(e)}]"

        history += [{"role": "user", "content": transcription}]
        return history, history



    def process_input(self, history: List[Dict], level: Optional[str] = None) -> tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """Generates assistant response from latest history."""
        
        if not history or history[-1]['role'] != 'user':
            return history, history 

        system_prompt = self.tutor_parent.get_system_message(mode="speaking", level=level)
        messages = [{"role": "system", "content": system_prompt}] + history
        
        logging.info("Full prompt being sent to OpenAI:")
        logging.info({
            "system_prompt": system_prompt,
            "full_history": history
        })
        try:
            chunks = self.openai_service.stream_chat_completion(messages=messages)
            reply = "".join(chunk for chunk in chunks)
        except Exception as e:
            logging.error(f"OpenAI chat completion error: {e}", exc_info=True)
            return f"Sorry, I encountered an issue generating a response: {e}", history
        
        history += [{"role": "assistant", "content": reply}]
        
        try:
            talker(reply)
        except Exception as e:
            logging.warning(f"TTS error: {e}", exc_info=True)
            history[-1]["content"] += " (Note: audio playback failed)"

        return history, history

    
        

   