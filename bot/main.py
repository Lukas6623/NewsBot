import asyncio
from datetime import datetime, timedelta, timezone
from html import escape
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from serverguard.config import get_settings
from serverguard.database.storage import Storage
from serverguard.services.website_monitor import ping

settings = get_settings(); storage = Storage(settings.database_path); router = Router()
ping_lock = asyncio.Lock()
class Compose(StatesGroup):
    title = State(); content = State(); media = State(); category = State(); duration = State(); preview = State()

def menu():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📝 Create Post", callback_data="create"), InlineKeyboardButton(text="🌐 Ping Website", callback_data="ping")], [InlineKeyboardButton(text="📚 My Posts", callback_data="posts"), InlineKeyboardButton(text="🗑 Delete Post", callback_data="posts")]])
def back(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅ Back", callback_data="home")]])
def authorized(event): return event.from_user is not None and event.from_user.id in settings.admin_ids
async def deny(event):
    if isinstance(event, CallbackQuery): await event.answer("Not authorized", show_alert=True)
    else: await event.answer("Not authorized.")

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    if not authorized(message): return await deny(message)
    await state.clear(); await message.answer("<b>🛡 ServerGuard</b>\nNews Control Center\n\nManage publications and check serverguard.site availability.", reply_markup=menu(), parse_mode="HTML")

@router.callback_query(F.data == "home")
async def home(call: CallbackQuery, state: FSMContext):
    if not authorized(call): return await deny(call)
    await state.clear(); await call.message.edit_text("<b>🛡 ServerGuard</b>\nNews Control Center", reply_markup=menu(), parse_mode="HTML"); await call.answer()

@router.callback_query(F.data == "create")
async def create(call: CallbackQuery, state: FSMContext):
    if not authorized(call): return await deny(call)
    await state.clear(); await state.set_state(Compose.title); await call.message.edit_text("Send the post title (1–160 characters).", reply_markup=back()); await call.answer()

@router.message(Compose.title)
async def title(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    if not 1 <= len(value) <= 160: return await message.answer("Title must be 1–160 characters.")
    await state.update_data(title=value); await state.set_state(Compose.content); await message.answer("Send the content (1–10,000 characters).")

@router.message(Compose.content)
async def content(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    if not 1 <= len(value) <= 10000: return await message.answer("Content must be 1–10,000 characters.")
    await state.update_data(content=value); await state.set_state(Compose.media); await message.answer("Send an image, or type <code>skip</code>.", parse_mode="HTML")

@router.message(Compose.media)
async def media(message: Message, state: FSMContext, bot: Bot):
    image_url = None
    if message.photo:
        settings.media_path.mkdir(parents=True, exist_ok=True); photo = message.photo[-1]; file = await bot.get_file(photo.file_id)
        name = f"{photo.file_unique_id}.jpg"; await bot.download_file(file.file_path, settings.media_path / name)
        image_url = f"{settings.public_api_url.rstrip('/')}/media/{name}" if settings.public_api_url else f"/media/{name}"
    elif (message.text or "").strip().lower() != "skip": return await message.answer("Send an image or type skip.")
    await state.update_data(image_url=image_url); await state.set_state(Compose.category)
    await message.answer("Choose a category:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=x, callback_data=f"cat:{x}")] for x in ("Update", "Release", "Security", "Announcement")]))

@router.callback_query(Compose.category, F.data.startswith("cat:"))
async def category(call: CallbackQuery, state: FSMContext):
    if not authorized(call): return await deny(call)
    await state.update_data(category=call.data[4:]); await state.set_state(Compose.duration)
    keys = [[InlineKeyboardButton(text=x, callback_data=f"dur:{x}")] for x in ("1 day", "7 days", "30 days", "Forever")]
    keys.append([InlineKeyboardButton(text="Custom date", callback_data="dur:custom"), InlineKeyboardButton(text="⬅ Back", callback_data="home")])
    await call.message.edit_text("Choose publication duration:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keys)); await call.answer()

async def preview(call_or_message, state: FSMContext, expires: datetime | None, duration: str):
    await state.update_data(expires_at=expires.isoformat() if expires else None, duration=duration); data = await state.get_data(); await state.set_state(Compose.preview)
    image_line = "\nImage: attached" if data.get("image_url") else ""
    text = f"<b>Preview</b>\n\n<b>{escape(data['title'])}</b>\n{escape(data['content'])}\n\nCategory: {data['category']}\nDuration: {duration}{image_line}"
    await call_or_message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Publish", callback_data="publish"), InlineKeyboardButton(text="Edit", callback_data="edit"), InlineKeyboardButton(text="Cancel", callback_data="home")]]))

@router.callback_query(Compose.duration, F.data.startswith("dur:"))
async def duration(call: CallbackQuery, state: FSMContext):
    choice = call.data[4:]
    if not authorized(call): return await deny(call)
    if choice == "custom":
        return await call.message.edit_text("Send a future date in UTC as YYYY-MM-DD.", reply_markup=back())
    expires = None if choice == "Forever" else datetime.now(timezone.utc) + timedelta(days=int(choice.split()[0]))
    await preview(call.message, state, expires, choice); await call.answer()

@router.message(Compose.duration)
async def custom_duration(message: Message, state: FSMContext):
    try:
        value = datetime.strptime((message.text or "").strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if value <= datetime.now(timezone.utc): raise ValueError
    except ValueError: return await message.answer("Use a future UTC date as YYYY-MM-DD.")
    await preview(message, state, value, value.strftime("%Y-%m-%d UTC"))

@router.callback_query(Compose.preview, F.data == "publish")
async def publish(call: CallbackQuery, state: FSMContext):
    if not authorized(call): return await deny(call)
    data = await state.get_data(); expires = datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None
    post_id = await storage.create(data["title"], data["content"], data["category"], data.get("image_url"), expires); await state.clear()
    await call.message.edit_text(f"✅ Published <code>{post_id}</code>", parse_mode="HTML", reply_markup=menu()); await call.answer()

@router.callback_query(Compose.preview, F.data == "edit")
async def edit_preview(call: CallbackQuery, state: FSMContext):
    if not authorized(call): return await deny(call)
    await state.set_state(Compose.title); await call.message.edit_text("Send the replacement title (1–160 characters).", reply_markup=back()); await call.answer()

@router.callback_query(F.data == "ping")
async def check(call: CallbackQuery):
    if not authorized(call): return await deny(call)
    if ping_lock.locked(): return await call.answer("A check is already running", show_alert=True)
    async with ping_lock:
        result = await ping(settings.public_site_url, settings.ping_timeout_seconds)
    status = "ONLINE" if result["available"] else "OFFLINE"; http = f"HTTP: {result['status_code']}" if result["status_code"] else "No HTTP response"
    await call.message.edit_text(f"🌐 <b>ServerGuard Website</b>\n\nStatus: <b>{status}</b>\n{http}\nResponse time: {result['elapsed_ms']} ms", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Check Again", callback_data="ping"), InlineKeyboardButton(text="⬅ Back", callback_data="home")]])); await call.answer()

@router.callback_query(F.data == "posts")
async def posts(call: CallbackQuery):
    if not authorized(call): return await deny(call)
    rows = await storage.posts(); text = "<b>📚 My Posts</b>\n\n" + ("\n".join(f"<code>{r['id']}</code> · {escape(r['title'])} · {r['status']}" for r in rows) or "No posts yet.")
    buttons = [[InlineKeyboardButton(text=f"View {r['id']}", callback_data=f"view:{r['id']}"), InlineKeyboardButton(text="🗑 Delete", callback_data=f"delete:{r['id']}")] for r in rows]; buttons.append([InlineKeyboardButton(text="⬅ Back", callback_data="home")]); await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)); await call.answer()

@router.callback_query(F.data.startswith("view:"))
async def view(call: CallbackQuery):
    if not authorized(call): return await deny(call)
    post = await storage.get(call.data[5:])
    if not post: return await call.answer("Post not found", show_alert=True)
    expiry = post['expires_at'] or 'Forever'
    text = f"<b>{escape(post['title'])}</b>\n\n{escape(post['content'])}\n\nID: <code>{post['id']}</code>\nCategory: {post['category']}\nPublished: {post['published_at']}\nExpires: {expiry}\nStatus: {post['status']}"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗑 Delete", callback_data=f"delete:{post['id']}"), InlineKeyboardButton(text="⬅ Back", callback_data="posts")]])); await call.answer()

@router.callback_query(F.data.startswith("delete:"))
async def delete(call: CallbackQuery):
    if not authorized(call): return await deny(call)
    post_id = call.data[7:]; post = await storage.get(post_id)
    if not post: return await call.answer("Post not found", show_alert=True)
    await call.message.edit_text(f"Delete <b>{escape(post['title'])}</b>?", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Confirm delete", callback_data=f"confirm:{post_id}"), InlineKeyboardButton(text="Cancel", callback_data="posts")]])); await call.answer()

@router.callback_query(F.data.startswith("confirm:"))
async def confirm(call: CallbackQuery):
    if not authorized(call): return await deny(call)
    await storage.delete(call.data[8:]); await call.answer("Deleted"); await posts(call)

async def main():
    if not settings.telegram_bot_token or not settings.admin_ids: raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_ADMIN_IDS are required")
    await storage.init(); bot = Bot(settings.telegram_bot_token); dp = Dispatcher(); dp.include_router(router); await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
