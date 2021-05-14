#!/usr/bin/python3
import discord
import asyncio
import youtube_dl
import logging
import time
### Music related things
#TODO: basic music playing
    #TODO: get it to play one thing from youtube
        # download a video with youtube-dl x
        # join a voice channel x
        # play something in a voice channel x
        # auto connect and disconnect afterwards x
        # steam a video and play in voice channel x
        # request a video by url and steam in voice channel x
    # basic usage:
        # play and pause x
        # bot volume x
        # removing items from queue x
        # clearing queue x
        # current status x
        # stop playing current song put back into queue
        # 'play this now then continue' x
        # skip song x
        # have killing bot not leave things in weird state x
    # advanced usage:
        # named playlists
        # saving playlists
            # saving playlist to file
                # naming playlist
            # loading playlist

        # fancier output
        # typing when thinking
        # DM's when commands fail
        # undo/redo for queue actions
    # misc:
        # leave voice channel when disconnecting x
        # safe multithreading
        # metrics
        # reorder command that takes [#,#,#,#,#]
        # play with argument becomes playnow x
        # warning about playlists (done with typing command)
        # replace string_queue_item
        # handle music failing better (retries and prompts)
        # follows both text and voice x
            # text channel attachment x
            # voice channel attachment x
        # seperate commands and member functions x




class MusicItem:
        # { type = "single", data = {ydtl data} }
        # or
        # { type = "playlist", data = [{ydtl data}, {ydtl data}, ... ], title = "string" }
        def __init__(self, data):
            if data is None:
                self.type = None
                return
            
            # playlist and single song support
            if 'entries' in data:
                self.type = "playlist"
                self.title = data.get('title')
                self.data = data.get('entries')
            else:
                self.type = 'single'
                self.title = data.get('title')
                self.data = data


class MusicPlayer:
    def __init__(self, client, ytdl):
        self.client = client;
        self.ffmpeg_options = {
            'options': '-vn'
        }
        self.ytdl = ytdl        

        # logger used for warning etc
        self.logger = logging.getLogger('discord')

        # volume
        self.volume = 1.0
        # the volume transformer currently in use (used to change volume)
        self.player = None

        # list of loaded playlists (not being played)
        self.playlists = {}

        # name of current queue
        # queues are stored in a dictionary of queues
        self.music_queues = {}
        # by default there are 10 named queues
        for i in range(0,3):
            self.music_queues[str(i)] = []
        self.current_queue = "0"

        # max number of songs to add
        self.max_playlist_size = 100

        self.voice_client = None

        # state can be stopped, paused, or playing
        self.state = "stopped"

        # song currently playing
        self.currently_playing = None

        # text channel currently doing things in
        self.text_channel = None
        # voice channel currently playing
        self.voice_channel = None


    ### commands

    # playnow, stop, play, pause, add, next, queue, set_volume, clear, remove



    async def command_play(self, textChannel, voiceChannel):
        if not await self.ensureText(textChannel):
            return

        if not await self.ensureVoice(voiceChannel):
            await self.send_error("Couldn't play.")
            return False
        await self.play()


    async def command_playnow(self, url, textChannel, voiceChannel):
        if not await self.ensureText(textChannel):
            return
        if not await self.ensureVoice(voiceChannel):
            await self.send_error("Couldn't play.")
            return False
        await self.playnow(url)

    async def command_pause(self, textChannel):
        if not await self.ensureText(textChannel):
            return
        await self.pause()

    async def command_stop(self, textChannel):
        if not await self.ensureText(textChannel):
            return
        await self.stop()
        await self.disconnect()

    async def command_add(self, url,  textChannel):
        if not await self.ensureText(textChannel):
            return
        await self.add(url)

    async def command_addAt(self, url, pos, textChannel):
        if not await self.ensureText(textChannel):
            return
        await self.addAt(url, pos)

    async def command_getQueue(self, textChannel):
        if not await self.ensureText(textChannel):
            return
        await self.getQueue()

    async def command_next(self, textChannel, voiceChannel):
        if not await self.ensureText(textChannel):
            return
        if not await self.ensureVoice(voiceChannel):
            await self.send_error("Couldn't skip, player error")
            return False
        await self.next()

    async def command_clear(self, textChannel):
        if not await self.ensureText(textChannel):
            return
        await self.clear()

    async def command_remove(self, pos, textChannel):
        if not await self.ensureText(textChannel):
            return
        await self.remove(pos)

    async def command_setVolume(self, vol, textChannel):
        if not await self.ensureText(textChannel):
            return
        await self.setVolume(vol)

    async def command_follow(self, textChannel, voiceChannel):
        await self.follow(textChannel, voiceChannel)

    async def command_print_queues(self, textChannel):

        if not await self.ensureText(textChannel):
            return
        await self.print_queues()

    async def command_switch_queue(self, queue_name, textChannel):
        if not await self.ensureText(textChannel):
            return
        await self.switch_queue(queue_name)


    ### internals

    async def send_error(self, message):
        await self.client.send_error(message, self.text_channel)

    # prints to terminal and sends voice channel

    async def follow(self, tc, vc):
        if (tc == self.text_channel and vc == self.voice_channel):
            await self.send_error("Nothing to change, text and voice channel both identical.")
            return False
        #if the text channel differs, change it and send a message
        if (tc != self.text_channel):
            self.text_channel = tc
            await self.text_channel.send("Text channel changed.")
        #if the voice channel differs, change it and send a messge
        if (vc != self.voice_channel):
            if not await self.ensureVoice(vc):
                return

    async def ensureVoice(self, voiceChannel):
        # ensures that the bot will play in the channel selected
        # returns false if the voice client fails for any reason

        if voiceChannel is None:
            print ("no voice channel, returning")
            return False


        #if there is a mismatch between voice client and voice channel
        if self.voice_channel is not None and self.voice_channel != voiceChannel:
            #move to that channel
            await self.voice_client.move_to(voiceChannel)
            self.voice_channel = voiceChannel
            await self.text_channel.send("Moved to new channel.")

        #if there is no voice client already, make one
        if self.voice_channel is None:
            self.voice_client = await voiceChannel.connect();
            if self.voice_client is None:
                await self.send_error("Connection to voice server failed")
                return False
            self.voice_channel = voiceChannel
            await self.text_channel.send("Voice channel set to {}".format(self.voice_channel.name))
            return True

                
        # the voice channel is set correctly
        if self.voice_channel == voiceChannel:
            return True
            

    async def ensureText(self, textChannel):
        # ensures that the bot's text channel and the request's text channel match
        # if they don't, asks them to use the channel with the name or do follow
        # returns false if there is a mismatch

        if textChannel == self.text_channel:
            return True

        if self.text_channel is None:
            self.text_channel = textChannel
            await self.text_channel.send("Text channel set to {}.".format(self.text_channel.name))
            return True


        # implicitly a mismatch in the given channel and set channel
        await textChannel.send("Commands currently accepted in the {} channel. Do 'follow' to switch this channel, or use that one.".format(self.text_channel.name))
        return False

    async def playnow(self, url):
        #make sure the url is good
        item = await self.parseUrl(url)
        if item is None:
            await self.send_error("The url is not valid, can't play")
            return False

        await self.stop()

        #play the requested song
        await self.addAt(0, url)
        if not await self.ensureVoice(self.voice_channel):
            await self.send_error("Couldn't play.")
            return False
        await self.play()

    # put the current song back in the queue and stop playing
    async def stop(self):
        # put the currently playing thing in the queue
        if self.currently_playing is not None:
            self.music_queues[self.current_queue].insert(0, self.currently_playing)
            # remove it from currently playing
            self.currently_playing = None
        # stop playing
        await self.set_status("stopped")
        if self.voice_client is not None:
            self.voice_client.stop()

    # leave all voice channels
    async def disconnect(self):
        for voiceClient in self.client.voice_clients:
            await voiceClient.disconnect();
        self.voice_client = None
        self.voice_channel = None

        await self.text_channel.send("Disconnected.")

    # unpause, or play first thing in queue
    async def play(self):
        ## preconditions
        # if playing anything
        if self.currently_playing is not None:
            #if paused, continue 
            if self.state == "paused":
                self.voice_client.resume()
                await self.set_status("playing", self.currently_playing.title)
                return
            await self.sendError(textChannel, "already playing")
            return
        
        # if there is not something in the queue
        if len(self.music_queues[self.current_queue]) == 0:
            await self.sendError(self.text_channel, "Couldn't play, no songs added")
            return
           

        ## main bit

        # get data for song
        item = self.music_queues[self.current_queue][0]
        source = discord.FFmpegPCMAudio(item.data['url'], **self.ffmpeg_options)
        player = discord.PCMVolumeTransformer(source, self.volume)
        player.volume = self.volume


        # attempt to play
        if (self.voice_client):
            self.voice_client.play(player, after=self.donePlaying)
        else: 
            await self.sendError(self.text_channel, "Couldn't play, no voice client")
            source.cleanup()

        # if successful, update data
        if self.state == "stopped":
            self.state = "playing";

        self.currently_playing = item
        self.player = player
        del self.music_queues[self.current_queue][0]
        await self.set_status("playing", item.data.get('title'))


    async def pause(self):
        # stop playback for now
        await self.set_status("paused")
        await self.text_channel.send("Paused.")


    async def addAt(self, pos, url):
        # check validity of pos
        try:
            pos = int(pos)
        except ValueError:
            await self.sendError(self.text_channel, "Couldn't parse that number, sorry")
            return

        if pos < 0 or (len(self.music_queues[self.current_queue]) > 0 and pos > len(self.music_queues[self.current_queue])):
            await self.sendError(self.text_channel, "Number not valid, needs to correspond to queue item")

        # if given metadata already
        # get metadata
        songs = await self.parseUrl(url)
        if songs is None or songs[0] is None:
            await self.send_error("Couldn't parse webpage. Can't play song.")
            return False

        # add metadata to queue
        i = 0
        currentlen = len(self.music_queues[self.current_queue])
        for song in songs:
            self.music_queues[self.current_queue].insert(pos + i, song)

            # if we hit the song limit
            if currentlen + i >= self.max_playlist_size:
                # if it was a playlist
                if i > 1:
                    await self.send_error("Too many songs added, max {}. only able to add up to song {}, \"{}\".".format(
                        self.max_playlist_size, 
                        pos + i,
                        self.music_queues[self.current_queue][pos + i].title))
                    return False
                else:
                    #otherwise
                    await self.send_error("Too many songs added, max {}. Not able to add song.".format(
                        self.max_playlist_size))
                    return
            i += 1

        await self.text_channel.send("Added: {}. Position in queue: {}".format(
            self.string_queue_item(self.music_queues[self.current_queue][pos]), pos))
        

    async def add(self, url):
        if len(self.music_queues[self.current_queue]) == 0:
            await self.addAt(0, url)
        else:
            await self.addAt(len(self.music_queues[self.current_queue]), url)

    async def next(self):
        #stop the current song
        await self.stop()
        #remove the entry added to the front
        await self.remove(0)
        #play
        await self.play()

    async def getQueue(self):
        ## prints the queue out in messages of 50 entries

        # current queue name
        queuestring = "\n```Current Queue: {}```\n```".format(self.current_queue)

        # currently playing
        if self.currently_playing is not None:
            if self.state != "paused":
                queuestring += "Currently Playing: " + self.string_queue_item(self.currently_playing) + "\n"
            else:
                queuestring += "Currently Playing: " + self.string_queue_item(self.currently_playing) + " (Paused)"  +  "\n"
        else:
            queuestring += "Currently Playing: Nothing.\n"

        queuestring += '```\n```'

        # items in queue
        if len(self.music_queues[self.current_queue]) == 0:
            queuestring += "No items in queue."
        else:
            i = 0
            for item in self.music_queues[self.current_queue]:
                # if the string gets too long, split the message
                if len(queuestring) + len(self.string_queue_item(item)) > 2000:
                    queuestring += "```"
                    await self.text_channel.send(queuestring);
                    queuestring = "```\n"
                queuestring += str(i) + ': '
                queuestring += self.string_queue_item(item)
                queuestring += '\n'
                i += 1

        queuestring += "```"
        await self.text_channel.send(queuestring);

    def print_abbreviated_queue(self, q):
        # queue name
        ret = "```Name: {}".format(q) 
        # first three items (if that long)
        if len(self.music_queues[q]) == 0:
            ret += " <empty>```"
            return ret
        else:
            ret += " Length: {}".format(len(self.music_queues[q]))
        
        qlen = 3
        if len(self.music_queues[q]) < 3:
            qlen = len(self.music_queues[q])  

        for i in range(0,qlen):
            ret += "\n{}: {}".format(i, self.music_queues[q][i].title)
            i += 1

        if len(self.music_queues[q]) > 3:
            ret += "\n...```"
        else:
            ret += "\n```"


        return ret
            

    async def print_queues(self):
        printstring = ""
        for q in self.music_queues.keys():
            printstring += self.print_abbreviated_queue(q)
        await self.text_channel.send(printstring)

    async def switch_queue(self, name):
        print( "Before: {} {}".format(self.currently_playing, self.state))

        if name not in self.music_queues:
            await self.send_error("No queue with name \'{}\' found.".format(name))
            return False
        #TODO: make this pause instead of stop

        wasPlaying = self.currently_playing

        if self.currently_playing:
            await self.stop()

        self.current_queue = name
        if wasPlaying and len(self.music_queues[self.current_queue]) > 0:
            print ("!!!!!!!!")
            await self.play()

        await self.text_channel.send("Switched queue to \'{}\'.".format(name))
        print( "After: {} {}".format(self.currently_playing, self.state))

    async def setVolume(self, volume, textChannel):
        # volume is a string, try to turn it into a float
        try:
            vol = int(volume)
        except ValueError:
            await self.sendError(textChannel, "Couldn't parse that number, should be 1-100")
            return
        if vol > 100 or vol < 1:
            await self.sendError(textChannel, "Number should be integer between 1 and 100 inclusive")
            return
        
        # if that works set it
        self.volume = vol/100

        if self.player is not None:
            self.player.volume = self.volume
        await textChannel.send("Volume set to {}".format(volume))

    async def clear(self):
        self.music_queues[self.current_queue] = []
        await self.text_channel.send("Song queue cleared.")
        
    async def remove(self, index):
        # check validity
        try:
            index = int(index)
        except ValueError:
            await self.send_error("Couldn't parse that number, sorry")
            return False

        if index < 0 or index > len(self.music_queues[self.current_queue]) - 1:
            await self.send_error("Number not valid, needs to correspond to queue item")
            return False

        
        title = self.music_queues[self.current_queue][index].title
        del self.music_queues[self.current_queue][index]

        await self.text_channel.send("Removed {} at positon {}".format(title, index))


    ## internals

    #status is playing with name, paused, stopped, or idle
    async def set_status(self, status, name=None):
        if status == "playing":
            game = discord.Game(name)
            await self.client.change_presence(status=discord.Status.online, activity=game)

        elif status == "idle":
            game = discord.CustomActivity("vibin")
            await self.client.change_presence(status=discord.Status.idle, activity=game)
            self.state = "idle"

        elif status == "paused":
            if self.voice_client is None or self.state != "playing":
                await self.send_error("Can't pause, not playing")
                return

            self.voice_client.pause();
            game = discord.CustomActivity("paused")
            await self.client.change_presence(status=discord.Status.idle, activity=game)
            self.state = "paused"

        elif status == "stopped":
            game = discord.CustomActivity("stopped")
            await self.client.change_presence(status=discord.Status.idle, activity=game)
            self.state = "stopped"

        else:
            logger.warning("set_status given bad value: {}".format(status))


    def string_queue_item(self, item):
        ty_res = time.gmtime(item.data.get('duration'))
        res = time.strftime("%H:%M:%S",ty_res)
        return item.data.get('title') + ', Length: ' + res

    async def sendError(self, textChannel, message):
        if textChannel is not None:
            await textChannel.send(message)
            print (message)
        else: 
            print ("error! no text channel to send response: {}".format(message))


    # returns data or none depending on url parsing
    async def parseUrl(self, url):
        # get metadata
        loop = asyncio.get_event_loop()
        #TODO: tell if the url is a playlist, and warn about it
        try:
            data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(url, download=False))
        except:
            return None

        # if getting data failed; return none
        if data is None:
            return None

        #make the MusicItem object
        songs = []
        if 'entries' in data:
            for entry in data.get('entries'):
                songs.append(MusicItem(entry))
        else:
            songs.append(MusicItem(data))
        return songs



    def donePlaying(self, error):
        if error:
            print("error in playing song: {}".format(error))

        self.currently_playing = None

        #if manually stopped or paused don't do anything
        if self.state != "playing":
            return

        # if there are no more songs, don't do anything
        if len(self.music_queues[self.current_queue]) == 0:
            return

        #try to play the next song

        #fancy way of calling nextsong and disconnectvoice from non-async function
        coro = self.play()
        fut = asyncio.run_coroutine_threadsafe(coro, self.client.loop)
        try:
            fut.result()
        except Exception as e:
            # an error happened sending the message
            print("playing next song coroutine failed: {}".format(e.message))
            pass

        if not self.state != "paused":
            # if there's nothing to play, disconnect from voice
            coro2 = self.stop()
            fut2 = asyncio.run_coroutine_threadsafe(coro2, self.client.loop)
            try:
                fut2.result()
            except Exception as e:
                # an error happened sending the message
                print("song stop coroutine failed: {}".format(e.message))
                pass

        coro3 = self.set_status("stopped")
        fut3 = asyncio.run_coroutine_threadsafe(coro3, self.client.loop)
        try:
            fut3.result()
        except Exception as e:
            # an error happened sending the message
            print("song status change coroutine failed: {}".format(e.message))
            pass

    # gets called after a song is done playing, maybe because of an error 

    async def joinVoice(self, voiceChannel):
        self.voice_client = await voiceChannel.connect();
