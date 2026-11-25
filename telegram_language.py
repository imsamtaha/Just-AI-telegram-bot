"""Lebanese entry points and command descriptions for Telegram."""

ALIASES = {
    "لبناني": "/ar", "عربي": "/ar", "english": "/en",
    "مساعدة": "/help", "أطلس": "/atlas", "مهارات": "/skills",
    "ضيف_مهارة": "/addskill", "فعّل_مهارة": "/skill", "احذف_مهارة": "/delskill",
    "برمجة": "/coding", "barmaje": "/coding", "مساعد": "/personal", "mose3ade": "/personal",
    "إبداع": "/creative", "تصميم": "/designer", "أفكار": "/creator",
    "غرافيك": "/graphic", "صور": "/photo", "فيديو": "/video",
    "تحرير": "/copyedit", "هوية": "/brand", "مشاهد": "/storyboard",
    "تذكّر": "/remember", "ذاكرة": "/memory", "انسى": "/forget",
    "ذكّرني": "/followup", "تذكيرات": "/followups", "إلغاء": "/cancel",
}

LANGUAGE_BUTTONS = {
    "keyboard": [[{"text": "لبناني"}, {"text": "English"}]],
    "resize_keyboard": True,
    "one_time_keyboard": True,
}

STYLE = (
    "For Arabic replies, write natural Lebanese colloquial chat, e.g. يا هلا، شو بدّك، "
    "فيك، هيك، خلّينا. Avoid formal Modern Standard Arabic for everyday chat. "
    "Match Lebanese Arabizi when the user writes that way (e.g. kifak, 3, 7, 2). "
    "Keep code and technical identifiers intact. Honor explicit language or register requests."
)

LEBANESE_HELP = (
    "يا هلا! شو بدّك نعمل اليوم؟\n\n"
    "برمجة (barmaje) — منشتغل عالكود ومنحلّ الأخطاء\n"
    "مساعد (mose3ade) — منرتّب مهامّك وأسبوعك\n"
    "مهارات — شوف شو حافظ من مهارات\n"
    "ضيف_مهارة <اسم> <تعليمات> — احفظ مهارة\n"
    "فعّل_مهارة <اسم> <مهمّة> — استعملها بهالمهمّة\n"
    "احذف_مهارة <اسم> — امحي مهارة\n\n"
    "إبداع — تصميم، أفكار، غرافيك، صور، فيديو، تحرير، هوية، مشاهد\n"
    "أطلس — افتح لوحة ATLAS\n"
    "تذكّر <ملاحظة> | ذاكرة | انسى\n"
    "ذكّرني 30m <مهمّة> | تذكيرات | إلغاء <رقم>\n\n"
    "فيك تكتب اسم الأمر بالعربي مع / أو بلاها. /ar لبناني | /en English"
)
