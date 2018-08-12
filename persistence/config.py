from os.path import exists
from collections import OrderedDict
import json

class Config():
	def __init__(self):
		self.CONFIG_PATH = "config.json"

		with open("persistence/default_config.json", "r") as f:
			self.DEFAULT_CONFIG = json.load(f, object_pairs_hook=OrderedDict)

		if not exists(self.CONFIG_PATH):
			with open(self.CONFIG_PATH, "w") as f:
				json.dump(self.DEFAULT_CONFIG, f, indent=4)
				self.config = self.DEFAULT_CONFIG
				print("config.json configuration file created")
		else:
			with open(self.CONFIG_PATH, "r") as f:
				self.config = json.load(f)

	def reload(self):
		# TODO: reload config
		pass
