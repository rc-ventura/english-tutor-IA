import { useState } from 'react';

export default function App() {
  const [essay, setEssay] = useState('');
  const [writingHistory, setWritingHistory] = useState([]);
  const [topic, setTopic] = useState('');
  const [audioUrl, setAudioUrl] = useState('');

  async function handleEvaluate() {
    const formData = new FormData();
    formData.append('essay', essay);
    formData.append('level', 'B1');
    const res = await fetch('/api/writing/evaluate', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    setWritingHistory(data.history);
  }

  async function handleTopic() {
    const formData = new FormData();
    formData.append('level', 'B1');
    const res = await fetch('/api/writing/topic', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    setTopic(data.history[data.history.length - 1].content);
  }

  async function handleAudio(e) {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('level', 'B1');
    const res = await fetch('/api/speech', { method: 'POST', body: formData });
    const data = await res.json();
    setAudioUrl(data.audio_path);
  }

  return (
    <div style={{ padding: '1rem' }}>
      <h1>Sophia AI React</h1>
      <section>
        <h2>Writing</h2>
        <textarea
          rows={10}
          value={essay}
          onChange={e => setEssay(e.target.value)}
          placeholder="Write your essay"
        />
        <div>
          <button onClick={handleEvaluate}>Evaluate</button>
          <button onClick={handleTopic}>Random Topic</button>
        </div>
        <pre>{JSON.stringify(writingHistory, null, 2)}</pre>
        {topic && <p><strong>Topic:</strong> {topic}</p>}
      </section>
      <section>
        <h2>Speaking</h2>
        <input type="file" accept="audio/*" onChange={handleAudio} />
        {audioUrl && <audio src={audioUrl} controls />}        
      </section>
    </div>
  );
}
