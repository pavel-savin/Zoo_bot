from aiogram import Router, Bot
from aiogram import types
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext   # Отслеживания вопроса
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile


from config import TOKEN, EMAIL, PHONE, WEBSITE, BOT_USERNAME, FEEDBACK_FORM
from questions import questions

import animals_info
from animals_info import animal_info
from animals_info import animal_images

bot = Bot(token=TOKEN)
router = Router()

# глобальные переменные
animals = animals_info.animals
current_question_index = 0

async def send_main_menu(chat_id: int, state: FSMContext, exclude: list[str] | None = None):
    """
    Отправляет меню с кнопками для перехода к другим функциям,
    исключая указанные пункты.
    """
    menu_actions = {
        "start": "Вернуться к старту",
        "info": "Наша цель",
        "share": "Поделиться результатом",
        "feedback": "Обратная связь",
        "restart": "Пройти викторину"
    }

    # Если exclude не None, исключаем все указанные пункты
    if exclude:
        for action_to_exclude in exclude:
            if action_to_exclude in menu_actions:
                del menu_actions[action_to_exclude]

    # Создаём кнопки
    inline_keyboard = [
        [types.InlineKeyboardButton(text=label, callback_data=f"menu:{action}")]
        for action, label in menu_actions.items()
    ]

    markup = types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    # Отправляем сообщение с кнопками
    menu_message = await bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)

    # Сохраняем id сообщения
    await state.update_data(menu_message_id=menu_message.message_id)


# обработчики команд
@router.message(Command('start', 'help'))
async def start(msg: Message, state: FSMContext):
    text = """ Тотемный компас: открой свой путь в <b>“Клуб друзей”</b>!

Как это работает?\n <b>Просто следуй этим шагам:</b>

1. Выбери тот ответ, который отражает твои чувства и предпочтения.
2. Будь честным с собой, ведь твой внутренний зверь уже готов раскрыться!
<b>Что тебя ждёт?</b> 

Пройдя викторину, ты узнаешь тотемное животное, которое будет олицетворять твою личность. 
Познакомься поближе с программой <b>“Клуб друзей” Московского зоопарка</b>, которая даст тебе возможность:

1. Почувствовать связь с животными зоопарка.
2. Помогать в их защите и уходе.
3. Пригласи друзей пройти викторину и узнать, кто является их тотемом! Делись результатами и впечатлениями о “Клубе друзей” и зоопарке в социальных сетях!
    """
    await bot.send_message(msg.chat.id, text, parse_mode='HTML')
    await send_main_menu(msg.chat.id, state, exclude=["start", "share"])


@router.message(Command('info'))
async def info(msg: Message, state: FSMContext):
    # Часть текста до изображения
    text_before = """
Основная цель Московского зоопарка — сохранение биоразнообразия планеты. 
Когда вы берёте животное под опеку, вы помогаете нам сохранять редкие виды и заботиться об их будущем.
"""
    file_path = 'images/selection/MSK.jpeg'

    text_after = f"""
Сейчас опекуны стали частью сообщества — <b>Клуб друзей Московского зоопарка</b>, 
где каждый может внести свой вклад в сохранение природы и участвовать в жизни зоопарка.

Не теряй времени, узнай как можешь помочь нашим опекунам!!!

Для связи:
📧 Электронная почта: <a href="mailto:{EMAIL}">{EMAIL}</a>  
📞 Телефон: <a href="tel:{PHONE.replace(' ', '').replace('-', '')}">{PHONE}</a>
🌐 Вебсайт: <a href="{WEBSITE}">{WEBSITE}</a>
"""
    await bot.send_message(msg.chat.id, text=text_before, parse_mode='HTML')
    photo = FSInputFile(file_path)
    await bot.send_photo(msg.chat.id, photo)
    await bot.send_message(msg.chat.id, text=text_after, parse_mode='HTML')
    await send_main_menu(msg.chat.id, state, exclude=["info"])



@router.message(Command('share'))
async def share_result(msg: Message, state: FSMContext):
    data = await state.get_data()
    if 'animals' in data:
        result = max(data['animals'], key=data['animals'].get)
        file_path = animal_images.get(result)
        
        if file_path:  # Проверяем, есть ли файл для животного
            photo = FSInputFile(file_path)  # Создаем объект FSInputFile для локального файла
            await bot.send_photo(
                msg.chat.id,
                photo,
                caption=(
                    'Поделись изображением в мессенджере - помоги остальным узнать о "Клубе друзей".\n\n'
                    f'Мое тотемное животное: {result}\n\n'
                    f'Присоединяйся к нашему боту: {BOT_USERNAME}'
                )
            )
        else:
            await bot.send_message(msg.chat.id, f"Изображение для '{result}' не найдено.")

    # Меню (исключаем "share")
    await send_main_menu(msg.chat.id, state, exclude=["share"])

# Google forms
@router.message(Command('feedback'))
async def get_feedback(msg: Message, state: FSMContext):
    file_path = 'images/selection/logo.jpg'
    await bot.send_photo(msg.chat.id, FSInputFile(file_path))
    text = f'Чтобы оставить отзыв о работе нашего бота, перейдите по ссылке:\n\n{FEEDBACK_FORM}'
    await bot.send_message(msg.chat.id, text)
    await send_main_menu(msg.chat.id, state, exclude=["feedback"])


@router.message(Command('restart'))
async def restart(msg: Message, state: FSMContext):
    await state.clear()
    await quiz(msg, state)

class QuizState(StatesGroup):
    waiting_for_answer = State()

# Логика викторины
@router.message(Command('quiz'))
async def quiz(msg: Message, state: FSMContext):
    await state.update_data(current_question_index=0,
                            animals={animal: 0 for animal in animals.keys()})
    await send_question(msg.chat.id, state, msg)

async def send_question(chat_id: int, state: FSMContext, msg: Message):
    data = await state.get_data()
    current_question_index = data.get('current_question_index', 0)
    if current_question_index < len(questions):
        question = questions[current_question_index]
        # Создание Inline-кнопок
        inline_keyboard_buttons = [
            [types.InlineKeyboardButton(text=option, callback_data=f"answer:{option}")]
            for option in question['options']
        ]
        inline_markup = types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard_buttons)
        # Удаляем предыдущее сообщение с вопросом (если оно существует)
        question_message_id = data.get('question_message_id')
        if question_message_id:
            try:
                await bot.delete_message(chat_id, question_message_id)
            except Exception:
                pass
        # Отправка нового вопроса
        sent_message = await bot.send_message(chat_id, question['question'], reply_markup=inline_markup)
        # Сохранение ID текущего сообщения с вопросом
        await state.update_data(question_message_id=sent_message.message_id)
        # Установить состояние ожидания ответа
        await state.set_state(QuizState.waiting_for_answer)
    else:
        await show_result(chat_id, state, msg)

@router.callback_query(lambda c: c.data.startswith("answer:"))
async def handle_inline_answer(callback_query: types.CallbackQuery, state: FSMContext):
    selected_option = callback_query.data.split(":")[1]
    # Получаем данные состояния
    data = await state.get_data()
    current_question_index = data.get('current_question_index', 0)
    if current_question_index < len(questions):
        question = questions[current_question_index]
        # Обновляем счётчики животных
        for animal in question['animal_mapping'].get(selected_option, []):
            data['animals'][animal] = data['animals'].get(animal, 0) + 1
        # Обновляем состояние
        await state.update_data(current_question_index=current_question_index + 1, animals=data['animals'])
        # Удаляем сообщение с кнопками
        try:
            await callback_query.message.delete()
        except Exception as e:
            pass
        # Переходим к следующему вопросу
        await send_question(callback_query.message.chat.id, state, callback_query.message)
    else:
        await show_result(callback_query.message.chat.id, state, callback_query.message) #!!!

@router.callback_query(lambda c: c.data.startswith("menu:"))
async def handle_menu_callback(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data.split("menu:")[1]

    # Удаляем текущее меню
    data = await state.get_data()
    menu_message_id = data.get('menu_message_id')
    if menu_message_id:
        try:
            await bot.delete_message(callback_query.message.chat.id, menu_message_id)
        except Exception:
            pass

    # Вызываем соответствующую команду
    if action == "start":
        await start(callback_query.message, state)
    elif action == "info":
        await info(callback_query.message, state)
    elif action == "share":
        await share_result(callback_query.message, state)
    elif action == "feedback":
        await get_feedback(callback_query.message, state)
    elif action == "restart":
        await restart(callback_query.message, state)
    # Закрываем всплывающее уведомление Telegram
    await callback_query.answer()

async def show_result(chat_id: int, state: FSMContext, msg: Message):
    data = await state.get_data()
    result = max(data['animals'], key=data['animals'].get)
    # Отправляем сообщение с результатом
    await bot.send_message(chat_id, f'Твое тотемное животное - <b>{result}</b>! 🎉', parse_mode='HTML')
    # Добавляем информацию о животном
    await animal_info(chat_id, result)
    await send_main_menu(msg.chat.id, state)

