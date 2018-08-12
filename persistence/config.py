from os.path import exists
import json

class Config():
	def __init__(self):
		self.CONFIG_PATH = "config.json"

		with open("persistence/default_config.json", "r") as f:
			self.DEFAULT_CONFIG = json.load(f)

		if not exists(self.CONFIG_PATH):
			with open(self.CONFIG_PATH, "w") as f:
				json.dump(self.DEFAULT_CONFIG, f)
				self.config = self.DEFAULT_CONFIG
				print("config.json configuration file created")
		else:
			with open(self.CONFIG_PATH, "r") as f:
				self.config = json.load(f)

	def reload(self):
		# TODO: reload config
		pass
