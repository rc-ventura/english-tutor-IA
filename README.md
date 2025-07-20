# 🎓 Sophia AI: Your Personal English Tutor

<div align="center">
  <p><strong>Sophia AI is a multimodal, AI-powered English tutor designed to accelerate language learning through immersive, interactive conversation and writing practice.</strong></p>
  <p>This project serves as a powerful demonstration of cutting-edge AI capabilities, creating a user experience that is both effective for students and compelling for investors.</p>

  [![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
  [![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991.svg)](https://openai.com/)
  [![Gradio](https://img.shields.io/badge/Gradio-UI-FF4B4B.svg)](https://gradio.app/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
</div>


## 🌟 The Vision: The Future of Language Learning

The global market for language learning is massive and continues to grow. However, traditional methods often lack the personalization and interactivity needed for true fluency. Sophia AI addresses this gap by providing a scalable, on-demand tutor that simulates real-world conversation, offering a significant competitive advantage.

For an investor, Sophia AI represents an opportunity to enter the EdTech market with a product built on a modern, efficient, and highly engaging technology stack.


## ✨ Key Features & Technical Highlights

Sophia AI combines a user-friendly interface with a powerful backend to deliver a seamless learning experience.

### 1. Interactive Speaking Practice (Voice-to-Voice)

- **User Experience**: Students engage in natural, spoken conversations. They speak, and Sophia listens, transcribes, and responds with both text and a natural-sounding voice, creating a fluid and immersive practice environment.
- **Technical Magic**: This is powered by a single, efficient call to OpenAI's **`gpt-4o-mini-audio-preview`** model, which returns both a text response and its corresponding audio. This multimodal approach reduces latency and complexity, creating a responsive, real-time feel.

### 2. Real-Time Writing Feedback

- **User Experience**: Students receive instant, streaming feedback on their writing. As they submit their text, Sophia analyzes it and provides corrections and suggestions, appearing word-by-word as if a live tutor were typing.
- **Technical Magic**: We use **OpenAI's streaming API** to deliver feedback dynamically, enhancing engagement and providing immediate value.

### 3. Audio-Enhanced Learning

- **User Experience**: Don't just read your feedback—listen to it. A single click on the "🗣️" icon converts the written feedback into audio, reinforcing learning by connecting text with correct pronunciation and intonation.
- **Technical Magic**: This feature leverages OpenAI's **Text-to-Speech (TTS)** API, adding another layer of multimodal interaction.


## 🛠️ The Technology Stack: Built for Scale

Our architecture is designed to be modular, scalable, and efficient.

- **Backend**: Python 3.8+
- **AI & Machine Learning**: OpenAI API
  - **Multimodal Chat**: `gpt-4o-mini-audio-preview` (Text + Audio Generation)
  - **Text Streaming**: `chat.completions` with `stream=True`
  - **Audio Transcription**: `gpt-4o-mini-transcribe` (Whisper)
  - **Text-to-Speech**: `tts-1`
- **Frontend**: Gradio (for rapid, interactive UI development)
- **Dependency Management**: Poetry


## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- An [OpenAI API Key](https://openai.com/)
- [Poetry](https://python-poetry.org/) (recommended)

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/seu-usuario/english-tutor-ai.git
    cd english-tutor-ai
    ```

2.  **Install dependencies using Poetry:**
    ```bash
    poetry install
    ```

3.  **Launch the application:**
    ```bash
    poetry run python main.py
    ```

4.  **Open the interface** in your browser (usually at `http://127.0.0.1:7860`) and **enter your OpenAI API Key** in the designated field.


## 🏗️ Project Architecture

The codebase is organized for clarity and maintainability, showcasing a professional development approach.

```
English-Tutor-AI/
├── assets/                # Static assets (images, css)
├── src/
│   ├── core/              # Core application logic (The "Brain")
│   │   ├── tutor.py       # Main orchestrator class
│   │   ├── speaking_tutor.py # Logic for speaking practice
│   │   └── writing_tutor.py  # Logic for writing feedback
│   ├── services/          # External API clients (OpenAI)
│   ├── models/            # Data models and system prompts
│   └── utils/             # Helper functions (e.g., audio processing)
├── ui/                    # Gradio user interface definition
├── tests/                 # Automated tests
├── main.py                # Application entry point
└── pyproject.toml         # Project dependencies (Poetry)
```

## ⚛️ React Integration

This repository also includes a minimal React frontend served via **FastAPI**.
The `api/server.py` file mounts the Gradio interface and exposes REST endpoints
used by the React app. To try it out:

1. Install the additional dependencies: `pip install fastapi uvicorn`.
2. Start the backend with `python api/server.py`.
3. Inside the `frontend` folder run `npm install` and `npm run dev`.
4. Open `http://localhost:5173` to use the React interface.


## 🔮 Future Roadmap & Vision

Sophia AI is a strong foundation. Future enhancements could include:

-   **Advanced Grammar Analysis**: Detailed explanations for grammatical errors.
-   **Personalized Learning Paths**: Tracking student progress and suggesting specific exercises.
-   **Vocabulary Builder**: Identifying and reinforcing new vocabulary.
-   **Multiple Tutor Personas**: Allowing users to choose different voices and teaching styles.
-   **Deployment to Cloud**: Packaging the application for scalable cloud deployment.


## 🤝 Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

1. Fork the project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

## 📧 Contact

Your Name - [@your_twitter](https://twitter.com/your_twitter) - your.email@example.com

Project Link: [https://github.com/your-username/english-tutor-ai](https://github.com/your-username/english-tutor-ai)

## 🙏 Acknowledgments

- [OpenAI](https://openai.com/) for providing the amazing API
- All contributors who helped improve this project
- The open-source community for all the support
