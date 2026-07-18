import re
import os
from google import genai
from google.genai import types as genai_types
from groq import Groq


def sanitize_for_prompt(text: str) -> str:
    text = re.sub(r'<\|im_start\|>|<\|im_end\|>|<\|system\|>|<\|user\|>|<\|assistant\|>', '', text)
    text = text.replace('\x00', '')
    return text[:10000]


def get_gemini_client():
    return genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


def get_groq_client():
    return Groq(api_key=os.environ.get("GROQ_API_KEY"))


def generate_text(prompt, model="gemini", system_instruction=None):
    """Unified interface: model = "gemini" or "groq"."""
    try:
        if model == "gemini":
            client = get_gemini_client()
            kwargs = {}
            if system_instruction:
                kwargs["config"] = genai_types.GenerateContentConfig(
                    system_instruction=system_instruction,
                )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                **kwargs,
            )
            return response.text

        if model == "groq":
            client = get_groq_client()
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(
                model="gemma2-9b-it",
                messages=messages,
            )
            return response.choices[0].message.content

        raise ValueError(f"Unknown model: {model}")
    except Exception as e:
        raise RuntimeError(f"AI generation failed: {str(e)}")
