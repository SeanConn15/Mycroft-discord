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
        # auto connect and disconnect afterwards
        # steam a video and play in voice channel
        # request a video by url and steam in voice channel

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
        self.volume = 1.0

        self.voiceClient = None
        self.playing = False

        # has data, (made by youtubedl) and 
        self.audio_queue = []
        #gets set to a song queue item
        self.currently_playing = None


    ### commands
    #async def playnow(self, voiceChannel):
    #    #put what's currently playing back in the queue (if applicable)
    #    #play the requested song

    async def play(self, voiceChannel):
        # unpause, or play first thing in queue
        if (self.currently_playing is None):
            if (len(self.audio_queue) > 0):
                # if not connected to a voice channel
                if self.voiceClient is None:
                    # do that
                    if voiceChannel is None:
                        print ("couldn't play, dont know where to join")
                        return
                    await self.joinVoice(voiceChannel)
                # get data for song
                data = self.audio_queue[0].get('data')
                
                #start playing first item in queue
                source = discord.FFmpegPCMAudio(data['url'], **self.ffmpeg_options)
                player = discord.PCMVolumeTransformer(source, self.volume)

                if (self.voiceClient):
                    self.voiceClient.play(player, after=self.donePlaying)
                else: 
                    print ("failed to play song, no voice client")
                    source.cleanup()

                self.playing = True
                self.currentlyPlaying = data
                del self.audio_queue[0]


    #async def pause():
    #    # stop playback for now

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

    def string_queue_item(self, item):
        data = item.get('data')
        ty_res = time.gmtime(data.get('duration'))
        res = time.strftime("%H:%M:%S",ty_res)
        return data.get('title') + ', Length: ' + res



    ## internals

    async def nextSong(self):
        if len(self.audio_queue) > 0:
            await self.play(voiceChannel=None)


    def donePlaying(self, error):
        if error:
            print("error in playing song: {}".format(error))

        #play the next song
        self.currently_playing = None
        self.playing = False

        coro = self.nextSong()
        fut = asyncio.run_coroutine_threadsafe(coro, self.client.loop)
        try:
            fut.result()
        except Exception as e:
            # an error happened sending the message
            print("playing next song coroutine failed: {}".format(e.message))
            pass

        if not self.playing:
            # if there's nothing to play, disconnect from voice
            coro2 = self.disconnectVoice()
            fut2 = asyncio.run_coroutine_threadsafe(coro2, self.client.loop)
            try:
                fut2.result()
            except Exception as e:
                # an error happened sending the message
                print("song disconnect coroutine failed: {}".format(e.message))
                pass

    # gets called after a song is done playing, maybe because of an error 

    async def joinVoice(self, voiceChannel):
        self.voiceClient = await voiceChannel.connect();

    async def disconnectVoice(self):
        for voiceClient in self.client.voice_clients:
            await voiceClient.disconnect();
        self.voiceClient = None
        self.playing = False
