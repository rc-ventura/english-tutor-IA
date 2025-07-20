from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import gradio as gr

from src.core.tutor import EnglishTutor
from ui.interfaces import GradioInterface

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tutor = EnglishTutor()
interface = GradioInterface(tutor).create_interface()
app = gr.mount_gradio_app(app, interface, path="/gradio")


@app.post("/api/speech")
async def process_speech(file: UploadFile = File(...), level: str = Form("B1")):
    """Handle speaking practice: audio upload -> response text + audio."""
    audio_path = f"/tmp/{file.filename}"
    with open(audio_path, "wb") as out:
        out.write(await file.read())

    hist, _ = tutor.speaking_tutor.handle_transcription(history=[], audio_filepath=audio_path)
    response_generator = tutor.speaking_tutor.handle_bot_response(history=hist, level=level)

    final_history, audio_out = None, None
    for hist_out, _, audio_path in response_generator:
        final_history = hist_out
        audio_out = audio_path
    return {"history": final_history, "audio_path": audio_out}


@app.post("/api/writing/evaluate")
async def evaluate(essay: str = Form(...), level: str = Form("B1")):
    """Evaluate an essay and return the conversation history."""
    gen = tutor.writing_tutor.process_input(essay, [], level)
    final_history = None
    for hist, _ in gen:
        final_history = hist
    return {"history": final_history}


@app.post("/api/writing/topic")
async def generate_topic(level: str = Form("B1")):
    """Generate a random writing topic."""
    gen = tutor.writing_tutor.generate_random_topic(level=level, history=[])
    final_history = None
    for hist, _ in gen:
        final_history = hist
    return {"history": final_history}


@app.get("/api/progress")
def progress():
    """Get current progress dashboard as HTML."""
    return {"html": tutor.progress_tracker.html_dashboard()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
