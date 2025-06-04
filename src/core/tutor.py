import os
import logging
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

from src.services.openai_service import OpenAIService
from src.models.prompts import get_system_message
from src.utils.audio import talker

class EnglishTutor:
    """Main English tutoring system coordinating all components."""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self._setup()
        self.openai_service = OpenAIService(
            api_key=self.openai_api_key,
            model=self.model
        )
    
    def _setup(self) -> None:
        """Initialize configuration."""
        load_dotenv(override=True)
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if not self.openai_api_key:
            logging.error("OpenAI API Key not set")
            raise ValueError("OpenAI API Key not found in environment")
            
        logging.info(f"OpenAI API Key loaded (starts with {self.openai_api_key[:8]})")
    
    def get_system_message(self, mode: str = "speaking", level: Optional[str] = None) -> str:
        """Get the appropriate system message based on tutoring mode."""
        return get_system_message(mode, level)

    def do_entry(self, message, history_speaking):
        history_speaking += [{"role":"user", "content":message}]
        return "", history_speaking, history_speaking

    def transcript_audio(self, audio_file):
        try:
            transcription = self.openai_service.transcribe_audio(audio_file)
            # Garante que sempre retorna string
            if not transcription or not isinstance(transcription, str):
                return ""
            return transcription
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""

    def chat(self, history_speaking):
        print("DEBUG messages:", history_speaking)  
        messages = [{"role": "system", "content": self.get_system_message()}] + history_speaking
        response = self.openai_service.get_chat_completion(
            messages=messages
        )

        reply = response.choices[0].message.content
        history_speaking += [{"role":"assistant", "content":reply}]
        talker(reply)
        return history_speaking, history_speaking

    def writing_chat(self, history_writing):
        print("DEBUG messages:", history_writing)  
        messages = [{"role": "system", "content": self.get_system_message(mode="writing", level="B1")}] + history_writing
        response = self.openai_service.get_chat_completion(
            messages=messages   
        )

        reply = response.choices[0].message.content
        history_writing += [{"role":"assistant", "content":reply}]
        talker(reply)
        return history_writing, history_writing

    def generate_random_topic(self, level, history_writing):

        print("DEBUG level:", level)
        print("DEBUG history:", history_writing)

        user_prompt = f"Generate a topic for a writing essay for a student with the level of {level}. Also, suggest structure and length expectation."
        messages = [{"role": "system", "content": self.get_system_message(mode="writing", level=level)},
                    {"role": "user", "content": user_prompt}]
        response = self.openai_service.get_chat_completion(
            messages=messages
        )

        reply = response.choices[0].message.content

        history_writing += [{"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": reply}]
                
        return history_writing, history_writing

    def register_essay(self, text, history_writing, level):
        history_writing += [{"role":"user", "content": f"Level: {level}. {text}"}]
        return " ", history_writing, history_writing

    def main(self):
        """Run the Gradio interface."""
        from src.core.interfaces import run_gradio_interface
        run_gradio_interface(self)

def main():
    """Entry point for the tutor application."""
    try:
        tutor = EnglishTutor()
        tutor.main()
    except Exception as e:
        logging.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    main()