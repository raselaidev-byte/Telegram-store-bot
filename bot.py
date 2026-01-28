"""
Complete Advanced Multi-Feature File Store Bot
✅ Batch upload (multiple files = one link)
✅ File search & history
✅ Multi-channel storage
✅ User statistics
✅ Admin panel
"""

import logging
import os
import asyncio
from datetime import datetime
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, ChannelInvalid

# ================== CONFIGURATION ==================
API_ID = int(os.getenv("API_ID", "38517413"))
API_HASH = os.getenv("API_HASH", "0723f854a0bb85dfcc5dcbeead6ad7ee")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8268848494:AAFylT8NorMRg2oAkpf9DEVsfKxfJ4OVmoQ")
STORAGE_CHANNELS = [-1003802230688]
MAIN_ADMIN_ID = int(os.getenv("MAIN_ADMIN_ID", "7415661180"))
ADMIN_IDS = [MAIN_ADMIN_ID]

DEVELOPER_USERNAME = os.getenv("DEVELOPER_USERNAME", "OxGhost_Bot")
SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "")
SUPPORT_GROUP = os.getenv("SUPPORT_GROUP", "")
DONATION_LINK = os.getenv("DONATION_LINK", "")
WELCOME_IMAGE = os.getenv("WELCOME_IMAGE", "")

# ================== STATS ==================
bot_stats = {
    "total_users": set(),
    "total_files": 0,
    "total_downloads": 0,
    "today_uploads": 0,
    "today_downloads": 0,
    "channel_usage": {ch: 0 for ch in STORAGE_CHANNELS},
    "total_batches": 0
}

user_data = {}
file_to_channel_map = {}
batch_files = {}
user_file_history = {}
batch_data = {}

# ================== LOGGING ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ================== BOT INIT ==================
app = Client("file_store_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, workers=10)

# ================== HELPERS ==================
def is_main_admin(user_id: int) -> bool:
    return user_id == MAIN_ADMIN_ID

def get_storage_channel():
    return min(STORAGE_CHANNELS, key=lambda ch: bot_stats["channel_usage"].get(ch, 0))

def generate_share_link(bot_username: str, file_id) -> str:
    return f"https://t.me/{bot_username}?start=file_{file_id}"

def generate_batch_link(bot_username: str, batch_id: str) -> str:
    return f"https://t.me/{bot_username}?start=batch_{batch_id}"

def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def update_user_data(user_id, username, action="upload"):
    if user_id not in user_data:
        user_data[user_id] = {
            "files_uploaded": 0,
            "batches_created": 0,
            "last_upload": None,
            "username": username,
            "join_date": datetime.now().strftime("%Y-%m-%d")
        }
    if action == "upload":
        user_data[user_id]["files_uploaded"] += 1
        user_data[user_id]["last_upload"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        user_data[user_id]["username"] = username
    elif action == "batch":
        user_data[user_id]["batches_created"] += 1

def get_main_keyboard() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton("👨‍💻 Developer", url=f"https://t.me/{DEVELOPER_USERNAME}")]]
    support_row = []
    if SUPPORT_CHANNEL:
        support_row.append(InlineKeyboardButton("📢 Channel", url=f"https://t.me/{SUPPORT_CHANNEL.replace('@','')}"))
    if SUPPORT_GROUP:
        support_row.append(InlineKeyboardButton("👥 Group", url=f"https://t.me/{SUPPORT_GROUP.replace('@','')}"))
    if support_row:
        buttons.append(support_row)
    if DONATION_LINK:
        buttons.append([InlineKeyboardButton("💰 Donate", url=DONATION_LINK)])
    buttons.append([
        InlineKeyboardButton("📊 My Stats", callback_data="my_stats"),
        InlineKeyboardButton("📁 My Files", callback_data="my_files")
    ])
    buttons.append([
        InlineKeyboardButton("🔍 Search", callback_data="search_files"),
        InlineKeyboardButton("ℹ️ About", callback_data="about_bot")
    ])
    return InlineKeyboardMarkup(buttons)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
         InlineKeyboardButton("👥 Users", callback_data="admin_users")],
        [InlineKeyboardButton("💾 Channels", callback_data="admin_channels"),
         InlineKeyboardButton("📦 Batches", callback_data="admin_batches")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
         InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")],
        [InlineKeyboardButton("🔧 Tech Info", callback_data="admin_tech"),
         InlineKeyboardButton("🔙 Close", callback_data="close_admin")]
    ]
    return InlineKeyboardMarkup(buttons)

# ================== START COMMAND ==================
@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user = message.from_user
    bot_stats["total_users"].add(user.id)

    if len(message.command) > 1:
        param = message.command[1]
        
        # Batch download
        if param.startswith("batch_"):
            batch_id = param.replace("batch_", "")
            if batch_id in batch_data:
                try:
                    await client.send_dice(message.chat.id, "🎲")
                except:
                    pass
                
                status_msg = await message.reply(f"⏳ **Fetching {len(batch_data[batch_id])} files...**")
                
                sent_count = 0
                for file_id in batch_data[batch_id]:
                    channel_id = file_to_channel_map.get(file_id)
                    if channel_id:
                        try:
                            await client.copy_message(message.chat.id, channel_id, file_id)
                            sent_count += 1
                            await asyncio.sleep(0.5)
                        except:
                            continue
                
                bot_stats["total_downloads"] += sent_count
                await status_msg.edit(f"✅ **Sent {sent_count}/{len(batch_data[batch_id])} files!**")
                logger.info(f"Batch download: {user.id} -> {batch_id}")
            else:
                await message.reply("❌ **Batch not found**")
            return
        
        # Single file download
        elif param.startswith("file_"):
            try:
                file_msg_id = int(param.replace("file_", ""))
                try:
                    await client.send_dice(message.chat.id, "🎲")
                except:
                    pass
                
                status_msg = await message.reply("⏳ **Fetching file...**")
                
                channel_to_check = file_to_channel_map.get(file_msg_id)
                
                if channel_to_check:
                    try:
                        await client.copy_message(message.chat.id, channel_to_check, file_msg_id)
                        bot_stats["total_downloads"] += 1
                        await status_msg.edit("✅ **File sent!**")
                        return
                    except:
                        pass
                
                found = False
                for channel_id in STORAGE_CHANNELS:
                    try:
                        await client.copy_message(message.chat.id, channel_id, file_msg_id)
                        bot_stats["total_downloads"] += 1
                        file_to_channel_map[file_msg_id] = channel_id
                        await status_msg.edit("✅ **File sent!**")
                        found = True
                        break
                    except:
                        continue
                
                if not found:
                    await status_msg.edit("❌ **File not found**")
                    
            except ValueError:
                await message.reply("❌ **Invalid link**")
            return

    try:
        await client.send_dice(message.chat.id, "🎲")
    except:
        pass

    welcome_text = f"""
👋 **Welcome {user.first_name}!**

**➤ Features:**
  • `📤` Upload single or multiple files
  • `📦` Batch upload - one link for multiple files
  • `🔗` Instant shareable links
  • `📊` Track your uploads
  • `📁` View your file history
  • `🔍` Search your files by name

**➤ Quick Start:**
  `1.` Send one or multiple files
  `2.` Type `/done` to generate batch link
  `3.` Or get individual links instantly

**➤ Commands:**
  `/help` - Full instructions
  `/mystats` - Your statistics
  `/myfiles` - Your file history
  `/cancel` - Cancel batch upload

**➤ Storage:** `{len(STORAGE_CHANNELS)}` channels • `{bot_stats['total_files']}` files
    """
    
    try:
        if WELCOME_IMAGE:
            await message.reply_photo(photo=WELCOME_IMAGE, caption=welcome_text, reply_markup=get_main_keyboard())
        else:
            await message.reply_text(welcome_text, reply_markup=get_main_keyboard())
    except:
        await message.reply_text(welcome_text, reply_markup=get_main_keyboard())

# ================== HELP COMMAND ==================
@app.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    help_text = f"""
📖 **Complete Guide**

**➤ Single File Upload:**
  • Send any file
  • Get instant shareable link
  • Share with anyone

**➤ Batch Upload (Multiple Files):**
  `1.` Send first file
  `2.` Keep sending more files
  `3.` Type `/done` when finished
  `4.` Get ONE link for ALL files!

**➤ Commands:**
  `/start` - Welcome
  `/help` - This guide
  `/mystats` - Your statistics
  `/myfiles` - View uploaded files
  `/search <name>` - Search files
  `/cancel` - Cancel batch
  `/done` - Complete batch
{"  `/admin` - Admin panel" if is_main_admin(message.from_user.id) else ""}

**➤ Features:**
  ✅ Single file links
  ✅ Batch links (multiple files)
  ✅ File history tracking
  ✅ Search by filename
  ✅ Multi-channel storage

**Contact:** @{DEVELOPER_USERNAME}
    """
    await message.reply_text(help_text, reply_markup=get_main_keyboard())

# ================== MY STATS ==================
@app.on_message(filters.command("mystats") & filters.private)
async def mystats_command(client: Client, message: Message):
    user = message.from_user
    if user.id in user_data:
        data = user_data[user.id]
        file_count = len(user_file_history.get(user.id, []))
        stats_text = f"""
📊 **Your Statistics**

**➤ User Info:**
  • **Name:** `{user.first_name}`
  • **ID:** `{user.id}`
  • **Joined:** `{data.get('join_date', 'Unknown')}`

**➤ Upload Stats:**
  • **Files:** `{data['files_uploaded']}`
  • **Batches:** `{data.get('batches_created', 0)}`
  • **Stored:** `{file_count}`
  • **Last:** `{data.get('last_upload', 'Never')}`

**Keep uploading!** 🚀
        """
    else:
        stats_text = "📊 **No uploads yet!**\n\nStart uploading!"
    await message.reply_text(stats_text)

# ================== MY FILES ==================
@app.on_message(filters.command("myfiles") & filters.private)
async def myfiles_command(client: Client, message: Message):
    user = message.from_user
    if user.id not in user_file_history or not user_file_history[user.id]:
        await message.reply("📁 **No files!**\n\nUpload some files first.")
        return
    
    files = user_file_history[user.id][-10:]
    files_text = "📁 **Your Recent Files** (Last 10)\n\n"
    
    for i, file_info in enumerate(reversed(files), 1):
        files_text += f"`{i}.` {file_info['name']}\n   Size: `{file_info['size']}`\n\n"
    
    files_text += f"\n**Total:** `{len(user_file_history[user.id])}`\nUse `/search` to find files"
    
    await message.reply_text(files_text)

# ================== SEARCH ==================
@app.on_message(filters.command("search") & filters.private)
async def search_command(client: Client, message: Message):
    user = message.from_user
    
    if len(message.command) < 2:
        await message.reply("**Usage:** `/search <filename>`\n\nExample: `/search document.pdf`")
        return
    
    search_query = " ".join(message.command[1:]).lower()
    
    if user.id not in user_file_history:
        await message.reply("📁 **No files to search!**")
        return
    
    results = []
    for file_info in user_file_history[user.id]:
        if search_query in file_info['name'].lower():
            results.append(file_info)
    
    if not results:
        await message.reply(f"🔍 **No results for:** `{search_query}`")
        return
    
    bot = await client.get_me()
    results_text = f"🔍 **Found {len(results)} file(s)**\n\n"
    
    for i, file_info in enumerate(results[:5], 1):
        link = generate_share_link(bot.username, file_info['file_id'])
        results_text += f"`{i}.` {file_info['name']}\n   `{link}`\n\n"
    
    if len(results) > 5:
        results_text += f"\n*Showing 5 of {len(results)}*"
    
    await message.reply_text(results_text)

# ================== CANCEL BATCH ==================
@app.on_message(filters.command("cancel") & filters.private)
async def cancel_batch(client: Client, message: Message):
    user = message.from_user
    if user.id in batch_files and batch_files[user.id]:
        count = len(batch_files[user.id])
        batch_files[user.id] = []
        await message.reply(f"❌ **Batch cancelled!**\n\n`{count}` files cleared.")
    else:
        await message.reply("ℹ️ **No active batch**")

# ================== DONE BATCH ==================
@app.on_message(filters.command("done") & filters.private)
async def done_batch(client: Client, message: Message):
    user = message.from_user
    
    if user.id not in batch_files or not batch_files[user.id]:
        await message.reply("ℹ️ **No files in batch!**\n\nSend files first, then `/done`")
        return
    
    files = batch_files[user.id]
    batch_id = f"{user.id}_{int(datetime.now().timestamp())}"
    batch_data[batch_id] = files.copy()
    
    bot = await client.get_me()
    batch_link = generate_batch_link(bot.username, batch_id)
    
    bot_stats["total_batches"] += 1
    update_user_data(user.id, user.username or user.first_name, "batch")
    
    success_text = f"""
✅ **Batch Created!**

**➤ Details:**
  • **Files:** `{len(files)}`
  • **Batch ID:** `{batch_id}`
  • **Created:** `{datetime.now().strftime('%Y-%m-%d %H:%M')}`

**➤ Batch Link:**
`{batch_link}`

**📦 One link for all {len(files)} files!**
    """
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔗 Share Batch", url=batch_link)
    ]])
    
    await message.reply_text(success_text, reply_markup=keyboard)
    
    batch_files[user.id] = []
    logger.info(f"Batch: {user.id} -> {batch_id} ({len(files)} files)")

# ================== ADMIN ==================
@app.on_message(filters.command("admin") & filters.private)
async def admin_command(client: Client, message: Message):
    if not is_main_admin(message.from_user.id):
        await message.reply("🔒 **Admin only**")
        return
    await message.reply_text("🔐 **Admin Panel**", reply_markup=get_admin_keyboard())

@app.on_message(filters.command("setwelcome") & filters.private)
async def set_welcome_image(client: Client, message: Message):
    if not is_main_admin(message.from_user.id):
        await message.reply("🔒 **Admin only**")
        return
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.reply("Reply to photo with /setwelcome")
        return
    try:
        file_id = message.reply_to_message.photo.file_id
        global WELCOME_IMAGE
        WELCOME_IMAGE = file_id
        await message.reply(f"✅ **Set!**\n\n`{file_id}`")
    except Exception as e:
        await message.reply(f"❌ `{str(e)}`")

@app.on_message(filters.command("setsupport") & filters.private)
async def set_support_command(client: Client, message: Message):
    if not is_main_admin(message.from_user.id):
        await message.reply("🔒 **Admin only**")
        return
    if len(message.command) < 3:
        await message.reply("`/setsupport channel @Username`\n`/setsupport group @Username`")
        return
    support_type = message.command[1].lower()
    support_link = message.command[2]
    if support_type == "channel":
        global SUPPORT_CHANNEL
        SUPPORT_CHANNEL = support_link
        await message.reply(f"✅ Channel: `{support_link}`")
    elif support_type == "group":
        global SUPPORT_GROUP
        SUPPORT_GROUP = support_link
        await message.reply(f"✅ Group: `{support_link}`")

@app.on_message(filters.command("setdonation") & filters.private)
async def set_donation_command(client: Client, message: Message):
    if not is_main_admin(message.from_user.id):
        await message.reply("🔒 **Admin only**")
        return
    if len(message.command) < 2:
        await message.reply("`/setdonation <link>`")
        return
    global DONATION_LINK
    DONATION_LINK = message.command[1]
    await message.reply(f"✅ Set: `{DONATION_LINK}`")

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    if not is_main_admin(message.from_user.id):
        await message.reply("🔒 **Admin only**")
        return
    if not message.reply_to_message:
        await message.reply("Reply to message with /broadcast")
        return
    status_msg = await message.reply("📢 **Broadcasting...**")
    success = 0
    failed = 0
    for user_id in bot_stats["total_users"]:
        try:
            await message.reply_to_message.copy(user_id)
            success += 1
            await asyncio.sleep(0.05)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except:
            failed += 1
    await status_msg.edit(f"✅ **Done!**\n\nSuccess: `{success}`\nFailed: `{failed}`")

# ================== CALLBACKS ==================
@app.on_callback_query()
async def callback_handler(client: Client, callback: CallbackQuery):
    data = callback.data
    user = callback.from_user
    
    if data == "my_stats":
        if user.id in user_data:
            u = user_data[user.id]
            text = f"📊 Files: {u['files_uploaded']}\nBatches: {u.get('batches_created',0)}"
        else:
            text = "📊 No uploads yet!"
        await callback.answer(text, show_alert=True)
        return
    
    elif data == "my_files":
        if user.id in user_file_history:
            text = f"📁 You have {len(user_file_history[user.id])} files!\n\nUse /myfiles"
        else:
            text = "📁 No files yet!"
        await callback.answer(text, show_alert=True)
        return
    
    elif data == "search_files":
        text = "🔍 Use: /search <filename>"
        await callback.answer(text, show_alert=True)
        return
    
    elif data == "about_bot":
        text = f"ℹ️ Users: {len(bot_stats['total_users'])}\nFiles: {bot_stats['total_files']}\nBatches: {bot_stats['total_batches']}"
        await callback.answer(text, show_alert=True)
        return
    
    if not is_main_admin(user.id):
        await callback.answer("🔒 Admin only!", show_alert=True)
        return
    
    if data == "admin_stats":
        top_users = sorted(user_data.items(), key=lambda x: x[1]['files_uploaded'], reverse=True)[:5]
        top_list = "\n".join([f"  {i+1}. {u['username']} - {u['files_uploaded']}" for i,(uid,u) in enumerate(top_users)]) if top_users else "  No data"
        text = f"""
📊 **Statistics**

**Overall:**
Users: {len(bot_stats['total_users'])}
Files: {bot_stats['total_files']}
Batches: {bot_stats['total_batches']}

**Top Users:**
{top_list}
        """
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")]])
        await callback.message.edit(text, reply_markup=back_btn)
    
    elif data == "admin_users":
        text = f"👥 **Users:** {len(bot_stats['total_users'])}\n**Active:** {len(user_data)}"
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")]])
        await callback.message.edit(text, reply_markup=back_btn)
    
    elif data == "admin_channels":
        channel_info = ""
        for i, ch_id in enumerate(STORAGE_CHANNELS, 1):
            usage = bot_stats["channel_usage"].get(ch_id, 0)
            channel_info += f"  {i}. {ch_id} - {usage} files\n"
        text = f"💾 **Channels**\n\n{channel_info}\n**Load Balancing:** Active"
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")]])
        await callback.message.edit(text, reply_markup=back_btn)
    
    elif data == "admin_batches":
        text = f"📦 **Batches**\n\nTotal: {bot_stats['total_batches']}\nActive: {len(batch_data)}"
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")]])
        await callback.message.edit(text, reply_markup=back_btn)
    
    elif data == "admin_settings":
        text = f"⚙️ **Settings**\n\nDev: @{DEVELOPER_USERNAME}\nChannel: {SUPPORT_CHANNEL or 'Not set'}\nGroup: {SUPPORT_GROUP or 'Not set'}"
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")]])
        await callback.message.edit(text, reply_markup=back_btn)
    
    elif data == "admin_broadcast":
        text = "📢 Reply to message with `/broadcast`"
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")]])
        await callback.message.edit(text, reply_markup=back_btn)
    
    elif data == "admin_tech":
        text = f"🔧 **Tech**\n\nPyrogram 2.0\nPython 3.12\nChannels: {len(STORAGE_CHANNELS)}"
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")]])
        await callback.message.edit(text, reply_markup=back_btn)
    
    elif data == "back_to_admin":
        text = "🔐 **Admin Panel**"
        await callback.message.edit(text, reply_markup=get_admin_keyboard())
    
    elif data == "close_admin":
        await callback.message.delete()
    
    await callback.answer()

# ================== FILE UPLOAD ==================
@app.on_message((filters.document | filters.video | filters.audio | filters.photo) & filters.private)
async def handle_file_upload(client: Client, message: Message):
    user = message.from_user
    
    if user.id not in batch_files:
        batch_files[user.id] = []
    
    status_msg = await message.reply("⏳ **Processing...**")
    
    try:
        selected_channel = get_storage_channel()
        stored_msg = await message.copy(selected_channel)
        
        bot_stats["channel_usage"][selected_channel] = bot_stats["channel_usage"].get(selected_channel, 0) + 1
        file_to_channel_map[stored_msg.id] = selected_channel
        
        batch_files[user.id].append(stored_msg.id)
        
        bot = await client.get_me()
        share_link = generate_share_link(bot.username, stored_msg.id)
        
        file_info = "File"
        file_name = "Unknown"
        file_size = 0
        
        if message.document:
            file_name = message.document.file_name
            file_info = f"📄 `{file_name}`"
            file_size = message.document.file_size
        elif message.video:
            file_name = f"Video_{stored_msg.id}.mp4"
            file_info = f"🎥 Video ({message.video.duration}s)"
            file_size = message.video.file_size
        elif message.audio:
            file_name = message.audio.title or f"Audio_{stored_msg.id}.mp3"
            file_info = f"🎵 `{file_name}`"
            file_size = message.audio.file_size
        elif message.photo:
            file_name = f"Photo_{stored_msg.id}.jpg"
            file_info = "🖼 Photo"
            file_size = message.photo.file_size
        
        if user.id not in user_file_history:
            user_file_history[user.id] = []
        user_file_history[user.id].append({
            "file_id": stored_msg.id,
            "name": file_name,
            "size": format_size(file_size),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        
        batch_count = len(batch_files[user.id])
        
        success_text = f"""
✅ **File Uploaded!**

**➤ File:** {file_info}
**➤ Size:** `{format_size(file_size)}`
**➤ ID:** `{stored_msg.id}`

**➤ Single Link:**
`{share_link}`

**➤ Batch:** `{batch_count}` file(s) in queue
📦 Send more or `/done` for batch link!
🚫 `/cancel` to clear queue
        """
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔗 Share", url=share_link)
        ]])
        
        await status_msg.edit(success_text, reply_markup=keyboard)
        
        bot_stats["total_files"] += 1
        bot_stats["today_uploads"] += 1
        update_user_data(user.id, user.username or user.first_name, "upload")
        
        logger.info(f"Upload: {user.id} -> {file_name} -> {stored_msg.id}")
        
    except Exception as e:
        await status_msg.edit(f"❌ **Failed**\n\n`{str(e)}`")
        logger.error(f"Upload error: {e}")

# ================== OTHER MESSAGES ==================
@app.on_message(filters.text & filters.private)
async def handle_text(client: Client, message: Message):
    if not message.text.startswith('/'):
        await message.reply(
            "ℹ️ **Send files to start!**\n\n"
            "**Single:** Get instant link\n"
            "**Batch:** Send multiple, then `/done`\n\n"
            "Use `/help` for guide",
            reply_markup=get_main_keyboard()
        )

# ================== STARTUP ==================
async def main():
    try:
        await app.start()
        bot = await app.get_me()
        logger.info(f"✅ Bot started: @{bot.username}")
        print(f"\n{'='*60}")
        print(f"✅ ADVANCED FILE STORE BOT STARTED")
        print(f"{'='*60}")
        print(f"📱 Bot: @{bot.username}")
        print(f"🌐 Mode: PUBLIC + BATCH SUPPORT")
        print(f"💾 Channels: {len(STORAGE_CHANNELS)}")
        print(f"👨‍💻 Dev: @{DEVELOPER_USERNAME}")
        print(f"")
        print(f"🔥 Features:")
        print(f"   • Single file links")
        print(f"   • Batch links (multiple → one link)")
        print(f"   • File search & history")
        print(f"   • Multi-channel storage")
        print(f"   • Auto load balancing")
        print(f"{'='*60}\n")
        await idle()
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        print(f"\n❌ Error: {e}\n")
        raise
    finally:
        await app.stop()

if __name__ == "__main__":
    print("🚀 Starting Advanced File Store Bot...")
    print("⏳ Please wait...\n")
    app.run(main())