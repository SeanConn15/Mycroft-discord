#!/bin/python3
import discord
import asyncio
import signal
import sys, traceback
import subprocess # for executing shell functions
import time
import os
import random
from musicplayer import MusicPlayer
from PIL import Image # for basic image processing

# for web scraping
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
import urllib.parse
#TODO: @me if there are issues with a command
#TODO: if someone does the cozy reaction post it from the bot
#TODO: make help better, command specific
#TODO: improve waifu command, ownership etc
#TODO: make admin only commands for controlling other things in the server

#TODO: make dprint append to a file, for debugging (add time and stuff)
#TODO: compute how long commands take
#TODO: better logging using module



############# Initializations ############# 
print ('Initializing stuff')
keyword = "m-"
# set during initalization, the admin's unique id
admin = 0
_helpmessage = ["",
                "To talk to mycroft, use `{} <command> [arguments]`.\n".format(keyword) + \
                "Here are some of the things you do with mycroft:", 
                "```",
                "Music:", 
                "  add [youtube url]: add a song to the queue",
                "  play: start playing the queue",
                "  disconnect: leave voice, stop playing music",
                "  queue: print out the music queue",
                "  playnow [youtube url]: stop whatever is playing and play this",
                "  clear: clear the music queue", 
                "  remove [index]: remove song at [index] from queue", 
                "```",
                "```",
                "Misc:", 
                "  hello: have mycroft say hello", 
                "  meme <name>: print out image \"name\", if already saved.", 
                "  save [name]: save an attached image as a meme, to be accessed by name", 
                "  list:        list available meme names", 
                "```",
                "https://github.com/SeanConn15/Mycroft-discord"]

helpmessage = ""
for line in _helpmessage:
    helpmessage += line + '\n'

# setting debug flag
# changes what output is printed, and changes
# various things for quick stopping and starting
debug = True
if len(sys.argv) > 1:
    if sys.argv[1] == "d":
        debug = True



# debug function
# if not debug_needed, prints string
# otherwise prints string iff debug is set
def dprint(str):
    if(debug):
        print (str)


## global variables
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
                 global browser
                 interruptRecieved = False
                 print ("Interrupt Recieved: disconnecting...")
                 #if using a musicbot, disconnect it
                 if mp is not None:
                     await mp.stop()
                 await client.change_presence(status=discord.Status.offline) 
                 await client.close()
                 print ("disconnected.")
                 #also stop the web browser
                 if browser is not None:
                     browser.close()


            # if on debug mode check every second
            if (debug):
                await asyncio.sleep(1)
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

    ## TODO: remove after testing
    if (m.author.id != admin):
        dprint("not admin")
        return

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
    content = m.content.split(' ')

    #split messages that start with the prefix with no space
    if (len(content[0]) > len(keyword) and content[0][:len(keyword)] == keyword):
        #insert the two parts of the message
        content.insert(0, keyword);
        content.insert(1, content[1][len(keyword):])
        #remove the old first word
        content.remove(content[2])

    dprint ("Recieved: [{}]".format(m.content))

   

    # ignore things that don't start with the keyword,
    # except if in a DM.
    if (content[0] != keyword and m.channel.type != discord.ChannelType.private):
        return

    # the keyword is not case sensitive
    content[0] = content[0].lower()

    # now content is [command, args, ...]

    ## Parsing command


    # if the command is invoked with a keyword, remove it
    # this is so commands can be parsed the same even if they are in DM's
    if (content[0] == keyword):
        del content[0]


    if (content[0] == "help"):
       await m.channel.send(helpmessage)
    elif (content[0] == "test"):
        if (random.randint(0,1) == 1):
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
    elif (content[0] == "waifu"):
        await getWaifu(m)
    elif (content[0] == "add"):
        if len(content) < 2:
            await mp.add("https://www.youtube.com/watch?v=CsGYh8AacgY", m.channel)
            return
        await mp.add(content[1], m.channel)
    elif (content[0] == "playnow"):
        if len(content) < 2:
            await m.channel.send("playnow needs a song to play")
            return
        await mp.playnow(content[1], m.channel)
    elif (content[0] == "play"):
        if m.author.voice:
            vc = m.author.voice.channel
        else:
            vc = None
        await mp.play(vc, m.channel)
    elif (content[0] == "pause"):
        await mp.pause(m.channel)
    elif(content[0] == "queue"):
        await mp.getQueue(m.channel)
    elif (content[0] == "volume"):
        await mp.setVolume(content[1], m.channel)
    elif (content[0] == "clear"):
        await mp.clear(m.channel)
    elif (content[0] == "remove"):
        await mp.remove(content[1], m.channel)
    elif (content[0] == "stop"):
        await mp.stop()
    elif (content[0] == "disconnect"):
        await mp.disconnectVoice()



    # super secret admin commands
    if (m.author.id == admin):
        if (content[0] == "ip"):
            response = subprocess.run("dig @resolver1.opendns.com ANY myip.opendns.com +short", shell=True, stdout=subprocess.PIPE, encoding="utf-8")

            await m.channel.send("The IP of the server is: {}".format(response.stdout))

    dprint("-- command execution complete --")
    
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


async def getWaifu(message):
    #gets a picture of danny devito from duckduckgo

    #### parse the webpage and get a list of links
    global browser
    if not browser:
        await message.channel.send("Browser not started")
        return

    #load the search
    browser.get('https://duckduckgo.com/?q=danny+devito')
    #click the images button
    browser.find_element_by_class_name('js-zci-link--images').click() 

    #print(browser.title)
    images = browser.find_elements_by_class_name('tile--img__img')
    #print(len(images))
    if (len(images) == 0):
        dprint("no images found in web scrape!!!")
        dprint("HTML------------------\n\n{}\n\n-----------------".format(browser.page_source))
        return

    waifu_link = images[random.randint(0, len(images) - 1)]
    waifu_link = urllib.parse.unquote(waifu_link.get_attribute('src'))
    waifu_link = waifu_link[waifu_link.find('?') + 3:]

    #### Select one of them and save it
    urllib.request.urlretrieve(waifu_link, "tempWaifu.jpg")


    #### Send it
    try:
        df = discord.File(fp="./tempWaifu.jpg",filename="best_waifu.jpg")
    except IOError:
        dprint("Tried to open a saved waifu image and failed")
        return


    ##post the file
    await message.channel.send(content=None, file=df)

    ## delete the local copy
    os.remove("./tempWaifu.jpg")



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

#dprint ('Starting the browser')
#
#options = Options()
#options.headless = True
#browser = webdriver.Firefox(options=options)
browser = None


# creating music player
dprint("Making music player")
mp = MusicPlayer(client);

# connecting to discord
print('Making connections')
client.run(token)
