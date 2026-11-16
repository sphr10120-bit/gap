# ربات آغازگر گفت‌وگوی گیم کنسولی

یک worker پایتون برای گروه تلگرام `@Pixel_Mediair` که پس از ۱۵ دقیقه سکوت یک بحث گیمی شروع می‌کند، هفته‌ای یک بحث ویژه، یک نظرسنجی و یک quiz می‌فرستد، و به منشن‌ها و ریپلای‌ها پاسخ می‌دهد. CoArena و XingChi پشتیبانی می‌شوند؛ مالک ربات می‌تواند API فعال را از پیوی عوض کند.

اگر به پیام یکی از اعضا ریپلای کنی و ربات را منشن کنی، ربات متن همان پیام را به‌عنوان موضوع اصلی پاسخ می‌گیرد و متن همراه منشن را به‌عنوان راهنمای اضافی در نظر می‌گیرد. اگر به پیام خود ربات ریپلای کنی، پیام قبلی فقط زمینه است و ربات به پیام تازهٔ تو جواب می‌دهد.

## قابلیت‌ها

ربات به‌صورت پیش‌فرض پس از ۱۵ دقیقه سکوت موضوعی برای بحث می‌فرستد و بین دو شروع خودکار دست‌کم ۶۰ دقیقه فاصله می‌گذارد. همچنین هر ۷ روز یک بحث هفتگی دارد. شمارش هفته از اولین فعالیتی آغاز می‌شود که ربات در گروه می‌بیند؛ با اجرای `/weekly` می‌توان بحث هفتگی را دستی شروع کرد و موعد بعدی را از همان زمان تنظیم کرد. زمان‌بندی poll و quiz نیز از اولین فعالیت گروه آغاز می‌شود: poll پس از ۲۴ ساعت و quiz حدود ۳٫۵ روز بعد منتشر می‌شود و هرکدام سپس هر ۷ روز تکرار می‌شوند؛ اگر هر دو به‌علت downtime عقب بیفتند، پس از برگشت سرویس پشت‌سرهم فرستاده نمی‌شوند.

برای پیوستگی گفتگو، حداکثر ۱۲ پیام متنی اخیر گروه (از اعضا و ربات) در SQLite روی Volume نگه‌داری می‌شود و پس از ۳۰ روز خودکار حذف می‌شود. رسانه‌ها ذخیره نمی‌شوند و تاریخچه فقط برای درک context پاسخ‌ها استفاده می‌شود. ترجیحات صریح گیمی کاربران نیز حداکثر ۳۰ روز، تا سقف ۵ مورد برای هر عضو نگه‌داری می‌شود؛ می‌توان با `/rememberme` ترجیحی را صریحاً ثبت کرد. هر عضو با `/forgetme` می‌تواند ترجیحات، پیام‌های ذخیره‌شدهٔ منتسب به خودش و پاسخ‌های ربات مرتبط با آن‌ها را پاک کند. حافظه فقط برای گروه تنظیم‌شده فعال است.

خبرهای جدید با Google News RSS در فارسی و انگلیسی جست‌وجو می‌شوند. منابع رسمی پلتفرم/ناشر، مثل PlayStation Blog، Xbox Wire، Nintendo News و Steam، در رتبه‌بندی جلوتر از رسانه‌های خبری بازی قرار می‌گیرند؛ نتیجه‌های تکراری و قدیمی‌تر از ۳۰ روز کنار گذاشته می‌شوند. برای پرسش دربارهٔ نسخه یا Build بازی Project Zomboid، صفحهٔ رسمی سازنده هم مستقیماً خوانده می‌شود و در صورت ریپلای، متن سؤالِ پیام اصلی نیز وارد جست‌وجو می‌شود. ربات منبع و لینک هر خبر را در پاسخ درج می‌کند و خبر نامرتبط را به موضوع کاربر نسبت نمی‌دهد. لینک‌های بلند RSS به برچسب کوتاه و قابل‌کلیک تبدیل می‌شوند تا URL خام در پیام گروه دیده نشود.

در گروه هدف، اعضا می‌توانند از این دستورها استفاده کنند:

- `/poll` برای نظرسنجی گیمیِ بدون پاسخ درست؛
- `/quiz` برای quiz با پاسخ درست و توضیح؛
- `/weekly` برای شروع زودتر بحث هفتگی؛
- `/status` برای دیدن API فعال، لحن، زمان‌بندی و حدود حافظه؛
- `/rememberme <ترجیح>` برای ثبت علاقه‌مندی گیمی خودت؛
- `/forgetme` برای حذف حافظهٔ مرتبط با حساب خودت.

در پیوی ربات، فقط مالک با شناسهٔ `8524573838` اجازه دارد `/apis` را برای دیدن وضعیت اتصال APIها و `/setapi coarena` یا `/setapi xingchi` را برای سوییچ API فعال اجرا کند. این فرمان فقط provider را عوض می‌کند؛ هر API از مدل تعریف‌شده در متغیرهای خودش (`COARENA_MODEL` یا `XINGCHI_MODEL`) استفاده می‌کند. انتخاب API در SQLite روی Volume ذخیره می‌شود و بعد از restart یا deploy باقی می‌ماند. فرمان در گروه یا برای حساب‌های دیگر API را تغییر نمی‌دهد.

نظرسنجی و quiz زمان‌بندی‌شده و دستی به‌صورت poll بومی تلگرام و با مهلت ۱۵ دقیقه‌ای ارسال می‌شوند. برای جلوگیری از شلوغی، هر نوع poll در گروه حداکثر هر ۱۲۰ ثانیه و `/weekly` دستی حداکثر هر ساعت قابل اجراست. سؤال‌ها از طریق API فعال ساخته می‌شوند؛ اگر API موقتاً در دسترس نباشد، ربات از سؤال پیش‌فرض استفاده می‌کند. موعدهای هفتگی در SQLite روی Volume باقی می‌مانند.

اگر CoArena یا XingChi خطای موقت شبکه یا 5xx بدهد، درخواست حداکثر سه بار با مکث افزایشی و محدود دوباره ارسال می‌شود. خطاهای دائمی مثل کلید نامعتبر بیهوده تکرار نمی‌شوند.

لحن از طریق `BOT_TONE` انتخاب می‌شود: `friendly` برای لحن گرم و کمی صمیمی یا `serious` برای لحن جدی‌تر. مقدار پیش‌فرض `friendly` است. در هر دو حالت ربات از ایموجی و استیکر استفاده نمی‌کند.

برای اینکه ربات سازنده را با احترام متعادل بشناسد، شناسهٔ عددی Telegram را با نام `CREATOR_TELEGRAM_ID` در Railway Variables قرار بده. این مقدار را فقط در تنظیمات خصوصی Railway وارد کن، نه در کد یا GitHub؛ ربات عدد را به مدل یا لاگ نمی‌فرستد. فقط وقتی پیام واقعاً از همان Telegram user ID باشد، prompt پاسخ لحن محترمانهٔ ویژه می‌گیرد؛ از تملق یا افشای شناسه جلوگیری شده است. سوییچ API فقط در پیوی و فقط برای شناسهٔ `API_OWNER_TELEGRAM_ID` مجاز است.

مدل پیش‌فرض CoArena برابر `deepseek-v4-1-flash-1017` است. مدل پیش‌فرض XingChi برابر `claude-sonnet-5` تنظیم شده تا انتخاب قبلی حفظ شود؛ اگر شناسهٔ دقیق این مدل در فهرست حساب XingChi متفاوت است، مقدار `XINGCHI_MODEL` را به همان شناسه تغییر بده. درخواست XingChi از مسیر Anthropic Messages API یعنی `/v1/messages` فرستاده می‌شود. با `LLM_PROVIDER` API آغازین را انتخاب کن؛ مالک بعد از راه‌اندازی می‌تواند API فعال را از پیوی با `/setapi` عوض کند. برای پرسش‌های مربوط به خبر، آپدیت، تاریخ انتشار یا قیمت تازه، جست‌وجوی وب فعال می‌شود؛ نتیجهٔ RSS تا ۵ دقیقه cache می‌شود و با `NEWS_CACHE_TTL_SECONDS` قابل تنظیم است. برای جست‌وجوی RSS کلید دیگری لازم نیست.

## تنظیم APIهای مدل

برای CoArena در [صفحهٔ API CoArena](https://coarena.ai/account/api) و برای XingChi در [صفحهٔ کلیدهای XingChi](https://xingchiapi.com/keys) کلید بساز. کلیدها را فقط در Railway Variables با نام‌های `COARENA_API_KEY` و `XINGCHI_API_KEY` به‌صورت محرمانه تنظیم کن؛ دست‌کم یکی از این دو لازم است. هیچ‌کدام را در کد، چت یا repository نگذار.

endpoint پیش‌فرض CoArena برابر `https://coarena.ai/api/v1` است. XingChi به‌صورت پیش‌فرض از `https://api.xingchiapi.com/v1/messages` استفاده می‌کند؛ ریشهٔ سرویس را با `XINGCHI_BASE_URL` می‌توان تغییر داد. CoArena از مسیر Chat Completions و XingChi از قالب Anthropic Messages API استفاده می‌کند. مدل‌ها با `COARENA_MODEL` و `XINGCHI_MODEL` تنظیم می‌شوند و provider آغازین با `LLM_PROVIDER=coarena` یا `LLM_PROVIDER=xingchi` انتخاب می‌شود. شناسهٔ دقیق مدل را از صفحهٔ حساب/مدل‌های XingChi بردار و در `XINGCHI_MODEL` بگذار. XingChi یک gateway ثالث است، نه API رسمی OpenAI یا Anthropic؛ درخواست‌های بات برای پردازش به ارائه‌دهندهٔ مدل انتخابی ارسال می‌شوند.

## استقرار و نگهداری state در Railway

اگر repository به Railway وصل است، بعد از push شدن تغییرات، سرویس را redeploy کن. Start Command همچنان `python bot.py` است؛ این worker از polling استفاده می‌کند و به دامنه یا پورت HTTP نیاز ندارد.

برای اینکه زمان‌بندی سکوت، موعد بحث هفتگی و cooldownها بعد از redeploy حفظ شوند، یک **Volume** به همان سرویس Railway اضافه کن و Mount Path را `/app/data` قرار بده. Railway مقدار `RAILWAY_VOLUME_MOUNT_PATH` را خودکار می‌سازد و ربات از آن برای انتخاب فایل SQLite استفاده می‌کند. اگر می‌خواهی مسیر را دستی و صریح تنظیم کنی، در **Variables** این override را وارد کن:

```text
BOT_DB_PATH=/app/data/bot_state.sqlite3
```

Railway طبق [راهنمای Volumeها](https://docs.railway.com/volumes) فایل‌ها را در مسیر mountشده نگه می‌دارد. اگر Volume وصل نشود، ربات همچنان اجرا می‌شود، اما فایل SQLite در فضای موقت سرویس است و تضمینی برای ماندنش بعد از deploy جدید نیست. تاریخچه و ترجیحات ذخیره‌شده شامل متن کاربران است؛ آن‌ها فقط روی Volume گروه تنظیم‌شده قرار می‌گیرند، زمان نگهداری محدود دارند و با `/forgetme` قابل حذف‌اند.

اگر در Railway خطای permission روی فایل SQLite دیدی و image با کاربر غیر root اجرا می‌شود، `RAILWAY_RUN_UID=0` را مطابق راهنمای Volumeهای Railway تنظیم کن.

متغیرهای اصلی Railway:

```text
TELEGRAM_BOT_TOKEN=توکن BotFather
COARENA_API_KEY=کلید API
XINGCHI_API_KEY=کلید API اختیاری برای provider دوم
COARENA_BASE_URL=https://coarena.ai/api/v1
COARENA_MODEL=deepseek-v4-1-flash-1017
XINGCHI_BASE_URL=https://api.xingchiapi.com
XINGCHI_MODEL=claude-sonnet-5
LLM_PROVIDER=coarena
BOT_TONE=friendly
CREATOR_TELEGRAM_ID=<numeric_telegram_user_id>
API_OWNER_TELEGRAM_ID=8524573838
BOT_DB_PATH=/app/data/bot_state.sqlite3
TARGET_CHAT_USERNAME=Pixel_Mediair
IDLE_MINUTES=15
TOPIC_COOLDOWN_MINUTES=60
REPLY_COOLDOWN_SECONDS=60
CONVERSATION_TTL_MINUTES=15
CONVERSATION_MAX_MESSAGES=12
CONVERSATION_HISTORY_TTL_DAYS=30
USER_MEMORY_TTL_DAYS=30
USER_MEMORY_MAX_ITEMS=5
WEEKLY_TOPIC_INTERVAL_DAYS=7
INTERACTION_COOLDOWN_SECONDS=120
WEEKLY_INTERACTION_INTERVAL_DAYS=7
WEEKLY_INTERACTION_FIRST_DELAY_HOURS=24
WEEKLY_INTERACTION_SPACING_HOURS=84
TOPIC_RETRY_COOLDOWN_SECONDS=900
CHECK_INTERVAL_SECONDS=20
NEWS_SEARCH_ENABLED=true
NEWS_SEARCH_MAX_RESULTS=4
NEWS_CACHE_TTL_SECONDS=300
```

`TARGET_CHAT_ID` اختیاری است و برای گروه خصوصی یا گروهی که username آن قابل تشخیص نیست استفاده می‌شود. اگر متغیرهای قدیمی `RADOXAI_API_KEY`, `RADOXAI_BASE_URL` یا `RADOXAI_MODEL` در Railway مانده‌اند، آن‌ها را حذف و به‌جایش متغیرهای `XINGCHI_*` را تنظیم کن. متغیرهای قدیمی `FREEMODEL_*` را نیز حذف کن.

## آماده‌سازی تلگرام

توکن را از `@BotFather` بگیر و Privacy Mode را خاموش کن (`/setprivacy` و سپس انتخاب bot و Disable). برای دیدن همهٔ پیام‌های گروه، Telegram نیاز دارد Privacy Mode خاموش باشد یا ربات مدیر گروه باشد. بعد ربات را به `Pixel_Mediair` اضافه کن. برای بررسی وضعیت از `/status` استفاده کن.

## اجرای محلی

```bash
python -m pip install -r requirements.txt
cp .env.example .env
python bot.py
```

## حریم خصوصی و عیب‌یابی

در SQLite روی Volume فقط متن ۱۲ پیام متنی اخیر گروه برای context ذخیره می‌شود و پس از ۳۰ روز منقضی و پاکسازی می‌شود. علاوه بر آن، حداکثر ۵ ترجیح گیمی صریح برای هر عضو تا ۳۰ روز نگه‌داری می‌شود. ربات ترجیحات را از پیام‌هایی که به‌وضوح دربارهٔ علاقه‌مندی به بازی/کنسول‌اند تشخیص می‌دهد؛ برای ثبت دستی از `/rememberme` استفاده کن. هر عضو می‌تواند با `/forgetme` ردیف‌های منتسب به شناسهٔ خودش را پاک کند. این داده‌ها فقط در پاسخ‌های مرتبط به مدل فرستاده می‌شوند؛ context گفتگو فقط برای پاسخ مستقیم به منشن/ریپلای استفاده می‌شود. شناسهٔ سازنده در SQLite یا prompt ذخیره نمی‌شود. `CONVERSATION_TTL_MINUTES` فقط TTL کش موقت RAM است؛ retention پایدار با `CONVERSATION_HISTORY_TTL_DAYS` تنظیم می‌شود.

اگر ربات پیام‌های گروه را نمی‌بیند، Privacy Mode و `TARGET_CHAT_USERNAME` یا `TARGET_CHAT_ID` را بررسی کن. برای خطای مدل، Railway Logs، کلید API provider فعال و وجود شناسهٔ مدل را بررسی کن؛ کلید را در log یا پیام نفرست. برای خطای 402 یا 429، سهمیه، balance و محدودیت همان provider را بررسی کن. اگر یک Bot Token را استفاده می‌کنی، فقط یک worker polling را هم‌زمان اجرا کن.

## منابع فنی

- [Telegram Bot API — sendPoll](https://core.telegram.org/bots/api/methods/sendpoll.md)
- [python-telegram-bot changelog](https://docs.python-telegram-bot.org/en/stable/changelog.html) — نسخهٔ 22.8 برای `correct_option_ids` در quiz
- [Railway Volumes](https://docs.railway.com/volumes)
- [PlayStation Blog](https://blog.playstation.com/)، [Xbox Wire](https://news.xbox.com/en-us/) و [Nintendo News](https://www.nintendo.com/us/whatsnew/)
