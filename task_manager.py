mode = dict()
tasks = dict()

def is_add_task(user_id):
    return user_id in mode and mode[user_id] == 'ADD_TASK'

def start_add_task(user_id):
    mode[user_id] = 'ADD_TASK'

def finish_add_tast(user_id, task_name):
    mode[user_id] = 'DEFAULT'
    if user_id in tasks:
        tasks[user_id].append(task_name)
    else:
        tasks[user_id] = [task_name]