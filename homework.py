import json
import os
import telegram
import logging
import time
import requests

from http import HTTPStatus

from dotenv import load_dotenv


load_dotenv()

PRACTICUM_TOKEN = os.getenv('P_TOKEN')
TELEGRAM_TOKEN = os.getenv('T_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='program.log',
    encoding='UTF-8'
)


def check_tokens():
    """Проверка обязательных переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    else:
        error_message = (
            'Отсутствуют обязательные переменные: '
        )
        if not PRACTICUM_TOKEN:
            error_message += 'PRACTICUM_TOKEN '
        if not TELEGRAM_TOKEN:
            error_message += 'TELEGRAM_TOKEN '
        if not TELEGRAM_CHAT_ID:
            error_message += 'TELEGRAM_CHAT_ID'
        logging.error(error_message)
        return False


def send_message(bot, message):
    """Отправляем пользователю сообщение"""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Отправка сообщения в telegram')
    except Exception:
        logging.exception('Ошибка при отправке сообщения в telegram')


def get_api_answer(current_timestamp):
    """Отправка запроса к эндпоинту API-сервиса"""
    timestamp = current_timestamp or int(time.time())
    params = {"from_date": timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        logging.debug('Отправка запроса к эндпоинту API-сервиса')
    except Exception as error:
        logging.error(f'Ошибка при запросе к эндпоинту API: {error}')
    if response.status_code != HTTPStatus.OK:
        logging.error(
            f'Ответ не соответствует коду 200: {response.status_code}'
        )
        raise requests.exceptions.RequestException(
            f'Ответ не соответствует коду 200: {response.status_code}'
        )
    try:
        return response.json()
    except json.JSONDecodeError:
        logging.error('Ответ с сервера ее соответствуюет формату')
        send_message('Ответ с сервера ее соответствуюет формату')


def check_response(response):
    """Проверка ответа API на соответствие документации"""
    try:
        homework = response['homeworks']
    except KeyError as error:
        logging.error(f'Ошибка доступа по ключу: {error}')
    if not isinstance(homework, list):
        logging.error('Не соответствующий тип данных')
        raise TypeError('Не соответствующий тип данных')
    return homework


def parse_status(homework):
    """Информация о статусе домашней работы"""
    if 'homework_name' not in homework:
        raise KeyError('Ключ "homework_name" не найден')
    if 'status' not in homework:
        raise KeyError('Ключ "status" не найден')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise Exception(f'Статус работы не определён: {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return (
        f'Изменился статус проверки работы'
        f' "{homework_name}". {verdict}'
    )


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствуют обязательные переменные')
        return Exception('Отсутствуют обязательные переменные')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = ''
    error_message = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date', current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                message = 'Статус проверки пока не обновлён'
            if message != status:
                send_message(bot, message)
                status = message
        except Exception as error:
            logging.error(error)
            message_t = str(error)
            if message_t != error_message:
                send_message(bot, message_t)
                error_message = message_t
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
