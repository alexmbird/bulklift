import unittest

from util import dict_not_nulls


class TestDictNotNulls(unittest.TestCase):

  def test_dict_not_nulls(self):
    "dict_not_nulls() recursively strips pairs with empty-values"
    d1 = dict_not_nulls({'a': 1, 'b': None, 'c': {}, 'd': {'z':None}, 'e': {'y':1}})
    assert 'a' in d1
    assert 'b' not in d1
    assert 'c' not in d1
    assert 'd' not in d1
    assert 'e' in d1
