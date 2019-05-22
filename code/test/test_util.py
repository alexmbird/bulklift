import unittest
from pathlib import Path

from util import dict_not_nulls, available_cpu_count, vfat_sanitize


class TestDictNotNulls(unittest.TestCase):

  def test_dict_not_nulls(self):
    "dict_not_nulls() recursively strips pairs with empty-values"
    d1 = dict_not_nulls({'a': 1, 'b': None, 'c': {}, 'd': {'z':None}, 'e': {'y':1}})
    assert 'a' in d1
    assert 'b' not in d1
    assert 'c' not in d1
    assert 'd' not in d1
    assert 'e' in d1


class TestCpuCount(unittest.TestCase):

  def test_available_cpu_count(self):
    "available_cpu_count() returns a number of cpus"
    cc = available_cpu_count()
    assert cc > 0
    assert cc == int(cc)


class TestFat32Sanitize(unittest.TestCase):

  def test_fat32_sanitize(self):
    "Sanitize filenames for vfat"
    self.assertEqual(vfat_sanitize(Path('/this/is/fi ne')), Path('/this/is/fi ne'))
    self.assertEqual(vfat_sanitize(Path('/this/<s/?not')), Path('/this/s/not'))
    self.assertEqual(vfat_sanitize('/this/>s/?not'), Path('/this/s/not'))
