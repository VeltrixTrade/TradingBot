"""
Mustafa Bot - OpenAI (ChatGPT) Client
عميل ChatGPT API للتحليل الذكي
"""

import json
import asyncio
import logging
from typing import Dict

logger = logging.getLogger('mustafa_bot.ai.openai')


class OpenAIClient:
    """OpenAI ChatGPT API client."""

    def __init__(self, api_key: str, model: str = 'gpt-4o-mini'):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.name = 'chatgpt'

    async def analyze(self, system_prompt: str, analysis_prompt: str,
                      max_retries: int = 3) -> Dict:
        """Send analysis request to ChatGPT and parse JSON response."""
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": analysis_prompt},
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                    response_format={"type": "json_object"},
                )

                content = response.choices[0].message.content
                result = self._parse_response(content)

                if 'error' not in result:
                    logger.info(f'ChatGPT analysis: {result.get("direction")} '
                                f'(confidence: {result.get("confidence")}%)')
                    return result

            except Exception as e:
                logger.warning(f'ChatGPT attempt {attempt + 1}/{max_retries} failed: {e}')
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return {'error': 'ChatGPT: All retries failed', 'provider': self.name}

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
            logger.error(f'ChatGPT JSON parse error: {e}')
            return {'error': f'JSON parse error: {e}', 'provider': self.name}
