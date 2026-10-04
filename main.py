import common.logger_config
import sys
import logging

from assistant_core.application import AssistantApplication
from assistant_core.database.db_service import get_active_users
from assistant_core.integrations.manager import IntegrationManager

from assistant_core.log_parser import LogParser
from assistant_core.tts_engine import TTSEngine
from assistant_core.asr_engine import ASREngine
from assistant_core.voice_authenticator import VoiceAuthenticator
from channels.local_audio_channel import LocalAudioChannel
from common.config import WAKE_WORD, VOSK_MODEL_PATH, IGNORE_WHEN_SPEAKING, INTERRUPT_TTS

logger = logging.getLogger("MAIN_CONTROLLER")


def main():
    logger.info("Инициализация")

    try:
        asr = ASREngine(model_path=VOSK_MODEL_PATH)
        tts = TTSEngine(speaker='baya')

        channel = LocalAudioChannel(
            asr=asr,
            tts=tts,
            wake_word=WAKE_WORD,
            interrupt_enabled=INTERRUPT_TTS,
            ignore_when_speaking=IGNORE_WHEN_SPEAKING
        )

        manager = IntegrationManager()
        parser = LogParser()
        voice_auth = VoiceAuthenticator()
        active_users = get_active_users()
        voice_auth.sync_cache(active_users)

        app = AssistantApplication(
            channel=channel,
            manager=manager,
            parser=parser,
            voice_auth=voice_auth
        )

    except Exception as e:
        logger.critical(f"Ошибка при сборке зависимостей: {e}")
        sys.exit(1)

    app.run()


if __name__ == "__main__":
    main()
