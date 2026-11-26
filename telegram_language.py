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

PRIVATE_COMMANDS = (
    ("start", "Start and choose your language", "بلّش واختار اللغة"),
    ("help", "Browse the commands", "شوف الأوامر"),
    ("ar", "Switch to Lebanese Arabic", "حوّل عاللبناني"),
    ("en", "Switch to English", "حوّل عالإنجليزي"),
    ("atlas", "Open the ATLAS dashboard", "افتح لوحة ATLAS"),
    ("coding", "Get coding help", "مساعدة بالبرمجة"),
    ("personal", "Get personal assistance", "رتّب مهامّك"),
    ("creative", "Browse creative modes", "شوف أدوات الإبداع"),
    ("designer", "Plan visual direction", "خطّط للتصميم"),
    ("creator", "Brainstorm ideas", "طلّع أفكار"),
    ("graphic", "Plan graphics and layouts", "خطّط للغرافيك"),
    ("photo", "Plan photo edits", "خطّط لتعديل الصور"),
    ("video", "Plan video edits", "خطّط للمونتاج"),
    ("copyedit", "Edit a draft", "عدّل النص"),
    ("brand", "Plan a brand identity", "اشتغل عالهويّة"),
    ("storyboard", "Plan a storyboard", "رتّب المشاهد"),
    ("skills", "List your saved skills", "شوف مهاراتك"),
    ("addskill", "Save a skill", "ضيف مهارة"),
    ("skill", "Use a saved skill", "استعمل مهارة"),
    ("delskill", "Delete a saved skill", "امحي مهارة"),
    ("remember", "Save a note", "احفظ ملاحظة"),
    ("memory", "List saved notes", "شوف ملاحظاتك"),
    ("forget", "Clear notes and recent chat context", "امحي الملاحظات وآخر المحادثة"),
    ("followup", "Set a reminder", "حطّ تذكير"),
    ("followups", "List reminders", "شوف تذكيراتك"),
    ("cancel", "Cancel a reminder", "الغي تذكير"),
)

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
