from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥Купить VPN", callback_data="buy_vpn")],
        [InlineKeyboardButton(text="👤Пополнить баланс", callback_data="replenish")],
        [InlineKeyboardButton(text="💳Профиль", callback_data="account")]
    ])

def subscription_options(config_id=None):
    """Варианты подписки"""
    if config_id:
        # Кнопки для продления
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
        # Кнопки для покупки нового конфига
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
    for config in configs:
        btn_text = f"🔑 #{config['config_id']} (до {config['end_date'][5:10]})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f'config_{config["config_id"]}')])

    #buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data='main_menu')])
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


# def subscription_options(config_id=None):
#     """Варианты подписки"""
#     markup = InlineKeyboardMarkup()
#     if config_id:
#         # Кнопки для продления
#         markup.row(
#             InlineKeyboardButton("1 месяц - 100₽", callback_data=f'1_extend_{config_id}'),
#             InlineKeyboardButton("2 месяца - 180₽", callback_data=f'2_extend_{config_id}')
#         )
#         markup.row(
#             InlineKeyboardButton("3 месяца - 260₽", callback_data=f'3_extend_{config_id}'),
#             InlineKeyboardButton("◀️ Назад", callback_data=f'config_{config_id}')
#         )
#     else:
#         # Кнопки для покупки нового конфига
#         markup.row(
#             InlineKeyboardButton("1 месяц - 100₽", callback_data='1_month'),
#             InlineKeyboardButton("2 месяца - 180₽", callback_data='2_months')
#         )
#         markup.row(
#             InlineKeyboardButton("3 месяца - 260₽", callback_data='3_months'),
#             InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')
#         )
#     return markup
#
# def configs_menu(configs):
#     """Меню конфигов"""
#     markup = InlineKeyboardMarkup()
#     for config in configs:
#         btn_text = f"🔑 #{config['config_id']} (до {config['end_date'][5:10]})"
#         markup.add(InlineKeyboardButton(btn_text, callback_data=f'config_{config["config_id"]}'))
#     markup.row(InlineKeyboardButton("◀️ Назад", callback_data='back_to_main'))
#     return markup
#
# def config_actions(config_id):
#     """Действия с конфигом"""
#     markup = InlineKeyboardMarkup()
#     markup.row(
#         InlineKeyboardButton("📥 Скачать", callback_data=f'download_{config_id}'),
#         InlineKeyboardButton("🔄 Продлить", callback_data=f'extend_{config_id}')
#     )
#     markup.row(
#         InlineKeyboardButton("🗑️ Удалить", callback_data=f'delete_{config_id}'),
#         InlineKeyboardButton("◀️ Назад", callback_data='account')
#     )
#     return markup
