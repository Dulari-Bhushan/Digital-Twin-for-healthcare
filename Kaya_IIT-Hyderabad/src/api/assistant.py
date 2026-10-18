"""Patient assistant: safety rules that run in code before and after the language model.

Order of play for every message:
  1. Emergency words        -> fixed message in the user's language; the model is never called.
  2. Medicine or dose asks  -> fixed refusal that sends the patient to their doctor; the model is never called.
  3. App navigation         -> a tab switch and a short confirmation; the model is never called.
  4. Otherwise the model answers from the patient's own twin summary and a glossary, then its reply is checked for dose
     advice and trimmed.
"""
from __future__ import annotations

import re

LANGS = ("en", "hi", "te", "kn")

EMERGENCY_RE = re.compile(
    r"chest pain|can'?t breathe|cannot breathe|short(ness)? of breath|faint|unconscious|passed out|seizure|convuls|stroke|"
    r"vomiting blood|very low sugar|severe low|heart attack|"
    r"सीने में दर्द|साँस नहीं|सांस नहीं|साँस लेने में|बेहोश|चक्कर|दौरा|दिल का दौरा|"
    r"ఛాతీ నొప్పి|ఊపిరి|స్పృహ తప్ప|మూర్ఛ|గుండెపోటు|"
    r"ಎದೆ ನೋವು|ಉಸಿರಾಟ|ಉಸಿರು|ಪ್ರಜ್ಞೆ|ಮೂರ್ಛೆ|ಹೃದಯಾಘಾತ",
    re.IGNORECASE,
)
MEDICINE_RE = re.compile(
    r"insulin|\bdose\b|\bdosage\b|\bunits?\b|metformin|tablet|\bpills?\b|medicine|medication|prescription|glimepiride|"
    r"इंसुलिन|खुराक|दवा|दवाई|गोली|मेटफॉर्मिन|"
    r"ఇన్సులిన్|మోతాదు|మందు|మాత్ర|మెట్‌ఫార్మిన్|"
    r"ಇನ್ಸುಲಿನ್|ಡೋಸ್|ಔಷಧ|ಮಾತ್ರೆ|ಮೆಟ್‌ಫಾರ್ಮಿನ್",
    re.IGNORECASE,
)
DOSE_ADVICE_RE = re.compile(
    r"\b\d+(\.\d+)?\s*(mg|mcg|ml)(?!\s*/)\b|\b\d+(\.\d+)?\s*(units?|iu)\b|"
    r"(increase|decrease|reduce|stop|skip|double|start)\s+(your|the)?\s*(insulin|metformin|medicine|medication|dose)",
    re.IGNORECASE,
)

EMERGENCY_MSG = {
    "en": "This could be an emergency. Please call 108 or your local emergency number, or go to the nearest hospital now. Do not wait for the app.",
    "hi": "यह आपातकाल हो सकता है। कृपया अभी 108 पर कॉल करें या नज़दीकी अस्पताल जाएँ। ऐप का इंतज़ार न करें।",
    "te": "ఇది అత్యవసర పరిస్థితి కావచ్చు. దయచేసి వెంటనే 108కి కాల్ చేయండి లేదా దగ్గరి ఆసుపత్రికి వెళ్ళండి. యాప్ కోసం వేచి ఉండకండి.",
    "kn": "ಇದು ತುರ್ತು ಪರಿಸ್ಥಿತಿ ಆಗಿರಬಹುದು. ದಯವಿಟ್ಟು ಈಗಲೇ 108ಕ್ಕೆ ಕರೆ ಮಾಡಿ ಅಥವಾ ಹತ್ತಿರದ ಆಸ್ಪತ್ರೆಗೆ ಹೋಗಿ. ಆ್ಯಪ್‌ಗಾಗಿ ಕಾಯಬೇಡಿ.",
}
MEDICINE_MSG = {
    "en": "I can't advise on medicines or doses. Please ask your doctor or pharmacist. I can explain your sugar readings and your habits.",
    "hi": "मैं दवाओं या खुराक पर सलाह नहीं दे सकता। कृपया अपने डॉक्टर या फ़ार्मासिस्ट से पूछें। मैं आपकी शुगर रीडिंग और आदतें समझा सकता हूँ।",
    "te": "నేను మందులు లేదా మోతాదుల గురించి సలహా ఇవ్వలేను. దయచేసి మీ డాక్టర్ లేదా ఫార్మసిస్ట్‌ను అడగండి. మీ షుగర్ రీడింగులను, అలవాట్లను వివరించగలను.",
    "kn": "ನಾನು ಔಷಧ ಅಥವಾ ಡೋಸ್ ಬಗ್ಗೆ ಸಲಹೆ ನೀಡಲಾರೆ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ವೈದ್ಯರು ಅಥವಾ ಔಷಧಿಕಾರರನ್ನು ಕೇಳಿ. ನಿಮ್ಮ ಶುಗರ್ ರೀಡಿಂಗ್ ಮತ್ತು ಅಭ್ಯಾಸಗಳನ್ನು ವಿವರಿಸಬಲ್ಲೆ.",
}
FALLBACK_MSG = {
    "en": "I could not answer that just now. Please try again, or ask your doctor.",
    "hi": "मैं अभी इसका जवाब नहीं दे पाया। कृपया फिर कोशिश करें या अपने डॉक्टर से पूछें।",
    "te": "నేను ఇప్పుడు దీనికి సమాధానం ఇవ్వలేకపోయాను. దయచేసి మళ్లీ ప్రయత్నించండి లేదా మీ డాక్టర్‌ను అడగండి.",
    "kn": "ನಾನು ಈಗ ಇದಕ್ಕೆ ಉತ್ತರಿಸಲಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ ಅಥವಾ ನಿಮ್ಮ ವೈದ್ಯರನ್ನು ಕೇಳಿ.",
}

TABS = ["today", "insights", "body", "try"]
TAB_LABEL = {
    "en": ["Today", "Insights", "Your body", "Try a change"],
    "hi": ["आज", "जानकारी", "आपका शरीर", "बदलाव आज़माएँ"],
    "te": ["ఈరోజు", "విశ్లేషణ", "మీ శరీరం", "మార్పు ప్రయత్నించండి"],
    "kn": ["ಇಂದು", "ವಿಶ್ಲೇಷಣೆ", "ನಿಮ್ಮ ದೇಹ", "ಬದಲಾವಣೆ ಪ್ರಯತ್ನಿಸಿ"],
}
OPEN_MSG = {"en": "Opening {tab}.", "hi": "{tab} खोल रहा हूँ।", "te": "{tab} తెరుస్తున్నాను.", "kn": "{tab} ತೆರೆಯುತ್ತಿದ್ದೇನೆ."}
NAV_VERB_RE = re.compile(r"\b(show|open|go to|take me|where|see|view|navigate)\b|दिखा|खोल|कहाँ|कहां|చూపించ|తెరవ|ఎక్కడ|ತೋರಿಸ|ತೆರೆ|ಎಲ್ಲಿ", re.IGNORECASE)
NAV_WORDS = [
    (3, r"try a change|what if|simulat|बदलाव|आज़माएँ|आजमा|మార్పు|ప్రయత్నించ|ಬದಲಾವಣೆ|ಪ್ರಯತ್ನ"),
    (2, r"\bbody\b|liver|kidney|eyes?\b|organ|शरीर|लिवर|किडनी|आँख|आंख|శరీరం|కాలేయం|కిడ్నీ|మూత్రపిండ|కళ్ళు|ದೇಹ|ಯಕೃತ್ತು|ಕಿಡ್ನಿ|ಮೂತ್ರಪಿಂಡ|ಕಣ್ಣು"),
    (1, r"insight|weekly|time in range|graph|chart|जानकारी|साप्ताहिक|सीमा में|విశ్లేషణ|వారం|పరిధిలో|ವಿಶ್ಲೇಷಣೆ|ವಾರ|ವ್ಯಾಪ್ತಿಯಲ್ಲಿ"),
    (0, r"\btoday\b|home|habits?|steps|आज|होम|आदतें|కదలిక|ఈరోజు|అలవాట్లు|ಇಂದು|ಅಭ್ಯಾಸ"),
]

APP_GUIDE = (
    "The app has four tabs at the bottom. Today: your sugar right now, one thing to do today, and your habits. "
    "Insights: your time in the healthy range, day by day. Your body: rings for liver, eyes and kidneys. "
    "Try a change: see what walking or eating less rice could do. The EN, Hindi, Telugu and Kannada buttons at the top change the language. "
    "The microphone speaks to the assistant and the speaker button reads text aloud."
)
GLOSSARY = (
    "Time in range: the share of the day your sugar is between 70 and 180 mg/dL; above 70 percent is a good goal. "
    "Sugar and glucose mean the same here. Low sugar is below 70; high sugar is above 180. "
    "The liver ring is the chance of fat building up in the liver over a year. The eye ring is the chance retinopathy gets worse in two years. "
    "The kidney number is the kidney filter score (eGFR); lower means the kidneys filter less. "
    "Estimates are guidance, not a diagnosis."
)
LANG_NAME = {"en": "English", "hi": "Hindi", "te": "Telugu", "kn": "Kannada"}


def classify(message: str, lang: str) -> dict:
    """Rule-based triage. Returns {'kind': 'emergency'|'medicine'|'navigate'|'chat', ...}."""
    m = message.strip()
    lang = lang if lang in LANGS else "en"
    if EMERGENCY_RE.search(m):
        return {"kind": "emergency", "reply": EMERGENCY_MSG[lang]}
    if MEDICINE_RE.search(m):
        return {"kind": "medicine", "reply": MEDICINE_MSG[lang]}
    if NAV_VERB_RE.search(m):
        for tab, pat in NAV_WORDS:
            if re.search(pat, m, re.IGNORECASE):
                return {"kind": "navigate", "tab": tab, "reply": OPEN_MSG[lang].format(tab=TAB_LABEL[lang][tab])}
    return {"kind": "chat"}


def clean_reply(text: str, lang: str, max_chars: int = 650) -> tuple[str, bool]:
    """Strip formatting, trim, and replace any dose advice. Returns (text, was_blocked)."""
    t = re.sub(r"[*_#`>]+", "", text).strip()
    if DOSE_ADVICE_RE.search(t):
        return MEDICINE_MSG[lang], True
    if len(t) > max_chars:
        cut = t[:max_chars]
        t = cut[: max(cut.rfind("."), cut.rfind("।"), cut.rfind("?"), cut.rfind("!")) + 1] or cut
    return t, False


def patient_context(a: dict, tab: int) -> str:
    """A compact, factual summary of this patient's twin for the model. No names or contact details exist in the data."""
    m, pr = a["metrics"], a["profile"]
    fc, sr = a["forecast"], a["series"]
    k = len(fc["t"]) - 1
    g = sr["glucose"][fc["t"][k]]
    q, p = fc["q"][k], fc["p"][k]
    tl, kp = a["liver"]["timeline"], a["kidney"]["projection"]
    grades = ["no retinopathy", "mild", "moderate", "severe", "proliferative"]
    return (
        f"Patient: {pr['age']:.0f}-year-old {'woman' if pr['sex'] == 'F' else 'man'} with type 2 diabetes for {pr['duration_yrs']} years. "
        f"Sugar now {g:.0f} mg/dL; expected in 2 hours about {g + q[2][1]:.0f} (chance of going above 180: {p[0] * 100:.0f} percent; "
        f"chance of going below 70: {p[1] * 100:.0f} percent). "
        f"Over 14 days: {m['tir'] * 100:.0f} percent of time in range, {m['tar'] * 100:.0f} percent above 180, {m['tbr'] * 100:.1f} percent below 70. "
        f"Liver fat risk over a year: {tl['steatosis'][-1] * 100:.0f} percent. Eyes: {grades[a['eye']['grade']]}, chance of getting worse in 2 years {a['eye']['progression_2y'] * 100:.0f} percent. "
        f"Kidney filter score {pr['labs']['egfr']:.0f}, expected about {kp['egfr'][-1]:.0f} in five years at current habits. "
        f"The patient is currently on the '{['Today', 'Insights', 'Your body', 'Try a change'][tab]}' tab."
    )


def system_prompt(lang: str, context: str) -> str:
    tabs = ", ".join(f"'{x}'" for x in TAB_LABEL.get(lang, TAB_LABEL["en"]))
    return (
        "You are Kaya's friendly helper inside a diabetes app for older adults in India. "
        f"Reply only in {LANG_NAME.get(lang, 'English')}, in at most three short, simple sentences, in plain words, without lists or markdown. "
        "Explain what the numbers and screens mean, and help the person use the app. Be honest and kind: only praise what the numbers support, "
        "and when the numbers are poor, say so gently and suggest one small step such as a short walk after meals and talking to the doctor. "
        "Rules you must never break: never give medicine names, doses or changes; never diagnose; never promise outcomes; "
        "if the person describes a symptom or feels unwell, tell them to contact their doctor. "
        "If you do not know, say so and suggest asking the doctor. Use only the facts below; do not invent numbers.\n\n"
        f"APP: {APP_GUIDE}\nGLOSSARY: {GLOSSARY}\nPATIENT FACTS: {context}"
    )
