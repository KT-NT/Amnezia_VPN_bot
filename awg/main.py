import logging
import random
import os
import subprocess
from datetime import datetime, timedelta
from aiogram.dispatcher import dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db import Database  # Импортируем базу данных из db.py
from keyboards import *  # Импортируем клавиатуры
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import Message
import asyncio
from aiogram.types import CallbackQuery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = '8005821803:AAG5oLy-BhqKyvfEgNnMgeYfDKCNvsIGIQU'

db = Database()
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)


@router.message(Command("start"))
async def handle_start(message: Message):
    user_id = message.from_user.id
    if not db.user_exists(user_id):
        db.add_user(user_id)
        logger.info(f"Новый пользователь: {user_id}")
    await message.answer("Добро пожаловать!", reply_markup=main_menu())


@router.callback_query(lambda c: c.data == "replenish")
async def handle_replenish(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.update_balance(user_id, 100)  # Пополнение на 100 руб.
    await callback.message.edit_text("✅ Баланс пополнен на 100 руб.")
    await callback.answer() # Закрываем всплывающее уведомление Telegram

@router.callback_query(lambda c: c.data == "buy_vpn")
async def buy_vpn(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text("💰 Выберите срок подписки:", reply_markup=subscription_options())
    await callback.answer()

# Покупка VPN
@router.callback_query(lambda c: c.data in ['1_month', '2_months', '3_months'])
async def handle_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    duration = int(callback.data.split('_')[0])  # 1, 2 или 3 месяца
    price = {1: 100, 2: 180, 3: 260}[duration]  # Стоимость подписки

    if db.get_balance(user_id) >= price:
        port = random.randint(10000, 65535)
        config_id = db.add_config(user_id, duration, port)
        db.update_balance(user_id, -price)

        # Создание конфигурации VPN
        try:
            subprocess.run(["./newclient.sh", str(user_id), "your_endpoint", "your_wg_config_file", "your_docker_container"], check=True)
            await send_config(user_id, config_id)
            await callback.message.edit_text(f"✅ Подписка на {duration} месяц(ев) активирована!", reply_markup=None)
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при создании VPN-конфигурации: {e}")
            await callback.message.edit_text("❌ Ошибка при создании VPN.", reply_markup=None)
    else:
        await callback.answer("❌ Недостаточно средств на балансе.")

# Профиль пользователя
@router.callback_query(lambda c: c.data == "account")
async def handle_account(callback: CallbackQuery):
    user_id = callback.from_user.id
    configs = db.get_configs(user_id)

    if not configs:
        await callback.message.edit_text("У вас нет активных конфигураций.", reply_markup=None)
        return

    keyboard = configs_menu(configs)
    await callback.message.edit_text("Ваши активные конфигурации:", reply_markup=keyboard)

# Выбор конфигурации
@router.callback_query(lambda c: c.data.startswith('config_'))
async def handle_config(callback: CallbackQuery):
    config_id = int(callback.data.split('_')[1])
    config = db.get_config(config_id)

    if not config:
        await callback.answer("❌ Конфигурация не найдена.")
        return

    keyboard = config_actions(config_id)
    await callback.message.edit_text(
        f"⚙️ Конфиг #{config_id}\nПорт: {config['port']}\nСрок действия: {config['end_date']}",
        reply_markup=keyboard
    )

# Удаление конфигурации
@router.callback_query(lambda c: c.data.startswith('delete_'))
async def handle_delete(callback: CallbackQuery):
    config_id = int(callback.data.split('_')[1])
    config = db.get_config(config_id)

    if config:
        try:
            subprocess.run(["./removeclient.sh", str(config['user_id']), config['public_key'], "your_wg_config_file", "your_docker_container"], check=True)
            db.delete_config(config_id)
            await callback.answer("✅ Конфигурация удалена.")
            await handle_account(callback)  # Обновляем список конфигураций
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при удалении VPN-конфигурации: {e}")
            await callback.answer("❌ Ошибка при удалении конфигурации.")
    else:
        await callback.answer("❌ Конфигурация не найдена.")

# Скачивание конфигурации
@router.callback_query(lambda c: c.data.startswith('download_'))
async def handle_download(callback: CallbackQuery):
    config_id = int(callback.data.split('_')[1])
    await send_config(callback.from_user.id, config_id)
    await callback.answer("✅ Конфигурация отправлена.")

# Продление конфигурации
@router.callback_query(lambda c: c.data.startswith('extend_'))
async def handle_extend(callback: CallbackQuery):
    config_id = int(callback.data.split('_')[1])
    await callback.message.edit_text(
        "💰 Выберите срок продления:",
        reply_markup=subscription_options(config_id)
    )

# Выбор продления
@router.callback_query(lambda c: 'extend' in c.data)
async def handle_extend_subscription(callback: CallbackQuery):
    parts = callback.data.split('_')
    duration = int(parts[0])  # 1, 2 или 3 месяца
    config_id = int(parts[-1])  # ID конфигурации
    price = {1: 100, 2: 180, 3: 260}[duration]  # Стоимость подписки

    user_id = callback.from_user.id
    if db.get_balance(user_id) >= price:
        db.extend_config(config_id, duration)
        db.update_balance(user_id, -price)
        await callback.answer(f"✅ Конфигурация продлена на {duration} месяц(ев)!")
    else:
        await callback.answer("❌ Недостаточно средств на балансе.")

# Функция отправки конфигурации пользователю
async def send_config(user_id, config_id):
    try:
        config = db.get_config(config_id)
        if config:
            content = f"""🔑 Ваш конфиг:
ID: {config['config_id']}
Порт: {config['port']}
Срок действия: {config['end_date']}"""

            filename = f"config_{config_id}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)

            with open(filename, "rb") as f:
                await bot.send_document(user_id, f, caption="📂 Ваш конфиг VPN")

            os.remove(filename)
        else:
            await bot.send_message(user_id, "❌ Конфигурация не найдена.")
    except Exception as e:
        logger.error(f"Ошибка отправки конфигурации: {e}")
        await bot.send_message(user_id, "❌ Произошла ошибка при отправке конфигурации.")

@router.callback_query(lambda c: c.data == "back_to_account") # Обработчик кнопки "Назад в профиль"
async def handle_back_to_account(callback: CallbackQuery):
    await handle_account(callback)  # Вызывает обработчик профиля
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("back_to_config_")) # Обработчик кнопки "Назад в конфигурацию"
async def handle_back_to_config(callback: CallbackQuery):
    config_id = callback.data.split("_")[-1]
    await handle_config(callback)  # Показывает меню конфигурации
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("back_to_main")) # Обработчик кнопки "Назад в конфигурацию"
async def handle_back_main(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu())
    await callback.answer()


async def main():
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())





# Обработка выбора подписки
# @router.callback_query(lambda c: c.data in ['1_month', '2_months', '3_months'])
# #@dp.callback_query_handler(lambda c: c.data in ['1_month', '2_months', '3_months'])
# async def handle_subscription(callback: types.CallbackQuery):
#     user_id = callback.from_user.id
#     duration = int(callback.data.split('_')[0])  # 1, 2 или 3 месяца
#     price = {1: 100, 2: 180, 3: 260}[duration]  # Стоимость подписки
#
#     if db.get_balance(user_id) >= price:
#         port = random.randint(10000, 65535)
#         config_id = db.add_config(user_id, duration, port)
#         db.update_balance(user_id, -price)
#
#         # Создание конфигурации VPN с помощью newclient.sh
#         try:
#             subprocess.run(["./newclient.sh", str(user_id), "your_endpoint", "your_wg_config_file", "your_docker_container"], check=True)
#             await send_config(user_id, config_id)
#             await callback.answer(f"✅ Подписка на {duration} месяц(ев) активирована!")
#         except subprocess.CalledProcessError as e:
#             logger.error(f"Ошибка при создании конфигурации VPN: {e}")
#             await callback.answer("❌ Ошибка при создании конфигурации VPN.")
#     else:
#         await callback.answer("❌ Недостаточно средств на балансе.")
#
# # Команда /account (профиль)
# @router.callback_query(Command("account"))
# async def handle_account(message: types.Message):
#     user_id = message.from_user.id
#     configs = db.get_configs(user_id)
#
#     if not configs:
#         await message.answer("У вас нет активных конфигураций.")
#         return
#
#     keyboard = InlineKeyboardMarkup(row_width=1)
#     for config in configs:
#         btn_text = f"🔑 Конфиг #{config['config_id']} (до {config['end_date']})"
#         keyboard.add(InlineKeyboardButton(btn_text, callback_data=f"config_{config['config_id']}"))
#
#     await message.answer("Ваши активные конфигурации:", reply_markup=keyboard)
#
# # Обработка выбора конфигурации
# @router.callback_query(lambda c: c.data.startswith('config_'))
# #@dp.callback_query_handler(lambda c: c.data.startswith('config_'))
# async def handle_config(callback: types.CallbackQuery):
#     config_id = int(callback.data.split('_')[1])
#     config = db.get_config(config_id)
#
#     if not config:
#         await callback.answer("❌ Конфигурация не найдена.")
#         return
#
#     keyboard = InlineKeyboardMarkup(row_width=2)
#     keyboard.add(
#         InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_{config_id}"),
#         InlineKeyboardButton("📥 Скачать", callback_data=f"download_{config_id}"),
#         InlineKeyboardButton("🔄 Продлить", callback_data=f"extend_{config_id}")
#     )
#
#     await callback.message.edit_text(
#         f"⚙️ Конфиг #{config_id}\nПорт: {config['port']}\nСрок действия: {config['end_date']}",
#         reply_markup=keyboard
#     )
#
# # Обработка удаления конфигурации
# @router.callback_query(lambda c: c.data.startswith('delete_'))
# #@dp.callback_query_handler(lambda c: c.data.startswith('delete_'))
# async def handle_delete(callback: types.CallbackQuery):
#     config_id = int(callback.data.split('_')[1])
#     config = db.get_config(config_id)
#
#     if config:
#         try:
#             subprocess.run(["./removeclient.sh", str(config['user_id']), config['public_key'], "your_wg_config_file", "your_docker_container"], check=True)
#             db.delete_config(config_id)
#             await callback.answer("✅ Конфигурация удалена.")
#             await handle_account(callback.message)
#         except subprocess.CalledProcessError as e:
#             logger.error(f"Ошибка при удалении конфигурации VPN: {e}")
#             await callback.answer("❌ Ошибка при удалении конфигурации VPN.")
#     else:
#         await callback.answer("❌ Конфигурация не найдена.")
#
# # Обработка скачивания конфигурации
# #@dp.callback_query_handler(lambda c: c.data.startswith('download_'))
# @router.callback_query(lambda c: c.data.startswith('download_'))
# async def handle_download(callback: types.CallbackQuery):
#     config_id = int(callback.data.split('_')[1])
#     await send_config(callback.from_user.id, config_id)
#     await callback.answer("✅ Конфигурация отправлена.")
#
# # Обработка продления конфигурации
# @router.callback_query(lambda c: c.data.startswith('extend_'))
# #@dp.callback_query_handler(lambda c: c.data.startswith('extend_'))
# async def handle_extend(callback: types.CallbackQuery):
#     config_id = int(callback.data.split('_')[1])
#     await callback.message.edit_text(
#         "💰 Выберите срок продления:",
#         reply_markup=subscription_options(config_id)
#     )
#
# # Обработка выбора продления
# @router.callback_query(lambda c: 'extend' in c.data)
# #@dp.callback_query_handler(lambda c: 'extend' in c.data)
# async def handle_extend_subscription(callback: types.CallbackQuery):
#     parts = callback.data.split('_')
#     duration = int(parts[0])  # 1, 2 или 3 месяца
#     config_id = int(parts[-1])  # ID конфигурации
#     price = {1: 100, 2: 180, 3: 260}[duration]  # Стоимость подписки
#
#     user_id = callback.from_user.id
#     if db.get_balance(user_id) >= price:
#         db.extend_config(config_id, duration)
#         db.update_balance(user_id, -price)
#         await callback.answer(f"✅ Конфигурация продлена на {duration} месяц(ев)!")
#     else:
#         await callback.answer("❌ Недостаточно средств на балансе.")
#
# # Функция для отправки конфигурации
# async def send_config(user_id, config_id):
#     try:
#         config = db.get_config(config_id)
#         if config:
#             content = f"""🔑 Ваш конфиг:
# ID: {config['config_id']}
# Порт: {config['port']}
# Срок действия: {config['end_date']}"""
#
#             filename = f"config_{config_id}.txt"
#             with open(filename, "w", encoding="utf-8") as f:
#                 f.write(content)
#
#             with open(filename, "rb") as f:
#                 await bot.send_document(user_id, f, caption="📂 Ваш конфиг VPN")
#
#             os.remove(filename)
#         else:
#             await bot.send_message(user_id, "❌ Конфигурация не найдена.")
#     except Exception as e:
#         logger.error(f"Ошибка отправки конфигурации: {e}")
#         await bot.send_message(user_id, "❌ Произошла ошибка при отправке конфигурации.")