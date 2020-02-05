import re

import constants
import task_manager

import telebot
from telebot import types

import sys, os, logging, shutil, time

send_sorry = '--sorry' in sys.argv

if '-n' in sys.argv or '--no' in sys.argv: #overwrite previous logs
    pass
elif '-y' in sys.argv or '--yes' in sys.argv:
    if os.path.exists(constants.logs):
        shutil.copy(constants.logs, constants.logs)
elif os.path.exists(constants.logs) and not '--disable-logging' in sys.argv:
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
    task_manager.load_schedules()
    task_manager.load_urgent()
    task_manager.load_routine()

    get_sender_id = lambda msg: msg.from_user.id
    get_chat_id = lambda msg: msg.chat.id
    get_basic_info = lambda msg: (get_sender_id(msg), get_chat_id(msg))

    def listener(messages):
        for m in messages:
            logging.info('Got message {0} from user {1}'.format(m.text, get_sender_id(m)))

    bot = telebot.TeleBot(constants.bot_token)
    bot.set_update_listener(listener)

    def remove_callback_query_handler(func):
        for handler in bot.callback_query_handlers:
            if handler['function'] == func:
                del handler
                break

    def urgent_bot_callback(uid, cid):
        if task_manager.has_urgent(uid):
            urgent = task_manager.show_urgent(uid)
            bot.send_message(cid, urgent, disable_web_page_preview=True)
    
    '''
    @bot.message_handler(commands=['abort'])
    def abort(message):
        bot.reply_to(message, 'Aborting...')
        os._exit(0)
    '''

    @bot.message_handler(commands=['ping'])
    def pong(message):
        bot.reply_to(message, 'pong')

    @bot.message_handler(commands=['show_tasks'])
    def show_tasks(message):
        uid, cid = get_basic_info(message)

        logging.info('Showing all tasks to user {0}'.format(uid))

        sender_id = get_sender_id(message)
        if task_manager.has_tasks(sender_id):
            text = task_manager.show_tasks(sender_id) #nice string with all tasks
            
            bot.send_message(cid, text, disable_web_page_preview=True) #if one of the tasks contains a link 
        else:
            bot.send_message(cid, 'Ура, все задачи выполнены! Можно отдыхать :)')

    @bot.message_handler(commands=['add_task'])
    def add_task(message):
        uid, cid = get_basic_info(message)
        logging.info('Trying to add task for user {0}'.format(uid))

        force_reply = types.ForceReply(selective=False)
        msg = bot.send_message(cid, 'Введи название задачи', reply_markup=force_reply)
        def process_task_name(task_msg):
            task_text = task_msg.text
            task_manager.add_task(get_sender_id(task_msg), task_text)
            logging.info('Added task \'{0}\' to user {1}'.format(task_text, get_sender_id(task_msg)))
            bot.send_message(get_chat_id(task_msg), 'Задача \'{0}\' добавлена успешно!'.format(task_text), disable_web_page_preview=True)

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
            bot.send_message(cid, 'Задача \'{0}\' успешно удалена!'.format(task_name), disable_web_page_preview=True)

            new_tasks = task_manager.get_tasks(uid)
            if tasks != new_tasks:
                new_markup = types.InlineKeyboardMarkup(row_width=3)
                btns = [types.InlineKeyboardButton(task, callback_data=str(idx)) for idx, task in enumerate(new_tasks)]
                new_markup.add(*btns)
                bot.edit_message_reply_markup(chat_id=cid, message_id=keyboard_message.message_id, reply_markup = new_markup)
                tasks = list(new_tasks)

    @bot.message_handler(commands=['add_schedule'])
    def add_schedule(message):
        from task import ScheduleTypes

        uid, cid = get_basic_info(message)

        force_reply = types.ForceReply(selective=False)
        data = {'name': None, 'type': None, 'time': None, 'value': None}
        type_convert = {
            'Ежедневно': ScheduleTypes.DAILY,
            #'Каждые х дней': ScheduleTypes.XDAYS,
            'Еженедельно': ScheduleTypes.WEEKLY
        }
        def process_task_time(time_msg):
            time_text = time_msg.text
            if len(time_text) > 4:
                time_text = time_text[:4]

            pattern = re.compile('\d{1,2}:\d\d')
            if not pattern.match(time_text):
                bot.reply_to(time_msg, 'Введи время в формате HH:MM')

                #Send time select once again
                temp_msg = bot.send_message(get_chat_id(time_msg), 'В какое время напоминать о задаче? (В формате HH:MM)', reply_markup=force_reply)
                bot.register_next_step_handler(temp_msg, process_task_time)
                return
            
            #Avoid invalid time formats with things like '5:30'
            if len(time_text) == 3:
                time_text = '0' + time_text

            data['time'] = time_text
            def callback(task):
                bot.send_message(task.owner_id, 'Напоминаю о задача: {0}'.format(task.name))

            task_manager.add_schedule(uid, data['name'], data['type'], data['time'], callback)
            bot.send_message(uid, 'Задача {0} успешно добавлена!'.format(data['name']))

        def process_task_type(type_msg):
            type_text = type_msg.text
            if type_text not in type_convert:
                bot.reply_to(type_msg, 'Нажми на одну из кнопок для выбора')

                #Send type select once again
                type_select = types.ReplyKeyboardMarkup(one_time_keyboard=True)
                type_select.add(*list(type_convert.keys()))
                temp_msg = bot.send_message(get_chat_id(type_msg), 'Как часто напоминать о задаче?', reply_markup=type_select)
                bot.register_next_step_handler(temp_msg, process_task_type)   

                return

            data['type'] = type_convert[type_text]
            temp_msg = bot.send_message(get_chat_id(type_msg), 'В какое время напоминать о задаче? (В формате HH:MM)', reply_markup=force_reply)
            bot.register_next_step_handler(temp_msg, process_task_time)


        def process_task_name(task_msg):
            task_text = task_msg.text
            data['name'] = task_text
            type_select = types.ReplyKeyboardMarkup(one_time_keyboard=True)
            type_select.add(*list(type_convert.keys()))
            name_msg = bot.send_message(get_chat_id(task_msg), 'Как часто напоминать о задаче?', reply_markup=type_select)
            bot.register_next_step_handler(name_msg, process_task_type)

        first_msg = bot.send_message(cid, 'Введите название задачи', reply_markup=force_reply)
        bot.register_next_step_handler(first_msg, process_task_name)

    @bot.message_handler(commands=['show_schedules'])
    def show_schedules(message):
        pass

    @bot.message_handler(commands=['remove_schedule'])
    def remove_schedule(message):
        pass

    @bot.message_handler(commands=['configure_urgent'])
    def configure_urgent(message):
        uid, cid = get_basic_info(message)
        
        bot.send_message(cid, 'Сейчас я помогу тебе настроить список срочных дел...')
        time.sleep(1)
        force_reply = types.ForceReply(selective=False)
        def process_time(time_msg):
            time_text = time_msg.text
            pattern = re.compile('\d{1,2}:\d\d')
            if not pattern.match(time_text):
                temp_msg = bot.send_message(cid, 'Ты отправил время в неправильном формате. Пожалуйста, отправь время в формате HH:MM', reply_markup=force_reply)

                bot.register_next_step_handler(temp_msg, process_time)
                return

            if len(time_text) == 3:
                time_text = '0' + time_text
            
            bot.send_message(cid, 'Отлично. Теперь я смогу чаще напоминать тебе о срочных делах')
            task_manager.reconfigure_urgent(uid, cid, time_text, urgent_bot_callback)

        msg = bot.send_message(cid, 
          'Отправь мне время в формате HH:MM. Я буду напоминать тебе о твоих срочных задачах каждые HH часов MM минут!',
          reply_markup=force_reply)
        bot.register_next_step_handler(msg, process_time)

    @bot.message_handler(commands=['add_urgent'])    
    def add_urgent(message):
        uid, cid = get_basic_info(message)
        
        force_reply = types.ForceReply(selective=False)
        def process_task_name(task_msg):
            task_text = task_msg.text
            task_manager.add_urgent(get_sender_id(task_msg), task_text)
            bot.send_message(get_chat_id(task_msg), 'Задача \'{0}\' успешно добавлена в срочный список!'.format(task_text), disable_web_page_preview=True)

        msg = bot.send_message(cid, 'Введи название задачи', reply_markup=force_reply)
        bot.register_next_step_handler(msg, process_task_name)

    @bot.message_handler(commands=['remove_urgent'])
    def remove_urgent(message):
        uid, cid = get_basic_info(message)

        if not task_manager.has_urgent(uid):
            bot.send_message(cid, 'Срочный список пуст. Удалять нечего')
            return 

        tasks = task_manager.get_urgent(uid)

        markup = types.InlineKeyboardMarkup(row_width=3)
        btns = [types.InlineKeyboardButton(task, callback_data=str(idx)) for idx, task in enumerate(tasks)]
        markup.add(*btns)

        keyboard_message = bot.send_message(cid, 'Что удалить?', reply_markup=markup)

        @bot.callback_query_handler(func=lambda call: True)
        def remove(call):
            if not task_manager.has_urgent(uid):
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

            task_manager.remove_urgent(uid, task_name)
            bot.send_message(cid, 'Задача \'{0}\' успешно удалена из срочного списка!'.format(task_name), disable_web_page_preview=True)

            new_tasks = task_manager.get_urgent(uid)
            if tasks != new_tasks:
                new_markup = types.InlineKeyboardMarkup(row_width=3)
                btns = [types.InlineKeyboardButton(task, callback_data=str(idx)) for idx, task in enumerate(new_tasks)]
                new_markup.add(*btns)
                bot.edit_message_reply_markup(chat_id=cid, message_id=keyboard_message.message_id, reply_markup = new_markup)
                tasks = list(new_tasks)

    @bot.message_handler(commands=['show_urgent'])
    def show_urgent(message):
        uid, cid = get_basic_info(message)

        urgent_bot_callback(uid, cid)

    @bot.message_handler(commands=['routine'])
    def show_routine_menu(message):
        bot.callback_query_handlers.clear() #remove all previous callback query handlers so they don't interfere with new ones here

        uid, cid = get_basic_info(message)

        markup = types.InlineKeyboardMarkup(row_width=1)
        btns = []
        btns.append(types.InlineKeyboardButton('Создать новую', callback_data='add'))
        btns.append(types.InlineKeyboardButton('Показать все', callback_data='show'))
        markup.add(*btns)

        bot.send_message(cid, 'Настройки рутинных задач', reply_markup=markup)

        @bot.callback_query_handler(func = lambda call: call.data == 'add')
        def add_routine(main_call):
            from task import ScheduleTypes

            force_reply = types.ForceReply(selective=False)
            type_convert = {
                'Понедельник': ScheduleTypes.MONDAY,
                'Вторник': ScheduleTypes.TUESDAY,
                'Среда': ScheduleTypes.WEDNESDAY,
                'Четверг': ScheduleTypes.THURSDAY,
                'Пятница': ScheduleTypes.FRIDAY,
                'Суббота': ScheduleTypes.SATURDAY,
                'Воскресенье': ScheduleTypes.SUNDAY,
            }

            def process_task_name(task_msg):
                task_text = task_msg.text
                type_select = types.InlineKeyboardMarkup(row_width=2)
                keys = list(type_convert.keys()) + ['Конец']
                type_select.add(*(types.InlineKeyboardButton(x, callback_data=x) for x in keys))
                days_msg = bot.send_message(cid, 'В какие дни рутину нужно выполнять? (Нажми на кнопки нужных дней, затем нажми \'Конец\', чтобы закончить ввод дней)', reply_markup=type_select)
                schedule_days = []

                @bot.callback_query_handler(func = lambda call : True)
                def add_day(call):
                    if call.data == 'Конец':
                        task_manager.add_routine(uid, task_text, schedule_days)
                        bot.send_message(cid, 'Рутина \'{0}\' добавлена успешно'.format(task_text))
                        bot.edit_message_reply_markup(cid, days_msg.message_id, reply_markup=None)

                        remove_callback_query_handler(add_day) #remove this handler because it has reads any call
                        return

                    schedule_days.append(type_convert[call.data])
                    #format callback data 
                    s = list(call.data)
                    if s[-1] == 'а':
                        s[-1] = 'у'
                    s = ''.join(s)
                    bot.send_message(cid, 'Теперь я буду напоминать о рутине в {0}'.format(s))

                    keys.remove(call.data)
                    type_select = types.InlineKeyboardMarkup(row_width=2)
                    type_select.add(*(types.InlineKeyboardButton(x, callback_data=x) for x in keys))

                    bot.edit_message_reply_markup(cid, days_msg.message_id, reply_markup=type_select)

            first_msg = bot.send_message(cid, 'Введи название рутины', reply_markup=force_reply)
            bot.register_next_step_handler(first_msg, process_task_name)
        
        @bot.callback_query_handler(func = lambda call: call.data == 'show')
        def show_routines(main_call):
            routines = task_manager.get_routines(uid)
            if routines is None:
                bot.send_message(cid, 'Нет рутин.')
                return

            names = [x['name'] for x in routines]

            initial_markup = types.InlineKeyboardMarkup(row_width=2)
            btns = (types.InlineKeyboardButton(name, callback_data=str(names.index(name))) for name in names)
            initial_markup.add(*btns)

            intial_text = 'Твои рутины:'
            initial_msg = bot.send_message(cid, intial_text, reply_markup=initial_markup)
            mid = initial_msg.message_id

            def reset():
                bot.edit_message_text(intial_text, cid, mid)
                bot.edit_message_reply_markup(cid, mid, reply_markup=initial_markup)

            def call_is_int(call):
                try:
                    int(call.data)
                    return True
                except:
                    return False

            @bot.callback_query_handler(func = call_is_int)
            def more_info_routine(call):
                name = names[int(call.data)]
                info_markup = types.InlineKeyboardMarkup(row_width=1)
                #info_markup.add(types.InlineKeyboardButton('Изменить дни', callback_data='change'))
                info_markup.add(types.InlineKeyboardButton('Удалить', callback_data='remove'))

                bot.edit_message_text(name, cid, mid)
                bot.edit_message_reply_markup(cid, mid, reply_markup=info_markup)

                @bot.callback_query_handler(func = lambda call: call.data == 'remove')
                def remove_routine(call):
                    task_manager.remove_routine(uid, name)
                    bot.send_message(cid, 'Рутина \'{0}\' успешно удалена'.format(name))

                    reset()

    #This is like 'default' option in switch statement (handles any message)
    @bot.message_handler(func=lambda msg: True)
    def handle_text(message):
        sender_id = get_sender_id(message)
        text = message.text
        chat_id = message.chat.id
        logging.info('Got unknown text \'{0}\' from user {1}'.format(text, sender_id))
        bot.send_message(chat_id, 'Понял')    

    bot.enable_save_next_step_handlers(delay=2)
    bot.load_next_step_handlers()

    from threading import Thread
    def run():
        bot.infinity_polling(True)
    polling_thread = Thread(target=run)
    polling_thread.setDaemon(False)
    polling_thread.start()   
    print('Start polling...')

    import schedule
    while True:
        if not polling_thread.is_alive():
            break
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
