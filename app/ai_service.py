import os
import google.generativeai as genai
from groq import Groq


def get_gemini_client():
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    return genai.GenerativeModel("gemini-2.5-flash")


def get_groq_client():
    return Groq(api_key=os.environ.get("GROQ_API_KEY"))


def generate_text(prompt, model="gemini", system_instruction=None):
    """Unified interface: model = "gemini" or "groq"."""
    try:
        if model == "gemini":
            client = get_gemini_client()
            full_prompt = (
                f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
            )
            response = client.generate_content(full_prompt)
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
