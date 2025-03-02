from http import HTTPStatus
import time
import os
import logging

import requests
from telebot import TeleBot
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность токенов."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    for token_name, token_value in tokens.items():
        if not token_value:
            logging.critical(f'Отсутствует токен: {token_name}')
            return False
    logging.info('Все токены доступны')
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Сообщение отправлено: {message}')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Делает запрос к API и возвращает ответ в формате JSON."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if response.status_code == HTTPStatus.OK:
            logging.info('Успешный запрос к API')
            return response.json()
        else:
            error_message = f'Ошибка при запросе к API: {response.status_code}'
            logging.error(error_message)
            raise Exception()
    except requests.RequestException:
        raise ConnectionError()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        logging.error('Ответ API не является словарем')
        raise TypeError()
    if 'homeworks' not in response or 'current_date' not in response:
        logging.error('Отсутствуют ключи в ответе API')
        raise KeyError()
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        logging.error('homeworks не является списком')
        raise TypeError()
    logging.info('Ответ API соответствует документации')
    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы из ответа API."""
    if 'homework_name' not in homework or 'status' not in homework:
        logging.error('Отсутствуют ключи в информации о домашней работе')
        raise KeyError()
    homework_name = homework['homework_name']
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        logging.error(f'Неизвестный статус домашней работы: {status}')
        raise ValueError()
    verdict = HOMEWORK_VERDICTS[status]
    logging.info(f'Статус домашней работы {homework_name} изменен на {status}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    # Создаем объект класса бота
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
        filename='main.log',
    )
    if not check_tokens():
        logging.critical('Отсутствуют необходимые токены. Остановка!')
        return
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logging.debug('Нет новых статусов домашних работ')
            timestamp = response.get('current_date', timestamp)
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
