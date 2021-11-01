import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}

bot = None
current_timestamp = 0
error_sent_messages = []


def log_and_inform(message):
    """Логирует ошибки уровня ERROR.
    Однократно отправляет информацию об ошибках в телеграм,
    если отправка возможна.
    """
    logging.error(message)
    if message not in error_sent_messages:
        try:
            send_message(bot, message)
            error_sent_messages.append(message)
        except Exception as error:
            logging.info('Не удалось отправить сообщение об ошибке, '
                         f'{error}')


def send_message(bot, message):
    """Отправляет сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'Отправлено сообщение: "{message}"')
    except Exception as error:
        logging.error(f'Cбой отправки сообщения, ошибка: {error}')


def get_api_answer(url, current_timestamp):
    """Отправляет запрос к API домашки на  ENDPOINT."""
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': current_timestamp}
    response = requests.get(url, headers=headers, params=payload)
    if response.status_code != 200:
        message = 'Эндпоинт не отвечает'
        log_and_inform(message)
        raise Exception(message)
    return response.json()


def check_response(response):
    """Проверяет полученный ответ на корректность."""
    if 'current_date' not in response:
        message = 'В полученном ответе нет "current_date", {error}'
        log_and_inform(message)
        raise KeyError(f'{message}')
    homework = response.get('homeworks')[0]
    keys = ['status', 'homework_name']
    for key in keys:
        if key not in homework:
            message = f'Ключа {key} нет в ответе API'
            log_and_inform(message)
            raise KeyError(message)
    if homework['status'] not in HOMEWORK_STATUSES:
        message = 'Неизвестный статус домашней работы'
        log_and_inform(message)
        raise KeyError(message)
    global current_timestamp
    current_timestamp = response['current_date']
    return homework


def parse_status(homework):
    """Формирует сообщение с обновленным статусом для отправки."""
    homework_status = homework['status']
    homework_name = homework['homework_name']
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Настраивает логгирование и запускает бота."""
    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        level=logging.INFO,
        format='%(asctime)s, %(levelname)s, %(message)s'
    )

    vars = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    for var in vars:
        if os.getenv(var) is None:
            message = 'Проблемы с переменными окружения'
            logging.critical(message)
            raise SystemExit(message)

    global bot
    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    while True:
        try:
            response = get_api_answer(ENDPOINT, current_timestamp)
            if 'homeworks' in response:
                checked_response = check_response(response)
                message = parse_status(checked_response)
                if message is not None:
                    send_message(bot, message)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            log_and_inform(message)
            time.sleep(RETRY_TIME)
        continue


if __name__ == '__main__':
    main()
