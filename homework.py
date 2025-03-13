from http import HTTPStatus
import sys
import time
import os
import logging
from logging import StreamHandler, FileHandler

from telebot import TeleBot, apihelper
from dotenv import load_dotenv
import requests

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
    token_not_found = [
        token_name for token_name, token_value in tokens.items()
        if not token_value
    ]
    if token_not_found:
        logging.critical(f'Токены не найдены: {", ".join(token_not_found)}')
        sys.exit(1)
    logging.info('Все токены доступны')


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    try:
        logging.info('Отправляю сообщение..')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Сообщение отправлено: {message}')
    except (apihelper.ApiException, requests.RequestException) as error:
        raise ConnectionError(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Делает запрос к API и возвращает ответ в формате JSON."""
    logging.info(f'Отправляю запрос к {ENDPOINT} с параметрами: {timestamp}')
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if response.status_code != HTTPStatus.OK:
            raise ValueError(
                f'Ошибка при запросе к API статус:{response.status_code}'
            )
        logging.debug('Успешный запрос к API')
        return response.json()
    except requests.RequestException as error:
        raise ConnectionError(
            f'Сбой запроса к {ENDPOINT} c параметрами {timestamp}:{error}'
        )


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    logging.info('Начинаю проверку ответа от сервера..')
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарем')
    if 'homeworks' not in response:
        raise KeyError('Ожидаемых ключей не найдено!')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('homeworks не является списком')
    logging.info('Ответ API соответствует документации')
    logging.info('Проверка ответа от сервера завершена успешно!')
    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы из ответа API."""
    logging.info('Начинаю проверку статуса домашней работы..')
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ожидаемый ключ: homework_name')
    if 'status' not in homework:
        raise KeyError('Отсутствует ожидаемый ключ: status')
    homework_name = homework['homework_name']
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус домашней работы: {status}')
    verdict = HOMEWORK_VERDICTS[status]
    logging.info(f'Статус домашней работы {homework_name} изменен на {status}')
    logging.info('Проверка статуса домашней работы завершена успешно!')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_sent_message = None

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                if message != last_sent_message:
                    send_message(bot, message)
                    last_sent_message = message
            else:
                logging.debug('Нет новых статусов домашних работ')
            timestamp = response.get('current_date', int(time.time()))
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != last_sent_message:
                logging.error(message, exc_info=True)
                send_message(bot, message)
                last_sent_message = message
        finally:
            time.sleep(RETRY_PERIOD)

def main():
    """Основная логика работы бота."""
    # Создаем объект класса бота
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_sent_message = None

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                if message != last_sent_message:
                    send_message(bot, message)
                    last_sent_message = message
            else:
                logging.debug('Нет новых статусов домашних работ')
            timestamp = response.get('current_date', int(time.time()))
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != last_sent_message:
                logging.error(message, exc_info=True)
                send_message(bot, message)
                last_sent_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    stream_handler = StreamHandler(sys.stdout)
    file_handler = FileHandler('main.log')
    formatter = logging.Formatter(
        '%(created)f, %(asctime)s, %(msecs)d, %(levelname)s,'
        '%(message)s, %(module)s, %(name)s'
    )
    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[stream_handler, file_handler],
    )
    main()
