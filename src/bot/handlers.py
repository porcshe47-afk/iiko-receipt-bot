from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, MenuButtonWebApp
import os
import logging
from ..services.gemini import GeminiService
from ..config import settings

router = Router()
logger = logging.getLogger(__name__)

gemini = GeminiService(api_key=settings.GEMINI_API_KEY)

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    # Устанавливаем кнопку меню в левом нижнем углу чата
    try:
        await bot.set_chat_menu_button(
            chat_id=message.chat.id,
            menu_button=MenuButtonWebApp(text="Открыть", web_app=WebAppInfo(url=f"{settings.BASE_URL}/webapp"))
        )
    except Exception as e:
        logger.error(f"Failed to set menu button: {e}")

    kb = [
        [KeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=f"{settings.BASE_URL}/webapp"))]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(
        "Привет! Я помогу тебе поставить накладные на приход в iiko.\n"
        "Просто пришли мне фото накладной или чека.",
        reply_markup=keyboard
    )

@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot):
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    
    os.makedirs("temp", exist_ok=True)
    file_path = f"temp/{photo.file_id}.jpg"
    await bot.download_file(file_info.file_path, file_path)
    
    processing_msg = await message.answer("Распознаю документ... Пожалуйста, подождите.")
    
    try:
        result = await gemini.recognize_invoice(file_path)
        
        if "error" in result:
            await processing_msg.edit_text("Не удалось распознать документ. Попробуйте сделать фото четче.")
            return

        session_id = 123 
        webapp_url = f"{settings.BASE_URL}/webapp?session_id={session_id}"
        
        kb = [
            [KeyboardButton(text="Проверить и подтвердить", web_app=WebAppInfo(url=webapp_url))]
        ]
        keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        
        await processing_msg.delete()
        await message.answer(
            f"Документ распознан! Найдено позиций: {len(result.get('items', []))}.\n"
            "Нажмите кнопку ниже, чтобы проверить и отправить в iiko.",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.exception("Error in handle_photo")
        await processing_msg.edit_text("Произошла ошибка при обработке фото.")
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
