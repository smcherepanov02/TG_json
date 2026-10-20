#!pip install pyTelegramBotAPI json_repair json5
from telebot import TeleBot, types
import json
import json_repair
import json5

BOT_TOKEN = '' # тут надо ввести ТОКЕН_BOT
bot = TeleBot(token=BOT_TOKEN, parse_mode='html')

MAX_MESSAGE_LENGTH = 10000
TELEGRAM_LIMIT = 4000

def send_safe_message(chat_id, text, reply_markup=None):
    try:
        if len(text) > TELEGRAM_LIMIT:
            text = text[:TELEGRAM_LIMIT] + "\n\n...[Текст обрезан, превышен лимит]"
        bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")

# ----------------------------------------ФУНКЦИЯ ОБРАБОТКИ JSON----------------------------------------

def process_and_reply(chat_id, raw_text):
    raw_text = raw_text.strip()
    
    # Игнорируем пустые сообщения
    if not raw_text:
        return

    # 1. Пытаемся распарсить как есть (валидный JSON)
    try:
        data = json.loads(raw_text)
        formatted = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)
        send_safe_message(chat_id, f'✅ <b>JSON корректный, ошибок нет:</b>\n<code>{formatted}</code>')
        return
    except json.JSONDecodeError:
        pass

    # 2. Пытаемся починить через json_repair
    data = None
    try:
        data = json_repair.loads(raw_text)
        if not data:
            data = None
    except Exception:
        pass

    # 3. Если json_repair не справился, пробуем json5
    if data is None:
        try:
            data = json5.loads(raw_text)
        except Exception:
            pass

    # 4. Отправляем результат
    if data is not None:
        formatted = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)
        msg = (
            f'🛠 <b>В JSON были ошибки, но я их исправил!</b>\n'
            f'Вот исправленный вариант:\n'
            f'<code>{formatted}</code>'
        )
        send_safe_message(chat_id, msg)
    else:
        # 5. Если совсем не смогли, показываем, где ошибка в ОРИГИНАЛЕ
        try:
            json.loads(raw_text)
        except json.JSONDecodeError as e:
            lines = raw_text.splitlines()
            line_idx = min(e.lineno - 1, len(lines) - 1)
            line_text = lines[line_idx] if lines else ""
            pointer = " " * (e.colno - 1) + "^"
            
            error_msg = (
                f'<b>К сожалению, автоматически исправить не удалось.</b>\n'
                f'Ошибка: <code>{e.msg}</code>\n'
                f'Строка {e.lineno}, колонка {e.colno}:\n'
                f'<code>{line_text}\n{pointer}</code>'
            )
            send_safe_message(chat_id, error_msg)
        except Exception:
            send_safe_message(chat_id, '<b>Это не похоже на JSON.</b> Проверьте текст.')

# ----------------------------------------ХЭНДЛЕРЫ ----------------------------------------

@bot.message_handler(commands=['start'])
def start_command_handler(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Мой репозиторий"))
    send_safe_message(
        chat_id=message.chat.id, 
        text='Привет! Пришли мне JSON текстом или файлом — я найду ошибки и починю.',
        reply_markup=markup
    )

# ВАЖНО: Этот обработчик должен идти ДО общего @bot.message_handler()
@bot.message_handler(func=lambda m: m.text == "Мой репозиторий")
def repository_link_handler(message: types.Message):
    send_safe_message(
        chat_id=message.chat.id,
        text='Вот ссылка на мой репозиторий: https://github.com/smcherepanov02' # Cсылка на репозиторий
    )

@bot.message_handler(content_types=['document'])
def handle_document(message: types.Message):
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        raw_text = downloaded_file.decode('utf-8')
        process_and_reply(message.chat.id, raw_text)
    except Exception as e:
        send_safe_message(message.chat.id, f"Не удалось прочитать файл: {e}")

# Общий обработчик (срабатывает для всего остального текста)
@bot.message_handler()
def message_handler(message: types.Message):
    raw_text = message.text or ""
    if len(raw_text) > MAX_MESSAGE_LENGTH:
        send_safe_message(
            message.chat.id, 
            'Текст слишком большой. Пожалуйста, отправьте его как файл (.txt или .json).'
        )
        return
    process_and_reply(message.chat.id, raw_text)

if __name__ == '__main__':
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)