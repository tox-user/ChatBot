import sqlite3

class DB():
	def __init__(self):
		self.db_name = "chatbot.db"
		self.db = sqlite3.connect(self.db_name)
		self.cursor = self.db.cursor()
		self.cursor.execute('CREATE TABLE IF NOT EXISTS channels(id TEXT PRIMARY KEY, topic TEXT, is_audio INTEGER DEFAULT 0, admin_id TEXT)')
		self.cursor.execute('CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY, message TEXT, date DATETIME DEFAULT CURRENT_TIMESTAMP, channel_id, TEXT)')
		#TODO: autoinvite list
		#self.cursor.execute('CREATE TABLE IF NOT EXISTS autoinvite_list(id TEXT PRIMARY KEY)')

		self.db.commit()

		self.create_channel("tox", "general Tox chat", "0")
		self.create_channel("#toktok", "toxcore development channel", "0")

	def create_channel(self, name, topic, admin_pk):
		self.cursor.execute("SELECT id FROM channels WHERE id = ?", (name,))
		rows = self.cursor.fetchall()

		if not rows or len(rows) <= 0:
			self.cursor.execute("INSERT INTO channels (id, topic, admin_id) VALUES (?, ?, ?)", (name, topic, admin_pk,))
			self.db.commit()

	def create_audio_channel(self, name, topic, adminPk):
		pass

	def log_message(self, group_name, message):
		self.cursor.execute("INSERT INTO logs (message, channel_id) VALUES (?, ?)", (message, group_name,))
		self.db.commit()

	def get_log(self, group_name):
		return self.cursor.execute("SELECT message FROM logs WHERE channel_id = ? LIMIT 500", (group_name,))

	def close(self):
		self.db.close()

	def get_channels(self):
		return self.cursor.execute("SELECT id, topic, is_audio FROM channels")

