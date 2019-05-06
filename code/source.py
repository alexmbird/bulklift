import os
import os.path
import yaml
from copy import deepcopy

from clint.textui import indent, puts

from util import dict_deep_merge
from transcoders import TRANSCODERS


class MediaSourceNode(object):

  CONFIG_YAML_FILE = '.bulklift.yaml'


  def __init__(self, path, parent):
    self.parent = parent
    self.path = path
    self.config = self._loadConfig()


  @property
  def config_path(self):
    return os.path.join(self.path, self.CONFIG_YAML_FILE)


  @property
  def root(self):
    return self if self.parent is None else self.parent


  def _loadConfig(self):
    conf = deepcopy(self.parent.config) if self.parent else dict()
    try:
      with open(self.config_path, 'r') as stream:
        dict_deep_merge(conf, yaml.safe_load(stream))
    except FileNotFoundError:
      pass
    if 'config' not in conf:
      raise RuntimeError("Failed to inherit base config; missing a {} in your root?".format(self.CONFIG_YAML_FILE))
    return conf


  def walk(self):
    subnodes = [MediaSourceNode(d.path, self) for d in os.scandir(self.path) if d.is_dir()]
    for node in subnodes:
      node.doTranscoding()
      node.walk()


  def doTranscoding(self):
    for o_name, o_spec in self.config.get('outputs', {}).items():
      if o_spec.get('enabled', False):
        transcoder = TRANSCODERS[o_spec['codec']](
          self, self.config['metadata'], o_spec, self.config['config']
        )
        puts(str(transcoder))
        with indent(2):
          transcoder.transcode()


  def __str__(self):
    return "<{} {}>".format(self.__class__.__name__, self.path)
