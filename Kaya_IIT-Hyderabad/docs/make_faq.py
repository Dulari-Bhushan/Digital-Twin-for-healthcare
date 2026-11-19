"""Builds the one-page FAQ for visitors (English and Japanese) as HTML and PDF: docs/faq/Kaya_FAQ_en.* and Kaya_FAQ_ja.*

    python docs/make_faq.py

Every number on the page carries a source number that points to the list at the bottom. The facts were checked against those sources
when the page was written; the Kaya results come from the repository README. The text shrinks until it fits one A4 page.
"""
from __future__ import annotations

import asyncio
import html
from pathlib import Path

OUT = Path(__file__).resolve().parent / "faq"

SOURCES = [
    ("1", "JSDT Renal Data Registry, Annual Dialysis Data Report 2022 (Renal Replacement Therapy, 2025)", "https://doaj.org/article/4dc0063c9e1d4489aa9ab59e7320e229"),
    ("2", "Canon Institute for Global Studies, column on dialysis costs (FY2015: ¥1,564 billion in total, ¥4.81 million per patient)", "https://cigs.canon/en/article/20180119_4687.html"),
    ("3", "Claims studies: BMJ Open Diabetes Res Care 2016;4:e000291 (eye exam 35.6%, urine microalbumin 15.4%) and a nationwide claims analysis, Diabetes Res Clin Pract 2019 (46.5% and 19.4%)", "https://drc.bmj.com/content/4/1/e000291"),
    ("4", "MHLW National Health and Nutrition Survey 2016, as reported by NutraIngredients-Asia", "https://www.nutraingredients-asia.com/Article/2017/09/27/Diabetes-in-Japan-Number-of-patients-hits-record-10m"),
    ("5", "MHLW, Specific Health Checkups and Health Guidance, FY2022 results", "https://www.mhlw.go.jp/content/12400000/001255672.pdf"),
    ("6", "MHLW, Annual Report on Health, Labour and Welfare: patient copayment by age", "https://www.mhlw.go.jp/english/wp/wp-hw11/dl/02e.pdf"),
    ("7", "Designated large hospitals: from October 2022 at least ¥7,000 extra for a first visit without a referral letter; each hospital sets its amount (for example Japanese Red Cross Yokohama City Bay Hospital)", ""),
    ("8", "Kaya results: project README and model cards", "https://github.com/Dulari-Bhushan/Digital-Twin-for-healthcare"),
]

EN = {
    "lang": "en", "title": "Kaya",
    "tag": "A digital twin that lets doctors watch every patient with diabetes and act early.",
    "flow_h": "From pain point to solution", "flow_l": "The problem today", "flow_r": "What Kaya does",
    "flow": [
        ("Kidney and eye damage is found late", "Kaya forecasts glucose, kidney, eye and liver risk and alerts the doctor, with the reason"),
        ("Yearly eye and urine tests are skipped", "A screening tracker shows who is overdue and invites them to book"),
        ("Short hours, closed weekends, hard to book", "Booking calendar, remote review of reports, messages and prescriptions"),
        ("Between visits the doctor is blind", "One live priority list with every patient's recent glucose and records"),
        ("Referrals mean paperwork", "A referral letter in Japanese, ready for the doctor to sign"),
    ],
    "facts_h": "The numbers behind it",
    "facts": [
        ("39,683", "people started dialysis in Japan in 2022. Diabetes is the top cause, at 38.7%.", "1", "red"),
        ("≈ ¥4.8 million", "is what dialysis costs per patient each year, about ¥1.6 trillion in all.", "2", "yellow"),
        ("36 to 47%", "of people on diabetes drugs get a yearly eye exam; only about 15 to 19% get a urine albumin test.", "3", "blue"),
        ("Over 10 million", "people in Japan are strongly suspected of having diabetes (2016 survey).", "4", "orange"),
        ("58%", "took the yearly checkup (ages 40 to 74) in FY2022: 82% in employer plans, 37.5% in municipal insurance.", "5", "teal"),
        ("70 to 90%", "of medical costs are paid by insurance: patients pay 30%, 20% at 70 to 74, 10% at 75 and over (more with higher incomes).", "6", "red"),
    ],
    "qa": [
        ("What is Kaya?", "A digital twin of each patient's glucose, kidneys, eyes and liver. The doctor gets one live priority list, alerts with the reason behind them, the patient's records, and can message the patient, send a prescription and try a medicine change on the twin first. The patient gets a simple phone app."),
        ("Who uses it, and who pays?", "The doctor and clinic use it every day. In Japan, insurers and private clinics fund an annual subscription per enrolled patient, because they save most when dialysis is avoided; in India, hospital and lab chains pay. No price is set yet. We will agree it with pilot partners."),
        ("Why kidneys and eyes?", "Diabetes is the top cause of new dialysis [1], yet the yearly tests that catch damage early are often skipped [3]. Kaya links glucose, kidney and eye risk with whether those tests happened, and helps the doctor act."),
        ("How does it help when clinics close early and on weekends?", "Patients can ask for a slot in a calendar at any time and send reports from home. The doctor reviews them remotely, sends advice or a prescription, and asks patients to come in only when it matters. Reception confirms requests, keeps urgent slots, and tells patients automatically if the doctor is called away."),
        ("Does it replace the doctor?", "No. It is decision support. It does not diagnose or advise on doses; the doctor decides and signs. The patient assistant refuses medicine and dose questions and tells anyone with emergency symptoms to call 119."),
        ("How accurate is it?", "On 34 real glucose-sensor recordings, the 2-hour forecast error is 28 mg/dL, against 37 for assuming no change. It catches 72% of low-sugar episodes, a median 45 minutes ahead, at about one false alert per patient-day. It also spots liver fibrosis risk better than the standard FIB-4 score (0.83 vs 0.63). Results are from held-out data and not yet tested in Japan. [8]"),
        ("Is patient data safe?", "Yes. The prototype holds synthetic data only. Kaya is designed around Japan's Act on the Protection of Personal Information (APPI), the government guidelines for the safe management of medical information systems, and the HL7 FHIR standard: patient consent, encrypted storage and transfer, role-based access with an audit log, and no patient names or IDs shared with outside services. A real deployment goes through a full security review first."),
        ("How does it fit Japan's care system?", "Patients usually start at a clinic or pharmacy, and a first visit to a large hospital without a clinic's letter costs at least ¥7,000 extra [7], so the clinic doctor is the right user. Kaya prepares a referral letter (紹介状) in Japanese for the doctor to sign."),
        ("What does a clinic need to start?", "A web browser for the doctor and reception, and a phone for each patient. No new devices or sensors are required. The patient app speaks Japanese and English, with Hindi, Telugu and Kannada also available."),
        ("How is it different from other diabetes apps?", "The apps we found log glucose or coach lifestyle. We did not find one that links glucose, kidney and eye risk and whether the yearly tests happened, in one workspace for the doctor with booking, messaging, prescribing and referral. We looked at public information only; this is to be verified."),
    ],
    "foot": "Prototype with synthetic data. Not a medical device and not a diagnosis: the doctor decides. Figures are quoted from the sources below; Kaya's own results are out-of-sample and not yet tested in Japan.",
    "src_h": "Sources", "team": "Team Kaya · open source (Apache 2.0)",
}

JA = {
    "lang": "ja", "title": "Kaya",
    "tag": "糖尿病の患者さん一人ひとりの状態を医師がいつでも把握し、早めに手を打てるようにするデジタルツイン。",
    "flow_h": "課題から解決まで", "flow_l": "いまの課題", "flow_r": "Kayaができること",
    "flow": [
        ("腎臓や目の障害が見つかるのが遅い", "血糖・腎臓・目・肝臓のリスクを予測し、理由つきで医師に知らせます"),
        ("年1回の目・尿の検査が受けられていない", "検査の遅れを一覧で確認でき、予約をご案内します"),
        ("診療時間が短い、週末は休み、予約が取りにくい", "予約カレンダー、レポートの遠隔確認、メッセージと処方"),
        ("受診の合間は、医師から状態が見えない", "全患者の最近の血糖と記録を、優先順位つきの一覧で確認できます"),
        ("紹介には書類の手間がかかる", "日本語の紹介状を作成し、医師が確認して署名します"),
    ],
    "facts_h": "数字で見る背景",
    "facts": [
        ("39,683人", "2022年に日本で新たに透析を始めた人数。最多の原因は糖尿病で、38.7%を占めます。", "1", "red"),
        ("約480万円", "透析患者1人あたりの年間医療費。全体では年間約1.6兆円です。", "2", "yellow"),
        ("36〜47%", "糖尿病の薬を使っている人のうち、年1回の眼の検査を受けた割合。尿アルブミン検査は約15〜19%にとどまります。", "3", "blue"),
        ("1,000万人以上", "日本で糖尿病が強く疑われる人の数（2016年の調査）。", "4", "orange"),
        ("58%", "2022年度に特定健診（40〜74歳）を受けた人の割合。健保組合は82%、市町村国保は37.5%です。", "5", "teal"),
        ("7〜9割", "医療費のうち医療保険が負担する割合。窓口負担は70歳未満3割、70〜74歳2割、75歳以上1割です（所得が高い方は負担が増えます）。", "6", "red"),
    ],
    "qa": [
        ("Kayaとは何ですか？", "患者さん一人ひとりの血糖、腎臓、目、肝臓の状態を再現するデジタルツインです。医師は、優先順位つきの患者一覧、理由つきのアラート、診療記録を一つの画面で確認でき、患者さんへのメッセージや処方の送信、薬を変えた場合の予測の確認もできます。患者さんは、やさしいスマートフォンアプリを使います。"),
        ("誰が使い、誰が費用を負担しますか？", "日々使うのは医師とクリニックです。日本では、透析を防げたときに最も医療費が減る保険者や民間のクリニックが、加入患者数に応じた年額で負担する想定です（インドでは病院や検査会社のチェーン）。価格はまだ決めておらず、パイロットの協力先と相談して決めます。"),
        ("なぜ腎臓と目なのですか？", "新たに透析を始める人の最多の原因は糖尿病であり［1］、早期発見のための年1回の検査は受けられていないことが多いからです［3］。Kayaは、血糖、腎臓と目のリスク、検査の実施状況をつなげて、医師の次の一手を支えます。"),
        ("診療時間が短く、週末が休みでも役に立ちますか？", "患者さんは、いつでもカレンダーから予約を依頼でき、検査結果を自宅から送れます。医師は遠隔で確認し、助言や処方を送り、本当に必要なときだけ来院をお願いできます。受付は依頼を確認し、緊急用の枠を確保し、医師が急に不在になったときは患者さんに自動で連絡します。"),
        ("医師の代わりになりますか？", "なりません。診断や薬の量の助言は行わない、判断を支援するツールです。決めるのも署名するのも医師です。患者さん向けのアシスタントは、薬や量についての質問には答えず、緊急の症状がある方には119番への連絡を案内します。"),
        ("どのくらい正確ですか？", "実際の血糖センサー記録34人分で、2時間先の血糖予測の誤差は28 mg/dLで、「変化なし」とした場合（37 mg/dL）より小さくなりました。1人1日あたり約1回の誤警報で、低血糖の72%を、中央値で約45分前に検知します。肝線維化のリスクも、標準的なFIB-4（0.63）より高い精度（0.83）で見つけます。結果は未知のデータでの評価で、日本ではまだ検証していません。［8］"),
        ("患者さんのデータは安全ですか？", "はい。プロトタイプが扱うのは架空のデータだけです。Kayaは、個人情報保護法、国の「医療情報システムの安全管理に関するガイドライン」、国際標準のHL7 FHIRに沿って設計しています。患者さんの同意、保存と通信の暗号化、役割ごとのアクセス制限と操作記録、氏名やIDを外部サービスに渡さないことが柱です。実際の運用の前には、セキュリティの審査を行います。"),
        ("日本の医療の仕組みに合いますか？", "患者さんはまず診療所や薬局を受診し、大病院を診療所の紹介状なしで初めて受診すると、7,000円以上の特別料金がかかります［7］。そのため、使う人は診療所の医師です。Kayaは日本語の紹介状を作成し、医師が確認して署名します。"),
        ("始めるのに何が必要ですか？", "医師と受付はウェブブラウザ、患者さんはスマートフォンがあれば始められます。新しい機器やセンサーは必要ありません。患者さん向けアプリは日本語と英語に対応し、ヒンディー語、テルグ語、カンナダ語も使えます。"),
        ("ほかの糖尿病アプリとの違いは？", "私たちが調べた範囲では、多くは血糖の記録や生活指導が中心でした。血糖、腎臓と目のリスク、年1回の検査の実施状況を、医師向けの一つの画面でつなげ、予約・メッセージ・処方・紹介までできるものは見つかっていません。調べたのは公開情報のみで、確認は今後です。"),
    ],
    "foot": "合成データで作ったプロトタイプです。医療機器ではなく、診断は行いません。判断するのは医師です。数字は下記の出典から引用しており、Kaya自身の結果は未知のデータでの評価で、日本ではまだ検証していません。",
    "src_h": "出典", "team": "Team Kaya ・ オープンソース（Apache 2.0）",
}

COLORS = {"red": "#8a8f94", "yellow": "#8a8f94", "blue": "#8a8f94", "orange": "#8a8f94", "teal": "#8a8f94"}   # black and white for printing
DARK = {k: "#4a4f54" for k in COLORS}


def page(c: dict) -> str:
    ja = c["lang"] == "ja"
    font = "'Yu Gothic UI','Yu Gothic','Meiryo','Hiragino Sans','Noto Sans JP','Segoe UI',sans-serif" if ja else "'Segoe UI','Helvetica Neue',Arial,sans-serif"
    colors = list(COLORS.values())
    tiles = "".join(f'<div class="tile" style="border-top-color:{COLORS[col]}"><b style="color:{DARK[col]}">{html.escape(n)}</b><span>{html.escape(t)} <sup>{s}</sup></span></div>' for n, t, s, col in c["facts"])
    rows = "".join(f'<div class="fr"><div class="pn" style="border-left-color:{colors[i % 5]}">{html.escape(a)}</div><div class="ar" style="color:{colors[i % 5]}">&#10140;</div><div class="so" style="background:#f6f7f8;border-color:#b5b9bd">{html.escape(b)}</div></div>' for i, (a, b) in enumerate(c["flow"]))
    flow = f'<h2>{html.escape(c["flow_h"])}</h2><div class="flow"><div class="fh"><span>{html.escape(c["flow_l"])}</span><span></span><span>{html.escape(c["flow_r"])}</span></div>{rows}</div>'
    half = (len(c["qa"]) + 1) // 2

    def qa(items, start):
        return "".join(f'<div class="qa"><h3><i style="background:{colors[(start + i) % 5]}">{start + i + 1}</i>{html.escape(q)}</h3><p>{html.escape(a)}</p></div>' for i, (q, a) in enumerate(items))

    srcs = "".join(f'<li><b>{n}</b> {html.escape(t)}' + (f' <a href="{u}">{html.escape(u.replace("https://", "").split("/")[0])}</a>' if u else "") + "</li>" for n, t, u in SOURCES)
    return f"""<!doctype html><html lang="{c['lang']}"><head><meta charset="utf-8"><title>Kaya FAQ ({c['lang']})</title>
<style>
@page {{ size: A4; margin: 0; }}
:root {{ --fs: 9.4px; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; background: #fff; }}
body {{ font-family: {font}; color: #30353a; }}
.page {{ width: 210mm; height: 297mm; padding: 9mm 10mm 7mm; position: relative; overflow: hidden; font-size: var(--fs); line-height: {1.5 if ja else 1.38}; }}
header {{ display: flex; align-items: center; gap: 12px; border-bottom: 4px solid transparent; border-image: linear-gradient(#9a9fa4,#9a9fa4) 1; padding-bottom: 7px; }}
header img {{ height: 15mm; filter: grayscale(1); }} header h1 {{ margin: 0; font-size: 2.6em; line-height: 1.1; }}
.tag {{ margin: 7px 0 9px; font-size: 1.42em; line-height: 1.3; font-weight: 600; color: #4a4f54; }}
h2 {{ margin: 6px 0 5px; font-size: 1.2em; letter-spacing: .02em; }}
.tiles {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }}
.tile {{ border: 1.5px solid #e3e6e8; border-top: 4px solid; border-radius: 9px; padding: 5px 8px 6px; display: flex; flex-direction: column; gap: 1px; }}
.tile b {{ font-size: 1.85em; line-height: 1.15; }} .tile span {{ font-size: .98em; color: #3c4145; }} sup {{ font-size: .7em; color: #555; font-weight: 700; }}
.flow {{ display: grid; gap: 4px; }}
.fh, .fr {{ display: grid; grid-template-columns: 1fr 1.6em 1.35fr; align-items: stretch; gap: 4px; }}
.fh span {{ font-size: .85em; font-weight: 700; color: #555; text-transform: uppercase; letter-spacing: .05em; }}
.pn {{ background: #f4f5f6; border-left: 5px solid; border-radius: 6px; padding: 3px 8px; font-weight: 600; display: flex; align-items: center; }}
.ar {{ display: flex; align-items: center; justify-content: center; font-size: 1.3em; }}
.so {{ border: 1.5px solid; border-radius: 6px; padding: 3px 8px; display: flex; align-items: center; }}
.cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0 14px; margin-top: 4px; }}
.qa {{ break-inside: avoid; margin-bottom: 6px; }}
.qa h3 {{ margin: 0 0 1px; font-size: 1.1em; display: flex; gap: 6px; align-items: baseline; }}
.qa h3 i {{ flex: none; font-style: normal; color: #fff; font-weight: 800; width: 1.55em; height: 1.55em; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: .86em; transform: translateY(1px); }}
.qa p {{ margin: 0 0 0 calc(1.55em + 6px); color: #3c4145; }}
.note {{ margin-top: 3px; padding: 5px 8px; border-radius: 8px; background: #fbf0cf; color: #5c4a10; font-size: .95em; }}
footer {{ margin-top: 5px; border-top: 1px solid #e3e6e8; padding-top: 4px; }}
footer h4 {{ margin: 0 0 2px; font-size: .95em; }} footer ol {{ list-style: none; margin: 0; padding: 0; columns: 2; column-gap: 14px; font-size: .78em; line-height: 1.28; color: #4a4f54; }}
footer li {{ break-inside: avoid; margin-bottom: 1px; }} footer a {{ color: #4a4f54; text-decoration: none; }}
.team {{ position: absolute; right: 10mm; bottom: 4mm; font-size: .78em; color: #555; }}
</style></head><body><div class="page" id="page">
<header><img src="../poster/img/logo_transparent.png" alt="Kaya"></header>
<div class="tag">{html.escape(c['tag'])}</div>
<h2>{html.escape(c['facts_h'])}</h2><div class="tiles">{tiles}</div>
{flow}
<div class="cols"><div>{qa(c['qa'][:half], 0)}</div><div>{qa(c['qa'][half:], half)}</div></div>
<footer><h4>{html.escape(c['src_h'])}</h4><ol>{srcs}</ol></footer>
<div class="team">{html.escape(c['team'])}</div>
</div></body></html>"""


async def build() -> None:
    from playwright.async_api import async_playwright

    OUT.mkdir(exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome")
        for c in (EN, JA):
            html_path = OUT / f"Kaya_FAQ_{c['lang']}.html"
            html_path.write_text(page(c), encoding="utf-8")
            pg = await b.new_page(viewport={"width": 794, "height": 1123})
            await pg.goto(html_path.as_uri())
            await pg.wait_for_timeout(500)
            fs = 11.8
            while fs > 6.5:                       # shrink the text until everything fits on the page
                await pg.evaluate(f"document.documentElement.style.setProperty('--fs','{fs}px')")
                over = await pg.evaluate("(()=>{const p=document.getElementById('page');return [p.scrollHeight,p.clientHeight,p.scrollWidth,p.clientWidth]})()")
                if over[0] <= over[1] + 1 and over[2] <= over[3] + 1:
                    break
                fs = round(fs - 0.1, 2)
            html_path.write_text(page(c).replace("--fs: 9.4px", f"--fs: {fs}px"), encoding="utf-8")
            await pg.goto(html_path.as_uri())
            await pg.wait_for_timeout(500)
            await pg.pdf(path=str(OUT / f"Kaya_FAQ_{c['lang']}.pdf"), format="A4", print_background=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
            print(c["lang"], "font size", fs, "px")
            await pg.close()
        await b.close()


if __name__ == "__main__":
    asyncio.run(build())
