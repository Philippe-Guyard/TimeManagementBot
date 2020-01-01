#This script will be used in case a 500 server error or something dumb like that occurs 

from subprocess import Popen
import sys, time

filename = sys.argv[1]
args = []
if len(sys.argv) > 1:
    args = sys.argv[2:]
args = ' '.join(args)
python_args = 'python ' + filename
if len(args) > 0:
    python_args += ' ' + args

prc = Popen(python_args, shell=True)
prc.wait() #First exception. We want to save this log

python_args = 'python {0} --disable-logging --sorry' #we don't want the logs of all programs. Also notify me about crash
retry = 0
while True:
    start = time.time()
    prc = Popen(python_args, shell=True)
    prc.wait()
    end = time.time()

    if end - start < 10: #program worked for less than 10 seconds. 
        #Exception is probably thrown before anything could be sent to the bot
        #retry multiple times and if the same thing happens in a row than abort
        #not to override the system
        retry += 1
        if retry > 3:
            break
    else:
        retry = 0
    