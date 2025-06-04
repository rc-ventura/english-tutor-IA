import gradio as gr
import logging
import os
from typing import List, Dict, Any, Tuple, Optional
from src.utils.audio import process_audio
import logging

# Configuração de logging para debug
logging.basicConfig(level=logging.INFO)

class GradioInterface:
    """Handles all Gradio UI components and interactions."""
    
    def __init__(self, tutor):
        self.tutor = tutor
        
    def create_interface(self):
        """Create and configure the Gradio interface."""
        with gr.Blocks() as demo:
            # State
            history_speaking = gr.State([])
            history_writing = gr.State([])

            with gr.Tab("Speaking Skills"):
                gr.Markdown("### Practice your speaking and get AI feedback")
                
                logging.info("Criando chatbot (speaking)")
                with gr.Row():
                    chatbot = gr.Chatbot(
                        type="messages",
                        height=500,
                        avatar_images=["https://cdn-icons-png.flaticon.com/512/25/25231.png", "https://cdn-icons-png.flaticon.com/512/25/25231.png"]
                    )
                logging.info("Criando textbox (entry)")
                with gr.Row():
                    entry = gr.Textbox(label="Chat with your AI English Tutor")
                    logging.info("Criando audio (mic)")
                    mic = gr.Audio(
                     sources=["microphone"],
                     type="filepath", 
                     label="Record audio (click to speak)" )
               
                logging.info("Criando botões send/clear")
                with gr.Row():
                    send_button = gr.Button("Submit", variant="primary")
                    clear = gr.Button("Clear")
                    
            with gr.Tab("Writing Skills"):
                gr.Markdown("### Practice your writing and get AI feedback")
                
                logging.info("Criando dropdown (level)")
                with gr.Row(scale=1):
                    level = gr.Dropdown(
                        label="🎓 Select your English level",
                        choices=["A1", "A2", "B1", "B2", "C1", "C2"],
                        value="B1",
                        interactive=True
                    )
                    logging.info("Criando botão generate_btn")
                    generate_btn = gr.Button("🎲 Generate random topic")
                    
                logging.info("Criando chatbot_writing e input_writing")
                with gr.Row():
                    chatbot_writing = gr.Chatbot(
                        height=550,
                        type="messages",
                        avatar_images=["https://cdn-icons-png.flaticon.com/512/25/25231.png", "https://cdn-icons-png.flaticon.com/512/25/25231.png"]
                    )
                    input_writing = gr.Textbox(label="Input Text", lines=25, placeholder="Type your text here...")
                
                logging.info("Criando evaluate_btn e clear_writing")
                with gr.Row():
                    evaluate_btn = gr.Button("Evaluate", variant="primary")
                    clear_writing = gr.Button("Clear", variant="secondary")

            # Event handlers
            entry.submit(
                fn=self.tutor.do_entry,
                inputs=[entry, history_speaking],
                outputs=[entry, chatbot, history_speaking]
            ).then(
                fn=self.tutor.chat,
                inputs=history_speaking,
                outputs=[chatbot, history_speaking]
            )

            send_button.click(
                fn=self.tutor.do_entry,
                inputs=[entry, history_speaking],
                outputs=[entry, chatbot, history_speaking]
            ).then(
                fn=self.tutor.chat,
                inputs=history_speaking,
                outputs=[chatbot, history_speaking]
            )

            # When mic stops recording, process the audio and update the entry
            mic.stop_recording(
                fn=lambda audio_file: process_audio(audio_file, self.tutor),
                inputs=[mic],
                outputs=[entry, mic]  # Update entry with transcription and clear mic
            )

            # Clear button - clear text entry
            clear.click(
                fn=lambda: "",  # Clear text entry
                inputs=None,
                outputs=[entry]
            )
            
            # Clear audio when clicking the clear button
            mic.clear(
                fn=None,  # No function needed, just clear the audio
                inputs=None,
                outputs=[mic],
            )

            # Clear writing area and chatbotc
            clear_writing.click(
                fn=lambda: ("", []),  # Clear input_writing and chatbot_writing
                inputs=None,
                outputs=[input_writing, chatbot_writing]
            )

            generate_btn.click(
                fn=self.tutor.generate_random_topic,
                inputs=[level, history_writing],
                outputs=[chatbot_writing, history_writing]
            )

            evaluate_btn.click(
                fn=self.tutor.register_essay,
                inputs=[input_writing, history_writing, level],
                outputs=[input_writing, chatbot_writing, history_writing]
            ).then(
                fn=self.tutor.writing_chat,
                inputs=history_writing,
                outputs=[chatbot_writing, history_writing]
            )

        return demo

def run_gradio_interface(tutor):
    """Create and launch the Gradio interface"""
    interface = GradioInterface(tutor)
    demo = interface.create_interface()
    
    demo.launch(
        share=True,
        show_error=True,
        max_threads=1, 
    )
