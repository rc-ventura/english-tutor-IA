from typing import TYPE_CHECKING

import gradio as gr

if TYPE_CHECKING:
    from src.core.tutor import EnglishTutor


class GradioInterface:
    """Handles all Gradio UI components and interactions."""

    def __init__(self, tutor: "EnglishTutor"):
        self.tutor = tutor

    def create_interface(self):
        """Create and configure the Gradio interface."""

        css = """
            .container {
                border: 2px solid #9c27b0 !important;
                border-radius: 15px !important;
                padding: 15px !important;
                box-shadow: 0 4px 8px rgba(156, 39, 176, 0.2) !important;
                transition: all 0.3s ease !important;
            }

            .container:hover {
                box-shadow: 0 6px 12px rgba(156, 39, 176, 0.3) !important;
            }

            .gradio-button {
                border-radius: 8px !important;
                width: 50% !important;
            }
        """

        with gr.Blocks(css=css, theme=gr.themes.Soft()) as demo:
            # State
            history_speaking = gr.State([])
            history_writing = gr.State([])
            level = gr.State("B1")  # default level

            with gr.Sidebar():
                gr.Image("./assets/sophia-ia.png", label="Sophia IA")
                gr.Markdown("## English Tutor AI")
                gr.Textbox(label="Api Key", value="")
                gr.Dropdown(
                    label="model",
                    choices=["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-3.5-turbo"],
                    value="gpt-4o-mini",  # Default value for the dropdown
                )

            with gr.Tab("Speaking Skills"):
                # ... (chatbot, entry, mic components)
                chatbot_speaking = gr.Chatbot(
                    label="Speaking Conversation",
                    height=500,
                    type="messages",
                    elem_classes="container",
                )
                audio_input_mic = gr.Audio(
                    sources=["microphone"],
                    type="filepath",
                    label="Record your voice",
                    elem_classes="container",
                )

                # Speaking Event Handler (for microphone)
                audio_input_mic.stop_recording(
                    fn=self.tutor.speaking_tutor.transcribe_audio_only,
                    inputs=[
                        audio_input_mic,
                        history_speaking,
                    ],  # Pass level explicitly or via a shared state/dropdown
                    outputs=[chatbot_speaking, history_speaking],
                ).then(
                    fn=self.tutor.speaking_tutor.process_input,
                    inputs=[history_speaking],
                    outputs=[chatbot_speaking, history_speaking],
                ).then(
                    fn=lambda: None, inputs=None, outputs=[audio_input_mic]
                )

            with gr.Tab("Writing Skills"):
                # ... (level dropdown, topic generation, essay input, evaluation)
                with gr.Row():
                    level_dropdown_writing = gr.Dropdown(
                        label="Select English Level",
                        choices=["A1", "A2", "B1", "B2", "C1", "C2"],
                        value="B1",  # Default value for the dropdown
                    )
                    with gr.Column():
                        generate_topic_btn = gr.Button("Generate Essay Topic", elem_classes="gradio-button")
                        evaluate_essay_btn = gr.Button(
                            "Evaluate My Essay",
                            variant="primary",
                            elem_classes="gradio-button",
                        )

                with gr.Column():
                    with gr.Row():
                        essay_input_text = gr.Textbox(
                            label="Your Essay",
                            lines=25,
                            placeholder="Write your essay here...",
                        )
                        chatbot_writing = gr.Chatbot(
                            label="Writing Feedback",
                            height=600,
                            type="messages",
                            elem_classes="container",
                        )

                generate_topic_btn.click(
                    fn=self.tutor.writing_tutor.generate_random_topic,
                    inputs=[
                        level_dropdown_writing,
                        history_writing,
                    ],  # Pass dropdown value and history
                    outputs=[
                        chatbot_writing,
                        history_writing,
                    ],  # Topic appears in chatbot, history updated
                )

                evaluate_essay_btn.click(
                    fn=self.tutor.writing_tutor.process_input,
                    inputs=[essay_input_text, history_writing, level_dropdown_writing],
                    outputs=[
                        chatbot_writing,
                        history_writing,
                    ],  # Feedback in chatbot, history updated
                )

        return demo


def run_gradio_interface(tutor: "EnglishTutor"):
    """Create and launch the Gradio interface"""
    interface = GradioInterface(tutor)
    demo = interface.create_interface()

    demo.launch(
        share=True,
        show_error=True,
        max_threads=1,
    )
