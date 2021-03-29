#!/usr/bin/python3
import discord
import asyncio
import youtube_dl
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
        # 'play this now then continue'
        # skip song
        # have killing bot not leave things in weird state
    # advanced usage:
        # playlists as items not individual songs
        # saving playlists
        # fancier output
        # typing when thinking
        # DM's when commands fail
        # undo/redo for queue actions
    # misc:
        # leave voice channel when disconnecting
        # safe multithreading
        # metrics
        # reorder command that takes [#,#,#,#,#]

class MusicPlayer:
    def __init__(self, client):
        self.client = client;
        self.ytdl_format_options = {
            'format': 'bestaudio/best',
            'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
        }
        self.ffmpeg_options = {
            'options': '-vn'
        }
        self.ytdl = youtube_dl.YoutubeDL(self.ytdl_format_options)
        
        # volume
        self.volume = 1.0
        # the volume transformer currently in use (used to change volume)
        self.player = None

        # dictionary, data is a dictionary of video data including stream url
        self.audio_queue = []

        self.voice_client = None
        # is a song currently playing (false when paused)
        self.is_playing = False

        # song currently playing
        self.currently_playing = None



    ### commands
    #async def playnow(self, voiceChannel):
    #    #put what's currently playing back in the queue (if applicable)
    #    #play the requested song

    # put the current song back in the queue and stop playing
    async def stop(self):
        # put the currently playing thing in the queue
        self.audio_queue.insert(0, self.currently_playing)
        # stop playing
        self.voice_client.stop()

    # unpause, or play first thing in queue
    async def play(self, voiceChannel, textChannel):
        ## preconditions
        # if playing anything
        if self.currently_playing is not None:
            #if paused, continue 
            if not self.is_playing:
                self.voice_client.resume()
                self.is_playing = True
                return
            await self.sendError(textChannel, "already playing")
            return
        
        # if there is not something in the queue
        if len(self.audio_queue) == 0:
            await self.sendError(textChannel, "Couldn't play, no songs added")
            return
           
        ## main bit

        # ensure connection to a voice channel
        if self.voice_client is None:
            # connect to the user's
            if voiceChannel is None:
                await self.sendError(textChannel, "Couldn't play, dont know where join.")
                return
            await self.joinVoice(voiceChannel)

        # get data for song
        data = self.audio_queue[0].get('data')
        source = discord.FFmpegPCMAudio(data['url'], **self.ffmpeg_options)
        player = discord.PCMVolumeTransformer(source, self.volume)
        player.volume = self.volume


        # attempt to play
        if (self.voice_client):
            self.voice_client.play(player, after=self.donePlaying)
        else: 
            await self.sendError(textChannel, "Couldn't play, no voice client")
            source.cleanup()

        # if successful, update data
        self.is_playing = True
        self.currently_playing = { 'data': data }
        self.player = player
        del self.audio_queue[0]
        await self.set_playing(True, data.get('title'))



    async def pause(self, textChannel):
        # stop playback for now
        if self.voice_client is None or not self.is_playing:
            self.sendError(textChannel, "Can't pause, not playing")
            return

        self.voice_client.pause();
        await self.set_playing(False, status=None)

    #async def leave():
    #    # pause and disconnect

    async def add(self, url, textChannel):
        # add something to the queue
        #stop playing whatever was playing
        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(url, download=False))
        except:
            await textChannel.send("Couldn't parse webpage. Can't play song.")
            return

        #if it's a playlist
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        self.audio_queue.append({
            'data': data})
        await textChannel.send("Added: {}. Position in queue: {}".format(
            self.string_queue_item(self.audio_queue[len(self.audio_queue)-1]), 
            len(self.audio_queue) - 1))

    async def getQueue(self, textChannel):
        ret = ''
        if self.currently_playing is not None:
            if self.is_playing:
                ret += "Currently Playing: " + self.string_queue_item(self.currently_playing) + "\n"
            else:
                ret += "Currently Playing: " + self.string_queue_item(self.currently_playing) + " (Paused)"  +  "\n"
        else:
            ret += "Not currently playing anything.\n"

        if len(self.audio_queue) == 0:
            ret += "No items in queue."
        else:
            i = 0
            for item in self.audio_queue:
                ret += str(i) + ': '
                ret += self.string_queue_item(item)
                ret += '\n'
                i += 1
        await textChannel.send(ret);

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

    async def clear(self, textChannel):
        self.song_queue = []
        await textChannel.send("Song queue cleared.")
        
    async def remove(self, index, textChannel):
        # check validity
        try:
            index = int(index)
        except ValueError:
            await self.sendError(textChannel, "Couldn't parse that number, sorry")
            return

        if index < 0 or index > len(self.audio_queue) - 1:
            await self.sendError(textChannel, "Number not valid, needs to correspond to queue item")

        
        title = self.audio_queue[index].get('data').get('title')
        del self.audio_queue[index]

        await self.sendError(textChannel, "Removed {} at positon {}".format(title, index))


    ## internals

    async def set_playing(self, playing, status):
        self.is_playing = playing;
        if playing:
            game = discord.Game(status)
            await self.client.change_presence(status=discord.Status.online, activity=game)
        else:
            game = discord.CustomActivity("vibin")
            await self.client.change_presence(status=discord.Status.idle, activity=game)

    def string_queue_item(self, item):
        data = item.get('data')
        ty_res = time.gmtime(data.get('duration'))
        res = time.strftime("%H:%M:%S",ty_res)
        return data.get('title') + ', Length: ' + res

    async def sendError(self, textChannel, message):
        if textChannel is not None:
            await textChannel.send(message)
            print (message)
        else: 
            print ("error! no text channel to send response: {}".format(message))



    async def nextSong(self):
        if len(self.audio_queue) > 0:
            await self.play(textChannel=None, voiceChannel=None)


    def donePlaying(self, error):
        if error:
            print("error in playing song: {}".format(error))

        #play the next song
        self.currently_playing = None

        #fancy way of calling nextsong and disconnectvoice from non-async function
        coro = self.nextSong()
        fut = asyncio.run_coroutine_threadsafe(coro, self.client.loop)
        try:
            fut.result()
        except Exception as e:
            # an error happened sending the message
            print("playing next song coroutine failed: {}".format(e.message))
            pass

        if not self.is_playing:
            # if there's nothing to play, disconnect from voice
            coro2 = self.disconnectVoice()
            fut2 = asyncio.run_coroutine_threadsafe(coro2, self.client.loop)
            try:
                fut2.result()
            except Exception as e:
                # an error happened sending the message
                print("song disconnect coroutine failed: {}".format(e.message))
                pass

        coro3 = self.set_playing(False, status=None)
        fut3 = asyncio.run_coroutine_threadsafe(coro3, self.client.loop)
        try:
            fut2.result()
        except Exception as e:
            # an error happened sending the message
            print("song staus change coroutine failed: {}".format(e.message))
            pass

    # gets called after a song is done playing, maybe because of an error 

    async def joinVoice(self, voiceChannel):
        self.voice_client = await voiceChannel.connect();

    async def disconnectVoice(self):
        for voiceClient in self.client.voice_clients:
            await voiceClient.disconnect();
        self.voice_client = None
        await self.set_playing(False, status=None)
