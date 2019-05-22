import unittest
from pathlib import Path

from manifest import Manifest


class TestManifest(unittest.TestCase):

  def test_LoadExampleTree1(self):
    "Load manifests from example tree 1"
    p = Path('examples/tree_1')
    man_root = Manifest.load(p)
    self.assertTrue(man_root['root'])
    self.assertEqual(man_root['metadata'], {})
    p = p / 'Electronic'
    man_genre = Manifest.load(p)
    self.assertFalse(man_genre['root'])
    self.assertEqual(man_genre['metadata'], {'genre':'Electronic'})
    p = p / 'Artist Name 1'
    man_artist = Manifest.load(p)
    self.assertFalse(man_artist['root'])
    self.assertEqual(man_artist['metadata'], {'genre':'Electronic', 'artist':'Artist Name 1'})
    man_album_a = Manifest.load(p / '1998 90 Minutes of Bleep-Bloop Noises')
    self.assertFalse(man_album_a['root'])
    self.assertEqual(man_album_a['metadata'], {
      'genre':'Electronic',
      'artist': 'Artist Name 1',
      'album': '90 Minutes of Bleep-Bloop Noises',
      'year': 1998
    })
    self.assertEqual(len(man_album_a.outputs), 2)
    man_album_b = Manifest.load(p / '2004 Album Made With My Mate')
    self.assertFalse(man_album_b['root'])
    self.assertEqual(man_album_b['metadata'], {
      'genre':'Electronic',
      'artist': 'Artist Name 1 (and his mate)',
      'album': 'Album Made With My Mate',
      'year': 2004
    })
    self.assertEqual(man_album_b.outputs_enabled, [])


  def test_LoadNoRoot(self):
    "Raise exception if root is missing"
    with self.assertRaises(RecursionError):
      man_noroot = Manifest.load(Path('/'))
