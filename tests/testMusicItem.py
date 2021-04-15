# include the parent directories files
import sys 
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# including unit testing stuff
import unittest

# needed stuff
from musicplayer import MusicItem

class MusicPlayerTest(unittest.TestCase):
    def test_simple(self):
        data = { 'title': 'Test',
                'url': 'test'}

        mi = MusicItem(data)

        self.assertEqual(mi.data, data)
        self.assertEqual(mi.title, data.get('title'))
        self.assertEqual(mi.type, 'single')

    def test_playlist(self):
        entry_data = { 'title': 'Test',
                'url': 'test'}
        entries = []
        for i in range(0,4):
            entries.append(entry_data)

        data = { 'title': 'Test',
                'url': 'test',
                'entries': entries}

        mi = MusicItem(data)

        self.assertEqual(mi.title, data.get('title'))
        self.assertEqual(mi.type, 'playlist')
        self.assertEqual(mi.data, data.get('entries'))
