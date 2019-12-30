import constants
import task_manager

import telebot
from telebot import types

import sys, os, logging, shutil
#config logger
if os.path.exists(constants.logs):
    response = input('{0} already exists. Do you want to save it? (y/n) '.format(constants.logs))
    save_prev = response.lower().startswith('y')
    if save_prev:
        shutil.copy(constants.logs, constants.logs_backup)
logging.basicConfig(
    handlers=[logging.FileHandler(constants.logs, 'w', 'utf-8')],
    format='%(levelname)s - %(asctime)s - %(message)s', level=logging.INFO)

def my_handler(type, value, tb):
    logging.exception('Uncaught exception: {0}'.format(str(value)), exc_info=True)

# Install exception handler for all uncaught exceptions
sys.excepthook = my_handler

def main():
    task_manager.load_tasks()

    get_sender_id = lambda msg: msg.from_user.id
    get_chat_id = lambda msg: msg.chat.id
    get_basic_info = lambda msg: (get_sender_id(msg), get_chat_id(msg))

    def listener(messages):
        for m in messages:
            logging.info('Got message {0} from user {1}'.format(m.text, get_sender_id(m)))

    bot = telebot.TeleBot(constants.bot_token)
    bot.set_update_listener(listener)

    def remove_markup(message, txt='Хорошо!'):
        markup = types.ReplyKeyboardRemove(selective=False)
        bot.send_message(message.chat.id, text=txt, reply_markup=markup)
    
    @bot.message_handler(commands=['start'])
    def welcome(message):
        bot.reply_to(message, 'Привет!')

    @bot.message_handler(commands=['show_tasks'])
    def show_tasks(message):
        uid, cid = get_basic_info(message)

        logging.info('Showing all tasks to user {0}'.format(uid))

        sender_id = get_sender_id(message)
        if task_manager.has_tasks(sender_id):
            text = task_manager.show_tasks(sender_id) #nice string with all tasks
            
            bot.send_message(cid, text)
        else:
            bot.send_message(cid, 'Ура, все задачи выполнены! Можно отдыхать :)')

    @bot.message_handler(commands=['add_task'])
    def add_task(message):
        uid, cid = get_basic_info(message)
        logging.info('Trying to add task for user {0}'.format(uid))

        msg = bot.send_message(cid, 'Введи название задачи')
        def process_task_name(task_msg):
            task_text = task_msg.text
            task_manager.add_task(get_sender_id(task_msg), task_text)
            logging.info('Added task \'{0}\' to user {1}'.format(task_text, get_sender_id(task_msg)))
            bot.send_message(get_chat_id(task_msg), 'Задача \'{0}\' добавлена успешно!'.format(task_text))

        bot.register_next_step_handler(msg, process_task_name)

    @bot.message_handler(commands=['remove_task'])
    def remove_task(message):
        uid, cid = get_basic_info(message)

        if not task_manager.has_tasks(uid):
            bot.send_message(cid, 'Все задачи выполнены. Удалять нечего')
            return 

        tasks = task_manager.get_tasks(uid)

        markup = types.InlineKeyboardMarkup(row_width=3)
        btns = [types.InlineKeyboardButton(task, callback_data=str(idx)) for idx, task in enumerate(tasks)]
        markup.add(*btns)

        keyboard_message = bot.send_message(cid, 'Что удалить?', reply_markup=markup)

        @bot.callback_query_handler(func=lambda call: True)
        def remove(call):
            if not task_manager.has_tasks(uid):
                return

            nonlocal tasks
            task_name = ''
            try:
                task_name = tasks[int(call.data)]
            except IndexError:
                logging.error('Index error occured, aborting remove task...')
                logging.error('Tasks: {0}; index: {1}'.format(tasks, call.data))
                bot.send_message(cid, 'Возникла внутреняя ошибка. Попробуйте позже...')
                return
                
            logging.info('Removing task \'{0}\' from user {1}'.format(task_name, uid))
            task_manager.remove_task(uid, task_name)
            bot.send_message(cid, 'Задача \'{0}\' успешно удалена!'.format(task_name))

            new_tasks = task_manager.get_tasks(uid)
            if tasks != new_tasks:
                new_markup = types.InlineKeyboardMarkup(row_width=3)
                btns = [types.InlineKeyboardButton(task, callback_data=str(idx)) for idx, task in enumerate(new_tasks)]
                new_markup.add(*btns)
                bot.edit_message_reply_markup(chat_id=cid, message_id=keyboard_message.message_id, reply_markup = new_markup)
                tasks = new_tasks

    #This should always be last decorator as this is like 'default' option in switch statement (handles any message)
    @bot.message_handler(func=lambda msg: True)
    def handle_text(message):
        sender_id = get_sender_id(message)
        text = message.text
        chat_id = message.chat.id
        logging.info('Got unknown text \'{0}\' from user {1}'.format(text, sender_id))
        bot.send_message(chat_id, 'Понял')    

    bot.enable_save_next_step_handlers(delay=2)
    bot.load_next_step_handlers()
    bot.polling()

if __name__ == "__main__":
    main()