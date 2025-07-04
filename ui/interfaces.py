import gradio as gr
from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING, List, Dict, Tuple
import pandas as pd

if TYPE_CHECKING:
    from src.core.tutor import EnglishTutor


class GradioInterface:
    """Handles all Gradio UI components and interactions."""

    def __init__(self, tutor: "EnglishTutor"):
        self.tutor = tutor

    @staticmethod
    def _count_words(text: str) -> str:
        """Return a string representing the word count for display."""
        if not text:
            return "Word Count: 0"
        return f"Word Count: {len(text.split())}"

    @staticmethod
    def _update_progress(
        progress: List[Dict[str, str]], essay_type: str, text: str
    ) -> Tuple[List[Dict[str, str]], pd.DataFrame]:
        """Append a new entry to the progress dashboard."""
        entry = {
            "Timestamp": datetime.now().strftime("%H:%M:%S"),
            "Essay Type": essay_type,
            "Word Count": str(len(text.split())),
        }
        progress = progress + [entry]
        return progress, pd.DataFrame(progress)

    def set_api_key_ui(self, api_key: str):
        """UI wrapper for setting the API key. Handles exceptions and returns Gradio feedback."""
        try:
            self.tutor.set_api_key(api_key)
            return gr.Success("API key set successfully!")
        except ValueError as e:
            return gr.Error(str(e))

    def create_interface(self):
        """Create and configure the Gradio interface."""

        css_path = Path("assets/styles.css")
        css = css_path.read_text()

        with gr.Blocks(css=css, theme=gr.themes.Soft(), elem_id="main-container") as demo:
            # State
            history_speaking = gr.State([])
            history_writing = gr.State([])
            progress_state = gr.State([])
            level = gr.State("B1")  # default level
            dashboard_table = gr.DataFrame(
                headers=["Timestamp", "Essay Type", "Word Count"],
                interactive=False,
                elem_id="dashboard-table",
                visible=False,
            )

            with gr.Sidebar():
                with gr.Accordion("Settings", open=True):
                    gr.Image(
                        "./assets/sophia-ia.png",
                        label="English Tutor AI",
                        elem_classes="avatar-image",
                        container=False,
                    )

                    gr.Markdown("## Sophia AI", elem_id="title")

                    api_key_box = gr.Textbox(
                        label="API Key",
                        type="password",
                        elem_classes="input-textbox",
                        elem_id="api-key",
                    )
                    with gr.Row():
                        set_key_btn = gr.Button("Set", elem_classes="gradio-button", elem_id="set-key")
                        clear_key_btn = gr.Button("Clear", elem_classes="gradio-button", elem_id="clear-key")

                    set_key_btn.click(fn=self.set_api_key_ui, inputs=[api_key_box], outputs=[api_key_box])
                    clear_key_btn.click(fn=lambda: None, inputs=None, outputs=[api_key_box])

            with gr.Tab("Speaking Skills"):
                # ... (chatbot, entry, mic components)
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
                # Chained event handler for the speaking tutor
                # 1. User stops recording -> transcribe audio and update history
                audio_input_mic.stop_recording(
                    fn=self.tutor.speaking_tutor.handle_transcription,
                    inputs=[history_speaking, audio_input_mic, level],
                    outputs=[chatbot_speaking, history_speaking],
                ).then(
                    # 2. After transcription -> get bot response (updates history with text) and audio path
                    fn=self.tutor.speaking_tutor.handle_bot_response,
                    inputs=[history_speaking, level],
                    outputs=[chatbot_speaking, history_speaking, audio_output_speaking],
                ).then(
                    # 3. After bot responds -> clear the audio input component
                    fn=lambda: None,
                    inputs=None,
                    outputs=[audio_input_mic],
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
                    essay_type_dropdown = gr.Dropdown(
                        label="Essay Type",
                        choices=[
                            "Narrative",
                            "Opinion",
                            "Descriptive",
                            "Argumentative",
                        ],
                        value="Narrative",
                        elem_classes="dropdown-select",
                        elem_id="essay-type",
                    )
                    # audio_output_writing = gr.Audio(visible=True, autoplay=False, elem_id="audio-output-writing")

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

                    word_count = gr.Markdown("Word Count: 0", elem_id="word-count")

                    with gr.Row(elem_id="writing-buttons"):
                        play_audio_btn = gr.Button("🗣️", elem_classes="gradio-button", elem_id="play-audio-btn")
                        clear_writing_btn = gr.Button("Clear", elem_classes="gradio-button", elem_id="clear-essay-btn")

                audio_output_writing = gr.Audio(
                    visible=False, autoplay=True, label="Feedback Audio", elem_id="audio-output-writing"
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
                ).then(
                    fn=self._update_progress,
                    inputs=[progress_state, essay_type_dropdown, essay_input_text],
                    outputs=[progress_state, dashboard_table],
                )
                play_audio_btn.click(
                    fn=self.tutor.writing_tutor.play_audio,
                    inputs=[history_writing],  # Pass the history state
                    outputs=[audio_output_writing],  # Output to the invisible audio component
                )

                essay_input_text.change(
                    fn=self._count_words,
                    inputs=[essay_input_text],
                    outputs=[word_count],
                )

                clear_writing_btn.click(fn=lambda: None, inputs=None, outputs=[essay_input_text])

            with gr.Tab("Progress Dashboard"):
                dashboard_table.render()
                dashboard_table.visible = True

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
