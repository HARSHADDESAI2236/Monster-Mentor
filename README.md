# Monster Mentor (Streamlit + Gemma 4)

Learn OS, DBMS and ML through friendly monsters. Built-in lessons and quizzes work offline; **Gemma 4 runs in the cloud through the Gemini API** (nothing to download) and adds:

- **Ask the monster**: chat with the lesson's monster, who answers in character.
- **Fresh quiz**: Gemma generates new multiple-choice questions for the current lesson.
- **Explain my mistakes**: after a quiz, Gemma explains why your wrong answers were wrong.
- **New lesson**: type any concept and Gemma writes a monster lesson with a quiz (can be saved into `content/`).

## Setup (no Ollama, no model download)
1. Get a free API key at https://aistudio.google.com/apikey
2. Install and run:
```
pip install -r requirements.txt
streamlit run app.py
```
3. Paste the key in the sidebar, or set it once:
   - env var: `export GEMINI_API_KEY="your-key"` (Windows: `setx GEMINI_API_KEY "your-key"`)
   - or create `.streamlit/secrets.toml` containing `GEMINI_API_KEY = "your-key"`

Models: `gemma-4-26b-a4b-it` (faster) and `gemma-4-31b-it` (stronger). Free-tier requests are rate-limited; if you hit the limit the app says so, so wait a minute.

Without a key, the lessons and built-in quizzes still work.

## Tests
```
python -m unittest discover tests
```

## Layout
- `app.py`: Streamlit UI
- `monster_mentor/gemma_client.py`: Gemini API client (chat, streaming, JSON quiz/lesson generation + validation)
- `monster_mentor/prompts.py`: all prompts in one place
- `monster_mentor/quiz_engine.py`, `progress.py`, `loader.py`: grading, saved scores, content loading
- `content/<topic>/*.json`: lessons. Schema: `id, title, monster, analogy, concept, quiz[{q, options[], answer, why}]`
