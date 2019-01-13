import os
from dotenv import load_dotenv
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton
import time
from random import randint
import sqlite3

def get_token(path = os.getcwd()):
    """ gets token from .env """

    path += "\\.env"
    load_dotenv(path)
    token = os.environ.get("token")
    return token

class User():
    def __init__(self, username):
        self.username = username
        self.score = 0
        self.current_lang_path = ""

        self.conn = sqlite3.connect("users.db")
        self.cursor = self.conn.cursor()

        # creating table if don't have one
        try:
            self.conn.execute("CREATE TABLE Users (username STRING UNIQUE, score INTEGER, current_lang_path STRING)")
            self.conn.commit()
        except:
            pass

        # adding stats about new user into db
        try:
            sql = "INSERT INTO Users (username, score, current_lang_path) VALUES (?, ?, ?)"
            self.conn.execute(sql, (self.username, self.score, self.current_lang_path))
            self.conn.commit()
        except:
            pass

        self.languages = [
            "English", "Portuguese", "Danish", "Dutch", "French", "German", "Icelandic", "Italian", "Japanese",
            "Korean", "Norwegian", "Polish", "Romanian", "Russian", "Spanish", "Swedish", "Turkish", "Welsh"
        ]

    def get_score(self):
        """ returns score of user from database """

        sql = "SELECT score FROM Users WHERE username = '" + self.username + "'"
        self.cursor.execute(sql)
        return self.cursor.fetchall()[0][0]

    def increase_score(self):
        """ increases score of a user by 1 """

        old_score = self.get_score()
        new_score = old_score + 1
        sql = "UPDATE Users SET score = ? WHERE username = ?"
        self.conn.execute(sql, (new_score, self.username))
        self.conn.commit()

    def get_lang_path(self):
        """ returns current_lang_path of user from database """

        sql = "SELECT current_lang_path FROM Users WHERE username = '" + self.username + "'"
        self.cursor.execute(sql, )
        return self.cursor.fetchall()[0][0]

    def get_lang(self):
        """ returns current users language based on path stored in database """

        path = self.get_lang_path()
        for language in self.languages:
            if language in path:
                return language

    def set_lang_path(self, new_lang_path):
        """ updates current_lang_path in database """

        sql = "UPDATE Users SET current_lang_path = ? WHERE username = ?"
        self.conn.execute(sql, (new_lang_path, self.username))
        self.conn.commit()

    def get_top(self):
        """ returns usernames of 10 users with gratest score parameter """

        sql = "SELECT username FROM Users ORDER BY score DESC LIMIT 10"
        self.cursor.execute(sql)
        return self.cursor.fetchall()

class PolyglotBot():
    def __init__(self, token):
        self.token = token
        self.bot = telepot.Bot(token)

    def choose_track(self, language):
        """ returns random track from specified folder (language argument) """

        current_dir = os.curdir
        path = os.path.join(current_dir, language)
        tracks = os.listdir(path)
        track_num = randint(0, len(tracks) - 1)
        return tracks[track_num]

    def choose_language(self):
        """ returns one of the languages from folder "audio" """

        current_dir = os.curdir
        path = os.path.join(current_dir, "audio")
        languages = os.listdir(path)
        language_num = randint(0, len(languages) - 1)
        return languages[language_num]

    def choose_audio(self):
        """ returns path to the random track in random language """

        language = self.choose_language()
        track = self.choose_track(os.path.join("audio",  language))
        path = os.path.join("audio", language, track)
        return path

    def genrate_markup(self, correct_language):
        """ returns ReplyKeyboardMarkup which will be set after track will be sent by bot """

        rand_langs = []
        languages_copy = self.user.languages[:] # copying array by reference
        for i in range(4):
            lang_index = randint(0, len(languages_copy) - 1)
            lang = languages_copy[lang_index]
            rand_langs.append(lang)
            languages_copy.pop(lang_index)

        if correct_language not in rand_langs:
            correct_language_index = randint(0, 3)
            rand_langs[correct_language_index] = correct_language

        markup = ReplyKeyboardMarkup(
            keyboard = [
                [KeyboardButton(text = rand_langs[0]), KeyboardButton(text = rand_langs[1])],
                [KeyboardButton(text = rand_langs[2]), KeyboardButton(text = rand_langs[3])],
            ]
        )
        return markup

    def send_track(self, chat_id):
        """ checks current track, user needs to guess, in db
            if track path is specified in db, bot sends tracks
            if track path isn't specified, bot generates it, adds to db and sends to user
        """

        path = self.user.get_lang_path()
        if path == "":
            path = self.choose_audio()
            self.user.set_lang_path(path)

        message_text = "Guess this!"
        correct_language = self.user.get_lang()
        markup = self.genrate_markup(correct_language)
        self.bot.sendMessage(chat_id, message_text, reply_markup = markup)

        self.bot.sendAudio(chat_id, open(path, "rb"))

    def check_answer(self, chat_id, answer):
        """ checks if users answer is correct
            if answer is correct, bot adds 1 score to user and sets new track to guess
            if answer is incorrect, bot sends message where tells that answer is incorrect and offers new track to guess
        """

        language = self.user.get_lang()
        if answer == language:
            self.user.increase_score()

            message_text = "Correct!"
            self.bot.sendMessage(chat_id, message_text)

            self.user.set_lang_path("") # resets current_lang_path in database
            self.send_track(chat_id)
        else:
            message_text = "You answer is incorrect. Try again."
            self.bot.sendMessage(chat_id, message_text)

    def handle_start(self, msg):
        """ handles /start

            1) Sending start message
            2) Creating new user
            3) Sending track user need to guess
        """

        chat_id = msg["chat"]["id"]

        # sending start message
        message_text = "Hey there! I am PolyglotBot. Do you want to play a game? You need to guess language of audio I send to you. Let's start."
        self.bot.sendMessage(chat_id, message_text)

        # creating new user
        username = msg["chat"]["username"]
        self.user = User(username)

        # sending track to guess
        self.send_track(chat_id)

    def handle_leaderboard(self, chat_id):
        """ handles /leaderboard """

        message_text = ""
        top = self.user.get_top()
        for user in top:
            message_text += str(user[0]) + "\n"
        self.bot.sendMessage(chat_id, message_text)

    def handle_message(self, msg):
        """ handles incoming messages """

        _, chat_type, chat_id = telepot.glance(msg)

        if chat_type != "private":
            message_text = "You can play only in private chats."
            self.bot.sendMessage(chat_id, message_text)
        else:
            # if message is not a command we will perceive it as attempt to guess the language
            if msg["text"] == "/start":
                self.handle_start(msg)
            elif msg["text"] == "/leaderboard":
                self.handle_leaderboard(chat_id)
            else:
                self.check_answer(chat_id, msg["text"])

    def run(self):
        """ runs our bot :) """

        MessageLoop(self.bot, self.handle_message).run_as_thread()
        while True:
            time.sleep(5)

# getting TOKEN from .env
token = get_token()

# creating bot and running it
polyglot_bot = PolyglotBot(token)
polyglot_bot.run()
