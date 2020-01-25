import constants
import json, os

import pickle

tasks = dict()
schedules = dict()

def load_tasks():
    global tasks
    if not os.path.exists(constants.json_storage):
        open(constants.json_storage, 'w').close() #create the file in case it doesn't exist 

    with open(constants.json_storage, 'r') as f:
        s = f.readline()
        if s is not None and len(s) > 0:
            tasks = json.loads(s)
    
    #convert all user id's to int
    tasks = {int(key):value for key, value in tasks.items()}

def save_tasks():
    global tasks
    with open(constants.json_storage, 'w') as f:
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

#returns all user tasks inside list
def get_tasks(user_id):
    return list(tasks[user_id])

def show_tasks(user_id):
    nice_task_string = 'Твои задачи:\n'
    for item in tasks[user_id]:
        nice_task_string += '-{0}\n'.format(item)

    return nice_task_string

import task

def save_schedules():
    with open(constants.pickle_storage, 'wb') as f:
        pickle.dump(schedules, f)

def load_schedules():
    if not os.path.exists(constants.pickle_storage):
        open(constants.pickle_storage, 'w').close()
    
    global schedules
    with open(constants.pickle_storage, 'rb') as f:
        schedules = pickle.load(f)

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
