import gradio as gr


def echo(x):
    return x


def main():
    """Build and return the Gradio demo."""
    with gr.Blocks() as demo:
        with gr.Tab("Speaking Skills"):
            gr.Markdown("### Practice your speaking and get AI feedback")
            with gr.Row():
                _chatbot = gr.Chatbot(
                    height=500,
                    avatar_images=[
                        "https://cdn-icons-png.flaticon.com/512/25/25231.png",
                        "https://cdn-icons-png.flaticon.com/512/25/25231.png",
                    ],
                )
            with gr.Row():
                _entry = gr.Textbox(label="Chat with your AI English Tutor")
                _mic = gr.Audio(
                    sources=["microphone"],
                    type="filepath",
                    label="Record audio (click to speak)",
                )
            with gr.Row():
                _send_button = gr.Button("Submit", variant="primary")
                gr.Button("Clear")
            with gr.Tab("Writing Skills"):
                gr.Markdown("### Practice your writing and get AI feedback")
                with gr.Row():
                    _level = gr.Dropdown(
                        label="🎓 Select your English level",
                        choices=["A1", "A2", "B1", "B2", "C1", "C2"],
                        value="B1",
                        interactive=True,
                    )
                    gr.Button("🎲 Generate random topic")
                with gr.Row():
                    _chatbot_writing = gr.Chatbot(
                        height=550,
                        avatar_images=[
                            "https://cdn-icons-png.flaticon.com/512/25/25231.png",
                            "https://cdn-icons-png.flaticon.com/512/25/25231.png",
                        ],
                    )
                    _input_writing = gr.Textbox(label="Input Text", lines=25, placeholder="Type your text here...")
                with gr.Row():
                    _evaluate_btn = gr.Button("Evaluate", variant="primary")
                    _clear_writing = gr.Button("Clear", variant="secondary")
        return demo


def test_echo():
    assert echo("hi") == "hi"


if __name__ == "__main__":
    demo = main()
    demo.launch()
