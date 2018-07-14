from pytox import Tox
from time import sleep
from db import DB
from command import Command

SERVER = [
	"130.133.110.14",
	33445,
	"461FA3776EF0FA655F1A05477DF1B3B614F7D6B124F7DB1DD4FE3C08B03B640F"
]

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


class Core(Tox):
	def __init__(self, options=None):
		if options is not None:
			super(Core, self).__init__(options)

		self.db = DB()
		self.options = options
		self.self_set_name("ChatBot")
		print("ID: %s" % self.self_get_address())

		self.connect()

	def connect(self):
		print("connecting...")
		self.bootstrap(SERVER[0], SERVER[1], SERVER[2])

	def save_profile(self):
		with open(self.profile, "wb") as f:
			f.write(self.get_savedata())

	def loop(self):
		checked = False
		self.options.save_profile(self)

		try:
			while True:
				status = self.self_get_connection_status()

				if not checked and status:
					print("connected to DHT")
					checked = True

					channels = self.db.get_channels()
					for channel in channels:
						index = self.conference_new()
						self.conference_set_title(index, channel[0])

				if checked and not status:
					print("disconnected from DHT")
					self.connect()
					checked = False

				self.iterate()
				sleep(0.01)

		except KeyboardInterrupt:
			print("interrupted by user, exiting")
			self.db.close()
			self.options.save_profile(self)
			exit()

	def on_friend_request(self, pk, message):
		self.friend_add_norequest(pk)
		self.options.save_profile(self)

	def on_conference_invite(self, friendId, type, cookie):
		pass

	def on_friend_connection_status(self, friendId, status):
		pass

	def on_conference_message(self, groupId, peerId, type, message):
		author_name = "[%s]: " % self.conference_peer_get_name(groupId, peerId)
		message = author_name + message
		group_name = self.conference_get_title(groupId)
		self.db.log_message(group_name, message)

	def on_friend_message(self, friendId, message_type, message):
		response = Command.parse(self, message, friendId)

		if response != "":
			self.friend_send_message(friendId, message_type, response)
