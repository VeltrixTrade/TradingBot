"""
Mustafa Bot - Google Gemini AI Client
عميل Gemini API للتحليل الذكي
"""

import json
import asyncio
import logging
from typing import Dict

logger = logging.getLogger('mustafa_bot.ai.gemini')


class GeminiClient:
    """Google Gemini API client."""

    def __init__(self, api_key: str, model: str = 'gemini-2.0-flash'):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model,
            generation_config={
                'temperature': 0.3,
                'max_output_tokens': 2000,
                'response_mime_type': 'application/json',
            }
        )
        self.name = 'gemini'

    async def analyze(self, system_prompt: str, analysis_prompt: str,
                      max_retries: int = 3) -> Dict:
        """Send analysis request to Gemini and parse JSON response."""
        combined_prompt = f"{system_prompt}\n\n{analysis_prompt}"

        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    combined_prompt,
                )

                content = response.text
                result = self._parse_response(content)

                if 'error' not in result:
                    logger.info(f'Gemini analysis: {result.get("direction")} '
                                f'(confidence: {result.get("confidence")}%)')
                    return result

            except Exception as e:
                logger.warning(f'Gemini attempt {attempt + 1}/{max_retries} failed: {e}')
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return {'error': 'Gemini: All retries failed', 'provider': self.name}

    def _parse_response(self, content: str) -> Dict:
        """Parse AI response."""
        try:
            text = content.strip()
            if text.startswith('```json'):
                text = text[7:]
            elif text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()

            result = json.loads(text)

            required = ['direction', 'confidence']
            for field in required:
                if field not in result:
                    return {'error': f'Missing field: {field}', 'provider': self.name}

            result['provider'] = self.name
            return result

        except json.JSONDecodeError as e:
            logger.error(f'Gemini JSON parse error: {e}')
            return {'error': f'JSON parse error: {e}', 'provider': self.name}
