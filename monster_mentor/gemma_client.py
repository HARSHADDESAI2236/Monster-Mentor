"""Gemma 4 through the hosted Gemini API (no local install). Needs a free API key from
https://aistudio.google.com/apikey"""
import json
import os
import re
import time

from . import prompts

MODELS = ["gemma-4-26b-a4b-it", "gemma-4-31b-it", "gemini-2.5-flash"]
DEFAULT_MODEL = os.environ.get("GEMMA_MODEL", MODELS[0])


class GemmaError(Exception):
    """Raised for any problem talking to the API or parsing the model's output."""


def friendly_error(e):
    msg = str(e)
    low = msg.lower()
    if "429" in msg or "quota" in low or "rate" in low:
        return "Rate limit reached. Wait a minute and try again."
    if "api key" in low or "401" in msg or "403" in msg or "permission" in low:
        return "The API key was rejected. Check it at aistudio.google.com/apikey."
    if "503" in msg or "unavailable" in low or "high demand" in low:
        return (
            "The model is experiencing temporary high demand on Google's servers. "
            "Switching models in the sidebar (e.g. gemma-4-31b-it or gemini-2.5-flash) "
            "or trying again in 10-20 seconds usually resolves this."
        )
    return f"Gemma request failed: {msg[:200]}"


def validate_question(q):
    if not isinstance(q, dict):
        raise GemmaError("Question is not an object")
    opts = q.get("options")
    ans = q.get("answer")
    if not (isinstance(q.get("q"), str) and isinstance(opts, list) and len(opts) >= 2
            and all(isinstance(o, str) for o in opts)):
        raise GemmaError("Malformed question")
    if isinstance(ans, str) and ans.strip().isdigit():
        ans = int(ans)
    if not isinstance(ans, int) or isinstance(ans, bool) or not 0 <= ans < len(opts):
        raise GemmaError("Answer index out of range")
    return {"q": q["q"], "options": opts, "answer": ans, "why": str(q.get("why", ""))}


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except ValueError:
                pass
    raise GemmaError("Model did not return valid JSON")


class GemmaClient:
    def __init__(self, api_key=None, model=DEFAULT_MODEL):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model = model
        self._client = None

    # ---- connection ----
    def status(self):
        """Return (ok, message). Makes no network call, so it costs no quota."""
        if not self.api_key:
            return False, "Add your Gemini API key in the sidebar (free at aistudio.google.com/apikey)."
        return True, f"Ready: {self.model}"

    # ---- low-level calls (the only code that touches the SDK) ----
    def _sdk(self):
        from google import genai
        from google.genai import types
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client, types

    def _contents(self, messages, types):
        return [types.Content(role="model" if m["role"] == "assistant" else "user",
                              parts=[types.Part(text=m["content"])]) for m in messages]

    def _generate(self, messages, system=None):
        client, types = self._sdk()
        cfg = types.GenerateContentConfig(system_instruction=system) if system else None
        
        # Try primary model, retry with backoff on 503 temporary overload
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                resp = client.models.generate_content(
                    model=self.model,
                    contents=self._contents(messages, types),
                    config=cfg,
                )
                return resp.text or ""
            except Exception as e:
                err_low = str(e).lower()
                if ("503" in err_low or "unavailable" in err_low or "high demand" in err_low) and attempt < max_attempts - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise

    def _stream(self, messages, system=None):
        client, types = self._sdk()
        cfg = types.GenerateContentConfig(system_instruction=system) if system else None
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                for chunk in client.models.generate_content_stream(
                        model=self.model, contents=self._contents(messages, types), config=cfg):
                    if chunk.text:
                        yield chunk.text
                return
            except Exception as e:
                err_low = str(e).lower()
                if ("503" in err_low or "unavailable" in err_low or "high demand" in err_low) and attempt < max_attempts - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise

    # ---- chat ----
    def chat(self, messages, system=None):
        try:
            return self._generate(messages, system)
        except GemmaError:
            raise
        except Exception as e:
            raise GemmaError(friendly_error(e)) from e

    def stream_chat(self, messages, system=None):
        """Yield text chunks as they arrive (works with st.write_stream)."""
        try:
            yield from self._stream(messages, system)
        except GemmaError:
            raise
        except Exception as e:
            raise GemmaError(friendly_error(e)) from e

    # ---- structured generation ----
    def _json_call(self, prompt, retries=2):
        last = None
        for attempt in range(retries + 1):
            try:
                return parse_json(self.chat([{"role": "user", "content": prompt}]))
            except GemmaError as e:
                last = e
                err_str = str(e)
                if "Rate limit" in err_str or "API key" in err_str:
                    break  # retrying won't help
                if "high demand" in err_str and attempt < retries:
                    time.sleep(1.5)
        raise last

    def generate_quiz(self, lesson, n=3):
        data = self._json_call(prompts.quiz_prompt(lesson, n))
        items = data.get("quiz", []) if isinstance(data, dict) else data
        good = []
        for q in items:
            try:
                good.append(validate_question(q))
            except GemmaError:
                continue
        if not good:
            raise GemmaError("Gemma returned no usable questions. Try again.")
        return good

    def generate_lesson(self, topic, subject, monster_ids):
        data = self._json_call(prompts.lesson_prompt(topic, subject, monster_ids))
        if not isinstance(data, dict) or not all(k in data for k in ("title", "analogy", "concept", "quiz")):
            raise GemmaError("Lesson is missing fields")
        data["quiz"] = [validate_question(q) for q in data["quiz"]]
        if data.get("monster") not in monster_ids:
            data["monster"] = monster_ids[0]
        data["id"] = re.sub(r"[^a-z0-9]+", "-", str(data.get("id") or data["title"]).lower()).strip("-")
        return data

    def explain_mistakes(self, lesson, wrong):
        return self.chat([{"role": "user", "content": prompts.explain_mistakes_prompt(lesson, wrong)}])
