"""
Mustafa Bot - DeepSeek AI Client
عميل DeepSeek API للتحليل الذكي
"""

import json
import asyncio
import logging
from typing import Dict

logger = logging.getLogger('mustafa_bot.ai.deepseek')


class DeepSeekClient:
    """DeepSeek API client using OpenAI-compatible SDK."""

    def __init__(self, api_key: str, model: str = 'deepseek-chat'):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key,
            base_url='https://api.deepseek.com'
        )
        self.model = model
        self.name = 'deepseek'

    async def analyze(self, system_prompt: str, analysis_prompt: str,
                      max_retries: int = 3) -> Dict:
        """Send analysis request to DeepSeek and parse JSON response."""
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
                )

                content = response.choices[0].message.content
                result = self._parse_response(content)

                if 'error' not in result:
                    logger.info(f'DeepSeek analysis: {result.get("direction")} '
                                f'(confidence: {result.get("confidence")}%)')
                    return result

            except Exception as e:
                logger.warning(f'DeepSeek attempt {attempt + 1}/{max_retries} failed: {e}')
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return {'error': 'DeepSeek: All retries failed', 'provider': self.name}

    def _parse_response(self, content: str) -> Dict:
        """Parse AI response, handling markdown code blocks."""
        try:
            # Strip markdown code blocks if present
            text = content.strip()
            if text.startswith('```json'):
                text = text[7:]
            elif text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()

            result = json.loads(text)

            # Validate required fields
            required = ['direction', 'confidence']
            for field in required:
                if field not in result:
                    return {'error': f'Missing field: {field}', 'provider': self.name}

            result['provider'] = self.name
            return result

        except json.JSONDecodeError as e:
            logger.error(f'DeepSeek JSON parse error: {e}')
            return {'error': f'JSON parse error: {e}', 'provider': self.name}
