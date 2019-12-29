import constants
import json

tasks = dict()

def load_tasks():
    global tasks
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