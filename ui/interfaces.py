import gradio as gr
from pathlib import Path


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

        css_path = Path("assets/styles.css")
        css = css_path.read_text()

        with gr.Blocks(css=css, theme=gr.themes.Soft(), elem_id="main-container") as demo:
            # State
            history_speaking = gr.State([])
            history_writing = gr.State([])
            level = gr.State("B1")  # default level

            with gr.Sidebar():
                gr.Image(
                    "./assets/sophia-ia.png", label="English Tutor AI", elem_classes="avatar-image", container=False
                )

                gr.Markdown("## Sophia AI", elem_id="title")

                api_key_box = gr.Textbox(
                    label="API Key", type="password", elem_classes="input-textbox", elem_id="api-key"
                )
                with gr.Row():
                    set_key_btn = gr.Button("Set", elem_classes="gradio-button", elem_id="set-key")
                    clear_key_btn = gr.Button("Clear", elem_classes="gradio-button", elem_id="clear-key")

                with gr.Row():
                    model_dropdown = gr.Dropdown(
                        label="model",
                        choices=["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-3.5-turbo"],
                        value="",
                        elem_classes="dropdown-select",
                        elem_id="model-select",
                    )

                set_key_btn.click(fn=self.tutor.set_api_key, inputs=[api_key_box], outputs=[api_key_box])
                clear_key_btn.click(fn=lambda: None, inputs=None, outputs=[api_key_box])

            with gr.Tab("Speaking Skills"):
                # ... (chatbot, entry, mic components)
                chatbot_speaking = gr.Chatbot(
                    label="Speaking Conversation",
                    height=500,
                    type="messages",
                    show_copy_button=True,
                    autoscroll=True,
                    elem_classes="chatbot-container",
                    elem_id="chatbot-speaking",
                )
                audio_input_mic = gr.Audio(
                    sources=["microphone"],
                    type="filepath",
                    label="Record your voice",
                    elem_classes="container",
                    elem_id="mic-input",
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
                        value="B1",
                        elem_classes="dropdown-select",
                        elem_id="level-select",
                    )

                with gr.Row():
                    generate_topic_btn = gr.Button(
                        "Start",
                        elem_classes="gradio-button",
                    )

                with gr.Column():
                    with gr.Row(elem_id="writing-row"):
                        essay_input_text = gr.Textbox(
                            label="Your Essay",
                            lines=25,
                            placeholder="Write your essay here...",
                            elem_classes="input-textbox",
                            elem_id="essay-text",
                        )

                        chatbot_writing = gr.Chatbot(
                            label="Writing Feedback",
                            height=600,
                            type="messages",
                            elem_classes="chatbot-container",
                            elem_id="chatbot-writing",
                            show_copy_button=True,
                            autoscroll=True,
                        )

                    with gr.Row():
                        with gr.Row():
                            evaluate_essay_btn = gr.Button(
                                "Evaluate My Essay",
                                variant="primary",
                                elem_classes="gradio-button",
                                elem_id="evaluate-essay-btn",
                            )
                            clear_writing_btn = gr.Button(
                                "Clear", elem_classes="gradio-button", elem_id="clear-essay-btn"
                            )
                        with gr.Column():
                            with gr.Row():
                                play_audio_btn = gr.Button(
                                    "Play Audio", elem_classes="gradio-button", elem_id="play-audio-btn"
                                )
                                clear_chatbot_btn = gr.Button(
                                    "Clear", elem_classes="gradio-button", elem_id="clear-chatbot-btn"
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

                clear_writing_btn.click(fn=lambda: None, inputs=None, outputs=[essay_input_text])

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
