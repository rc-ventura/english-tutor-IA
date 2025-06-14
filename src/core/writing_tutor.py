
from src.core.base_tutor import BaseTutor
from src.utils.audio import talker
from typing import List, Dict, Optional
import logging

class WritingTutor(BaseTutor):

    def process_input(self, essay_text: str, history: List[Dict], level: Optional[str] = None):
        """Evaluate an essay and return updated chat history.

        This method now yields intermediate chat history states so that the
        frontend can display streaming tokens as they are received from the
        OpenAI API.
        """
        if not essay_text or not essay_text.strip():
            yield [{"role": "assistant", "content": "No essay provided. Please write your essay."}], history
            return
        


        user_message_content = (
            f"Please evaluate this essay for a {level} level student:\n\n{essay_text}"
        )
        new_history = history + [{"role": "user", "content": user_message_content}]
        # Immediately show the user's essay in the chat
        yield new_history, new_history

        system_prompt = self.tutor_parent.get_system_message(mode="writing", level=level)
        messages = [{"role": "system", "content": system_prompt}] + new_history
        
        try:
            assistant_message = {"role": "assistant", "content": ""}
            new_history.append(assistant_message)
            for chunk in self.openai_service.stream_chat_completion(messages=messages):
                assistant_message["content"] += chunk
                # Stream partial feedback to the UI
                yield new_history, new_history
        except Exception as e:
            logging.error(f"OpenAI chat completion error for writing: {e}", exc_info=True)
            new_history.append({"role": "assistant", "content": f"Sorry, I encountered an issue generating a response: {e}"})
            yield new_history, new_history
            return

        try:
            talker(new_history[-1]["content"])
        except Exception as e:
            logging.warning(f"TTS error for writing feedback: {e}", exc_info=True)
            new_history[-1]["content"] += " (Note: audio playback of feedback failed)"

        yield new_history, new_history
         
        
        
    def generate_random_topic(self, level: Optional[str] = None, history: Optional[List[Dict]] = None):
        
        user_prompt_content = f"Generate a topic for a writing essay for a student with the level of {level}. Also, suggest structure and number of lines and number of words expectation."
        
        system_prompt = self.tutor_parent.get_system_message(mode="writing", level=level)
        
        messages_for_topic = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt_content}
        ]

        new_history = history or []
        user_entry = {
            "role": "user",
            "content": f"Can you give me an essay topic for level {level}?",
        }
        new_history = new_history + [user_entry]
        # Immediately show the user request
        yield new_history, new_history

        try:
            assistant_message = {"role": "assistant", "content": ""}
            new_history.append(assistant_message)
            for chunk in self.openai_service.stream_chat_completion(
                messages=messages_for_topic
            ):
                assistant_message["content"] += chunk
                yield new_history, new_history
        except Exception as e:
            logging.error(f"Topic generation error: {e}", exc_info=True)
            new_history.append({
                "role": "assistant",
                "content": f"Sorry, I couldn't generate a topic right now: {e}",
            })
            yield new_history, new_history
            return

        # Optional TTS commented out
        yield new_history, new_history

        

    def register_essay(self, text: str, history: List[Dict], level: str) -> tuple[str, List[Dict]]:
        new_history = history.copy()
        new_history.append({"role":"user", "content": f"Level: {level}: {text}"})
        return " ", new_history


