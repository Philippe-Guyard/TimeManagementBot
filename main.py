from constants import bot_token
import task_manager

import telebot
from telebot import types

bot = telebot.TeleBot(bot_token)

get_sender_id = lambda msg: msg.from_user.id

def remove_markup(message, txt='Хорошо!'):
    markup = types.ReplyKeyboardRemove(selective=False)
    bot.send_message(message.chat.id, text=txt, reply_markup=markup)

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, 'Привет!')

@bot.message_handler(commands=['tasks'])
def show_task_params(message):
    markup = types.ReplyKeyboardMarkup(row_width=2)
    itembtn1 = types.KeyboardButton('Показать задачи на сегодня')
    itembtn2 = types.KeyboardButton('Добавить задачу')
    markup.add(itembtn1, itembtn2)
    bot.send_message(message.chat.id, 'Что нужно сделать?', reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == 'Добавить задачу')
def add_task(message):
    #remove markup from task params
    remove_markup(message)

    #start registering the task
    task_manager.start_add_task(get_sender_id(message))   
    bot.send_message(message.chat.id, 'Введи название задачи')

@bot.message_handler(func=lambda msg: msg.text == 'Показать задачи на сегодня')
def show_tasks(message):
    #remove markup from task params
    remove_markup(message)

    sender_id = get_sender_id(message)
    if sender_id in task_manager.tasks:
        nice_task_string = 'Твои задачи:\n'
        for item in task_manager.tasks[sender_id]:
            nice_task_string += '-{0}\n'.format(item)
        
        bot.send_message(message.chat.id, nice_task_string)
    else:
        bot.send_message(message.chat.id, 'Ура, все задачи выполнены! Можно отдыхать :)')
    

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