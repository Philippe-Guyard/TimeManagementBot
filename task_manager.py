import constants
import json, os

import pickle

'''
########################################################################################
From here only working with tasks
########################################################################################
'''

tasks = dict()

def load_tasks():
    global tasks
    if not os.path.exists(constants.task_storage):
        open(constants.task_storage, 'w').close() #create the file in case it doesn't exist 

    with open(constants.task_storage, 'r') as f:
        s = f.readline()
        if s is not None and len(s) > 0:
            tasks = json.loads(s)
    
    #convert all user id's to int
    tasks = {int(key):value for key, value in tasks.items()}

def save_tasks():
    global tasks
    with open(constants.task_storage, 'w') as f:
        f.write(json.dumps(tasks))

def has_tasks(user_id):
    return user_id in tasks and len(tasks[user_id]) > 0

def add_task(user_id, task_name):
    if user_id in tasks:
        tasks[user_id].append(task_name)
    else:
        tasks[user_id] = [task_name]
    
    save_tasks()

def remove_task(user_id, task_name):
    if user_id in tasks:
        if task_name in tasks[user_id]:
            tasks[user_id].remove(task_name)
        else:
            return False 
    else:
        return False
    
    save_tasks()
    return True

#returns all user tasks inside list
def get_tasks(user_id):
    return list(tasks[user_id])

def show_tasks(user_id):
    nice_task_string = 'Твои задачи:\n'
    for item in tasks[user_id]:
        nice_task_string += '-{0}\n'.format(item)

    return nice_task_string


'''
########################################################################################
From here only working with schedules
########################################################################################
'''
import task

schedules = dict()

def save_schedules():
    with open(constants.schedule_storage, 'wb') as f:
        pickle.dump(schedules, f)

def load_schedules():
    if not os.path.exists(constants.schedule_storage):
        open(constants.schedule_storage, 'w').close()
    
    global schedules
    try:
        with open(constants.schedule_storage, 'rb') as f:
            schedules = pickle.load(f)
    except:
        schedules = dict()


def add_schedule(user_id, name, stype, ttime, callback, value=None):
    schedule = task.Schedule(stype, ttime, value)
    next_task = task.Task(user_id, name, schedule)
    next_task.start(callback)

    if user_id in schedules:
        schedules[user_id].append(next_task)
    else:
        schedules[user_id] = [next_task]

    save_schedules()

def remove_schedule(user_id, name):
    if user_id not in schedules:
        return False

    old_len = len(schedules[user_id])
    schedules[user_id] = [x for x in schedules[user_id] if x.name != name]
    if old_len == len(schedules[user_id]): #nothing changed
        return False

    save_schedules()
    return True


'''
########################################################################################
From here only working with urgent
########################################################################################
'''
import schedule

urgent = dict()
urgent_task = dict()

def save_urgent():
    with open(constants.urgent_storage, 'wb') as f:
        pickle.dump(urgent, f)

def load_urgent():
    if not os.path.exists(constants.urgent_storage):
        open(constants.urgent_storage, 'w').close()
    
    global urgent
    try:
        with open(constants.urgent_storage, 'rb') as f:
            urgent = pickle.load(f)
    except: #
        urgent = dict()
    
def add_urgent(uid, name):
    if uid in urgent:
        urgent[uid].append(name)
    else:
        urgent[uid] = [name]
    
    save_urgent()

def remove_urgent(uid, name):
    if uid in urgent:
        if name in urgent[uid]:
            urgent[uid].remove(name)
            save_urgent()
            return True
        else:
            return False
    else:
        return False

#new_interval is of format 'hh:mm'
def reconfigure_urgent(uid, cid, new_interval, bot_callback):
    hours, minutes = map(int, new_interval.split(':'))
    total_mins = hours * 60 + minutes

    if uid in urgent_task:
        schedule.cancel_job(urgent_task[uid]) #cancel previous job
    schedule.every(total_mins).minutes.do(bot_callback, uid, cid) #create new job

def get_urgent(user_id):
    if user_id in urgent:
        return urgent[user_id]
    else:
        return []

def has_urgent(user_id):
    return user_id in urgent and len(urgent[user_id]) > 0

def show_urgent(user_id):
    nice_task_string = 'Напоминаю о твоих срочных задачах:\n'
    for item in urgent[user_id]:
        nice_task_string += '-{0}\n'.format(item)

    return nice_task_string

'''
########################################################################################
From here only working with routine
########################################################################################
'''
from task import ScheduleTypes

routines = dict()
routines_convert_back = {
    'Понедельник': ScheduleTypes.MONDAY,
    'Вторник': ScheduleTypes.TUESDAY,
    'Среда': ScheduleTypes.WEDNESDAY,
    'Четверг': ScheduleTypes.THURSDAY,
    'Пятница': ScheduleTypes.FRIDAY,
    'Суббота': ScheduleTypes.SATURDAY,
    'Воскресенье': ScheduleTypes.SUNDAY,
}
routines_convert = dict()
for key, value in routines_convert_back.items():
    routines_convert[value] = key

def save_routines():
    def dump_routines(f_handler):
        new_routines = dict()
        for uid, routines_list in routines.items():
            new_routines[uid] = []
            for routine in routines_list:
                new_days = list()
                for day in routine['days']:
                    new_days.append(routines_convert[day])
                
                new_routines[uid].append({'name': routine['name'], 'days': new_days})

        pickle.dump(new_routines, f_handler)

    with open(constants.routine_storage, 'wb') as f:
        dump_routines(f)

def load_routine():
    if not os.path.exists(constants.routine_storage):
        open(constants.routine_storage, 'w').close()
    
    temp_routines = dict()
    try:
        with open(constants.routine_storage, 'rb') as f:
            temp_routines = pickle.load(f)
    except: #
        temp_routines = dict()
    
    global routines
    for uid, routines_list in temp_routines.items():
            routines[uid] = []
            for routine in routines_list:
                new_days = list()
                for day in routine['days']:
                    new_days.append(routines_convert_back[day])
                
                routines[uid].append({'name': routine['name'], 'days': new_days})


    def callback(owner_id, name):
        add_task(owner_id, name)
    for uid, rtns in routines.items():
        for routine in rtns:
            for day in routine['days']:
                day.value.do(callback, uid, routine['name'])
                

def add_routine(uid, name, days):
    def callback(owner_id, name):
        add_task(owner_id, name)

    #day is already of type schedule.every().monday/tuesday...
    for day in days:
        day.value.do(callback, uid, name)
    
    if uid in routines:
        routines[uid].append({'name': name, 'days': days})
    else:
        routines[uid] = [{'name': name, 'days': days}]
    
    save_routines()

def remove_routine(uid, name):
    if uid in routines:
        routines[uid] = list(filter(lambda x: x['name'] != name, routines[uid]))
        save_routines()
        return True

    return False

def get_routines(uid):
    if uid in routines and len(routines[uid]) > 0:
        return routines[uid]

    return None