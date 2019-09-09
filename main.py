#!/bin/python3
import discord
import asyncio
import signal
import sys, traceback
import subprocess # for executing shell functions
import os
import random
from PIL import Image # for basic image processing


#TODO: @me if there are issues with a command
#TODO: if someone does the cozy reaction post it from the bot
#TODO: list available meme images
#TODO: split things that start with the keyphrase eg m-hello > m- hello
#TODO: make help better, command specific
#TODO: waifu roll command but search google for danny devito images
#TODO: make admin only commands for controlling other things in the server


############# Initializations ############# 
print ('Initializing stuff')
keyword = "m-"
# set during initalization, the admin's unique id
admin = 0
helpmessage = "\nTo talk to mycroft, use \"{} <command> [arguments]\".\n".format(keyword) + \
                "Here are some of the things you do with mycroft:\n" + \
              "hello: have mycroft say hello\n" + \
              "meme <name>: print out image \"name\", if already saved." + \
              "save [name]: save an attached image as a meme, to be accessed by name" + \
              "https://github.com/SeanConn15/Mycroft-discord"


# setting debug flag
# changes what output is printed, and changes
# various things for quick stopping and starting
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
        global debug
        while True:
            if (interruptRecieved):
                 interruptRecieved = False
                 print ("Interrupt Recieved: disconnecting...")
                 await client.close()
                 print ("disconnected.")

            # if on debug mode check every two seconds
            if (debug):
                await asyncio.sleep(2)
            else:
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

    global keyword

    ## Determining if message should be ignored
    
    # ignore things this bot sends
    if client.user == m.author:
        return

    if (m.channel.type == discord.ChannelType.private):
        dprint ("\n--DM Recieved--")
    else:
        dprint ("\n--Message Recieved--")


    # a list of the words in the message
    content = m.content.lower().split(' ')
    dprint ("Recieved: [{}]".format(m.content.lower()))

   

    # ignore things that don't start with the keyword,
    # except if in a DM.
    if (content[0] != keyword and m.channel.type != discord.ChannelType.private):
        return


    ## Parsing command


    # if the command is invoked with a keyword, remove it
    # this is so commands can be parsed the same even if they are in DM's
    if (content[0] == keyword):
        del content[0]


    if (content[0] == "help"):
       await m.author.send(helpmessage)
    elif (content[0] == "test"):
        if (random.randint(0,2) == 1):
            await m.channel.send("boop")
        else:
            await m.channel.send("beep")
    elif (content[0] == "hello"):
       await m.channel.send("Hello, {}.".format(m.author.name))
    elif (content[0] == "bruce"):
        f = discord.File(fp="memes/first.jpg", filename="test.jpg")
        await m.channel.send(content=None, file=f)
    elif (content[0] == "meme"):
        await getMeme(m, content)     
    elif (content[0] == "save"):
        await saveMeme(m, content)     
    elif (content[0] == "list"):
        await printMemes(m)


    # super secret admin commands
    if (m.author.id == admin):
        if (content[0] == "ip"):
            response = subprocess.run("dig @resolver1.opendns.com ANY myip.opendns.com +short", shell=True, stdout=subprocess.PIPE, encoding="utf-8")

            await m.channel.send("The IP of the server is: {}".format(response.stdout))

########## misc functions #########

# only use png for files

async def getMeme(message, content):

    if (len(content) < 2):
        await message.channel.send("yea but what meme")
        return
    ## get filename
    # first word is meme
    del content[0]
    # concatinate everything with underscores in between
    filename = ""
    for s in content:
        filename += s + '_'
    # remove last underscore and add filetype
    filename = filename[:-1]
    filename += ".png"
    ## try to find the file
    df = ""
    try:
        df = discord.File(fp="memes/" + filename,filename=filename)
    except IOError:
        dprint("Tried to open file: memes/{}, failed.".format(filename))
        await message.channel.send("I couldn't find that image.")
        return

    ##post the file
    await message.channel.send(content=None, file=df)

async def saveMeme(message, content):
    ## validate attachment
    if (len(content) < 2):
        await message.channel.send("yea but what name")
        return

    # if there is no file attached
    if not message.attachments:
        await message.channel.send("You didn't attach an image")
        return

    ## get filename
    # first word is meme
    del content[0]
    # concatinate everything with underscores in between
    filename = ""
    for s in content:
        filename += s + '_'
    # remove last underscore and add filetype
    filename = filename[:-1]
    filename += ".png"

    ## validate filename
    
    # if the file already exists tell them to try another filename
    # TODO: dont make them reupload the image
    if (os.path.isfile("memes/" + filename)):
        await message.channel.send("That name is already in use, try another")
        return

    #if it is not a png file, convert then save it
    if message.attachments[0].filename[-4:] != ".png":
        # temporarily save it
        await message.attachments[0].save("memes/TEMP-" + filename)
        try:
            im = Image.open("memes/TEMP-" + filename)
        except IOError:
            print ("image failed to save: memes/TEMP-" + filename)
            await message.channel.send("it didnt work, image failed to save")
            return
        # convert it and save it
        rgb_im = im.convert("RGB")
        rgb_im.save("memes/" + filename)
        # remove the temporary file
        os.remove("memes/TEMP-" + filename)

    #otherwise just save it
    else:
    ## save meme
        await message.attachments[0].save("memes/" + filename)

    if (os.path.isfile("memes/" + filename)):
        await message.channel.send("fuckkin saved")
    else:
        await message.channel.send("it didnt work")
    ## say you saved it
    #TODO: react with fuckkin saved if that emote exists


async def printMemes(message):
    response = "Here's all my memes:\n"
    for filename in os.listdir("memes/"):
        for word in filename.split("_"):
            if (word[-4:] == ".png"):
                response += word[:-4] + " "
            else:
             response += word + " "
        response += "\n"
    await message.channel.send(response)

############# Startup ############# 



# reading from startup files
print ('Reading files for information on things')
# getting the token from the .secrets file
tfile = open('secrets', 'r+', 1)
token = tfile.readline();  
token = token[:-1] # get rid of the newline
admin = tfile.readline();
admin = int(admin[:-1])
tfile.close();

# connecting to discord
print('Making connections')
client.run(token)

