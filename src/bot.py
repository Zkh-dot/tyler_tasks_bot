import telebot
from telebot import types
import json
from models import sql_tables
from queue import Queue

with open('config.json', 'r') as conf: 
    config = json.load(conf)    

sql_model = sql_tables()
tasks = Queue()
task = ""

markup=types.ReplyKeyboardMarkup(resize_keyboard=True)
markup.add(types.KeyboardButton("Выполнил"))
markup.add(types.KeyboardButton("Отменить выполненное"))
markup.add(types.KeyboardButton("Рейтинг"))
markup.add(types.KeyboardButton("Сколько сегодня"))

admin_markup = markup
admin_markup.add(types.KeyboardButton("Следующее задание"))
admin_markup.add(types.KeyboardButton("Посчитать"))
    
token = conf['token']
bot=telebot.TeleBot(token)

def is_admin(message):
    return message.chat.id in config['admins']

@bot.message_handler(commands=['start', 'help'])
def start_message(message):
    if is_admin(message):
        bot.send_message(message.chat.id, config['messages']['start'], reply_markup=admin_markup)
    else:
        bot.send_message(message.chat.id, config['messages']['start'], reply_markup=markup)
        
    if sql_model.add_user(message.chat.id, message.chat.username):
        bot.send_message(message.chat.id, config['messages']['welcome'], reply_markup=markup)

@bot.message_handler(content_types='text')
def message_reply(message):
    if message.text == "Посчитать" and is_admin(message):
        sql_model.calculate_score()
        bot.send_message(message.chat.id, config['messages']['confirm'])
        task = tasks.get()
        for id in sql_model.all_players():
            bot.send_message(id, f"Новое задание\n{task}")
        
    if message.text == "Выполнил":
        sql_model.complete(message.chat.id)
        bot.send_message(message.chat.id, config['messages']['confirm'])
    
    if message.text == "Отменить выполненное":
        sql_model.delete(message.chat.id)
        bot.send_message(message.chat.id, config['messages']['confirm'])

    if message.text == "Рейтинг":
        score = sql_model.users_score()
        score_line = '\n'.join([
            f"{index}. {x[0]} : {x[1]}" for index, x in enumerate(score)
        ])
        bot.send_message(message.chat.id, score_line)
        
    if message.text.split()[0] == "Задание" and is_admin(message):
        tasks.put(message.text.split()[1:])
        
        
    if message.text == "Сколько сегодня":
        bot.send_message(message.chat.id, sql_model.done_today(message.chat.id))

        
bot.infinity_polling()


bot.infinity_polling()