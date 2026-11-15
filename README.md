# ربات آغازگر گفت‌وگوی گیم کنسولی

یک worker پایتون برای گروه تلگرام `@Pixel_Mediair` که پس از ۱۵ دقیقه سکوت یک بحث گیمی شروع می‌کند، هفته‌ای یک بحث ویژه می‌فرستد، و به منشن‌ها و ریپلای‌ها پاسخ می‌دهد. پاسخ‌ها، سؤال‌های بحث، نظرسنجی و quiz با API سازگار OpenAI در CoArena ساخته می‌شوند.

## قابلیت‌ها

ربات به‌صورت پیش‌فرض پس از ۱۵ دقیقه سکوت موضوعی برای بحث می‌فرستد و بین دو شروع خودکار دست‌کم ۶۰ دقیقه فاصله می‌گذارد. همچنین هر ۷ روز یک بحث هفتگی دارد. شمارش هفته از اولین فعالیتی آغاز می‌شود که ربات در گروه می‌بیند؛ با اجرای `/weekly` می‌توان بحث هفتگی را دستی شروع کرد و موعد بعدی را از همان زمان تنظیم کرد.

برای ادامهٔ گفتگو، حداکثر ۱۲ پیام اخیر همان گروه را فقط در حافظهٔ RAM و حداکثر ۱۵ دقیقه نگه می‌دارد. پیام‌ها دست‌کم هر ۲۰ ثانیه پاکسازی می‌شوند و بعد از restart هم در دسترس نیستند. متن گفتگو در SQLite یا Volume ذخیره نمی‌شود. SQLite فقط زمان فعالیت، زمان آخرین پاسخ/بحث، حداکثر ۱۲ موضوع قبلی و cooldown دستورها را نگه می‌دارد.

خبرهای جدید با Google News RSS در فارسی و انگلیسی جست‌وجو می‌شوند. منابع رسمی پلتفرم/ناشر، مثل PlayStation Blog، Xbox Wire و Nintendo News، در رتبه‌بندی جلوتر از رسانه‌های خبری بازی قرار می‌گیرند؛ نتیجه‌های تکراری و قدیمی‌تر از ۳۰ روز کنار گذاشته می‌شوند. ربات منبع و لینک هر خبر را در پاسخ درج می‌کند و خبر نامرتبط را به موضوع کاربر نسبت نمی‌دهد. لینک‌های بلند RSS به برچسب کوتاه و قابل‌کلیک تبدیل می‌شوند تا URL خام در پیام گروه دیده نشود.

در گروه هدف، اعضا می‌توانند از این دستورها استفاده کنند:

- `/poll` برای نظرسنجی گیمیِ بدون پاسخ درست؛
- `/quiz` برای quiz با پاسخ درست و توضیح؛
- `/weekly` برای شروع زودتر بحث هفتگی؛
- `/status` برای دیدن مدل، لحن، زمان‌بندی و حدود حافظه.

نظرسنجی و quiz به‌صورت poll بومی تلگرام و با مهلت ۱۵ دقیقه‌ای ارسال می‌شوند. برای جلوگیری از شلوغی، هر نوع poll در گروه حداکثر هر ۱۲۰ ثانیه و `/weekly` دستی حداکثر هر ساعت قابل اجراست. سؤال‌های این دستورها با CoArena ساخته می‌شوند؛ اگر API موقتاً در دسترس نباشد، ربات از سؤال پیش‌فرض استفاده می‌کند.

اگر CoArena خطای موقت شبکه یا 5xx بدهد، درخواست حداکثر سه بار با مکث افزایشی و محدود دوباره ارسال می‌شود. خطاهای دائمی مثل کلید نامعتبر بیهوده تکرار نمی‌شوند.

لحن از طریق `BOT_TONE` انتخاب می‌شود: `friendly` برای لحن گرم و کمی صمیمی یا `serious` برای لحن جدی‌تر. مقدار پیش‌فرض `friendly` است. در هر دو حالت ربات از ایموجی و استیکر استفاده نمی‌کند.

مدل پیش‌فرض `deepseek-v4-1-flash-1017` است و با `COARENA_MODEL` قابل تغییر است. برای پرسش‌های مربوط به خبر، آپدیت، تاریخ انتشار یا قیمت تازه، جست‌وجوی وب فعال می‌شود؛ نتیجهٔ RSS تا ۵ دقیقه cache می‌شود و با `NEWS_CACHE_TTL_SECONDS` قابل تنظیم است. برای جست‌وجو کلید دیگری لازم نیست.

## تنظیم CoArena

در صفحهٔ [API CoArena](https://coarena.ai/account/api) کلید بساز و آن را در Railway با نام `COARENA_API_KEY` به‌صورت Variable محرمانه تنظیم کن. کلید را در کد، چت یا repository نگذار. endpoint پیش‌فرض پروژه `https://coarena.ai/api/v1` است و از `COARENA_BASE_URL` قابل تغییر است. شناسهٔ مدل نیز از `COARENA_MODEL` تنظیم می‌شود.

## استقرار و نگهداری state در Railway

اگر repository به Railway وصل است، بعد از push شدن تغییرات، سرویس را redeploy کن. Start Command همچنان `python bot.py` است؛ این worker از polling استفاده می‌کند و به دامنه یا پورت HTTP نیاز ندارد.

برای اینکه زمان‌بندی سکوت، موعد بحث هفتگی و cooldownها بعد از redeploy حفظ شوند، یک **Volume** به همان سرویس Railway اضافه کن و Mount Path را `/app/data` قرار بده. Railway مقدار `RAILWAY_VOLUME_MOUNT_PATH` را خودکار می‌سازد و ربات از آن برای انتخاب فایل SQLite استفاده می‌کند. اگر می‌خواهی مسیر را دستی و صریح تنظیم کنی، در **Variables** این override را وارد کن:

```text
BOT_DB_PATH=/app/data/bot_state.sqlite3
```

Railway طبق [راهنمای Volumeها](https://docs.railway.com/volumes) فایل‌ها را در مسیر mountشده نگه می‌دارد. اگر Volume وصل نشود، ربات همچنان اجرا می‌شود، اما فایل SQLite در فضای موقت سرویس است و تضمینی برای ماندنش بعد از deploy جدید نیست. خود متن پیام‌های اعضا هیچ‌وقت وارد این فایل نمی‌شود.

اگر در Railway خطای permission روی فایل SQLite دیدی و image با کاربر غیر root اجرا می‌شود، `RAILWAY_RUN_UID=0` را مطابق راهنمای Volumeهای Railway تنظیم کن.

متغیرهای اصلی Railway:

```text
TELEGRAM_BOT_TOKEN=توکن BotFather
COARENA_API_KEY=کلید API
COARENA_BASE_URL=https://coarena.ai/api/v1
COARENA_MODEL=deepseek-v4-1-flash-1017
BOT_TONE=friendly
BOT_DB_PATH=/app/data/bot_state.sqlite3
TARGET_CHAT_USERNAME=Pixel_Mediair
IDLE_MINUTES=15
TOPIC_COOLDOWN_MINUTES=60
REPLY_COOLDOWN_SECONDS=60
CONVERSATION_TTL_MINUTES=15
CONVERSATION_MAX_MESSAGES=12
WEEKLY_TOPIC_INTERVAL_DAYS=7
INTERACTION_COOLDOWN_SECONDS=120
TOPIC_RETRY_COOLDOWN_SECONDS=900
CHECK_INTERVAL_SECONDS=20
NEWS_SEARCH_ENABLED=true
NEWS_SEARCH_MAX_RESULTS=4
NEWS_CACHE_TTL_SECONDS=300
```

`TARGET_CHAT_ID` اختیاری است و برای گروه خصوصی یا گروهی که username آن قابل تشخیص نیست استفاده می‌شود. اگر متغیرهای قدیمی `FREEMODEL_API_KEY`, `FREEMODEL_BASE_URL` یا `FREEMODEL_MODEL` در Railway مانده‌اند، حذفشان کن؛ نسخهٔ فعلی از متغیرهای `COARENA_*` استفاده می‌کند.

## آماده‌سازی تلگرام

توکن را از `@BotFather` بگیر و Privacy Mode را خاموش کن (`/setprivacy` و سپس انتخاب bot و Disable). برای دیدن همهٔ پیام‌های گروه، Telegram نیاز دارد Privacy Mode خاموش باشد یا ربات مدیر گروه باشد. بعد ربات را به `Pixel_Mediair` اضافه کن. برای بررسی وضعیت از `/status` استفاده کن.

## اجرای محلی

```bash
python -m pip install -r requirements.txt
cp .env.example .env
python bot.py
```

## حریم خصوصی و عیب‌یابی

پیام‌های متنی گروه فقط برای حافظهٔ کوتاه‌مدت همان گروه در RAM استفاده می‌شوند: حداکثر ۱۲ پیام و ۱۵ دقیقه. این متن‌ها بعد از expiry پاک می‌شوند و بعد از restart هم باقی نمی‌مانند. برای پاسخ مستقیم، پیام فعلی و زمینهٔ اخیرِ همان گروه به CoArena فرستاده می‌شوند؛ منشن/ریپلای همیشه پاسخ‌پذیر است. پیام‌های عادی فقط وقتی فیلتر محلی آن‌ها را مرتبط با بازی کنسولی بداند، برای پاسخ احتمالی به CoArena می‌روند. زمان‌ها و موعدهای زمان‌بندی و موضوع‌های خود ربات در SQLite نگهداری می‌شوند.

اگر ربات پیام‌های گروه را نمی‌بیند، Privacy Mode و `TARGET_CHAT_USERNAME` یا `TARGET_CHAT_ID` را بررسی کن. برای خطای مدل، Railway Logs، مقدار `COARENA_API_KEY` و در دسترس بودن `COARENA_MODEL` را بررسی کن؛ کلید را در log یا پیام نفرست. برای خطای 429، محدودیت حساب یا سهمیهٔ CoArena را بررسی کن. اگر یک Bot Token را استفاده می‌کنی، فقط یک worker polling را هم‌زمان اجرا کن.

## منابع فنی

- [Telegram Bot API — sendPoll](https://core.telegram.org/bots/api/methods/sendpoll.md)
- [python-telegram-bot changelog](https://docs.python-telegram-bot.org/en/stable/changelog.html) — نسخهٔ 22.8 برای `correct_option_ids` در quiz
- [Railway Volumes](https://docs.railway.com/volumes)
- [PlayStation Blog](https://blog.playstation.com/)، [Xbox Wire](https://news.xbox.com/en-us/) و [Nintendo News](https://www.nintendo.com/us/whatsnew/)
