# include the parent directories files
import sys 
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# including unit testing stuff
import unittest
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock
from unittest.mock import Mock

# needed stuff
import youtube_dl
from musicplayer import MusicPlayer
import discord

#mocking things that need to be mocked
discord.FFmpegPCMAudio = Mock()
discord.PCMVolumeTransformer = Mock(discord.PCMVolumeTransformer)

class MusicPlayerTest(IsolatedAsyncioTestCase):
    def test_hello(self):
        self.assertEqual(1,1)

    def setUp(self):

        # creating mock discord interactions
        self.textChannel = AsyncMock()
        self.textChannel2 = AsyncMock()


        self.voiceChannel = AsyncMock(discord.VoiceChannel)
        self.voiceChannel.connect.return_value = AsyncMock(discord.VoiceClient)

        self.voiceChannel2 = AsyncMock(discord.VoiceChannel)
        self.voiceChannel2.connect.return_value = AsyncMock(discord.VoiceClient)

        self.client = AsyncMock()

        # creating mock data interactions
        data = { 'url': 'http://mock.url',
                'title': 'Mock Youtube Video' }
        self.ytdl = Mock()
        self.ytdl.extract_info = Mock(return_value=data)

        # creating client
        self.player = MusicPlayer(self.client, self.ytdl)
        
    def tearDown(self):
        self.textChannel = None
        self.textChannel2 = None
        self.voiceChannel = None
        self.voiceChannel2 = None
        self.ytdl = None
        self.client = None
        self.player = None


############ Testing normal operations

    async def test_creation(self):
        self.assertIsNotNone(self.client)

    async def test_addition(self):
        await self.player.command_add("test url", self.textChannel)
        assert len(self.player.music_queues[self.player.current_queue]) == 1
        await self.player.command_add("test url", self.textChannel)
        assert len(self.player.music_queues[self.player.current_queue]) == 2

    async def test_playing(self):
        await self.player.command_add("test url", self.textChannel)
        await self.player.command_play(self.textChannel, self.voiceChannel)

        # make sure the voice channel was joined
        assert self.player.voice_channel == self.voiceChannel
        # make sure the text channel was used
        self.assertEqual(self.player.text_channel,  self.textChannel)
        assert self.textChannel.send.called
        # make sure the player had play called
        assert self.player.voice_client is not None
        assert self.player.voice_client.play.called
        # make sure song is playing
        self.assertEqual( self.player.state, "playing")


    async def test_add_while_playing(self):
        data1 = { 'url': 'http://mock.url',
                'title': 'Mock Youtube Video' }
        self.ytdl.extract_info.return_value = data1
        # add first thing and play
        await self.player.command_add("test url", self.textChannel)
        await self.player.command_play(self.textChannel, self.voiceChannel)

        # add second thing
        data2 = { 'url': 'http://mock.url',
                'title': 'Mock Youtube Video 2' }
        self.ytdl.extract_info.return_value = data2

        await self.player.command_add("test url", self.textChannel)

        # make sure the currently playing song is the first one
        self.assertEqual(self.player.currently_playing.title,  data1.get('title'))
        # and the second on is in the queue
        self.assertEqual(self.player.music_queues[self.player.current_queue][0].title,  data2.get('title'))

    async def test_pause(self):
        #add and play a song
        await self.player.command_add("test url", self.textChannel)
        await self.player.command_play(self.textChannel, self.voiceChannel)

        #pause
        await self.player.command_pause(self.textChannel)

        #check that pause was called in the player, and the member is set
        assert self.player.voice_client.pause.called
        self.assertEqual(self.player.state, "paused")

    async def test_stop(self):
        #add and play a song
        await self.player.command_add("test url", self.textChannel)
        await self.player.command_play(self.textChannel, self.voiceChannel)

        #stop
        await self.player.command_stop(self.textChannel)
        #check that pause was called in the player, and the member is set
        assert self.player.voice_client is None
        assert self.player.currently_playing is None

    async def test_playnow(self):
        # add some songs and start playing
        await self.player.command_add("test url", self.textChannel)
        await self.player.command_add("test url", self.textChannel)
        await self.player.command_play(self.textChannel, self.voiceChannel)

        # try to play this song now
        data2 = { 'url': 'http://mock.url',
                'title': 'Mock Youtube Video 2' }
        self.ytdl.extract_info.return_value = data2

        await self.player.command_playnow("test url", self.textChannel, self.voiceChannel)

        # verify its playing
        self.assertEqual( data2.get('title'), self.player.currently_playing.title)
        assert self.player.voice_client is not None
        self.assertEqual(self.player.state, "playing")

    async def test_two_playnows(self):

        await self.player.command_playnow("test url", self.textChannel, self.voiceChannel)
        await self.player.command_playnow("test url", self.textChannel, self.voiceChannel)

        # verify its playing
        assert self.player.currently_playing is not None
        assert self.player.voice_client is not None
        self.assertEqual(self.player.state, "playing")

    async def test_queue_switch(self):
        # check that the default queue is zero
        self.assertEqual(self.player.current_queue, "0")
        await self.player.command_switch_queue("1", self.textChannel)
        self.assertEqual(self.player.current_queue, "1")

    async def test_adding_queues(self):

        # add something to the default queue
        data1 = { 'url': 'http://mock.url',
                'title': 'Mock Youtube Video 1' }
        self.ytdl.extract_info.return_value = data1
        await self.player.command_add("test url", self.textChannel)

        # switch to queue two
        data2 = { 'url': 'http://mock.url',
                'title': 'Mock Youtube Video 2' }
        self.ytdl.extract_info.return_value = data2
        await self.player.command_switch_queue("1", self.textChannel)

        # add somsething to it
        await self.player.command_add("test url", self.textChannel)

        # verify that the things were added correctly
        self.assertEqual(len(self.player.music_queues["0"]), 1)
        self.assertEqual(len(self.player.music_queues["1"]), 1)

        self.assertEqual(self.player.music_queues["0"][0].title, data1.get('title'))
        self.assertEqual(self.player.music_queues["1"][0].title, data2.get('title'))

    async def test_playing_in_queue(self):
        # add something to the default queue
        data1 = { 'url': 'http://mock.url',
                'title': 'Mock Youtube Video 1' }
        self.ytdl.extract_info.return_value = data1
        await self.player.command_add("test url", self.textChannel)

        # switch to queue two
        data2 = { 'url': 'http://mock.url',
                'title': 'Mock Youtube Video 2' }
        self.ytdl.extract_info.return_value = data2
        await self.player.command_switch_queue("1", self.textChannel)

        # add somsething to it
        await self.player.command_add("test url", self.textChannel)

        # play here
        await self.player.command_play(self.textChannel, self.voiceChannel)

        # make sure it's playing
        self.assertEqual(self.player.state, "playing")

    async def test_switching_queue_while_playing(self):
        await self.player.command_add("test url", self.textChannel)
        await self.player.command_play(self.textChannel, self.voiceChannel)
        await self.player.command_switch_queue("1", self.textChannel)

        self.assertEqual(self.player.state, "stopped")
        assert self.player.currently_playing is None

    async def test_switching_between_playing_queues(self):
        # song 1
        data1 = { 'url': 'http://mock.url',
                'title': 'Mock Youtube Video 1' }
        self.ytdl.extract_info.return_value = data1

        await self.player.command_add("test url", self.textChannel)
        # song 2
        data2 = { 'url': 'http://mock.url',
                'title': 'Mock Youtube Video 2' }
        self.ytdl.extract_info.return_value = data2
        await self.player.command_switch_queue("1", self.textChannel)
        await self.player.command_add("test url", self.textChannel)

        await self.player.command_play(self.textChannel, self.voiceChannel)

        
        await self.player.command_switch_queue("0", self.textChannel)
        
        self.assertEqual(self.player.state, "playing")
        self.assertEqual(self.player.currently_playing.title, data1.get('title'))


        await self.player.command_switch_queue("1", self.textChannel)
        self.assertEqual(self.player.currently_playing.title, data2.get('title'))


############ Testing errors

if __name__ == '__main__':
        unittest.main()

