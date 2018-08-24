import sqlite3
from config import Config

CHANNEL_ALREADY_EXISTS_ERROR = "error: channel already exists"

class DB():
	def __init__(self):
		self.config = Config().config
		self.db_name = self.config["database_file_name"]
		self.db = sqlite3.connect(self.db_name)
		self.cursor = self.db.cursor()

	def init_data(self):
		self.cursor.execute('CREATE TABLE IF NOT EXISTS channels(id TEXT PRIMARY KEY, topic TEXT, is_audio INTEGER DEFAULT 0, is_built_in INTEGER DEFAULT 0)')
		self.cursor.execute('CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY, message TEXT NOT NULL, date DATETIME DEFAULT CURRENT_TIMESTAMP, channel_id TEXT NOT NULL)')
		self.cursor.execute('CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, channel_id TEXT NOT NULL)')
		self.cursor.execute('CREATE TABLE IF NOT EXISTS irc_channels(id INTEGER PRIMARY KEY, channel_id TEXT NOT NULL, irc_network TEXT NOT NULL, irc_channel TEXT NOT NULL)')
		self.cursor.execute('CREATE TABLE IF NOT EXISTS autoinvite_list(id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, channel_id TEXT NOT NULL)')

		self.db.commit()

		for channel in self.config["channels"]:
			name = channel["name"]
			is_audio = channel["is_audio_channel"]
			topic = ""
			admin = ""
			irc_network = None
			irc_channel = None

			if "topic" in channel.keys():
				topic = channel["topic"]
			if "irc_network" in channel.keys():
				irc_network = channel["irc_network"]
			if "irc_channel" in channel.keys():
				irc_channel = channel["irc_channel"]
			if "admin_public_key" in channel.keys():
				admin = channel["admin_public_key"]

			if is_audio:
				is_audio = 1
			else:
				is_audio = 0

			if irc_network and irc_channel:
				self.create_channel(name, topic, is_audio, admin, True, irc_network, irc_channel)
			else:
				self.create_channel(name, topic, is_audio, admin, True)

	def create_channel(self, name, topic, is_audio=0, admin_pk="", is_built_in=False, irc_network="", irc_channel=""):
		name = name.decode("utf-8")
		topic = topic.decode("utf-8")
		irc_channel = irc_channel.decode("utf-8")

		if is_built_in:
			is_built_in = 1
		else:
			is_built_in = 0

		self.cursor.execute("SELECT id FROM channels WHERE id = ?", (name,))
		rows = self.cursor.fetchall()

		if not rows or len(rows) <= 0:
			self.cursor.execute("INSERT INTO channels (id, topic, is_audio, is_built_in) VALUES (?, ?, ?, ?)", (name, topic, is_audio, is_built_in,))
		else:
			return CHANNEL_ALREADY_EXISTS_ERROR

		if admin_pk != "":
			self.cursor.execute("SELECT id FROM admins WHERE user_id = ? AND channel_id = ?", (admin_pk, name,))
			rows = self.cursor.fetchall()
			if not rows or len(rows) <= 0:
				self.cursor.execute("INSERT INTO admins (user_id, channel_id) VALUES (?, ?)", (admin_pk, name,))

		if irc_network != "" and irc_channel != "":
			self.cursor.execute("SELECT id FROM irc_channels WHERE channel_id = ? AND irc_network = ? AND irc_channel = ?", (name, irc_network, irc_channel,))
			rows = self.cursor.fetchall()
			if not rows or len(rows) <= 0:
				self.cursor.execute("INSERT INTO irc_channels (channel_id, irc_network, irc_channel) VALUES (?, ?, ?)", (name, irc_network, irc_channel,))

		self.db.commit()
		return ""

	def delete_channel(self, name):
		name = name.decode("utf-8")
		self.cursor.execute("DELETE FROM channels WHERE id = ?", (name,))
		self.cursor.execute("DELETE FROM irc_channels WHERE channel_id = ?", (name,))
		self.cursor.execute("DELETE FROM logs WHERE channel_id = ?", (name,))
		self.cursor.execute("DELETE FROM admins WHERE channel_id = ?", (name,))
		self.cursor.execute("DELETE FROM autoinvite_list WHERE channel_id = ?", (name,))
		self.db.commit()

	def log_message(self, group_name, message):
		group_name = group_name.decode("utf-8")
		message = message.decode("utf-8")

		self.cursor.execute("INSERT INTO logs (message, channel_id) VALUES (?, ?)", (message, group_name,))
		self.db.commit()

	def get_log(self, group_name):
		group_name = group_name.decode("utf-8")
		return self.cursor.execute("SELECT message FROM (SELECT * FROM logs WHERE channel_id = ? ORDER BY date DESC LIMIT 500) ORDER BY date ASC;", (group_name,))

	def close(self):
		self.db.close()

	def get_channels(self, built_in_only=False):
		if not built_in_only:
			return self.cursor.execute("SELECT id, topic, is_audio, is_built_in FROM channels ORDER BY is_audio ASC")
		else:
			return self.cursor.execute("SELECT id, topic, is_audio, is_built_in FROM channels WHERE is_built_in = 1 ORDER BY is_audio ASC")

	def get_irc_channels(self):
		return self.cursor.execute("SELECT channel_id, irc_network, irc_channel FROM irc_channels")

	def toggle_autoinvite(self, user_id, channel_id):
		user_id = user_id.decode("utf-8")
		channel_id = channel_id.decode("utf-8")

		self.cursor.execute("SELECT * FROM autoinvite_list WHERE user_id = ? AND channel_id = ?", (user_id, channel_id,))
		rows = self.cursor.fetchall()

		is_invited = False
		if not rows or len(rows) <= 0:
			self.cursor.execute("INSERT INTO autoinvite_list (user_id, channel_id) VALUES (?, ?)", (user_id, channel_id,))
			is_invited = True
		else:
			self.cursor.execute("DELETE FROM autoinvite_list WHERE user_id = ? AND channel_id = ?", (user_id, channel_id,))

		self.db.commit()
		return is_invited

	def get_autoinvite_list(self, user_id):
		user_id = user_id.decode("utf-8")
		return self.cursor.execute("SELECT channel_id FROM autoinvite_list WHERE user_id = ? LIMIT 200", (user_id,))

	def is_channel_admin(self, user_public_key, channel_name):
		channel_name = channel_name.decode("utf-8")
		self.cursor.execute("SELECT * FROM admins WHERE user_id = ? AND channel_id = ?", (user_public_key, channel_name,))
		rows = self.cursor.fetchall()

		if not rows or len(rows) <= 0:
			return False
		else:
			return True
