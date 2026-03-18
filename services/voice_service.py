# services/voice_service.py

import httpx
import os
import base64
from pathlib import Path
from config import settings

class VoiceService:
    """
    Voice synthesis service.
    Primary: ElevenLabs API (if API key is set)
    Fallback: gTTS (Google Text-to-Speech, free, no API key needed)
    """

    ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self):
        self.elevenlabs_key = getattr(settings, 'ELEVENLABS_API_KEY', '')
        self.use_elevenlabs = bool(self.elevenlabs_key)

    async def synthesize_text(
        self,
        text: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # ElevenLabs default "Rachel" voice
        stability: float = 0.5,
        similarity_boost: float = 0.75
    ) -> bytes:
        """
        Convert text to speech.
        Returns raw MP3 bytes.
        """
        if self.use_elevenlabs:
            return await self._synthesize_elevenlabs(text, voice_id, stability, similarity_boost)
        else:
            return await self._synthesize_gtts(text)

    async def _synthesize_elevenlabs(self, text: str, voice_id: str, stability: float, similarity_boost: float) -> bytes:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}",
                headers={
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": self.elevenlabs_key
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": stability,
                        "similarity_boost": similarity_boost
                    }
                },
                timeout=30.0
            )
            if response.status_code != 200:
                raise Exception(f"ElevenLabs API error: {response.status_code} {response.text}")
            return response.content

    async def _synthesize_gtts(self, text: str) -> bytes:
        """
        Free fallback using gTTS. No API key needed.
        Returns MP3 bytes via a temp file.
        """
        from gtts import gTTS
        import tempfile
        import asyncio

        def _generate():
            tts = gTTS(text=text, lang='en', slow=False)
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                tts.save(tmp.name)
                with open(tmp.name, 'rb') as f:
                    audio_bytes = f.read()
                os.unlink(tmp.name)
                return audio_bytes

        # Run blocking gTTS in thread pool so it doesn't block the event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _generate)

    async def get_available_voices(self) -> list[dict]:
        """List available voices from ElevenLabs, or return defaults."""
        if not self.use_elevenlabs:
            return [
                {"voice_id": "gtts_default", "name": "Default (gTTS)", "provider": "gtts"}
            ]
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.ELEVENLABS_BASE_URL}/voices",
                headers={"xi-api-key": self.elevenlabs_key}
            )
            if response.status_code != 200:
                return []
            data = response.json()
            return [
                {
                    "voice_id": v["voice_id"],
                    "name": v["name"],
                    "provider": "elevenlabs",
                    "preview_url": v.get("preview_url")
                }
                for v in data.get("voices", [])
            ]