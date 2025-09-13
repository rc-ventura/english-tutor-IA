import gradio as gr
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import os
import base64
from urllib.parse import unquote
from gradio.routes import mount_gradio_app
from fastapi.middleware.cors import CORSMiddleware
from typing import TYPE_CHECKING, Optional, Dict, Any
from src.core.escalation_manager import EscalationManager
from src.utils.audio import analyze_pronunciation_metrics, save_audio_to_temp_file

if TYPE_CHECKING:
    # Type-only import to avoid circular import at runtime
    from src.core.tutor import EnglishTutor


class GradioInterface:
    """Handles all Gradio UI components and interactions."""

    def __init__(self, tutor: "EnglishTutor"):
        self.tutor = tutor

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
            speaking_mode = gr.State("Hybrid")  # default mode

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

                status_text = gr.Textbox(
                    label="Status",
                    interactive=False,
                    visible=True,
                    lines=2,
                    value=self.tutor.api_key_status,
                )

            set_key_btn.click(
                fn=self.tutor.set_api_key, inputs=[api_key_box], outputs=[status_text], api_name="set_api_key_ui"
            )

            clear_key_btn.click(fn=lambda: (None, None), inputs=None, outputs=[api_key_box, status_text])

            with gr.Tab("Speaking Skills"):
                speaking_mode = gr.Radio(
                    ["Hybrid", "Immersive"],
                    label="Practice Mode",
                    value="Hybrid",
                    elem_id="speaking_mode-radio",
                )

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
                    inputs=[history_speaking, audio_input_mic, english_level, speaking_mode],
                    outputs=[chatbot_speaking, history_speaking],
                    api_name="speaking_transcribe",
                ).then(
                    fn=self.tutor.speaking_tutor.handle_bot_response,
                    inputs=[history_speaking, english_level, speaking_mode],
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
                        elem_id="writing-type",
                    )

                # with gr.Row(elem_id="writing-button-row"):

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

                    play_audio_btn = gr.Button("playback", elem_classes="gradio-button", elem_id="play-audio-btn")
                    clear_writing_btn = gr.Button("Clear", elem_classes="gradio-button", elem_id="clear-essay-btn")

                audio_output_writing = gr.Audio(
                    visible=False, autoplay=True, label="Feedback Audio", elem_id="audio-output-writing"
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
    app = mount_gradio_app(app, demo, path="/gradio")

    # Add the CORS middleware to the FastAPI app
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------- Escalation API (FastAPI) -------------------
    escalation_manager = EscalationManager()

    @app.post("/api/escalations")
    async def create_escalation(payload: Dict[str, Any]):
        try:
            return escalation_manager.create(payload)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/escalations")
    async def list_escalations(status: Optional[str] = None):
        return escalation_manager.list(status)

    @app.post("/api/escalations/{escalation_id}/resolve")
    async def resolve_escalation(escalation_id: str, body: Optional[Dict[str, Any]] = None):
        note = (body or {}).get("resolution_note")
        try:
            return escalation_manager.resolve(escalation_id, note)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/escalations/{escalation_id}")
    async def get_escalation(escalation_id: str):
        rec = escalation_manager.get(escalation_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Escalation not found")
        return rec

    @app.get("/api/escalations/{escalation_id}/audio")
    async def get_escalation_audio(escalation_id: str):
        rec = escalation_manager.get(escalation_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Escalation not found")

        # Prefer persisted copy
        audio_path = rec.get("audio_relpath")
        # If not present, try to resolve from original URL
        if not audio_path:
            url = rec.get("audio_url_at_submit")
            if url:
                audio_path = escalation_manager._parse_local_path_from_url(url)  # type: ignore[attr-defined]

        if not audio_path or not os.path.exists(audio_path):
            raise HTTPException(status_code=404, detail="Audio file not available")

        # Best-effort media type
        ext = os.path.splitext(audio_path)[1].lower()
        media = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".m4a": "audio/mp4",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
        }.get(ext, "application/octet-stream")
        return FileResponse(audio_path, media_type=media)

    @app.post("/api/speaking/metrics")
    async def speaking_metrics(body: Dict[str, Any]):
        """Compute lightweight pronunciation metrics from user audio.

        Expected JSON body:
        - userAudioBase64: string (data URL or raw base64)
        - userAudioUrl: string (optional alternative; Gradio-style /file= URL or absolute path)
        - transcript: string (optional)
        - level: string (optional, A1..C2)
        """
        user_audio_b64 = (body or {}).get("userAudioBase64")
        user_audio_url = (body or {}).get("userAudioUrl")
        transcript = (body or {}).get("transcript")
        level = (body or {}).get("level")

        audio_path = None
        tmp_path = None

        try:
            if user_audio_b64:
                data = user_audio_b64
                suffix = ".wav"
                if isinstance(data, str) and data.startswith("data:"):
                    try:
                        header, b64data = data.split(",", 1)
                    except ValueError:
                        raise HTTPException(status_code=400, detail="Invalid data URL format")
                    mime = header.split(";")[0].split(":")[-1].lower()
                    suffix = {
                        "audio/wav": ".wav",
                        "audio/x-wav": ".wav",
                        "audio/mpeg": ".mp3",
                        "audio/mp4": ".m4a",
                        "audio/webm": ".webm",
                        "audio/ogg": ".ogg",
                        "audio/flac": ".flac",
                    }.get(mime, ".wav")
                    raw = base64.b64decode(b64data)
                else:
                    raw = base64.b64decode(str(data))

                tmp_path = save_audio_to_temp_file(raw, suffix=suffix)
                audio_path = tmp_path
            elif user_audio_url:
                url = str(user_audio_url)
                # Absolute local path
                if os.path.isabs(url) and os.path.exists(url):
                    audio_path = url
                else:
                    # Try to extract local path from Gradio-style URL: /file=/abs/path
                    local_path = None
                    if "file=" in url:
                        local_path = url.split("file=")[-1]
                        if "?" in local_path:
                            local_path = local_path.split("?")[0]
                        local_path = unquote(local_path)
                    if local_path and os.path.exists(local_path):
                        audio_path = local_path
                    else:
                        raise HTTPException(status_code=400, detail="userAudioUrl is not resolvable on server")
            else:
                raise HTTPException(status_code=400, detail="Provide userAudioBase64 or userAudioUrl")

            metrics = analyze_pronunciation_metrics(audio_path, transcript=transcript, level=level)
            return metrics
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    # ------------------- Progress API (FastAPI) -------------------
    @app.get("/api/progress")
    async def get_progress():
        try:
            return tutor.progress_tracker.to_json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app
