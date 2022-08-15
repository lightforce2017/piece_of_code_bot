import os
import re
from datetime import datetime

from aiogram import types
from aiogram.dispatcher.storage import FSMContext
from dotenv import load_dotenv
import pandas as pd

from config import weight_unit, currency
from filters import *
from keyboards import ListOfButtons
from main import bot, dp
from states import Form


# общая стоимость заказа в корзине в заданной валюте
total = 0

# список препаратов в корзине
order = []

# подготовка загрузки переменных
load_dotenv()

# загрузка сообщений бота
df = pd.read_csv(os.environ.get('MSG_LIST'), sep=";", encoding="cp1251")


async def send_to_admin(*args):
    """Первый запуск бота на сервере"""

    print('Бот запущен')


def normalize_pot(text):
    """Автоисправление введенной пользователем потенции

    Args:
        text (str[1]): символ, введенный пользователем

    Returns:
        str[1]: символ из подготовленного списка вариантов
    """
    rep = {
        "x": "X",
        "х": "X",
        "Х": "X",
        "c": "",
        "C": "",
        "с": "",
        "С": "",
        "m": "M",
        "м": "M",
        "М": "M"
    }  # замена 1-го символа на 2-й
    rep = dict((re.escape(k), v) for k, v in rep.items())
    pattern = re.compile("|".join(rep.keys()))
    text = pattern.sub(lambda m: rep[re.escape(m.group(0))], text)
    return text


def find_prep(name, filename):
    """Поиск препарата по названию 'name' в файле 'filename'

    Args:
        name (str): название препарата или часть названия
        filename (str): локальный путь к файлу с расширением XLS|XLSX

    Returns:
        list: список препаратов, содержащих строку name 
    """
    df = pd.read_excel(filename)
    df2 = df['Наименование']
    sub = name
    df2.dropna(inplace=True)
    return df2[df2.str.contains(sub, case=False)].tolist()


def get_type(name, filename):
    """Получение типа препарата

    Args:
        name (str): название препарата
        filename (str): локальное имя файла с расширением XLS|XLSX

    Returns:
        str: тип препарата: mono (монопрепарат) или shus (соль Шусслера)
    """
    df = pd.read_excel(filename)
    df2 = df['Наименование']
    sub = name
    df2.dropna(inplace=True)
    m = len(df2[df2.str.contains(sub, case=False)].tolist())
    if m > 0:
        return 'shus'
    else:
        return 'mono'


def is_correct_phone_number(phone):
    """Проверка корректности введенного номера телефона

    Args:
        phone (str): номер телефона в виде числа 
        с наличием либо отсутствием знака "+" перед ним

    Returns:
        bool: корректность введенного номера телефона
    """
    p = str(phone)

    status = True
    # проверка на ввод кода номера Казахстана
    if p[0:2] != '+7':
        if p[0] != '8':
            status = False
        else:  # телефон начинается с 8
            status = True
    else:  # телефон начинается с +7
        # удаление лишних скобок для подсчета цифр
        pp = p.replace('(', '').replace(')', '')
        # номер телефона имеет разрешенное количество цифр
        if (len(pp) >= 9 and len(pp) <= 13):
            status = True  # всего цифр 9..13
        else:
            status = False  # всего цифр <9 или >13

    return status


@dp.message_handler(commands=["start"])
async def start(message: Message, state: FSMContext):
    """Команда /start
    Отображает клавиатуру для выбора действия
    """
    #text = "Выберите категорию"
    text = df[df['name'] == "main_menu_text"]['ru'].values[0]
    keyboard = ListOfButtons(
        text=["Купить", "О препаратах", "Стоимость",
              "О доставке", "Где мы находимся"],
        align=[1, 2, 2]
    ).reply_keyboard
    # Ожидание нажатия кнопки с командой на клавиатуре
    await message.reply(text=text, reply_markup=keyboard)



@dp.message_handler(state=Form.Start)
async def start(message: Message, state: FSMContext):
    """Бот в стартовом состоянии"""

    # "Выберите категорию"
    text = df[df['name'] == "main_menu_text"]['ru'].values[0]
    keyboard = ListOfButtons(
        text=["Купить", "О препаратах", "Стоимость",
              "О доставке", "Где мы находимся"],
        align=[1, 2, 2]
    ).reply_keyboard
    await message.reply(text=text, reply_markup=keyboard)


@dp.message_handler(Button("Купить"))
async def btn5(message: Message):
    """Нажатие кнопки "Купить" """

    # "Введите название препарата, который хотите заказать."
    ms = df[df['name'] == "input_item_title"]['ru'].values[0] + "\n"

    # "Название препарата должно быть больше 3 символов"
    ms += df[df['name'] == "need_more_than_3s"]['ru'].values[0] + "\n\n"

    # "Для отмены поиска препарата напишите <b>отмена</b> и отправьте боту"
    ms += df[df['name'] == "for_cancel"]['ru'].values[0]

    await message.reply(ms)
    await Form.NameP.set()


@dp.message_handler(Button("О препаратах"))
async def btn1(message: Message):
    """ Нажатие кнопки "О препаратах" """

    # Информация о сайте аптеки
    ms = df[df['name'] == "about_us"]['ru'].values[0]
    await message.reply(ms)


@dp.message_handler(Button("Стоимость"))
async def btn2(message: Message):
    """ Нажатие кнопки "Стоимость" """

    # text = "Стоимость препарата зависит от его формы и веса"
    text = df[df['name'] == "cost_text"]['ru'].values[0]

    # "Вас интересует монопрепарат или комплексон?"
    btn_txt = df[df['name'].isin(['mono', 'shus'])]['ru'].tolist()
    keyboard = ListOfButtons(
        # ["монопрепарат", "комплексон"],
        text=btn_txt,
        callback=["mono", "shus"],
        align=[2]
    ).inline_keyboard
    await message.reply(text=text, reply_markup=keyboard)


@dp.callback_query_handler(Button("mono"))
async def с_btnm(call: CallbackQuery):
    await call.message.edit_reply_markup()
    """Нажатие внутренней кнопки mono 
    после нажатия кнопки "Стоимость"
    """

    cb = ["6", "12", "30", "200", "1M", "10M", "6X", "9X", "12X"]
    cb2 = ["price " + s for s in cb]

    # "Монопрепарат.
    # Выберите потенцию:"
    ms = df[df['name'] == "mono_choose_potention"]['ru'].values[0]
    keyboard = ListOfButtons(
        text=["6C", "12C", "30C", "200C", "1M", "10M", "6X", "9X", "12X"],
        callback=cb2,
        align=[3, 3, 3]
    ).inline_keyboard
    await call.message.reply(text=ms, reply_markup=keyboard)


