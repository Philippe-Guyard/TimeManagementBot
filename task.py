import logging

from enum import Enum
import schedule

class ScheduleTypes(Enum):
    DAILY = 1 #repeat every day
    XDAYS = 2 #repeat every X days
    WEEKLY = 3 #repeat every week

    #Simplify code like this for weekdays 
    MONDAY = schedule.every().monday 
    TUESDAY = schedule.every().tuesday
    WEDNESDAY = schedule.every().wednesday
    THURSDAY = schedule.every().thursday
    FRIDAY = schedule.every().friday
    SATURDAY = schedule.every().saturday
    SUNDAY = schedule.every().sunday

    WEEKDAYS = (MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY)

class Schedule:
    '''
    sch_type - schedule type
    trigger_time - time from which notifications start to come
    value - in case type is XDAYS 
    '''
    def __init__(self, sch_type, trigger_time, value=None):
        self.sch_type = sch_type
        self.trigger_time = trigger_time
        if value is not None:
            assert sch_type == ScheduleTypes.XDAYS, 'Schedule can only have a value attribute if type is XDAYS'
            self.value = value
    
    #callback is called at needed time
    def start(self, callback, source_task): 
        if self.sch_type == ScheduleTypes.DAILY:
            self.job = schedule.every().day.at(self.trigger_time).do(callback, source_task)
        elif self.sch_type == ScheduleTypes.XDAYS:
            self.job = schedule.every(self.value).days.at(self.trigger_time).do(callback, source_task)
        elif self.sch_type == ScheduleTypes.WEEKLY:
            self.job = schedule.every().week.at(self.trigger_time).do(callback, source_task) 
        else:
            logging.info('Unknown schedule type: {0}'.format(self.sch_type))

class Task:
    def __init__(self, user_id, name, task_schedule=None):
        self.owner_id = user_id
        self.name = name
        self.started = False
        if task_schedule is not None:
            self.task_schedule = task_schedule
    
    def start(self, callback=None):
        if self.task_schedule is not None:
            if callback is None:
              logging.error('No callback for scheduled task: {0}'.format(self.name))
              return
            else:
                self.task_schedule.start(callback, self)
        
        self.started = True

    def end(self):
        schedule.cancel_job(self.task_schedule.job)

    #Task as pretty str.
    #Example: 'Do something (! 3 hours and 27 minutes left !)'
    def pretty_str(self):
        pass