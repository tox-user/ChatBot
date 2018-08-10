import sqlite3

class DB():
	def __init__(self):
		self.db_name = "chatbot.db"
		self.db = sqlite3.connect(self.db_name)
		self.cursor = self.db.cursor()

	def init_data(self):
		self.cursor.execute('CREATE TABLE IF NOT EXISTS channels(id TEXT PRIMARY KEY, topic TEXT, is_audio INTEGER DEFAULT 0)')
		self.cursor.execute('CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY, message TEXT NOT NULL, date DATETIME DEFAULT CURRENT_TIMESTAMP, channel_id TEXT NOT NULL)')
		self.cursor.execute('CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, channel_id TEXT NOT NULL)')
		self.cursor.execute('CREATE TABLE IF NOT EXISTS irc_channels(id INTEGER PRIMARY KEY, channel_id TEXT NOT NULL, irc_network TEXT NOT NULL, irc_channel TEXT NOT NULL)')
		#self.cursor.execute('CREATE TABLE IF NOT EXISTS autoinvite_list(id INTEGER PRIMARY KEY NOT NULL, user_id TEXT NOT NULL, channel_id TEXT NOT NULL)')

		self.db.commit()

		self.create_channel("tox-public", "general Tox chat", 0, "", "chat.freenode.net", "#tox")
		self.create_channel("toktok", "toxcore development channel", 0, "", "chat.freenode.net", "#toktok")
		self.create_channel("offtopic", "everything unrelated to Tox")
		self.create_channel("public-audio-chat", "audio testing and general talks", 1)

	def create_channel(self, name, topic, is_audio=0, admin_pk="", irc_network="", irc_channel=""):
		self.cursor.execute("SELECT id FROM channels WHERE id = ?", (name,))
		rows = self.cursor.fetchall()

		if not rows or len(rows) <= 0:
			self.cursor.execute("INSERT INTO channels (id, topic, is_audio) VALUES (?, ?, ?)", (name, topic, is_audio,))
		else:
			return "ERROR: channel already exists"

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

	def log_message(self, group_name, message):
		self.cursor.execute("INSERT INTO logs (message, channel_id) VALUES (?, ?)", (message, group_name,))
		self.db.commit()

	def get_log(self, group_name):
		return self.cursor.execute("SELECT message FROM logs WHERE channel_id = ? LIMIT 500", (group_name,))

	def close(self):
		self.db.close()

	def get_channels(self):
		return self.cursor.execute("SELECT id, topic, is_audio FROM channels")

	def get_irc_channels(self):
		# TODO: sort audio channels at the bottom
		return self.cursor.execute("SELECT channel_id, irc_network, irc_channel FROM irc_channels")
