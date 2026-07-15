"""
Mustafa Bot - AI Manager (Triple Consensus System)
نظام الإجماع الثلاثي: DeepSeek + Gemini + ChatGPT
"""

import asyncio
import logging
from typing import List, Dict, Tuple
import numpy as np

from ai.deepseek_client import DeepSeekClient
from ai.gemini_client import GeminiClient
from ai.openai_client import OpenAIClient
from ai.prompts import Prompts

logger = logging.getLogger('mustafa_bot.ai.manager')


class AIManager:
    """Manages AI consensus across 3 models."""

    def __init__(self, deepseek_key: str, gemini_key: str, openai_key: str,
                 deepseek_model: str = 'deepseek-chat',
                 gemini_model: str = 'gemini-2.0-flash',
                 openai_model: str = 'gpt-4o-mini'):
        self.deepseek = DeepSeekClient(deepseek_key, deepseek_model)
        self.gemini = GeminiClient(gemini_key, gemini_model)
        self.openai = OpenAIClient(openai_key, openai_model)
        self.providers = [self.deepseek, self.gemini, self.openai]

    async def get_consensus_analysis(self, market_data: dict, smc_analysis: dict,
                                      signal_type: str = 'SCALP') -> Dict:
        """Run analysis on all 3 AI models in parallel and build consensus."""

        # Build appropriate prompt
        system_prompt = Prompts.SYSTEM_PROMPT
        if signal_type == 'SCALP':
            analysis_prompt = Prompts.build_scalp_prompt(market_data, smc_analysis)
        elif signal_type == 'SWING':
            analysis_prompt = Prompts.build_swing_prompt(market_data, smc_analysis)
        else:
            analysis_prompt = Prompts.build_analysis_prompt(market_data, smc_analysis)

        # Send to all 3 models concurrently
        logger.info('🧠 Sending analysis to 3 AI models...')

        results = await asyncio.gather(
            self.deepseek.analyze(system_prompt, analysis_prompt),
            self.gemini.analyze(system_prompt, analysis_prompt),
            self.openai.analyze(system_prompt, analysis_prompt),
            return_exceptions=True,
        )

        # Process results
        analyses = []
        for i, result in enumerate(results):
            provider_name = self.providers[i].name
            if isinstance(result, Exception):
                logger.error(f'{provider_name} exception: {result}')
                analyses.append({'error': str(result), 'provider': provider_name})
            else:
                analyses.append(result)

        # Filter valid analyses (no errors)
        valid = [a for a in analyses if 'error' not in a]

        if len(valid) == 0:
            logger.warning('All AI models failed')
            return {
                'direction': 'NEUTRAL',
                'agreement': 0,
                'confidence': 0,
                'entry': 0, 'stop_loss': 0,
                'take_profit_1': 0, 'take_profit_2': 0, 'take_profit_3': 0,
                'reasoning': 'فشل جميع نماذج الذكاء الاصطناعي في التحليل',
                'prediction': '',
                'reversal_zones': [],
                'individual_analyses': analyses,
                'consensus_reached': False,
                'consensus_text': '❌ لم يتم الوصول إلى إجماع - فشل جميع النماذج',
            }

        # Determine consensus
        direction, agreement = self._determine_consensus(valid)
        consensus_reached = agreement >= 2

        if not consensus_reached:
            return {
                'direction': 'NEUTRAL',
                'agreement': agreement,
                'confidence': 0,
                'entry': 0, 'stop_loss': 0,
                'take_profit_1': 0, 'take_profit_2': 0, 'take_profit_3': 0,
                'reasoning': self._combine_reasoning(analyses),
                'prediction': '',
                'reversal_zones': self._combine_reversal_zones(valid),
                'individual_analyses': analyses,
                'consensus_reached': False,
                'consensus_text': f'⚠️ لا إجماع - {agreement}/{len(valid)} نماذج متفقة',
            }

        # Calculate consensus values
        confidence = self._weighted_confidence(valid, direction)
        levels = self._average_levels(valid, direction)
        reasoning = self._combine_reasoning(analyses)
        reversal_zones = self._combine_reversal_zones(valid)

        # Get prediction from any valid analysis
        prediction = ''
        for a in valid:
            if a.get('prediction'):
                prediction = a['prediction']
                break

        # Consensus text
        models_agreed = [a.get('provider', '?') for a in valid if a.get('direction') == direction]
        dir_ar = 'شراء 🟢' if direction == 'BUY' else 'بيع 🔴' if direction == 'SELL' else 'محايد'
        consensus_text = (
            f"✅ إجماع {agreement}/{len(valid)}: {dir_ar}\n"
            f"النماذج المتفقة: {', '.join(models_agreed)}\n"
            f"الثقة المجمعة: {confidence}%"
        )

        logger.info(f'🗳️ Consensus: {direction} ({agreement}/{len(valid)}) - Confidence: {confidence}%')

        return {
            'direction': direction,
            'agreement': agreement,
            'confidence': confidence,
            'entry': levels.get('entry', 0),
            'stop_loss': levels.get('stop_loss', 0),
            'take_profit_1': levels.get('take_profit_1', 0),
            'take_profit_2': levels.get('take_profit_2', 0),
            'take_profit_3': levels.get('take_profit_3', 0),
            'reasoning': reasoning,
            'prediction': prediction,
            'reversal_zones': reversal_zones,
            'individual_analyses': analyses,
            'consensus_reached': True,
            'consensus_text': consensus_text,
        }

    def _determine_consensus(self, analyses: List[Dict]) -> Tuple[str, int]:
        """Determine consensus direction and agreement count."""
        votes = {'BUY': 0, 'SELL': 0, 'NEUTRAL': 0}

        for a in analyses:
            direction = a.get('direction', 'NEUTRAL').upper()
            if direction in votes:
                votes[direction] += 1
            else:
                votes['NEUTRAL'] += 1

        # Find majority
        max_votes = max(votes.values())
        for direction, count in votes.items():
            if count == max_votes and direction != 'NEUTRAL':
                return direction, count

        # If NEUTRAL has most votes or it's a tie
        if votes['NEUTRAL'] == max_votes:
            return 'NEUTRAL', votes['NEUTRAL']

        # Tie between BUY and SELL -> NEUTRAL
        return 'NEUTRAL', 0

    def _weighted_confidence(self, analyses: List[Dict],
                              consensus_direction: str) -> int:
        """Calculate weighted confidence from agreeing models."""
        agreeing = [a for a in analyses
                    if a.get('direction', '').upper() == consensus_direction]

        if not agreeing:
            return 0

        confidences = [a.get('confidence', 0) for a in agreeing]
        return int(np.mean(confidences))

    def _average_levels(self, analyses: List[Dict],
                         consensus_direction: str) -> Dict:
        """Average entry/SL/TP levels from models that agree."""
        agreeing = [a for a in analyses
                    if a.get('direction', '').upper() == consensus_direction]

        if not agreeing:
            return {}

        fields = ['entry', 'stop_loss', 'take_profit_1', 'take_profit_2', 'take_profit_3']
        result = {}

        for field in fields:
            values = [a.get(field, 0) for a in agreeing if a.get(field, 0) > 0]
            result[field] = round(float(np.mean(values)), 2) if values else 0

        return result

    def _combine_reasoning(self, analyses: List[Dict]) -> str:
        """Combine reasoning from all models."""
        parts = []
        for a in analyses:
            provider = a.get('provider', 'unknown')
            if 'error' in a:
                parts.append(f"❌ {provider}: {a['error']}")
            else:
                reasoning = a.get('reasoning', 'لا يوجد تحليل')
                direction = a.get('direction', '?')
                confidence = a.get('confidence', 0)
                parts.append(f"🤖 {provider} ({direction}, {confidence}%): {reasoning}")

        return '\n\n'.join(parts)

    def _combine_reversal_zones(self, analyses: List[Dict]) -> List[float]:
        """Combine and deduplicate reversal zones from all models."""
        all_zones = []
        for a in analyses:
            zones = a.get('reversal_zones', [])
            if isinstance(zones, list):
                for z in zones:
                    try:
                        all_zones.append(float(z))
                    except (TypeError, ValueError):
                        pass

        if not all_zones:
            return []

        # Group zones within $2 of each other
        all_zones.sort()
        grouped = []
        current_group = [all_zones[0]]

        for i in range(1, len(all_zones)):
            if all_zones[i] - current_group[-1] <= 2.0:
                current_group.append(all_zones[i])
            else:
                grouped.append(round(float(np.mean(current_group)), 2))
                current_group = [all_zones[i]]

        if current_group:
            grouped.append(round(float(np.mean(current_group)), 2))

        return grouped[:5]  # Top 5 zones

    async def get_prediction(self, market_data: dict, smc_analysis: dict) -> Dict:
        """Get price prediction consensus."""
        system_prompt = Prompts.SYSTEM_PROMPT
        prediction_prompt = Prompts.build_prediction_prompt(market_data, smc_analysis)

        results = await asyncio.gather(
            self.deepseek.analyze(system_prompt, prediction_prompt),
            self.gemini.analyze(system_prompt, prediction_prompt),
            return_exceptions=True,
        )

        valid = [r for r in results if isinstance(r, dict) and 'error' not in r]

        if not valid:
            return {
                'prediction': 'لم يتمكن الذكاء الاصطناعي من إنشاء توقع',
                'reversal_zones': [],
            }

        predictions = [a.get('prediction', '') for a in valid if a.get('prediction')]
        zones = self._combine_reversal_zones(valid)

        return {
            'prediction': '\n\n'.join(predictions),
            'reversal_zones': zones,
        }

    async def get_chat_response(self, user_message: str) -> str:
        """Get chat response from one of the AI models (Gemini as primary, ChatGPT/DeepSeek fallback)."""
        system_prompt = (
            "You are Mustafa Bot, an elite XAU/USD gold trading expert with 20+ years of institutional experience. "
            "Answer the user's questions about gold trading, technical analysis, SMC/ICT strategy, market psychology, "
            "or market predictions in Arabic. Keep your response professional, helpful, highly detailed, and concise. "
            "Adopt the tone of a seasoned financial mentor."
        )
        try:
            # Use Gemini as primary for fast response
            response = await asyncio.to_thread(
                self.gemini.model.generate_content,
                f"{system_prompt}\n\nUser Question: {user_message}"
            )
            return response.text
        except Exception as e:
            logger.warning(f"Gemini chat response failed: {e}, trying ChatGPT fallback")
            try:
                response = await asyncio.to_thread(
                    self.openai.client.chat.completions.create,
                    model=self.openai.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=0.7,
                    max_tokens=1500,
                )
                return response.choices[0].message.content
            except Exception as ex:
                logger.error(f"OpenAI chat response failed: {ex}")
                return "❌ عذراً، نواجه مشكلة في الاتصال بمستشار الذكاء الاصطناعي حالياً. يرجى المحاولة لاحقاً."

