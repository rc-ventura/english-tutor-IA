import gradio as gr
from typing import List, Dict


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.core.tutor import EnglishTutor

class GradioInterface:
    """Handles all Gradio UI components and interactions."""
    
    def __init__(self, tutor: 'EnglishTutor'):
        self.tutor = tutor
        
    def create_interface(self):
        """Create and configure the Gradio interface."""
        with gr.Blocks() as demo:
            # State
            history_speaking = gr.State([])
            history_writing = gr.State([])
            level = gr.State("B1") #default level



            with gr.Tab("Speaking Skills"):
                # ... (chatbot, entry, mic components)
                chatbot_speaking = gr.Chatbot(label="Speaking Conversation", height=500, type="messages")
                audio_input_mic = gr.Audio(sources=["microphone"], type="filepath", label="Record your voice")

                # Speaking Event Handler (for microphone)
                audio_input_mic.stop_recording(
                    fn=self.tutor.speaking_tutor.transcribe_audio_only,
                    inputs=[audio_input_mic, history_speaking], # Pass level explicitly or via a shared state/dropdown
                    outputs=[chatbot_speaking, history_speaking]
                ).then (
                    fn=self.tutor.speaking_tutor.process_input,
                    inputs=[history_speaking],
                    outputs=[chatbot_speaking, history_speaking]
                ).then(
                    fn=lambda: None,
                    inputs=None,
                    outputs=[audio_input_mic]
                )
           

            with gr.Tab("Writing Skills"):
                with gr.Row():
                # ... (level dropdown, topic generation, essay input, evaluation)
                    level_dropdown_writing = gr.Dropdown(
                        label="Select English Level", 
                        choices=["A1", "A2", "B1", "B2", "C1", "C2"], 
                        value="B1" # Default value for the dropdown
                    )
                    generate_topic_btn = gr.Button("Generate Essay Topic")
                
                with gr.Row():
                    with gr.Column():
                        essay_input_text = gr.Textbox(label="Your Essay", lines=25, placeholder="Write your essay here...")
                        evaluate_essay_btn = gr.Button("Evaluate My Essay", variant="primary")

                    chatbot_writing = gr.Chatbot(label="Writing Feedback", height=600, type="messages")
       
                generate_topic_btn.click(
                    fn=self.tutor.writing_tutor.generate_random_topic,
                    inputs=[level_dropdown_writing, history_writing], # Pass dropdown value and history
                    outputs=[chatbot_writing, history_writing] # Topic appears in chatbot, history updated
                )

                evaluate_essay_btn.click(
                    fn=self.tutor.writing_tutor.process_input,
                    inputs=[essay_input_text, history_writing, level_dropdown_writing],
                    outputs=[chatbot_writing, history_writing] # Feedback in chatbot, history updated
                )
            

        return demo

def run_gradio_interface(tutor: 'EnglishTutor'):
    """Create and launch the Gradio interface"""
    interface = GradioInterface(tutor)
    demo = interface.create_interface()
    
    demo.launch(
        share=True,
        show_error=True,
        max_threads=1, 
    )
