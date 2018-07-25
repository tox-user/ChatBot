# -*- coding: utf-8 -*-

HELP_MESSAGE = "Commands:\n\
%s\n\
Channel commands:\n\
%s"
CHANNEL_HELP_MESSAGE = "available channel commands: %s"
UNKNOWN_COMMAND_MESSAGE = "unknown command - type help for a list of commands"

COMMANDS = ["help", "id", "list", "join", "log", "create <channel_name> [topic]", "create_audio <channel_name> [topic]"]
IRC_COMMANDS = ["help", "id", "list", "log"]
CHANNEL_COMMANDS = ["!help", "!id", "!info", "!users"]

class Command(object):

	@staticmethod
	def parse(core, message, friend_id):

		response = ""

		if message == "help":
			response = Command.get_help_response()

		elif message.startswith("id"):
			response = Command.get_id_response(core)

		elif message.startswith("list"):
			response = Command.get_list_response(core)

		elif message.startswith("join ") or message.startswith("invite "):
			# TODO: notify when channel doesn't exist
			split_array = message.split(" ")
			channel_name = split_array[1]

			for group in core.conference_get_chatlist():
				group_name = core.conference_get_title(group)
				if group_name == channel_name:
					core.conference_invite(friend_id, group)
					break

		elif message.startswith("log "):
			# TODO: notify when channel doesn't exist
			response = Command.get_log_response(core, message)

		elif message.startswith("create ") or message.startswith("create_audio "):
			split_array = message.split(" ")
			num_arguments = len(split_array)
			is_name_provided = False

			if num_arguments >= 2:
				channel_name = split_array[1]
				is_name_provided = True

			topic = ""
			if num_arguments >= 3:
				for i in range(len(split_array)):
					if i >= 2:
						topic += split_array[i] + " "

				topic.rstrip(" ")

			if is_name_provided:
				is_audio = 0
				if message.startswith("create_audio "):
					is_audio = 1

				error = core.db.create_channel(channel_name, topic, is_audio, core.friend_get_public_key(friend_id))
				if error == "":
					group = core.conference_new()
					core.conference_set_title(group, channel_name)

					response = "channel %s created" % channel_name
				else:
					response = error
			else:
				response = "error: channel name was not provided"

		else:
			response = UNKNOWN_COMMAND_MESSAGE


		return response.encode("utf-8")

	@staticmethod
	def parse_channel(core, message, group_name):
		response = ""
		if message.startswith("!help"):
			response = Command.get_channel_help_response()

		elif message.startswith("!id"):
			response = Command.get_id_response(core)
		
		elif message.startswith("!info"):
			irc_channel = core.irc.get_connected_irc_channel(group_name)

			if irc_channel != "":
				response = "this channel is currently connected to %s IRC channel" % irc_channel
			else:
				response = "this channel is not connected to IRC"

		elif message.startswith("!users"):
			irc_channel = core.irc.get_connected_irc_channel(group_name)

			if irc_channel != "":
				core.irc.get_channel_users(irc_channel)
			else:
				response = "this channel is not connected to IRC"


		return response.encode("utf-8")

	@staticmethod
	def parse_irc(irc, target, message_text):
		response = ""

		if message_text.startswith("help"):
			response = Command.get_help_response(True)

		elif message_text.startswith("id"):
			response = Command.get_id_response(irc.core)

		elif message_text.startswith("list"):
			response = Command.get_list_response(irc.core, irc.db)

		elif message_text.startswith("log"):
			response = Command.get_log_response(irc.core, message_text, irc.db)

		else:
			response = UNKNOWN_COMMAND_MESSAGE


		return response.encode("utf-8")

	@staticmethod
	def parse_irc_channel(irc, target, message_text):
		response = ""

		if message_text.startswith("!help"):
			response = Command.get_channel_help_response()

		elif message_text.startswith("!id"):
			response = Command.get_id_response(irc.core)

		elif message_text.startswith("!info"):
			tox_channel = irc.get_connected_tox_channel(target)
			response = "this channel is currently connected to %s Tox channel on ChatBot" % tox_channel

		elif message_text.startswith("!users"):
			tox_channel = irc.get_connected_tox_channel(target)
			users = irc.core.get_group_peers(tox_channel)
			num_users = len(users)

			response = "%d users in %s Tox channel: " % (num_users, tox_channel)
			for user in users:
				response += user + ", "

			response = response.rstrip(", ")
			if num_users <= 0:
				response = response.rstrip(": ")


		return response.encode("utf-8")

	@staticmethod
	def get_id_response(core):
		return "my Tox ID is: %s" % core.self_get_address()

	@staticmethod
	def get_list_response(core, db=False):
		if not db:
			db = core.db

		response = ""
		channels = core.get_channels(db)

		for channel in channels:
			type = u"⌨"
			if channel["is_audio"]:
				type = u"🎧"

			topic = channel["topic"]
			if topic and topic != "":
				topic = u"\"%s\"" % topic

			response += u"%s %s   %s   \n" % (type, channel["name"], topic)

		return response

	@staticmethod
	def get_log_response(core, message, db=False):
		if not db:
			db = core.db

		response = ""

		split_array = message.split(" ")
		if len(split_array) >= 2:
			channel_name = split_array[1]
			rows = db.get_log(channel_name)

			for row in rows:
				response += row[0] + "\n"

		return response

	@staticmethod
	def get_help_response(is_irc=False):
		commands = COMMANDS
		if is_irc:
			commands = IRC_COMMANDS

		commands_string = ""
		for command in commands:
			commands_string += "%s\n" % command

		channel_commands_string = ""
		for command in CHANNEL_COMMANDS:
			channel_commands_string += "%s\n" % command

		return HELP_MESSAGE % (commands_string, channel_commands_string)
	
	@staticmethod
	def get_channel_help_response():
		commands_string = ""
		for command in CHANNEL_COMMANDS:
			commands_string += "%s " % command

		commands_string = commands_string.rstrip(" ")
		return CHANNEL_HELP_MESSAGE % commands_string
