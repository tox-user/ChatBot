from pytox import Tox
from time import sleep
from persistence.db import DB
from persistence.config import Config
from bot.command import Command
from bot.irc import IRC

MAX_GROUP_MESSAGE_LEN = 1024
SERVER = [
	"130.133.110.14",
	33445,
	"461FA3776EF0FA655F1A05477DF1B3B614F7D6B124F7DB1DD4FE3C08B03B640F"
]

# TODO: use all bootstrap nodes
# TODO: prevent group name changes
class Core(Tox):
	def __init__(self, options=None):
		if options is not None:
			super(Core, self).__init__(options)

		self.load_config()
		self.options = options
		print("Tox ID: %s" % self.self_get_address())

		self.connect()

		if self.config["enable_irc_sync_feature"]:
			self.start_irc_client()

	def connect(self):
		print("connecting to DHT...")
		self.bootstrap(SERVER[0], SERVER[1], SERVER[2])

	def on_connected(self):
		print("connected to DHT")
		self.create_groups()
	
	def on_disconnected(self):
		print("disconnected from DHT")
		self.connect()

	def save_profile(self):
		with open(self.profile, "wb") as f:
			f.write(self.get_savedata())

	def start_irc_client(self):
		print("connecting to IRC...")
		self.irc = IRC(self)
		self.irc.daemon = True
		self.irc.start()

	def loop(self):
		checked = False
		self.options.save_profile(self)

		try:
			while True:
				status = self.self_get_connection_status()

				if not checked and status:
					self.on_connected()
					checked = True

				if checked and not status:
					self.on_disconnected()
					checked = False

				self.iterate()
				sleep(0.01)

		except KeyboardInterrupt:
			print("interrupted by user, exiting")
			if self.config["enable_irc_sync_feature"]:
				self.irc.quit()
			self.db.close()
			self.options.save_profile(self)
			exit()

	def create_groups(self):
		groups = self.conference_get_chatlist()
		for group in groups:
			self.conference_delete(group)

		for channel in self.channels:
			index = self.conference_new()
			self.conference_set_title(index, channel["name"].encode("utf-8"))

	def on_friend_request(self, pk, message):
		self.friend_add_norequest(pk)
		self.options.save_profile(self)

	def on_conference_invite(self, friend_id, type, cookie):
		# TODO: join groups when invited without saving them to database but make sure they are listed
		# this will allow connecting channels from different group bots
		pass

	def on_friend_connection_status(self, friend_id, status):
		# TODO: autoinvite also when peer leaves group
		# autoinvite
		if status:
			user_id = self.friend_get_public_key(friend_id)
			rows = self.db.get_autoinvite_list(user_id)
			for row in rows:
				group = self.get_group_by_name(row[0].encode("utf-8"))
				if group != -1:
					self.conference_invite(friend_id, group)

	def on_conference_message(self, group_id, peer_id, type, message):
		author_name = "[%s]: " % self.conference_peer_get_name(group_id, peer_id)
		log_message = author_name + message
		group_name = self.conference_get_title(group_id)
		self.db.log_message(group_name, log_message)

		is_message_from_chatbot = self.conference_peer_number_is_ours(group_id, peer_id)
		if self.config["enable_irc_sync_feature"] and not is_message_from_chatbot:
			irc_channel = self.irc.get_bridged_irc_channel(group_name)
			if irc_channel != "":
				self.irc.send_message(irc_channel, log_message)

			response = Command.parse_channel(self, message, group_name)
			if response != "":
				response_messages = self.split_message(response)

				try:
					for response_message in response_messages:
						self.conference_send_message(group_id, 0, response_message.encode("utf-8"))
				except:
					print("ERROR: couldn't send a group message")

	def on_friend_message(self, friend_id, message_type, message):
		response = Command.parse(self, message, friend_id)

		if response != "":
			response_messages = self.split_message(response)

			try:
				for response_message in response_messages:
					self.friend_send_message(friend_id, message_type, response_message)
			except:
				print("ERROR: couldn't send message to a friend")

	def split_message(self, message):
		messages = []
		while len(message) > MAX_GROUP_MESSAGE_LEN:
			split_char = "\n"
			split_pos = message.rfind(split_char, 0, MAX_GROUP_MESSAGE_LEN-1)
			if split_pos <= 0:
				split_char = " "
				split_pos = message.rfind(split_char, 0, MAX_GROUP_MESSAGE_LEN-1)

				if split_pos <= 0:
					split_pos = MAX_GROUP_MESSAGE_LEN - 1

			new_message = message[:split_pos+1]
			messages.append(new_message)
			message = message[split_pos:]

		messages.append(message)
		return messages

	def get_group_peers(self, group_name):
		peers = []
		groups = self.conference_get_chatlist()
		for group in groups:
			if self.conference_get_title(group) == group_name:
				num_peers = self.conference_peer_count(group)
				for i in range(num_peers):
					peers.append(self.conference_peer_get_name(group, i))

				break

		return peers

	def get_group_by_name(self, group_name):
		groups = self.conference_get_chatlist()
		for group in groups:
			if self.conference_get_title(group) == group_name:
				return group

		print("ERROR: couldn't find group by name", group_name)
		return -1

	def send_group_message(self, group_name, message):
		if not self.self_get_connection_status():
			print("ERROR: failed to sync IRC message. No connection to DHT")
			return False

		group_id = self.get_group_by_name(group_name)
		if group_id == -1 or self.conference_peer_count(group_id) <= 1:
			return False
	
		try:
			self.conference_send_message(group_id, 0, message.encode("utf-8"))
		except:
			print("ERROR: couldn't send a group message")
			return False

		return True

	def get_channels(self, db=False, built_in_only=False):
		if not db:
			db = self.db

		channels = []
		rows = db.get_channels(built_in_only)
		for row in rows:
			id = row[0]
			topic = row[1]
			is_audio = row[2]
			is_built_in = row[3]

			if is_audio == 1:
				is_audio = True
			else:
				is_audio = False

			if is_built_in == 1:
				is_built_in = True
			else:
				is_built_in = False

			channels.append({"name": id, "topic": topic, "is_audio": is_audio, "is_built_in": is_built_in})

		return channels

	def load_config(self):
		self.config = Config().config

		# set Tox name and status
		self.self_set_name(self.config["tox_user_name"])
		self.self_set_status_message(self.config["tox_status_message"])

		# init database, load channels
		self.db = DB()
		self.db.init_data()
		self.channels = self.get_channels()

		# update built-in channels
		old_channel_names = []
		new_channel_names = []

		for channel in self.get_channels(False, True):
			old_channel_names.append(channel["name"])

		for channel in self.config["channels"]:
			new_channel_names.append(channel["name"])

		for channel_name in old_channel_names:
			if channel_name not in new_channel_names:
				print("deleting built-in channel %s" % channel_name)
				self.db.delete_channel(channel_name)

	def reload_config(self):
		was_irc_enabled = self.config["enable_irc_sync_feature"]
		self.load_config()

		# create missing channels
		for channel in self.channels:
			if self.get_group_by_name(channel["name"]) == -1:
				index = self.conference_new()
				self.conference_set_title(index, channel["name"].encode("utf-8"))

		print("config reloaded")

		# update IRC sync
		if self.config["enable_irc_sync_feature"] and not was_irc_enabled:
			self.start_irc_client()
		elif not self.config["enable_irc_sync_feature"] and was_irc_enabled:
			print("quitting IRC...")
			self.irc.quit()
		elif self.config["enable_irc_sync_feature"] and was_irc_enabled:
			self.irc.reload_config = True
