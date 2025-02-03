import logging
import re
import sys

class EmojiFilter(logging.Filter):
    """Фильтр для замены эмодзи на текстовые эквиваленты в логах"""
    
    EMOJI_TO_TEXT = {
        '✅': '[OK]',
        '❌': '[ERROR]',
        '📨': '[NEW]',
        '📸': '[PHOTO]',
        '🕒': '[WAIT]',
        '📝': '[EDIT]',
        '⚠️': '[WARN]',
        '🎉': '[CONGRATS]',
        '🔗': '[LINK]',
        '📣': '[ANNOUNCE]'
    }
    
    def filter(self, record):
        if isinstance(record.msg, str):
            for emoji, text in self.EMOJI_TO_TEXT.items():
                record.msg = record.msg.replace(emoji, text)
        return True

def setup_logging():
    """Настройка логирования с фильтрацией эмодзи"""
    
    # Создаем форматтер для логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Создаем обработчик для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Создаем обработчик для записи в файл
    file_handler = logging.FileHandler('bot.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Добавляем фильтр эмодзи к обоим обработчикам
    emoji_filter = EmojiFilter()
    console_handler.addFilter(emoji_filter)
    file_handler.addFilter(emoji_filter)
    
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler) 