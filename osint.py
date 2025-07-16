import logging
import requests
import json
import io # Untuk membuat file dalam memori
from datetime import datetime # Untuk nama file unik
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Konfigurasi Logging: Untuk melihat log aktivitas bot di konsol
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- KONFIGURASI BOT DAN API ANDA ---
# Ganti dengan token bot Telegram Anda yang sebenarnya dari BotFather
TELEGRAM_BOT_TOKEN = "8123963776:AAGT4dux632XTEsSmClrM9JPwzlTMjq5fuc"

# URL API PHP untuk masing-masing fitur
# PENTING: Pastikan URL ini sudah benar dan sesuai dengan API PHP Anda!
# Cukup base URL, parameter akan ditambahkan otomatis oleh bot.
PHP_API_URL_NOPOL = "http://64.235.41.142/find/nopol.php?input=B4NA"
PHP_API_URL_NIK = "http://64.235.41.142/commands/ceknik.php?nik=3173051311851001"
PHP_API_URL_LEAKED_DB = "http://64.235.41.142/commands/leaksdb.php?input=DUKCAPIL"
PHP_API_URL_DUKCAPIL = "http://64.235.41.142/commands/dukcapil.php?nama=Salsabila"

# URL API untuk cek IP eksternal
IP_API_URL = "http://ip-api.com/json/"

# URL FOTO/THUMBNAIL untuk tampilan menu /start
# PENTING: GANTI ini dengan URL foto/thumbnail Anda yang valid dan dapat diakses publik!
PHOTO_START_MENU_URL = "https://e.top4top.io/p_34830jxiw1.jpg"

# --- KONFIGURASI KEAMANAN DAN ADMIN ---
# PENTING: GANTI dengan ID Telegram admin Anda! (Untuk mendapatkan ID, chat dengan @userinfobot)
ADMIN_IDS = [7340515446] # Placeholder, ubah ini!

# Set untuk menyimpan ID Telegram pengguna yang memiliki akses premium
PREMIUM_USERS = set() # Data ini sementara (volatile), akan hilang jika bot di-restart

# Set untuk menyimpan semua ID pengguna yang pernah berinteraksi dengan bot
# Data ini bersifat volatile (akan hilang jika bot di-restart),
# untuk penyimpanan permanen diperlukan database atau file.
ALL_USERS = set()

# Batas karakter untuk pesan di chat Telegram
TELEGRAM_MESSAGE_LIMIT = 4000 # Batas sebenarnya 4096, beri sedikit margin

# Fungsi untuk meng-escape teks agar aman untuk MarkdownV2
def escape_markdown_v2(text: str) -> str:
    """
    Meng-escape karakter khusus di string agar aman untuk ParseMode.MARKDOWN_V2.
    Karakter yang perlu di-escape: _, *, [, ], (, ), ~, `, >, #, +, -, =, |, {, }, ., !
    """
    # Pastikan 'text' adalah string
    text = str(text)
    
    # Karakter-karakter yang perlu di-escape untuk MarkdownV2
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text = text.replace(char, '\\' + char)
    return text

def is_premium(user_id: int) -> bool:
    """Memeriksa apakah pengguna memiliki akses premium."""
    return user_id in PREMIUM_USERS or user_id in ADMIN_IDS

def is_admin(user_id: int) -> bool:
    """Memeriksa apakah pengguna adalah admin."""
    return user_id in ADMIN_IDS

def format_hacker_output(data: dict, title: str) -> str:
    """
    Memformat dictionary data menjadi string bergaya output terminal hacker,
    menggunakan MarkdownV2 untuk monospace.
    Semua nilai di dalam data akan di-escape.
    """
    output = f"```\n"
    output += f"┌───[ {escape_markdown_v2(title)} ]\n" # Escape title juga
    output += f"│\n"

    for key, value in data.items():
        # Escape key jika berisi karakter khusus, tapi biasanya tidak perlu terlalu sering untuk key
        # Cukup gunakan escape_markdown_v2 pada nilai
        displayed_key = key.replace('_', ' ').upper()
        
        if isinstance(value, dict):
            output += f"├── {escape_markdown_v2(displayed_key)}:\n"
            for sub_key, sub_value in value.items():
                displayed_sub_key = sub_key.replace('_', ' ').upper()
                escaped_sub_value = escape_markdown_v2(str(sub_value)) # Pastikan semua sub-nilai di-escape
                output += f"│   └── {escape_markdown_v2(displayed_sub_key)}: {escaped_sub_value}\n"
        elif isinstance(value, list):
            output += f"├── {escape_markdown_v2(displayed_key)}:\n"
            if not value:
                output += f"│   └── (Tidak ada hasil)\n"
            else:
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        output += f"│   ├── Item {i+1}:\n"
                        for sub_key, sub_value in item.items():
                            displayed_sub_key = sub_key.replace('_', ' ').upper()
                            escaped_sub_value = escape_markdown_v2(str(sub_value)) # Pastikan semua sub-nilai di-escape
                            output += f"│   │   └── {escape_markdown_v2(displayed_sub_key)}: {escaped_sub_value}\n"
                    else:
                        escaped_item = escape_markdown_v2(str(item)) # Pastikan item list di-escape
                        output += f"│   └── {escaped_item}\n"
        else:
            escaped_value = escape_markdown_v2(str(value)) # Pastikan semua nilai di-escape
            output += f"├── {escape_markdown_v2(displayed_key)}: {escaped_value}\n"
    output += f"└─$ _\n```"
    return output

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler untuk perintah /start.
    Mengirim foto dan pesan selamat datang dengan instruksi perintah.
    """
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    ALL_USERS.add(user_id) # Tambahkan ID pengguna ke daftar semua pengguna

    if not is_premium(user_id):
        await update.message.reply_text(
            f"Maaf, Anda tidak memiliki akses ke bot ini\\. "
            f"Silakan hubungi admin untuk mendapatkan akses premium\\.\n\n"
            f"Telegram ID Anda: `{escape_markdown_v2(str(user_id))}`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if PHOTO_START_MENU_URL and PHOTO_START_MENU_URL != "GANTI_DENGAN_URL_FOTO_ANDA":
        try:
            await context.bot.send_photo(chat_id=chat_id, photo=PHOTO_START_MENU_URL)
        except Exception as e:
            logger.warning(f"Gagal mengirim foto dari URL ({PHOTO_START_MENU_URL}): {e}. Pastikan URL foto benar dan bisa diakses.")

    welcome_message = (
        '*Halo\\! Selamat datang di Bot Detektif Data\\.*\n'
        'Saya bisa membantu Anda mencari berbagai informasi\\.\n'
        'Gunakan perintah berikut:\n\n'
        '`/nopol <plat_nomor>` \\(contoh: `/nopol B1234ABC`\\)\n'
        '`/nik <nomor_nik>` \\(contoh: `/nik 32xxxxxxxxxxxxxx`\\)\n'
        '`/leakeddb <kata_kunci>` \\(contoh: `/leakeddb email@contoh.com`\\)\n'
        '`/dukcapil <nama_lengkap>` \\(contoh: `/dukcapil Budi Santoso`\\)\n'
        '`/cekid` \\(Untuk melihat ID Telegram Anda\\)\n'
        '`/myip` \\(Untuk melihat detail IP Anda\\)\n\n'
        'Untuk bantuan lebih lanjut, ketik `/help`\\.'
    )
    await update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler untuk perintah /help.
    Menampilkan daftar fitur dan cara penggunaannya dengan contoh.
    """
    user_id = update.message.from_user.id
    ALL_USERS.add(user_id) 

    if not is_premium(user_id):
        await update.message.reply_text("Anda tidak memiliki akses ke fitur ini\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    help_text = (
        '*Berikut daftar fitur yang tersedia:*\n'
        '\\- *Cek Nopol*: Mencari informasi plat nomor kendaraan\\. Penggunaan: `/nopol <plat_nomor>`\n'
        '\\- *Cek NIK*: Mencari detail informasi NIK \\(Nomor Induk Kependudukan\\)\\. Penggunaan: `/nik <nomor_nik>`\n'
        '\\- *Leaked Database*: Mencari informasi yang mungkin bocor di database\\. Penggunaan: `/leakeddb <kata_kunci>`\n'
        '\\- *Cek Nama Dukcapil*: Mencari informasi nama melalui data Dukcapil\\. Penggunaan: `/dukcapil <nama_lengkap>`\n'
        '\\- *Cek ID Telegram*: Melihat ID Telegram Anda\\. Penggunaan: `/cekid`\n'
        '\\- *Cek IP Saya*: Melihat detail alamat IP Anda\\. Penggunaan: `/myip`\n\n'
        'Untuk kembali ke info awal, Anda bisa ketik `/start`\\.'
    )
    if is_admin(user_id):
        help_text += (
            '\n\n*Fitur Admin:*\n'
            '\\- *Tambah Pengguna Premium*: `/addpremium <user_id>`\n'
            '\\- *Lihat Daftar Pengguna*: `/listuser`'
        )

    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def cekid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler untuk perintah /cekid.
    Mengirimkan ID Telegram pengguna yang menggunakan perintah ini.
    """
    user_id = update.message.from_user.id
    ALL_USERS.add(user_id) 

    await update.message.reply_text(
        f"ID Telegram Anda adalah: `{escape_markdown_v2(str(user_id))}`",
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def listuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler untuk perintah /listuser.
    Menampilkan daftar semua ID pengguna yang pernah berinteraksi dengan bot. Hanya untuk admin.
    """
    user_id = update.message.from_user.id
    ALL_USERS.add(user_id) 

    if not is_admin(user_id):
        await update.message.reply_text("Anda tidak memiliki izin untuk menggunakan perintah ini\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    if not ALL_USERS:
        await update.message.reply_text("Belum ada pengguna yang berinteraksi dengan bot\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    users_list = sorted(list(ALL_USERS))
    list_output = "*Daftar Pengguna Bot:*\n"
    for uid in users_list:
        status = ""
        if is_admin(uid):
            status = " \\(Admin\\)"
        elif is_premium(uid):
            status = " \\(Premium\\)"
        list_output += f"\\- `{escape_markdown_v2(str(uid))}`{status}\n"
    
    if len(list_output) > TELEGRAM_MESSAGE_LIMIT:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"user_list_{timestamp}.txt"
        file_buffer = io.BytesIO(list_output.replace('\\', '').encode('utf-8'))
        file_buffer.name = file_name
        
        try:
            await context.bot.send_document(
                chat_id=user_id,
                document=file_buffer,
                caption="Daftar pengguna terlalu panjang, dikirim sebagai file teks\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            logger.info(f"Daftar pengguna (file) berhasil dikirim ke admin {user_id}")
        except Exception as e:
            logger.error(f"Gagal mengirim daftar pengguna (file) ke admin {user_id}: {e}")
            await update.message.reply_text(
                f"Maaf, gagal mengirim file daftar pengguna\\. Detail: `{escape_markdown_v2(str(e))}`",
                parse_mode=ParseMode.MARKDOWN_V2
            )
    else:
        await update.message.reply_text(list_output, parse_mode=ParseMode.MARKDOWN_V2)

async def myip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler untuk perintah /myip.
    Mengambil dan menampilkan detail IP publik pengguna.
    """
    user_id = update.message.from_user.id
    ALL_USERS.add(user_id) 

    if not is_premium(user_id):
        await update.message.reply_text("Anda tidak memiliki akses ke fitur ini\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    await update.message.reply_text(
        "Mencari informasi IP Anda \\.\\.\\.",
        parse_mode=ParseMode.MARKDOWN_V2
    )

    try:
        response = requests.get(IP_API_URL, timeout=10)
        response.raise_for_status()

        ip_data = None
        try:
            ip_data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"JSON Decode Error for My IP: {e}. Raw response: {response.text[:500]}")
            error_message = f"Terjadi kesalahan dalam memproses data dari server IP\\. Respons bukan format JSON yang valid\\.\nDetail: `{escape_markdown_v2(str(e))}`"
            await update.message.reply_text(escape_markdown_v2(error_message), parse_mode=ParseMode.MARKDOWN_V2)
            return
        
        if isinstance(ip_data, dict) and ip_data.get('status') == 'success':
            output_dict_chat = {
                "IP Address": ip_data.get('query', 'Tidak diketahui'),
                "Negara": f"{ip_data.get('country', 'Tidak diketahui')} ({ip_data.get('countryCode', 'N/A')})",
                "Kota": ip_data.get('city', 'Tidak diketahui'),
                "ISP": ip_data.get('isp', 'Tidak diketahui')
            }
            formatted_output_chat = format_hacker_output(output_dict_chat, "DETAIL IP ANDA (Ringkasan)")
            full_output_file_content = json.dumps(ip_data, indent=2)
            
            if len(formatted_output_chat) > TELEGRAM_MESSAGE_LIMIT:
                formatted_output_chat = formatted_output_chat[:TELEGRAM_MESSAGE_LIMIT - 50] + "\n...\n_Pesan terlalu panjang\\. Data lengkap ada di file\\._```"
            await update.message.reply_text(formatted_output_chat, parse_mode=ParseMode.MARKDOWN_V2)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"myip_{ip_data.get('query', 'unknown').replace('.', '_')}_{timestamp}.json"
            file_buffer = io.BytesIO(full_output_file_content.encode('utf-8'))
            file_buffer.name = file_name
            
            try:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=file_buffer,
                    caption=f"Berikut data lengkap IP Anda dengan input `{escape_markdown_v2(ip_data.get('query', 'N/A'))}`\\.",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                logger.info(f"File {file_name} berhasil dikirim ke {user_id}")
            except Exception as e:
                logger.error(f"Gagal mengirim file dokumen IP ke {user_id}: {e}")
                await update.message.reply_text(
                    f"Maaf, gagal mengirim file data lengkap IP\\. Detail: `{escape_markdown_v2(str(e))}`",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
        else:
            error_message = f"Maaf, tidak dapat mengambil detail IP Anda\\. Status: {ip_data.get('status', 'Tidak diketahui') if isinstance(ip_data, dict) else 'Bukan JSON objek'}\\. Pesan: {ip_data.get('message', 'N/A') if isinstance(ip_data, dict) else 'N/A'}"
            await update.message.reply_text(escape_markdown_v2(error_message), parse_mode=ParseMode.MARKDOWN_V2)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error saat menghubungi API IP eksternal: {e}")
        await update.message.reply_text(
            f"Terjadi kesalahan saat mencoba terhubung untuk mendapatkan detail IP Anda\\. Mohon coba lagi nanti\\.\nDetail: `{escape_markdown_v2(str(e))}`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e: # Catch all other unexpected errors
        logger.error(f"Terjadi kesalahan tak terduga (myip): {e}")
        await update.message.reply_text(
            f"Terjadi kesalahan tak terduga saat mencoba mendapatkan detail IP Anda\\. Mohon coba lagi nanti\\.\nDetail: `{escape_markdown_v2(str(e))}`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    finally:
        await update.message.reply_text(
            "Selesai\\. Silakan ketik perintah lain atau `/start` untuk melihat daftar perintah\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )


async def nopol_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    ALL_USERS.add(user_id)

    if not is_premium(user_id):
        await update.message.reply_text("Anda tidak memiliki akses ke fitur ini\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return
    if not context.args:
        await update.message.reply_text("Penggunaan: `/nopol <plat_nomor>` \\(contoh: `/nopol B1234ABC`\\)", parse_mode=ParseMode.MARKDOWN_V2)
        return
    input_data = " ".join(context.args).upper()
    await send_api_request(update, context, PHP_API_URL_NOPOL, 'input', input_data, "Cek Nopol")

async def nik_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    ALL_USERS.add(user_id)

    if not is_premium(user_id):
        await update.message.reply_text("Anda tidak memiliki akses ke fitur ini\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return
    if not context.args:
        await update.message.reply_text("Penggunaan: `/nik <nomor_nik>` \\(contoh: `/nik 32xxxxxxxxxxxxxx`\\)", parse_mode=ParseMode.MARKDOWN_V2)
        return
    input_data = " ".join(context.args)
    await send_api_request(update, context, PHP_API_URL_NIK, 'nik', input_data, "Cek Detail NIK")

async def leaked_db_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    ALL_USERS.add(user_id)

    if not is_premium(user_id):
        await update.message.reply_text("Anda tidak memiliki akses ke fitur ini\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return
    if not context.args:
        await update.message.reply_text("Penggunaan: `/leakeddb <kata_kunci>` \\(contoh: `/leakeddb email@contoh.com`\\)", parse_mode=ParseMode.MARKDOWN_V2)
        return
    input_data = " ".join(context.args)
    await send_api_request(update, context, PHP_API_URL_LEAKED_DB, 'input', input_data, "Leaked Database")

async def dukcapil_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    ALL_USERS.add(user_id)

    if not is_premium(user_id):
        await update.message.reply_text("Anda tidak memiliki akses ke fitur ini\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return
    if not context.args:
        await update.message.reply_text("Penggunaan: `/dukcapil <nama_lengkap>` \\(contoh: `/dukcapil Budi Santoso`\\)", parse_mode=ParseMode.MARKDOWN_V2)
        return
    input_data = " ".join(context.args)
    await send_api_request(update, context, PHP_API_URL_DUKCAPIL, 'nama', input_data, "Cek Nama Dukcapil")


async def send_api_request(update: Update, context: ContextTypes.DEFAULT_TYPE, api_url: str, param_name: str, input_data: str, feature_name: str) -> None:
    """
    Fungsi utama untuk mengirim permintaan ke API PHP dan memproses responsnya.
    Mengirimkan ringkasan di chat dan file lengkap sebagai dokumen.
    """
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    ALL_USERS.add(user_id) 

    await update.message.reply_text(
        f"Mencari informasi {feature_name} untuk: `{escape_markdown_v2(input_data)}` \\.\\.\\.",
        parse_mode=ParseMode.MARKDOWN_V2
    )

    try:
        params = {param_name: input_data}
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()

        # Log respons mentah untuk debugging
        logger.info(f"API Response for {feature_name} (RAW): {response.text[:2000]}...") # Batasi log agar tidak terlalu panjang

        raw_api_data = None
        try:
            raw_api_data = response.json() # Mencoba parsing JSON
        except json.JSONDecodeError as e:
            logger.error(f"JSON Decode Error for {feature_name}: {e}. Raw response: {response.text[:500]}")
            error_message = f"Terjadi kesalahan dalam memproses data dari server untuk {feature_name}\\. Respons bukan format JSON yang valid\\.\nDetail: `{escape_markdown_v2(str(e))}`"
            await update.message.reply_text(escape_markdown_v2(error_message), parse_mode=ParseMode.MARKDOWN_V2)
            return # Keluar dari fungsi jika JSON tidak valid
        
        formatted_output_chat = ""
        full_output_file_content = ""
        error_message = None

        # --- LOGIKA PEMROSESAN DATA UNTUK CHAT DAN FILE ---
        
        # Penanganan umum untuk non-dict, error, atau pesan tidak ditemukan
        # Urutan penting: Cek boolean dulu, lalu non-dict, lalu error/message.
        if isinstance(raw_api_data, bool): 
             error_message = f"Maaf, API {feature_name} mengembalikan nilai boolean, bukan data yang diharapkan\\. Detail: `{escape_markdown_v2(str(raw_api_data))}`"
             logger.error(f"Boolean API Response for {feature_name}: {raw_api_data}")
        elif not isinstance(raw_api_data, dict):
            error_message = f"Maaf, respons dari API {feature_name} tidak dalam format JSON objek yang diharapkan\\. Detail: `{escape_markdown_v2(str(type(raw_api_data)))}`"
            logger.error(f"Unexpected API Response Type for {feature_name}: {raw_api_data}")
        elif 'error' in raw_api_data and raw_api_data.get('error') is not None:
             error_message = f"API mengembalikan error: `{escape_markdown_v2(str(raw_api_data.get('error')))}`"
        elif isinstance(raw_api_data.get('message'), str) and ("tidak ditemukan" in raw_api_data['message'].lower() or "not found" in raw_api_data['message'].lower()):
            error_message = f"Informasi {feature_name} untuk '{escape_markdown_v2(input_data)}' tidak ditemukan: `{escape_markdown_v2(raw_api_data['message'])}`"
        else: # Jika tidak ada error eksplisit dan respons adalah dict, lanjutkan pemrosesan data
            if feature_name == "Cek Detail NIK":
                nik_data = raw_api_data.get('nik')
                if nik_data and isinstance(nik_data, dict):
                    output_dict_chat = {
                        "NIK": input_data,
                        "Nama": nik_data.get('nama', 'Tidak diketahui'),
                        "Tanggal Lahir": nik_data.get('tanggal_lahir', 'Tidak diketahui'),
                        "Provinsi": nik_data.get('provinsi', 'Tidak diketahui'),
                        "Kabupaten/Kota": nik_data.get('kabupaten_kota', 'Tidak diketahui')
                    }
                    if raw_api_data.get('bpjs') and isinstance(raw_api_data['bpjs'], dict) and raw_api_data['bpjs'].get('noKartu'):
                        output_dict_chat["BPJS Info"] = {
                            "No. Kartu": raw_api_data['bpjs'].get('noKartu', 'N/A'),
                            "Status Peserta": raw_api_data['bpjs'].get('statusPeserta', 'N/A')
                        }
                    formatted_output_chat = format_hacker_output(output_dict_chat, "NIK DATA (Ringkasan)")
                    full_output_file_content = json.dumps(raw_api_data, indent=2)
                else:
                    error_message = f"Maaf, data NIK yang ditemukan tidak dalam format yang diharapkan untuk '{escape_markdown_v2(input_data)}'."

            elif feature_name == "Leaked Database":
                # Asumsi struktur: {"data": [{"List": { ... }}]}
                if 'data' in raw_api_data and isinstance(raw_api_data['data'], list) and raw_api_data['data']:
                    list_data_wrapper = raw_api_data['data'][0]
                    list_data = list_data_wrapper.get('List') # Bisa string "No results found" atau dict of results

                    if list_data and (isinstance(list_data, str) and 'No results found' in list_data):
                        formatted_output_chat = format_hacker_output({"Pencarian": input_data, "Hasil": "Tidak ada data ditemukan."}, "LEAKED DATABASE SEARCH")
                    elif list_data and isinstance(list_data, dict):
                        results = []
                        for key, value in list_data.items():
                            if isinstance(value, dict) and 'Data' in value:
                                for item in value['Data']:
                                    result_str_parts = []
                                    for k, v in item.items():
                                        # Pastikan setiap kunci dan nilai di-escape sebelum digabungkan
                                        escaped_k = escape_markdown_v2(str(k.replace('_', ' ').title())) # Escape key juga
                                        escaped_v = escape_markdown_v2(str(v)) if v is not None else ''
                                        if v is not None and v != '':
                                            result_str_parts.append(f"{escaped_k}: {escaped_v}")
                                    if result_str_parts:
                                        # Escape key dari list_data (misal: "DUKCAPIL", "KPU")
                                        escaped_list_key = escape_markdown_v2(key.replace('_', ' ').upper())
                                        results.append(f"[{escaped_list_key}] " + ", ".join(result_str_parts))

                        if results:
                            display_limit = 5 # Batasi hasil yang ditampilkan di chat, misalnya 5 item teratas
                            display_results_chat = results[:display_limit]
                            
                            output_dict_chat = {
                                "Pencarian": input_data,
                                "Jumlah Hasil": len(results),
                                "Hasil Ditemukan (Teratas)": display_results_chat
                            }
                            formatted_output_chat = format_hacker_output(output_dict_chat, "LEAKED DATABASE RESULTS (Ringkasan)")
                            
                            if len(results) > display_limit:
                                formatted_output_chat += f"\n\n_Pesan terpotong\\. Ada {len(results) - display_limit} hasil lainnya\\. Silakan cek file di bawah untuk data lengkap\\._"
                            
                            # Siapkan semua hasil untuk file (di sini kita tidak perlu escape ke MDV2, hanya untuk tampilan chat)
                            # Data lengkap untuk file akan diproses sebagai JSON atau TXT plain
                            full_output_file_content = json.dumps(raw_api_data, indent=2) # Gunakan raw_api_data lengkap untuk file
                        else:
                            formatted_output_chat = format_hacker_output({"Pencarian": input_data, "Hasil": "Tidak ada data ditemukan."}, "LEAKED DATABASE SEARCH")
                    else:
                        error_message = f"Maaf, data 'List' dari API leaked database tidak dalam format yang diharapkan untuk '{escape_markdown_v2(input_data)}'."
                else:
                    error_message = f"Maaf, respons API leaked database tidak memiliki struktur 'data' yang diharapkan untuk '{escape_markdown_v2(input_data)}'."

            elif feature_name == "Cek Nopol":
                if isinstance(raw_api_data, dict):
                    output_dict_chat = {
                        "Plat Nomor": input_data,
                        "Model": raw_api_data.get('model', 'Tidak diketahui'),
                        "Tahun": raw_api_data.get('tahun', 'Tidak diketahui'),
                        "Warna": raw_api_data.get('warna', 'Tidak diketahui'),
                        "Status Pajak": raw_api_data.get('pajak_status', 'Tidak diketahui'),
                        "Tipe": raw_api_data.get('tipe', 'Tidak diketahui'),
                        "Keterangan": raw_api_data.get('keterangan', 'Tidak diketahui')
                    }
                    formatted_output_chat = format_hacker_output(output_dict_chat, "NOPOL INFO")
                    full_output_file_content = json.dumps(raw_api_data, indent=2)
                else:
                    error_message = f"Maaf, data Nopol yang ditemukan tidak dalam format objek JSON yang diharapkan untuk '{escape_markdown_v2(input_data)}'."

            elif feature_name == "Cek Nama Dukcapil":
                if isinstance(raw_api_data, dict):
                    output_dict_chat = {
                        "Nama Dicari": input_data,
                        "NIK": raw_api_data.get('nik', 'Tidak diketahui'),
                        "Nama Lengkap": raw_api_data.get('nama_lengkap', 'Tidak diketahui'),
                        "Tanggal Lahir": raw_api_data.get('tgl_lahir', 'Tidak diketahui'),
                        "Jenis Kelamin": raw_api_data.get('jenis_kelamin', 'Tidak diketahui')
                    }
                    formatted_output_chat = format_hacker_output(output_dict_chat, "DUKCAPIL INFO")
                    full_output_file_content = json.dumps(raw_api_data, indent=2)
                else:
                    error_message = f"Maaf, data Dukcapil yang ditemukan tidak dalam format objek JSON yang diharapkan untuk '{escape_markdown_v2(input_data)}'."


        # --- KIRIM HASIL ATAU PESAN ERROR ---
        if formatted_output_chat:
            # Periksa lagi panjang pesan sebelum mengirim ke Telegram
            if len(formatted_output_chat) > TELEGRAM_MESSAGE_LIMIT:
                # Pangkas dan tambahkan pesan bahwa ada data lengkap di file
                formatted_output_chat = formatted_output_chat[:TELEGRAM_MESSAGE_LIMIT - 50] + "\n...\n_Pesan terlalu panjang\\. Data lengkap ada di file\\._```"
            await update.message.reply_text(formatted_output_chat, parse_mode=ParseMode.MARKDOWN_V2)

            # Kirim file lengkap jika ada kontennya
            if full_output_file_content:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Tentukan ekstensi file berdasarkan konten atau fitur
                # Jika full_output_file_content adalah string JSON yang valid, gunakan .json, jika tidak .txt
                file_ext = "json" if full_output_file_content.strip().startswith('{') and full_output_file_content.strip().endswith('}') else "txt"
                file_name = f"{feature_name.replace(' ', '_').lower()}_{input_data.replace(' ', '_').lower().replace('/', '-')}_{timestamp}.{file_ext}" # Nama file lebih rapi dan unik
                
                # Konten file harus berupa bytes
                file_content_for_buffer = full_output_file_content
                # Hapus karakter escape Markdown jika format file adalah TXT
                # Ini penting agar file teks tidak punya backslash aneh-aneh
                if file_ext == "txt":
                    file_content_for_buffer = file_content_for_buffer.replace('\\', '')
                
                file_buffer = io.BytesIO(file_content_for_buffer.encode('utf-8'))
                file_buffer.name = file_name # Nama file untuk ditampilkan di Telegram
                
                try:
                    await context.bot.send_document(
                        chat_id=chat_id,
                        document=file_buffer,
                        caption=f"Berikut data lengkap untuk {feature_name} dengan input `{escape_markdown_v2(input_data)}`\\.",
                        parse_mode=ParseMode.MARKDOWN_V2 # Caption juga pakai MarkdownV2
                    )
                    logger.info(f"File {file_name} berhasil dikirim ke {chat_id}")
                except Exception as e:
                    logger.error(f"Gagal mengirim file dokumen ke {chat_id}: {e}")
                    await update.message.reply_text(
                        f"Maaf, gagal mengirim file data lengkap\\. Detail: `{escape_markdown_v2(str(e))}`",
                        parse_mode=ParseMode.MARKDOWN_V2
                    )

        elif error_message: # Jika ada pesan error spesifik dari logika di atas
            await update.message.reply_text(error_message, parse_mode=ParseMode.MARKDOWN_V2) # error_message sudah di-escape di tempat lain
        else: # Fallback untuk respons API yang tidak terduga atau tidak valid sama sekali (setelah lolos semua cek)
            raw_response_text = json.dumps(raw_api_data, indent=2) if raw_api_data is not None else response.text
            # Pastikan raw_response_text adalah string sebelum slicing
            if not isinstance(raw_response_text, str):
                raw_response_text = str(raw_response_text)
            
            await update.message.reply_text(
                f"Maaf, respons dari API {feature_name} tidak dalam format yang diharapkan untuk `{escape_markdown_v2(input_data)}`\\.\n"
                f"Respons mentah: ```json\n{escape_markdown_v2(raw_response_text[:1000])}\n``` \\(dipotong hingga 1000 karakter\\)\\.\nSilakan coba lagi nanti\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )

    except requests.exceptions.RequestException as e:
        logger.error(f"Error saat menghubungi API PHP ({feature_name}): {e}")
        await update.message.reply_text(
            f"Terjadi kesalahan saat mencoba terhubung ke server API untuk {feature_name}\\. Mohon coba lagi nanti\\.\nDetail: `{escape_markdown_v2(str(e))}`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except json.JSONDecodeError as e: # Tangkap error spesifik ini jika respons bukan JSON
        logger.error(f"Error parsing JSON dari API PHP ({feature_name}): {e}. Respons mentah: {response.text[:1000]}")
        await update.message.reply_text(
            f"Terjadi kesalahan dalam memproses data dari server untuk {feature_name}\\. Respons bukan format JSON yang valid\\.\nDetail: `{escape_markdown_v2(str(e))}`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e: # Tangkap error tak terduga lainnya
        logger.error(f"Terjadi kesalahan tak terduga ({feature_name}): {e}")
        await update.message.reply_text(
            f"Terjadi kesalahan tak terduga untuk {feature_name}\\. Mohon coba lagi nanti\\.\nDetail: `{escape_markdown_v2(str(e))}`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    finally:
        await update.message.reply_text(
            "Selesai\\. Silakan ketik perintah lain atau `/start` untuk melihat daftar perintah\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def add_premium_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Perintah admin untuk menambahkan user ke daftar premium.
    Hanya bisa diakses oleh ADMIN_IDS.
    """
    user_id = update.message.from_user.id
    ALL_USERS.add(user_id) # Tambahkan ID pengguna ke daftar semua pengguna

    if not is_admin(user_id):
        await update.message.reply_text("Anda tidak memiliki izin untuk menggunakan perintah ini\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    if not context.args: # Memastikan ada argumen setelah perintah
        await update.message.reply_text("Penggunaan: `/addpremium <user_id_telegram>`", parse_mode=ParseMode.MARKDOWN_V2)
        return

    try:
        new_premium_id = int(context.args[0]) # Mengambil ID dari argumen pertama
        if new_premium_id in PREMIUM_USERS:
            await update.message.reply_text(f"User ID `{escape_markdown_v2(str(new_premium_id))}` sudah premium\\.", parse_mode=ParseMode.MARKDOWN_V2)
        else:
            PREMIUM_USERS.add(new_premium_id) # Menambahkan ID ke set PREMIUM_USERS
            await update.message.reply_text(f"User ID `{escape_markdown_v2(str(new_premium_id))}` berhasil ditambahkan ke daftar premium\\.", parse_mode=ParseMode.MARKDOWN_V2)
            # Opsional: Beri tahu user yang baru ditambahkan
            try:
                await context.bot.send_message(
                    chat_id=new_premium_id,
                    text="Selamat\\! Anda sekarang memiliki akses premium ke Bot Detektif Data\\.\nSilakan ketik `/start` untuk memulai\\.",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            except Exception as e:
                logger.warning(f"Gagal mengirim pesan ke user premium baru {new_premium_id}: {e}")
                await update.message.reply_text(f"Gagal memberitahu user `{escape_markdown_v2(str(new_premium_id))}` \\(mungkin bot diblokir oleh user tersebut\\)\\.", parse_mode=ParseMode.MARKDOWN_V2)

    except ValueError: # Jika ID yang dimasukkan bukan angka
        await update.message.reply_text("User ID harus berupa angka\\.", parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e: # Tangkap error tak terduga lainnya
        await update.message.reply_text(f"Terjadi kesalahan: `{escape_markdown_v2(str(e))}`", parse_mode=ParseMode.MARKDOWN_V2)

def main() -> None:
    """Fungsi utama untuk menjalankan bot Telegram."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # --- PENDAFTARAN HANDLER ---
    # CommandHandler: Untuk perintah seperti /start, /help, /addpremium
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("addpremium", add_premium_user)) # Handler admin
    application.add_handler(CommandHandler("cekid", cekid_command)) # Handler untuk /cekid
    application.add_handler(CommandHandler("listuser", listuser_command)) # Handler untuk /listuser
    application.add_handler(CommandHandler("myip", myip_command)) # Handler untuk /myip

    # Menambahkan CommandHandler untuk setiap fitur
    application.add_handler(CommandHandler("nopol", nopol_command))
    application.add_handler(CommandHandler("nik", nik_command))
    application.add_handler(CommandHandler("leakeddb", leaked_db_command))
    application.add_handler(CommandHandler("dukcapil", dukcapil_command))

    # Bot hanya akan merespons CommandHandler yang terdaftar.
    # Pesan teks selain perintah akan diabaikan oleh bot.
    logger.info("Bot dimulai dan sedang mendengarkan pesan...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

