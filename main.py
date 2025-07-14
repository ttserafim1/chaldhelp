import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

# === ДАННЫЕ ===
API_TOKEN = "7956233168:AAH_VTL3nv0W3koyv0b2fnKlpUNgcdSc57g"
ADMIN_ID = 7638761975

# === Состояние FSM ===
class AnswerState(StatesGroup):
    waiting_for_reply = State()

# === Кнопки администратора ===
def get_admin_keyboard(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ответить", callback_data=f"reply:{user_id}")],
        [InlineKeyboardButton(text="❌ Закрыть тикет", callback_data=f"close:{user_id}")]
    ])

# === Кнопки оценки ===
def get_rating_keyboard():
    keyboard = []
    for row in range(2):
        buttons = []
        for i in range(1 + row * 5, 6 + row * 5):
            buttons.append(InlineKeyboardButton(text=f"{i}⭐", callback_data=f"rate:{i}"))
        keyboard.append(buttons)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# === /start ===
async def handle_start(message: Message):
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n"
        f"Я — ChaldHelp, бот поддержки сервера Chald Studio.\n"
        f"Напиши сюда свою проблему, и мы передадим её администрации."
    )

# === /help ===
async def handle_help(message: Message):
    await message.answer(
        "📘 Как работает бот:\n"
        "- Напиши сюда свою проблему\n"
        "- Админ получит тикет и сможет ответить\n"
        "- После решения ты сможешь поставить оценку\n\nСпасибо, что с нами!"
    )

# === Сообщение от игрока ===
async def handle_player_message(message: Message, bot: Bot):
    if message.from_user.id == ADMIN_ID:
        return  # админ просто пишет, но не в режиме ответа — игнорируем

    user_id = message.from_user.id
    username = message.from_user.username or "Без username"
    text = message.text

    ticket_text = (
        f"📨 Новый тикет!\n"
        f"👤 @{username} (ID: {user_id})\n"
        f"📝 {text}"
    )

    await bot.send_message(
        chat_id=ADMIN_ID,
        text=ticket_text,
        reply_markup=get_admin_keyboard(user_id)
    )

    await message.reply("✅ Ваше сообщение отправлено администрации. Ожидайте ответа!")

# === Ответить игроку ===
async def admin_reply_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return

    user_id = int(callback.data.split(":")[1])
    await state.set_state(AnswerState.waiting_for_reply)
    await state.update_data(reply_to=user_id)
    await callback.message.answer(f"✍️ Введите сообщение для игрока (ID: {user_id})")
    await callback.answer()

# === Отправка ответа от админа игроку ===
async def process_admin_reply(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return  # Только админ может быть в этом состоянии

    data = await state.get_data()
    user_id = data.get("reply_to")

    if user_id:
        try:
            # Отправляем игроку сообщение + предупреждение
            await message.bot.send_message(
                user_id,
                f"📢 Ответ от администрации:\n\n{message.text}\n\n"
                "⚠️ Из-за системы бота, если вы что-то не поняли, пересоздайте тикет."
            )
            await message.answer("✅ Сообщение отправлено игроку.")
        except Exception as e:
            await message.answer(f"❌ Не удалось отправить сообщение игроку.\n{e}")
    await state.clear()

# === Закрытие тикета ===
async def close_ticket_callback(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        return

    user_id = int(callback.data.split(":")[1])

    try:
        await bot.send_message(
            chat_id=user_id,
            text="✅ Ваш тикет был закрыт.\nПожалуйста, оцените работу администрации:",
            reply_markup=get_rating_keyboard()
        )
    except:
        await callback.message.answer("⚠️ Не удалось отправить сообщение игроку.")

    await callback.message.answer("📦 Тикет закрыт.")
    await callback.answer()

# === Получение оценки ===
async def rating_handler(callback: CallbackQuery, bot: Bot):
    score = int(callback.data.split(":")[1])
    await callback.message.edit_text(f"🌟 Спасибо за вашу оценку: {score}/10!")
    await bot.send_message(ADMIN_ID, f"📥 Игрок поставил оценку: {score}/10")
    await callback.answer("Спасибо за отзыв!")

# === Регистрация хендлеров ===
def setup_handlers(dp: Dispatcher):
    dp.message.register(handle_start, F.text == "/start")
    dp.message.register(handle_help, F.text == "/help")
    dp.message.register(process_admin_reply, AnswerState.waiting_for_reply)
    dp.message.register(handle_player_message)
    dp.callback_query.register(admin_reply_callback, F.data.startswith("reply"))
    dp.callback_query.register(close_ticket_callback, F.data.startswith("close"))
    dp.callback_query.register(rating_handler, F.data.startswith("rate"))

# === Запуск бота ===
async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    setup_handlers(dp)

    print("🤖 ChaldHelp запущен (v2: пересылка с предупреждением)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
