import gradio as gr
from pathlib import Path
from fastapi import FastAPI
from gradio.routes import mount_gradio_app
from fastapi.middleware.cors import CORSMiddleware


from typing import TYPE_CHECKING

import gradio as gr

if TYPE_CHECKING:
    from src.core.tutor import EnglishTutor


class GradioInterface:
    """Handles all Gradio UI components and interactions."""

    def __init__(self, tutor: "EnglishTutor"):
        self.tutor = tutor

    def set_api_key_ui(self, api_key: str):
        """UI wrapper for setting the API key. Handles exceptions and returns Gradio feedback."""
        try:
            self.tutor.set_api_key(api_key)
            return gr.Success("API key set successfully!")
        except ValueError as e:
            return gr.Error(str(e))

    def get_progress_html(self):
        """Return the current user progress dashboard HTML."""
        return self.tutor.progress_tracker.html_dashboard()

    def create_interface(self):
        """Create and configure the Gradio interface."""

        css_path = Path("assets/styles.css")
        css = css_path.read_text()

        with gr.Blocks(css=css, theme=gr.themes.Soft(), elem_id="main-container") as demo:
            # State
            history_speaking = gr.State([])
            history_writing = gr.State([])
            english_level = gr.State("B1")  # default level

            with gr.Sidebar():
                gr.Image(value="assets/sophia-ia.png", height=150, width=150, show_label=False, elem_id="sidebar-logo")

                gr.Markdown("## Sophia AI", elem_id="title")

                with gr.Accordion("⚙️ Settings", open=False):
                    with gr.Group():
                        api_key_box = gr.Textbox(
                            label="🔑 OpenAI API Key",
                            type="password",
                            placeholder="sk-...",
                            elem_id="api-key-box",
                            scale=3,
                        )
                        with gr.Row(elem_classes="settings-button-row"):
                            set_key_btn = gr.Button(
                                "💾 Save", variant="primary", elem_classes="gradio-button", elem_id="set-key-btn"
                            )
                            clear_key_btn = gr.Button(
                                "🗑️ Clear", variant="secondary", elem_classes="gradio-button", elem_id="clear-key-btn"
                            )

                    english_level = gr.Dropdown(
                        label="🌐 English Level",
                        choices=["A1", "A2", "B1", "B2", "C1", "C2"],
                        value="B1",
                        elem_id="level-select",
                    )

                set_key_btn.click(fn=self.set_api_key_ui, inputs=[api_key_box], outputs=[api_key_box])
                clear_key_btn.click(fn=lambda: None, inputs=None, outputs=[api_key_box])

            with gr.Tab("Speaking Skills"):
                chatbot_speaking = gr.Chatbot(
                    label="Speaking Conversation",
                    height=500,
                    type="messages",
                    show_copy_button=True,
                    autoscroll=True,
                    avatar_images=["./assets/user.png", "./assets/sophia-ia.png"],
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
                audio_output_speaking = gr.Audio(
                    visible=False, autoplay=True, label="Bot Speech Output", elem_id="audio-output-speaking"
                )
                audio_input_mic.stop_recording(
                    fn=self.tutor.speaking_tutor.handle_transcription,
                    inputs=[history_speaking, audio_input_mic, english_level],
                    outputs=[chatbot_speaking, history_speaking],
                    api_name="speaking_transcribe",
                ).then(
                    fn=self.tutor.speaking_tutor.handle_bot_response,
                    inputs=[history_speaking, english_level],
                    outputs=[chatbot_speaking, history_speaking, audio_output_speaking],
                    api_name="speaking_bot_response",
                ).then(
                    fn=lambda: None,
                    inputs=None,
                    outputs=[audio_input_mic],
                )

            with gr.Tab("Writing Skills"):
                with gr.Row():
                    writing_type = gr.Radio(
                        label="Writing Type",
                        choices=[
                            "Daily Journal",
                            "Email",
                            "Short Story",
                            "Formal Essay",
                            "Business Report",
                            "Creative Writing",
                        ],
                        value="Daily Journal",
                        container=True,
                    )

                with gr.Row(elem_id="writing-button-row"):
                    generate_topic_btn = gr.Button(
                        "Start",
                        elem_classes="gradio-button",
                    )
                    evaluate_essay_btn = gr.Button(
                        "Evaluate",
                        variant="primary",
                        elem_classes="gradio-button",
                        elem_id="evaluate-essay-btn",
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

                with gr.Row(elem_id="writing-buttons"):
                    play_audio_btn = gr.Button("🗣️", elem_classes="gradio-button", elem_id="play-audio-btn")
                    clear_writing_btn = gr.Button("Clear", elem_classes="gradio-button", elem_id="clear-essay-btn")

                audio_output_writing = gr.Audio(
                    visible=True, autoplay=True, label="Feedback Audio", elem_id="audio-output-writing"
                )

                generate_topic_btn.click(
                    fn=self.tutor.writing_tutor.generate_random_topic,
                    inputs=[
                        english_level,
                        history_writing,
                        writing_type,
                    ],
                    outputs=[
                        chatbot_writing,
                        history_writing,
                    ],
                    api_name="generate_topic",
                )

                evaluate_essay_btn.click(
                    fn=self.tutor.writing_tutor.process_input,
                    inputs=[essay_input_text, history_writing, english_level, writing_type],
                    outputs=[
                        chatbot_writing,
                        history_writing,
                    ],
                    api_name="evaluate_essay",
                )
                play_audio_btn.click(
                    fn=self.tutor.writing_tutor.play_audio,
                    inputs=[history_writing],
                    outputs=[audio_output_writing],
                    api_name="play_audio",
                )

                clear_writing_btn.click(fn=lambda: None, inputs=None, outputs=[essay_input_text])

            # ------------------- Progress Dashboard Tab -------------------
            with gr.Tab("Progress"):
                progress_html = gr.HTML(value=self.get_progress_html(), elem_id="progress-dashboard")
                refresh_progress_btn = gr.Button("Refresh", elem_classes="gradio-button", elem_id="refresh-progress")

                refresh_progress_btn.click(
                    fn=self.get_progress_html,
                    inputs=None,
                    outputs=[progress_html],
                )

        return demo


def run_gradio_interface(tutor: "EnglishTutor"):
    """Create and launch the Gradio interface"""
    interface = GradioInterface(tutor)
    demo = interface.create_interface().queue()

    # Mount the Gradio app onto a FastAPI app
    app = FastAPI()
    app = mount_gradio_app(app, demo, path="/")

    # Add the CORS middleware to the FastAPI app
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app
