import logging
import random
import os
import subprocess
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import InputFile, FSInputFile
import asyncio
from db import Database, SSHManager, load_servers, save_servers, add_server, remove_server, get_server_list
from keyboards import *
import logging 



# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TOKEN = '8005821803:AAFpKbNlXVPMair_JQKcOzQ4gj2JgsiWZdc'

db = Database()
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Константы для сервера
WG_CONFIG_FILE = "/opt/amnezia/awg/wg0.conf"  # Такие по дефолту
DOCKER_CONTAINER = "amnezia-awg"  # Так же по дефолту 
ENDPOINT = "89.208.97.144"  # Укажите правильный endpoint
CURRENT_SERVER = None


@router.message(Command("start"))
async def handle_start(message: Message):
    user_id = message.from_user.id
    if not db.user_exists(user_id):
        db.add_user(user_id)
        logger.info(f"Новый пользователь: {user_id}")

    logo_path = "logo.png"
    try:
        if os.path.exists(logo_path):
            await message.answer_photo(
                photo=FSInputFile(logo_path),
                caption="👋 Добро пожаловать в *VPN Бот!*\n\nВыберите действие:",
                parse_mode="Markdown",
                reply_markup=main_menu()
            )
        else:
            await message.answer(
                "👋 Добро пожаловать в VPN Бот!\n\nВыберите действие:",
                reply_markup=main_menu()
            )
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer(
            "👋 Добро пожаловать!\n\nВыберите действие:",
            reply_markup=main_menu()
        )
        
@router.callback_query(lambda c: c.data == "replenish")
async def handle_replenish(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.update_balance(user_id, 100)
    
    try:
        await bot.edit_message_caption(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            caption="✅ Баланс пополнен на 100 руб.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
                ]
            )
        )
    except Exception as e:
        logger.error(f"Ошибка изменения подписи: {e}")
        # Если произошла ошибка (например, сообщение не содержит фото), отправляем новое сообщение
        await callback.message.answer(
            "✅ Баланс пополнен на 100 руб.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
                ]
            )
        )
    await callback.answer()


@router.callback_query(lambda c: c.data == "buy_vpn")
async def buy_vpn(callback: CallbackQuery):
    await bot.edit_message_caption(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        caption="💰 Выберите срок подписки:",
        reply_markup=subscription_options()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "install_guide")
async def handle_install_guide(callback: CallbackQuery):
    await callback.message.edit_text(
        "📲 Выберите ваше устройство:",
        reply_markup=install_menu()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("install_"))
async def handle_install_platform(callback: CallbackQuery):
    platform = callback.data.split("_")[1]
    await callback.message.edit_text(
        f"🔧 Руководство для {platform.upper()}:",
        reply_markup=platform_guide_menu(platform)
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "back_to_install")
async def handle_back_to_install(callback: CallbackQuery):
    await callback.message.edit_text(
        "📲 Выберите ваше устройство:",
        reply_markup=install_menu()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data in ['1_month', '2_months', '3_months'])
async def handle_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    duration = int(callback.data.split('_')[0])
    price = {1: 100, 2: 180, 3: 260}[duration]

    if db.get_balance(user_id) >= price:
        port = random.randint(10000, 65535)
        config_id = db.add_config(user_id, duration, port)
        db.update_balance(user_id, -price)

        try:
            # Создаем конфиг без отправки
            subprocess.run(
                ["./newclient.sh", str(user_id), str(config_id), ENDPOINT, WG_CONFIG_FILE, DOCKER_CONTAINER],
                check=True
            )
            await callback.message.edit_text(
                f"✅ Подписка на {duration} месяц(ев) успешно активирована!\n"
                "Вы можете управлять конфигурацией в разделе «Профиль»",
                reply_markup=main_menu()
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка создания конфига: {e}")
            await callback.message.edit_text("❌ Ошибка при активации подписки")
    else:
        await callback.answer("❌ Недостаточно средств на балансе.")

@router.callback_query(lambda c: c.data == "account")
async def handle_account(callback: CallbackQuery):
    user_id = callback.from_user.id
    configs = db.get_configs(user_id)
    if not configs:
        await callback.message.edit_text(
            "У вас нет активных конфигураций.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
                ]
            )
        )
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
    """Обработчик кнопки скачивания"""
    config_id = int(callback.data.split('_')[1])
    await _send_config_file(callback.from_user.id, config_id)
    await callback.answer("✅ Файл отправлен")

async def _send_config_file(user_id: int, config_id: int):
    """Отправляет файл конфигурации"""
    try:
        config = db.get_config(config_id)
        if not config:
            await bot.send_message(user_id, "❌ Конфигурация не найдена")
            return

        # Исправленный путь к файлу
        file_path = f"./users/{user_id}/{user_id}_{config_id}.conf"
        
        if not os.path.exists(file_path):
            await bot.send_message(user_id, "❌ Файл конфигурации отсутствует")
            return

        await bot.send_document(
            chat_id=user_id,
            document=types.FSInputFile(file_path),
            caption=f"🔑 Конфигурация #{config_id}\nСрок действия: {config['end_date']}"
        )

    except Exception as e:
        logger.error(f"Ошибка отправки файла: {str(e)}")
        await bot.send_message(user_id, "❌ Ошибка при отправке файла")

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
    try:
        config_id = int(callback.data.split("_")[-1])
        await handle_config(callback)
    except ValueError:
        await callback.answer("❌ Некорректный идентификатор конфигурации.")
        logger.error(f"Неверный формат config_id: {callback.data}")

@router.callback_query(lambda c: c.data == "channel")
async def handle_channel(callback: CallbackQuery):
    await bot.edit_message_caption(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        caption="📢 Присоединяйтесь к нашему официальному каналу:",
        reply_markup=channel_menu()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "support")
async def handle_support(callback: CallbackQuery):
    await callback.message.edit_text(
        "🆘 По всем вопросам обращайтесь к администратору:",
        reply_markup=support_menu()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("back_to_main"))
async def handle_back_main(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu())
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
