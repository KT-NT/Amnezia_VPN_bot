from telebot import types

def main_menu():
    """Главное меню"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔥 Купить VPN", callback_data='buy_vpn'),
        types.InlineKeyboardButton("👤 Профиль", callback_data='account'),
        types.InlineKeyboardButton("💳 Пополнить баланс", callback_data='replenish'),
    )
    return markup

def subscription_options(config_id=None):
    """Варианты подписки"""
    markup = types.InlineKeyboardMarkup()
    if config_id:
        # Кнопки для продления
        markup.row(
            types.InlineKeyboardButton("1 месяц - 100₽", callback_data=f'1_extend_{config_id}'),
            types.InlineKeyboardButton("2 месяца - 180₽", callback_data=f'2_extend_{config_id}')
        )
        markup.row(
            types.InlineKeyboardButton("3 месяца - 260₽", callback_data=f'3_extend_{config_id}'),
            types.InlineKeyboardButton("◀️ Назад", callback_data=f'config_{config_id}')
        )
    else:
        # Кнопки для покупки нового конфига
        markup.row(
            types.InlineKeyboardButton("1 месяц - 100₽", callback_data='1_month'),
            types.InlineKeyboardButton("2 месяца - 180₽", callback_data='2_months')
        )
        markup.row(
            types.InlineKeyboardButton("3 месяца - 260₽", callback_data='3_months'),
            types.InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')
        )
    return markup
def configs_menu(configs):
    """Меню конфигов"""
    markup = types.InlineKeyboardMarkup()
    for config in configs:
        btn_text = f"🔑 #{config['config_id']} (до {config['end_date'][5:10]})"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'config_{config["config_id"]}'))
    markup.row(types.InlineKeyboardButton("◀️ Назад", callback_data='back_to_main'))
    return markup

def config_actions(config_id):
    """Действия с конфигом"""
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("📥 Скачать", callback_data=f'download_{config_id}'),
        types.InlineKeyboardButton("🔄 Продлить", callback_data=f'extend_{config_id}')
    )
    markup.row(
        types.InlineKeyboardButton("🗑️ Удалить", callback_data=f'delete_{config_id}'),
        types.InlineKeyboardButton("◀️ Назад", callback_data='account')
    )
    return markup