#!/bin/python3
import discord
import asyncio
import signal
import sys, traceback
#import os.path



############# Initializations ############# 
print ('Initializing stuff')
helpmessage = "Here are some of the things you do with mycroft:\n" + \
              "1: Say hello to mycroft using 'hello mycroft'\n" + \
              "https://github.com/SeanConn15/Mycroft-discord"


# setting debug flag
debug = False
if len(sys.argv) > 1:
    if sys.argv[1] == "d":
        debug = True



# debug function
# if not debug_needed, prints string
# otherwise prints string iff debug is set
def dprint(str):
    if(debug):
        print (str)


# users have a discord name, a perferred name, and a privilege level
# privilege level
# 0: do all the things
# 1: do none of the things

users = []


# set to True if an unhandled intrrupt signal is recieved
interruptRecieved = False

############ Client Definiton ############
# this is done to add a check for sigints and for local terminal input
class MycroftClient(discord.Client):
    def __init__(self, *args, **kwargs):

        # do whatever discord.Client does 
        super().__init__(*args, **kwargs)

        # adding additional functions
        self.bg_task = self.loop.create_task(self.interrupt_signal())

    # if an interrupt was triggered, disconnect
    async def interrupt_signal(self):
        global interruptRecieved 
        while True:
            if (interruptRecieved):
                 interruptRecieved = False
                 print ("Interrupt Recieved: disconnecting...")
                 await client.close()
                 print ("disconnected.")
            await asyncio.sleep(10)



client = MycroftClient();

############# Local Input        #############

def disconnect():
    dprint ("SIGINT Recieved, setting variable")
    global interruptRecieved 
    interruptRecieved = True


############# Asynchronus Events ############# 
@client.event
async def on_ready():
    print ("Connection established.")
    dprint ("Authenicated as {}".format(client.user.name))

    # register the CTRL+C signal handler to stop the bot, sets a variable in disconnect() that
    # an asnchronous event checks
    client.loop.add_signal_handler(signal.SIGINT, disconnect)


## On message recieved

@client.event
async def on_message(m):
    dprint ("\n--Message Recieved--", 3)
    ###definitions

    # a list of the words in the message
    content = m.content.lower().split(' ')




############# Startup ############# 


# Current fields:
# <user id> <permission level> 

# reading from startup files
print ('Reading files for information on things')
# getting the token from the .secrets file
tfile = open('secrets', 'r+', 1)
token = tfile.readline();  
token = token[:-1] # get rid of the newline
tfile.close();

# creating users file if needed
# if not os.path.exists('users'):
#     admins = open('users', 'w+')
# else:
#     admins = open('users', 'r')
# 
# # generating users list
# for line in admins:
#     line = line[:-1] # removing newline
#     print (line)
#     object = line.split(':') #splitting fields 
#     object[1] = int(object[1])
#     print (object, 3)
#     users.append(object)
# admins.close();

# connecting to discord
print('Making connections')
client.run(token)

