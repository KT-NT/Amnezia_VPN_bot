from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Купить VPN", callback_data="buy_vpn")],
        [InlineKeyboardButton(text="👤 Пополнить баланс", callback_data="replenish")],
        [InlineKeyboardButton(text="💳 Профиль", callback_data="account")],
        [InlineKeyboardButton(text="📢 Наш канал", callback_data="channel")],
        [InlineKeyboardButton(text="🆘 Поддержка", callback_data="support")],
        [InlineKeyboardButton(text="📲 Как установить", callback_data="install_guide")]
    ])

def install_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="iPhone", callback_data="install_ios")],
        [InlineKeyboardButton(text="Android", callback_data="install_android")],
        [InlineKeyboardButton(text="ПК", callback_data="install_pc")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])

def platform_guide_menu(platform: str):
    guide_links = {
        "ios": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "android": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "pc": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    }
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Гайд по установке", url=guide_links[platform])],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_install")]
    ])
def subscription_options(config_id=None):
    """Варианты подписки"""
    if config_id:
        buttons = [
            [
                InlineKeyboardButton(text="1 месяц - 100₽", callback_data=f'1_extend_{config_id}'),
                InlineKeyboardButton(text="2 месяца - 180₽", callback_data=f'2_extend_{config_id}')
            ],
            [
                InlineKeyboardButton(text="3 месяца - 260₽", callback_data=f'3_extend_{config_id}'),
                InlineKeyboardButton(text="◀️ Назад", callback_data=f'back_to_config_{config_id}')
            ]
        ]
    else:
        buttons = [
            [
                InlineKeyboardButton(text="1 месяц - 100₽", callback_data='1_month'),
                InlineKeyboardButton(text="2 месяца - 180₽", callback_data='2_months')
            ],
            [
                InlineKeyboardButton(text="3 месяца - 260₽", callback_data='3_months'),
                InlineKeyboardButton(text="◀️ Назад", callback_data='back_to_main')
            ]
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def configs_menu(configs):
    """Меню конфигов"""
    buttons = []
    for i, config in enumerate(configs, 1):
        btn_text = f"🔑 #{i} (ID: {config['config_id']}, до {config['end_date'][5:10]})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f'config_{config["config_id"]}')])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data='back_to_main')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def config_actions(config_id):
    """Действия с конфигом"""
    buttons = [
        [
            InlineKeyboardButton(text="📥 Скачать", callback_data=f'download_{config_id}'),
            InlineKeyboardButton(text="🔄 Продлить", callback_data=f'extend_{config_id}')
        ],
        [
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f'delete_{config_id}'),
            InlineKeyboardButton(text="◀️ Назад", callback_data='back_to_account')
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def channel_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Перейти в канал", url="https://t.me/IronNetVPN")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])

def support_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Написать админу", url="https://t.me/NotNikola")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
