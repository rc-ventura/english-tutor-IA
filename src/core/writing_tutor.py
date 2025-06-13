
from src.core.base_tutor import BaseTutor
from src.utils.audio import talker
from typing import List, Dict, Optional
import logging

class WritingTutor(BaseTutor):
    
    def process_input(self, essay_text: str, history: List[Dict], level: Optional[str] = None) -> tuple[str, List[Dict]]:
        if not essay_text or not essay_text.strip():
            return "No essay provided. Please write your essay.", history
        


        user_message_content = f"Please evaluate this essay for a {level} level student:\n\n{essay_text}"
        new_history = history + [{"role": "user", "content": user_message_content}]

        system_prompt = self.tutor_parent.get_system_message(mode="writing", level=level)
        messages = [{"role": "system", "content": system_prompt}] + new_history
        
        try:
            chunks = self.openai_service.stream_chat_completion(messages=messages)
            feedback = "".join(chunk for chunk in chunks)
        except Exception as e:
            logging.error(f"OpenAI chat completion error for writing: {e}", exc_info=True)
            return [{"role": "assistant", "content": f"Sorry, I encountered an issue generating a response: {e}"}], history
        
        new_history.append({"role": "assistant", "content": feedback})
        
        try:
            talker(feedback)
        except Exception as e:
            logging.warning(f"TTS error for writing feedback: {e}", exc_info=True)
            new_history[-1]["content"] += " (Note: audio playback of feedback failed)"
        
        return new_history, new_history
         
        
        
    def generate_random_topic(self, level: Optional[str] = None, history: Optional[List[Dict]] = None) -> tuple[str, List[Dict]]:

        user_prompt_content = f"Generate a topic for a writing essay for a student with the level of {level}. Also, suggest structure and number of lines and number of words expectation."
        
        system_prompt = self.tutor_parent.get_system_message(mode="writing", level=level)
        
        messages_for_topic = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt_content}
        ]

        try:
            chunks = self.openai_service.stream_chat_completion(
                messages=messages_for_topic
            )
            topic_suggestion = "".join(chunk for chunk in chunks)
        except Exception as e:
            logging.error(f"Topic generation error: {e}", exc_info=True)
            return [{"role": "assistant", "content": f"Sorry, I couldn't generate a topic right now: {e}"}], history
        
        
        updated_history = history + [
            {"role": "user", "content": f"Can you give me an essay topic for level {level}?"}, # Simplified user intent
            {"role": "assistant", "content": topic_suggestion}
        ]
                 

        get_generate_topic = [{"role": "assistant", "content": topic_suggestion}], updated_history
         # Optional: TTS for the topic suggestion
        # try:
        #     talker(topic_suggestion)
        # except Exception as e:
        #     # logging.warning(f"TTS error for topic suggestion: {e}", exc_info=True)
        #     pass # Don't alter return for this
        
        #talker(topic_suggestion)

        return get_generate_topic

        

    def register_essay(self, text: str, history: List[Dict], level: str) -> tuple[str, List[Dict]]:
        new_history = history.copy()
        new_history.append({"role":"user", "content": f"Level: {level}: {text}"})
        return " ", new_history


