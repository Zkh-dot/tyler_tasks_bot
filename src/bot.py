import telebot
from telebot import types
import json
from models import sql_tables, async_to_sync
from queue import Queue
from logger import SingleLogger
from sys import exit
from copy import deepcopy

with open('./src/config.json', 'r', encoding='utf-8') as conf: 
    config = json.load(conf)    

sql_model = sql_tables()
logger = SingleLogger().get_logger()
tasks = Queue()
task = ""

markup=types.ReplyKeyboardMarkup(resize_keyboard=True)
markup.add(types.KeyboardButton("Выполнил"))
markup.add(types.KeyboardButton("Отменить выполненное"))
markup.add(types.KeyboardButton("Рейтинг"))
markup.add(types.KeyboardButton("Сколько сегодня"))

admin_markup = deepcopy(markup)
# admin_markup.add(types.KeyboardButton("Следующее задание"))
admin_markup.add(types.KeyboardButton("Посчитать"))
    
token = config['token']
bot=telebot.TeleBot(token)

def is_admin(message):
    return message.chat.id in config['admins']

@bot.message_handler(commands=['start', 'help'])
def start_message(message):
    if is_admin(message):
        logger.debug(f"{message.chat.id} is admin")
        bot.send_message(message.chat.id, config['messages']['start'], reply_markup=admin_markup)
    else:
        bot.send_message(message.chat.id, config['messages']['start'], reply_markup=markup)
        
    if async_to_sync(sql_model.add_user(message.chat.id, message.chat.username)):
        logger.warning(f"user {message.chat.id} loged in")
        bot.send_message(message.chat.id, config['messages']['welcome'], reply_markup=markup)

@bot.message_handler(commands=['stop'])
def stop_message(message):
    if is_admin(message):
        bot.send_message(message.chat.id, 'Выключаюсь', reply_markup=admin_markup)
        exit(0)

@bot.message_handler(content_types='text')
def message_reply(message):
    logger.info(f"{message.text} from {message.chat.id}")
    if message.text == "Посчитать" and is_admin(message):
        if not async_to_sync(sql_model.calculate_score()):
            logger.info("calculated on empty queue")
        bot.send_message(message.chat.id, config['messages']['confirm'])
        if tasks.empty():
            for id in config['admins']:
                bot.send_message(id, config['messages']['empty_queue'])
        else:
            task = tasks.get()
            for id in async_to_sync(sql_model.all_players()):
                bot.send_message(id, f"Новое задание\n{task}")
        
    if message.text == "Выполнил":
        async_to_sync(sql_model.complete(message.chat.id))
        bot.send_message(message.chat.id, config['messages']['counted'])
    
    if message.text == "Отменить выполненное":
        async_to_sync(sql_model.delete(message.chat.id))
        bot.send_message(message.chat.id, config['messages']['confirm'])

    if message.text == "Рейтинг":
        score = async_to_sync(sql_model.users_score())
        score_line = '\n'.join([
            f"{index + 1}. {x[0]} : {x[1]}" for index, x in enumerate(score)
        ])
        bot.send_message(message.chat.id, score_line)
        
    if message.text.split()[0] == "Задание" and is_admin(message):
        tasks.put(' '.join(message.text.split()[1:]))
        bot.send_message(message.chat.id, config['messages']['confirm'])
        
        
        
    if message.text == "Сколько сегодня":
        bot.send_message(message.chat.id, async_to_sync(sql_model.done_today(message.chat.id)))

bot.infinity_polling()


bot.infinity_polling()