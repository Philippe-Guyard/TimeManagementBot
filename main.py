from constants import bot_token
import task_manager

import telebot
from telebot import types

task_manager.load_tasks()

bot = telebot.TeleBot(bot_token)

get_sender_id = lambda msg: msg.from_user.id
get_chat_id = lambda msg: msg.chat.id

def remove_markup(message, txt='Хорошо!'):
    markup = types.ReplyKeyboardRemove(selective=False)
    bot.send_message(message.chat.id, text=txt, reply_markup=markup)

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, 'Привет!')

@bot.message_handler(commands=['tasks'])
def show_task_params(message):
    cid = get_chat_id(message)
    uid = get_sender_id(message)

    markup = types.InlineKeyboardMarkup(row_width=3)
    itembtn1 = types.InlineKeyboardButton('Показать задачи на сегодня', callback_data='show')
    itembtn2 = types.InlineKeyboardButton('Добавить задачу', callback_data='add')
    itembtn3 = types.InlineKeyboardButton('Удалить задачу', callback_data='remove')
    markup.add(itembtn1, itembtn2, itembtn3)
    bot.send_message(cid, 'Что нужно сделать?', reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == 'add')
    def add_task(call):
        #start registering the task
        task_manager.start_add_task(get_sender_id(message))   
        bot.send_message(cid, 'Введи название задачи')

    @bot.callback_query_handler(func=lambda call: call.data == 'show')
    def show_tasks(call):
        sender_id = get_sender_id(message)
        if task_manager.has_tasks(sender_id):
            text = task_manager.show_tasks(sender_id) #nice string with all tasks
            
            bot.send_message(cid, text)
        else:
            bot.send_message(cid, 'Ура, все задачи выполнены! Можно отдыхать :)')

    @bot.callback_query_handler(func=lambda call: call.data == 'remove')
    def remove_task(call):
        if not task_manager.has_tasks(uid):
            bot.send_message(cid, 'Все задачи выполнены. Удалять нечего')
            return 

        tasks = task_manager.get_tasks(get_sender_id(message))

        markup = types.InlineKeyboardMarkup(row_width=3)
        btns = [types.InlineKeyboardButton(task, callback_data=task) for task in tasks]
        markup.add(*btns)

        bot.send_message(cid, 'Что удалить?', btns, reply_markup=markup)

        @bot.callback_query_handler(func=lambda call: True)
        def remove(call):
            print(call.data)
            task_manager.remove_task(uid, call.data)
            bot.send_message(cid, 'Задача \'{0}\' успешно удалена!'.format(call.data))

#This should always be last decorator as this is like 'default' option in switch statement (handles any message)
@bot.message_handler(func=lambda msg: True)
def handle_text(message):
    sender_id = get_sender_id(message)
    text = message.text
    chat_id = message.chat.id
    if task_manager.is_add_task(sender_id):
        #notify user
        task_manager.finish_add_tast(sender_id, text)
        bot.send_message(chat_id, 'Задача \'{0}\' добавлена успешно!'.format(text))
    else:
        bot.send_message(chat_id, 'Понял')    


bot.polling()