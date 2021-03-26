#!/usr/bin/python3
import discord
import asyncio
import youtube_dl
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

    async def play(self, voiceChannel, textChannel, url):

        # connect to the requester's voice channel
        if voiceChannel:
            
            print ("---{}---".format(url))
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

            source = discord.FFmpegPCMAudio(data['url'], **self.ffmpeg_options)
            player = discord.PCMVolumeTransformer(source, self.volume)

            await self.joinVoice(voiceChannel)
            if (self.voiceClient):
                self.voiceClient.play(player,  after=self.donePlaying)

        else:
            await textChannel.send("You're not in a voice channel! No go.")

    def donePlaying(self, error):
        if error:
            print("error in playing song: {}".format(error))

        # disconnect from voice
        coro = self.disconnectVoice()
        fut = asyncio.run_coroutine_threadsafe(coro, self.client.loop)
        try:
            fut.result()
        except:
            # an error happened sending the message
            print("song disconnect coroutine failed");
            pass

    # gets called after a song is done playing, maybe because of an error 

    async def joinVoice(self, voiceChannel):
        self.voiceClient = await voiceChannel.connect();

    async def disconnectVoice(self):
        for voiceClient in self.client.voice_clients:
            await voiceClient.disconnect();
