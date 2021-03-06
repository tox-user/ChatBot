import socket
import threading
from time import sleep
from persistence.db import DB
from persistence.config import Config
from bot.command import Command

# message type codes
NAMES_MESSAGE = 353
END_OF_NAMES = 366
MOTD_START = 375
MOTD = 372
MOTD_END = 376

MAX_MESSAGE_LEN = 450

class IRC(threading.Thread):
	def __init__(self, tox):
		threading.Thread.__init__(self)
		self.core = tox
		# TODO: replace with server for each channel
		self.server = "chat.freenode.net"
		self.nickname = self.core.config["irc_user_name"]
		self.quitting = False
		self.reload_config = False

	def connect(self):
		try:
			# TODO: use ssl
			self.sock.connect((self.server, 6667))
			# TODO: detect if name is taken
			user_string = u"USER %s %s %s %s \n" % (self.nickname, self.nickname, self.nickname, self.nickname)
			self.socket_send(user_string)
			self.set_nickname(self.nickname)

			if self.core.config["use_freenode_nickserv"]:
				identify_string = "PRIVMSG NickServ :IDENTIFY %s %s \n" % (self.nickname, self.core.config["freenode_nickserv_password"])
				self.socket_send(identify_string)

		except socket.timeout:
			print("ERROR: IRC connection timed out")
		except socket.error, error:
			print("ERROR: IRC socket error: %s" % error)

	def socket_send(self, string):
		try:
			self.sock.send(string.encode("utf-8"))
		except socket.timeout:
			print("ERROR: IRC connection timed out. Reconnecting...")
			self.sock.close()
			self.create_socket()
			sleep(1)
			self.connect_and_join()
		except socket.error, error:
			print("ERROR: IRC socket error: %s" % error)
		except:
			print("ERROR: IRC socket error")


	def set_nickname(self, nickname):
		self.nickname = nickname
		nick_string = u"NICK %s \n" % self.nickname
		self.socket_send(nick_string)

	def join_channel(self, channel):
		# TODO: notify when kicked or banned from channel
		self.socket_send(u"JOIN %s \n" % channel)

	def get_channel_users(self, channel):
		self.socket_send(u"NAMES %s \n" % channel)

	def connect_and_join(self):
		# TODO: connect to multiple servers
		#networks = []
		#for channel in self.channels:
			#if not channel.irc_network in networks:
				#networks.append(channel.irc_network)
				#self.connect(channel.irc_network)

		self.connect()

		for channel in self.channels:
			self.join_channel(channel["irc"])

	def ping_respond(self):
		self.socket_send(u"PONG \n")

	def send_message(self, target, message):
		# target can be channel name or username (then it's a private message)
		command = u"PRIVMSG %s :\n" % target
		message = message.decode("utf-8")
		messages = self.split_message(command, message)

		for msg_part in messages:
			text = u"PRIVMSG %s :%s\n" % (target, msg_part)
			self.socket_send(text)

	def split_message(self, command, original_message):
		converted_messages = []
		messages = self.split_message_on_new_line(original_message)

		for message in messages:
			while len(command + message) > MAX_MESSAGE_LEN:
				split_char = " "
				split_pos = message.rfind(split_char, 0, MAX_MESSAGE_LEN-1)

				if split_pos <= 0:
					split_pos = MAX_MESSAGE_LEN - 1

				new_message = message[:split_pos+1]
				converted_messages.append(new_message)
				message = message[split_pos:]

			converted_messages.append(message)

		return converted_messages

	def split_message_on_new_line(self, message):
		split_array = message.split("\n")
		return split_array

	def create_db(self):
		self.db = DB()

	def load_channels(self):
		self.channels = []
		rows = self.db.get_irc_channels()
		for row in rows:
			channel = row[0]
			irc_network = row[1]
			irc_channel = row[2]
			self.channels.append({"tox": channel, "irc": irc_channel, "irc_network": irc_network, "irc_users": []})

	def create_socket(self):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.settimeout(180)

	def run(self):
		#TODO: detect disconnects (notify users?) and reconnect
		self.create_db()
		self.create_socket()
		self.load_channels()
		self.connect_and_join()

		while not self.quitting:
			message = ""
			try:
				message = self.sock.recv(2048).decode("utf-8")
			except socket.timeout:
				print("ERROR: IRC connection timed out. Reconnecting...")
				self.sock.close()
				self.create_socket()
				sleep(1)
				self.connect_and_join()
			except socket.error, error:
				print("ERROR: IRC socket error: %s" % error)
			except:
				print("ERROR: IRC socket error")

			if message != "":
				self.parse(message)

			if self.reload_config:
				self.db.close()
				self.create_db()
				self.set_nickname(self.nickname)
				self.reload_config = False

		self.db.close()
		self.socket_send(u"QUIT \n")
		self.sock.close()
		print("disconnected from IRC")

	def parse(self, received_message):
		is_priv_message = False
		messages = received_message.split("\r\n")

		for message in messages:
			split_array = message.split(" ")

			if message.startswith("PING"):
				self.ping_respond()

			elif len(split_array) > 1:
				message_type = split_array[1]

				if message_type == "PRIVMSG":
					sender_username = message.split("!")[0][1:]
					message_info = message.split("PRIVMSG ", 1)[1].split(" :", 1)
					target = message_info[0]
					message_text = message_info[1]

					if target == self.nickname:
						is_priv_message = True
					else:
						tox_channel = self.get_bridged_tox_channel(target)
						formatted_message = "[%s]: %s" % (sender_username, message_text)
						is_message_sent = self.core.send_group_message(tox_channel, formatted_message)

						if not is_message_sent:
							self.log_irc_message(tox_channel, formatted_message)

					if is_priv_message:
						response = Command.parse_irc(self, target, message_text)
					else:
						response = Command.parse_irc_channel(self, target, message_text)

					if response != "":
						if is_priv_message:
							self.send_message(sender_username, response)
						else:
							self.send_message(target, response)

				elif message_type == str(NAMES_MESSAGE) and len(split_array) >= 5:
					target = split_array[4]
					channel = {}

					for cur_channel in self.channels:
						if cur_channel["irc"] == target:
							channel = cur_channel
							break

					for i in range(len(split_array)):
						if i < 5:
							continue

						user = split_array[i]
						if i == 5:
							user = split_array[i][1:]

						channel["irc_users"].append(user)

				elif message_type == str(END_OF_NAMES) and len(split_array) >= 4:
					target = split_array[3]
					channel = {}

					for cur_channel in self.channels:
						if cur_channel["irc"] == target:
							channel = cur_channel
							break

					tox_channel = self.get_bridged_tox_channel(target)
					num_users = len(channel["irc_users"])
					formatted_message = "%d users in %s IRC channel: " % (num_users, target)

					for user in channel["irc_users"]:
						formatted_message += "%s, " % user

					formatted_message = formatted_message.rstrip(", ")
					if num_users <= 0:
						formatted_message = formatted_message.rstrip(": ")

					self.core.send_group_message(tox_channel, formatted_message)
					channel["irc_users"] = []

				# TODO: don't print MOTD message
				#elif message_type == str(MOTD_START) or message_type == str(MOTD) or message_type == str(MOTD_END):
					#return

				print(message)

	def get_bridged_tox_channel(self, irc_channel):
		for channel in self.channels:
			if channel["irc"] == irc_channel.decode("utf-8"):
				return channel["tox"]

		return ""

	def get_bridged_irc_channel(self, group_name):
		for channel in self.channels:
			if channel["tox"] == group_name.decode("utf-8"):
				return channel["irc"]

		return ""

	def quit(self):
		self.quitting = True

	def log_irc_message(self, group_name, message):
		author_name = "[%s]: " % self.core.self_get_name()
		self.db.log_message(group_name, author_name + message)
