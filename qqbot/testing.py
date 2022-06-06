from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, callbackcontext


def sendQ(update, context):
	print("Got update")
	keyboard = [
		InlineKeyboardButton("This Works", callback_data="opt1|q143"),
		InlineKeyboardButton("This Too", callback_data="opt2|q143"),
		InlineKeyboardButton("This Not", callback_data="opt3|q143")
	]
	update.message.reply_text('Choose dis', reply_markup=InlineKeyboardMarkup.from_column(keyboard))


## Update stucture
# {
# 	'update_id': 76245581,
# 	'callback_query': {
# 		'id': '44269347452163626',
# 		'chat_instance': '-7666065834876445125',
# 		'message': {
# 			'message_id': 453,
# 			'date': 1590674445,
# 			'chat': {
# 				'id': 10307260,
# 				'type': 'private',
# 				'username': 'severeOC',
# 				'first_name': 'V.',
# 				'last_name': 'van Hausen'
# 			},
# 			'text': 'Choose dis',
# 			'entities': [],
# 			'caption_entities': [],
# 			'photo': [],
# 			'new_chat_members': [],
# 			'new_chat_photo': [],
# 			'delete_chat_photo': False,
# 			'group_chat_created': False,
# 			'supergroup_chat_created': False,
# 			'channel_chat_created': False,
# 			'reply_markup': {
# 				'inline_keyboard': [
# 					[{
# 						'text': 'This Works',
# 						'callback_data': 'opt1'
# 					}, {
# 						'text': 'This Too',
# 						'callback_data': 'opt2'
# 					}],
# 					[{
# 						'text': 'This Not',
# 						'callback_data': 'opt3'
# 					}]
# 				]
# 			},
# 			'from': {
# 				'id': 984067985,
# 				'first_name': 'QQBot_Dev',
# 				'is_bot': True,
# 				'username': 'QQDevbot'
# 			}
# 		},
# 		'data': 'opt2',
# 		'from': {
# 			'id': 10307260,
# 			'first_name': 'V.',
# 			'is_bot': False,
# 			'last_name': 'van Hausen',
# 			'username': 'severeOC',
# 			'language_code': 'en'
# 		}
# 	},
# 	'_effective_user': {
# 		'id': 10307260,
# 		'first_name': 'V.',
# 		'is_bot': False,
# 		'last_name': 'van Hausen',
# 		'username': 'severeOC',
# 		'language_code': 'en'
# 	},
# 	'_effective_chat': {
# 		'id': 10307260,
# 		'type': 'private',
# 		'username': 'severeOC',
# 		'first_name': 'V.',
# 		'last_name': 'van Hausen'
# 	},
# 	'_effective_message': {
# 		'message_id': 453,
# 		'date': 1590674445,
# 		'chat': {
# 			'id': 10307260,
# 			'type': 'private',
# 			'username': 'severeOC',
# 			'first_name': 'V.',
# 			'last_name': 'van Hausen'
# 		},
# 		'text': 'Choose dis',
# 		'entities': [],
# 		'caption_entities': [],
# 		'photo': [],
# 		'new_chat_members': [],
# 		'new_chat_photo': [],
# 		'delete_chat_photo': False,
# 		'group_chat_created': False,
# 		'supergroup_chat_created': False,
# 		'channel_chat_created': False,
# 		'reply_markup': {
# 			'inline_keyboard': [
# 				[{
# 					'text': 'This Works',
# 					'callback_data': 'opt1'
# 				}, {
# 					'text': 'This Too',
# 					'callback_data': 'opt2'
# 				}],
# 				[{
# 					'text': 'This Not',
# 					'callback_data': 'opt3'
# 				}]
# 			]
# 		},
# 		'from': {
# 			'id': 984067985,
# 			'first_name': 'QQBot_Dev',
# 			'is_bot': True,
# 			'username': 'QQDevbot'
# 		}
# 	}
# }
# block


def readA(update, context):
	query = update.callback_query
	print(query)
	print("Got answer %s to question %s from user %s" % (query.data, query.message.text, query.message.chat.id))

	query.answer()
	query.edit_message_text(text="Selected option: {}".format(query.data))


def main():
	# token 
	token = 'REMOVED'
	# developer token
	updater = Updater(token, use_context=True)

	dp = updater.dispatcher
	dp.add_handler(CommandHandler('test', sendQ))
	dp.add_handler(CallbackQueryHandler(readA))

	updater.start_polling()
	updater.idle()


# bot = telegram.Bot(token)


if __name__ == '__main__':
	main()
