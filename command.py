class Command(object):

	@staticmethod
	def parse(core, message, friendId):

		response = ""

		if message == "help":
			response = "Commands:\n\
help\n\
list\n\
join <channel_name>\n\
log <channel_name>\n\
create <channel_name> [topic]\n\
create_audio <channel_name> [topic]"

		elif message.startswith("list"):
			rows = core.db.get_channels()

			response = ""
			for row in rows:
				id = row[0]
				topic = row[1]
				is_audio = row[2]
				#TODO: display if channel supports audio
				response += "%s   %s   %s" % (id, topic, "\n")

		elif message.startswith("join ") or message.startswith("invite "):
			split_array = message.split(" ")
			channel_name = split_array[1]

			for group in core.conference_get_chatlist():
				group_name = core.conference_get_title(group)
				if group_name == channel_name:
					core.conference_invite(friendId, group)
					break

		elif message.startswith("log "):
			split_array = message.split(" ")
			channel_name = split_array[1]
			log = core.db.get_log(channel_name)

			response = ""
			for row in log:
				response += row[0] + "\n"

		elif message.startswith("create "):
			split_array = message.split(" ")
			num_arguments = len(split_array)
			is_name_provided = False

			if num_arguments >= 2:
				channel_name = split_array[1]
				is_name_provided = True

			if num_arguments >= 3:
				topic = split_array[2]
			else:
				topic = ""

			if is_name_provided:
				core.db.create_channel(channel_name, topic, core.friend_get_public_key(friendId))
				group = core.conference_new()
				core.conference_set_title(group, channel_name)

				response = "channel %s created" % channel_name
			else:
				response = "error: channel name was not provided"

		elif message.startswith("create_audio "):
			message = "this feature is not supported yet"

		else:
			message = "unknown command"
			return message

		return response
