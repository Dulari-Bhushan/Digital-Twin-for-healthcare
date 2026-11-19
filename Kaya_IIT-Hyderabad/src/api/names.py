"""Fictional names for the synthetic demo patients (matched to each patient's sex and age).

The names are invented for the demo and do not refer to real people. In Japan mode (the default, see region.py) the patients have Japanese
names: written like Hiroshi Tanaka in English screens and 田中 浩 in Japanese ones (the Japanese patient app greets 田中さん). In India mode they
have North Indian names.
"""
from region import REGION

NAMES_IN = {
    1789: "Kamla Devi", 62: "Harpreet Singh", 1217: "Pooja Verma", 1102: "Mohammed Rafiq", 1688: "Rajesh Sharma",
    302: "Brijmohan Yadav", 1008: "Ramprasad Mishra", 800: "Arjun Malhotra", 496: "Neha Chauhan", 1705: "Savitri Devi",
    1132: "Sunita Agarwal", 1091: "Anil Saxena", 308: "Prakash Joshi", 7: "Sanjay Gupta", 1520: "Vikram Rathore",
    1527: "Meena Tiwari", 507: "Surendra Pratap Singh", 1974: "Imran Qureshi", 1357: "Rakesh Bhatt", 814: "Dilip Pandey",
    1128: "Manoj Dubey", 1636: "Priya Kashyap", 750: "Gopal Chaudhary", 430: "Anjali Mehra",
}

# pid: (name for English screens, name for Japanese screens). Same sex and about the right generation as the Indian name it replaces.
NAMES_JP = {
    7: ("Kenji Yamamoto", "山本 健二"), 62: ("Takashi Nakamura", "中村 隆"), 302: ("Masaru Kobayashi", "小林 勝"), 308: ("Yoshio Kato", "加藤 義雄"),
    430: ("Emi Yoshida", "吉田 恵美"), 496: ("Aya Matsumoto", "松本 彩"), 507: ("Hideo Inoue", "井上 英雄"), 750: ("Koji Kimura", "木村 浩二"),
    800: ("Daisuke Hayashi", "林 大輔"), 814: ("Shinji Shimizu", "清水 慎二"), 1008: ("Tetsuo Yamaguchi", "山口 哲夫"), 1091: ("Hiroyuki Saito", "斎藤 浩之"),
    1102: ("Akira Mori", "森 明"), 1128: ("Naoki Ogawa", "小川 直樹"), 1132: ("Keiko Abe", "阿部 恵子"), 1217: ("Mio Ikeda", "池田 美緒"),
    1357: ("Tomoya Hashimoto", "橋本 智也"), 1520: ("Ryota Ishikawa", "石川 亮太"), 1527: ("Yumi Maeda", "前田 由美"), 1636: ("Yui Sato", "佐藤 結衣"),
    1688: ("Hiroshi Tanaka", "田中 浩"), 1705: ("Fumiko Ono", "小野 文子"), 1789: ("Sachiko Fujita", "藤田 幸子"), 1974: ("Shota Okada", "岡田 翔太"),
}
# the two extra Heart watch patients (messy-data examples), known in the artifacts by their Indian names
EDGE_JP = {"Radha Nair": ("Haruka Sasaki", "佐々木 遥"), "Geeta Pillai": ("Chieko Endo", "遠藤 千恵子")}

# The two patients used in the live demo, chosen for contrast.
DEMO_TAGS = {1688: "Demo: complex case", 1636: "Demo: well controlled"}


def name_of(pid: int) -> str:
    pid = int(pid)
    if REGION == "JP" and pid in NAMES_JP:
        return NAMES_JP[pid][0]
    return NAMES_IN.get(pid, f"Patient {pid}")


def name_ja_of(pid: int) -> str | None:
    """The name for Japanese screens (family name first), or None when the demo is set in India."""
    return NAMES_JP[int(pid)][1] if REGION == "JP" and int(pid) in NAMES_JP else None


def localize_name(old: str, pid: int) -> str:
    """A name baked into an artifact, in the current region's version."""
    if REGION == "JP":
        if int(pid) in NAMES_JP:
            return NAMES_JP[int(pid)][0]
        if old in EDGE_JP:
            return EDGE_JP[old][0]
    return old


def localize_name_ja(old: str, pid: int) -> str | None:
    if REGION == "JP":
        if int(pid) in NAMES_JP:
            return NAMES_JP[int(pid)][1]
        if old in EDGE_JP:
            return EDGE_JP[old][1]
    return None
