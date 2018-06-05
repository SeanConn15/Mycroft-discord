import discord
import asyncio
import signal
import sys, traceback
import os.path



############# Initializations ############# 
print ('Initializing stuff')
helpmessage = "Here are some of the things you do with mycroft:\n" + \
              "1: Say hello to mycroft using 'hello mycroft'\n" + \
              "https://github.com/SeanConn15/Mycroft-discord"

if len(sys.argv) != 2:
    print ('Usage: python main.py <verbosity>')
    sys.exit(0)


verbosity = int(sys.argv[1]); # the verbosity of the ouputs:
#if you have a verbosity of 3 you see levels 1, 2, and 3 for example 

# 1: essential stuff
#   startup
#   connections
#   errors

# 2: 
#   smaller stages
#   sent messages
#   recieved commands

# 3:
#   recieved messages
#   lines read from file

# debug function
def printline(str, level = 3):
    if(verbosity >= level):
        print (str)

def printstr(str, level = 3):
    if(verbosity >= level):
        sys.stdout.write(str)

# users have a discord name, a perferred name, and a privilege level
# privilege level
# 0: do all the things
# 1: do none of the things

users = []

client = discord.Client();



############# Asynchronus Events ############# 
@client.event
async def on_ready():
    printline ("Connection established.", 1)
    printline ("Authenicated as " + client.user.name + '.', 2)


## On message recieved
@client.event
async def on_message(m):
    printline ("\n--Message Recieved--", 3)
    ###definitions

    # a list of the words in the message
    content = m.content.lower().split(' ')
   
    if (m.server.id == None):
        printstr ("Server: DM", 3)
    else:
        printline ("Server: "  + m.server.name, 3)


    ### Author related stuff
    printline ("Author: " + m.author.name, 3)
    printline ("Text: " +  m.content, 3)

    ## mycroft cannot talk to himself
    if client.user == m.author:
        return

    ## you do not have to say mycroft in direct messages
    if content[0] != 'mycroft' and m.server == None:
        content.insert(0, 'mycroft');
    elif m.server == None:
        await client.send_message(m.channel, 'Some advice, if you are messaging me directly I know you are talking to me. No need to address me every time.')

    # ignore every message not starting with mycroft
    if content[0] == 'mycroft':


        # command related code
        printline('Command detected', 2);
        printline(content, 3);

        permissions = 100
        # find person in database
        found = False
        for user in users:
            if user[0] == m.author.id:
                found = True
                permissions = user[1]

        # add to database if not there
        if not found:
            newguy = [m.author.id, 100]
            name = m.author
            users.append(newguy)
            with open("users", "a") as f:
                f.write(m.author.id + ':100\n');

        

        # evaluate the message

        #default message
        if len(content) == 1:
            await client.send_message(m.channel, 'What do you require?')

        #DM only things
        if (m.server == None and content[1] != 'help' and content[1] != 'hello'):
            await client.send_message(m.channel, 'As of this moment, direct messages are only for the help screen and saying hi.')

        # regular commands
        elif 'hello' in content[1]: 
            await client.send_message(m.channel, 'Hello, ' + m.author.display_name + '.')
        elif content[1] == 'help':
            await client.send_message(m.author, helpmessage)



############# Startup ############# 


# Current fields:
# <user id> <permission level> 

# reading from startup files
printline ('Reading files for information on things', 1)
# getting the token from the .secrets file
tfile = open('secrets', 'r+', 1)
token = tfile.read(59); # 59 because the token is 60 characters long and 60 didn't work
tfile.close();

# creating users file if needed
if not os.path.exists('users'):
    admins = open('users', 'w+')
else:
    admins = open('users', 'r')

# generating users list
for line in admins:
    line = line[:-1] # removing newline
    object = line.split(':') #splitting fields 
    object[1] = int(object[1])
    printline (object, 3)
    users.append(object)
admins.close();

# connecting to discord
print('Making connections')
client.run(token)

