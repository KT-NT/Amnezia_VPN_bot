import logging
import random
import os
import subprocess
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
import asyncio
from db import Database, SSHManager, load_servers, save_servers, add_server, remove_server, get_server_list
from keyboards import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = '8005821803:AAG5oLy-BhqKyvfEgNnMgeYfDKCNvsIGIQU'

db = Database()
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Константы для сервера
WG_CONFIG_FILE = None
DOCKER_CONTAINER = None
ENDPOINT = None
CURRENT_SERVER = None

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
    await callback.answer()

@router.callback_query(lambda c: c.data == "buy_vpn")
async def buy_vpn(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text("💰 Выберите срок подписки:", reply_markup=subscription_options())
    await callback.answer()

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
            subprocess.run(
                ["./newclient.sh", str(user_id), ENDPOINT, WG_CONFIG_FILE, DOCKER_CONTAINER],
                check=True
            )
            await send_config(user_id, config_id)
            await callback.message.edit_text(f"✅ Подписка на {duration} месяц(ев) активирована!", reply_markup=None)
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при создании VPN-конфигурации: {e}")
            await callback.message.edit_text("❌ Ошибка при создании VPN.", reply_markup=None)
    else:
        await callback.answer("❌ Недостаточно средств на балансе.")

@router.callback_query(lambda c: c.data == "account")
async def handle_account(callback: CallbackQuery):
    user_id = callback.from_user.id
    configs = db.get_configs(user_id)

    if not configs:
        await callback.message.edit_text("У вас нет активных конфигураций.", reply_markup=None)
        return

    keyboard = configs_menu(configs)
    await callback.message.edit_text("Ваши активные конфигурации:", reply_markup=keyboard)

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

@router.callback_query(lambda c: c.data.startswith('delete_'))
async def handle_delete(callback: CallbackQuery):
    config_id = int(callback.data.split('_')[1])
    config = db.get_config(config_id)

    if config:
        try:
            subprocess.run(
                ["./removeclient.sh", str(config['user_id']), "your_public_key", WG_CONFIG_FILE, DOCKER_CONTAINER],
                check=True
            )
            db.delete_config(config_id)
            await callback.answer("✅ Конфигурация удалена.")
            await handle_account(callback)  # Обновляем список конфигураций
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при удалении VPN-конфигурации: {e}")
            await callback.answer("❌ Ошибка при удалении конфигурации.")
    else:
        await callback.answer("❌ Конфигурация не найдена.")

@router.callback_query(lambda c: c.data.startswith('download_'))
async def handle_download(callback: CallbackQuery):
    config_id = int(callback.data.split('_')[1])
    await send_config(callback.from_user.id, config_id)
    await callback.answer("✅ Конфигурация отправлена.")

@router.callback_query(lambda c: c.data.startswith('extend_'))
async def handle_extend(callback: CallbackQuery):
    config_id = int(callback.data.split('_')[1])
    await callback.message.edit_text(
        "💰 Выберите срок продления:",
        reply_markup=subscription_options(config_id)
    )

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

async def send_config(user_id, config_id):
    try:
        config = db.get_config(config_id)
        if config:
            # Чтение конфигурационного файла
            config_file_path = f"./users/{user_id}/{user_id}.conf"
            if os.path.exists(config_file_path):
                with open(config_file_path, "rb") as f:
                    await bot.send_document(user_id, f, caption="📂 Ваш конфиг VPN")
            else:
                await bot.send_message(user_id, "❌ Конфигурационный файл не найден.")
        else:
            await bot.send_message(user_id, "❌ Конфигурация не найдена.")
    except Exception as e:
        logger.error(f"Ошибка отправки конфигурации: {e}")
        await bot.send_message(user_id, "❌ Произошла ошибка при отправке конфигурации.")

@router.callback_query(lambda c: c.data == "back_to_account")
async def handle_back_to_account(callback: CallbackQuery):
    await handle_account(callback)
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("back_to_config_"))
async def handle_back_to_config(callback: CallbackQuery):
    config_id = int(callback.data.split("_")[-1])
    await handle_config(callback)
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("back_to_main"))
async def handle_back_main(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu())
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
