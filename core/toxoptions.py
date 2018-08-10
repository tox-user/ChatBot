from pytox import Tox

class ToxOptions():
	def __init__(self):
		self.ipv6_enabled = False
		self.udp_enabled = True
		self.local_discovery_enabled = True
		self.proxy_type = 0 # 1=http, 2=socks
		self.proxy_host = ""
		self.proxy_port = 0
		self.start_port = 0
		self.end_port = 0
		self.tcp_port = 0
		self.savedata_type = 0 # 1=toxsave, 2=secretkey
		self.savedata_data = b""
		self.savedata_length = 0
		self.profile = "chatbot.tox"

	def load_profile(self):
		self.savedata_data = open(self.profile, "rb").read()
		self.savedata_length = len(self.savedata_data)
		self.savedata_type = Tox.SAVEDATA_TYPE_TOX_SAVE

	def save_profile(self, tox):
		data = tox.get_savedata()
		with open(self.profile, "wb") as f:
			f.write(data)
