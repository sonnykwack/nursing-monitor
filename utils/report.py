from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime, timedelta
import sqlite3
import os

# ── 한글 폰트 등록 ───────────────────────────
def register_font():
    font_paths = [
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",  # Mac
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",     # Linux
    ]
    for path in font_paths:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont("Korean", path))
            return True
    return False

HAS_KOREAN = register_font()
FONT_NAME  = "Korean" if HAS_KOREAN else "Helvetica"

# ── DB에서 이번 주 이벤트 가져오기 ───────────
def get_weekly_events(hospital_id: int = 1):
    one_week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    conn   = sqlite3.connect("events.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM events WHERE hospital_id = ? AND timestamp >= ?"
        " ORDER BY timestamp DESC",
        (hospital_id, one_week_ago)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

# ── 리포트 생성 ──────────────────────────────
def generate_report(hospital_id: int = 1):
    events    = get_weekly_events(hospital_id)
    month_dir = f"reports/{hospital_id}/{datetime.now().strftime('%Y-%m')}"
    os.makedirs(month_dir, exist_ok=True)
    filename  = f"{month_dir}/report_{datetime.now().strftime('%Y%m%d')}.pdf"
    doc      = SimpleDocTemplate(filename, pagesize=A4)
    story    = []

    styles   = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        fontName=FONT_NAME,
        fontSize=20,
        spaceAfter=8,
        textColor=colors.HexColor("#2c3e50")
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        fontName=FONT_NAME,
        fontSize=12,
        spaceAfter=24,
        textColor=colors.HexColor("#888888")
    )
    body_style = ParagraphStyle(
        "Body",
        fontName=FONT_NAME,
        fontSize=11,
        spaceAfter=8,
    )

    # 제목
    story.append(Paragraph("스마트 요양 모니터링", title_style))
    story.append(Paragraph(
        f"주간 리포트 — {datetime.now().strftime('%Y년 %m월 %d일')}",
        subtitle_style
    ))

    # 요약
    fall_count  = sum(1 for e in events if "낙상" in e[2])
    sos_count   = sum(1 for e in events if "SOS" in e[2] or "음성" in e[2])
    sound_count = sum(1 for e in events if "비명" in e[2] or "충격음" in e[2])

    story.append(Paragraph("이번 주 요약", ParagraphStyle(
        "SectionTitle", fontName=FONT_NAME, fontSize=14,
        spaceAfter=12, textColor=colors.HexColor("#2c3e50")
    )))

    summary_data = [
        ["항목",         "횟수"],
        ["낙상 감지",    str(fall_count)],
        ["음성 SOS",     str(sos_count)],
        ["이상 소리",    str(sound_count)],
        ["전체 이벤트",  str(len(events))],
    ]

    summary_table = Table(summary_data, colWidths=[300, 100])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),  colors.HexColor("#2c3e50")),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",    (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE",    (0, 0), (-1, -1), 11),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#f9f9f9"), colors.white]),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("PADDING",     (0, 0), (-1, -1), 10),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 24))

    # 이벤트 상세 목록
    story.append(Paragraph("이벤트 상세 목록", ParagraphStyle(
        "SectionTitle", fontName=FONT_NAME, fontSize=14,
        spaceAfter=12, textColor=colors.HexColor("#2c3e50")
    )))

    if events:
        event_data = [["시간", "병실", "유형", "내용"]]
        for e in events:
            event_data.append([
                Paragraph(e[4], body_style),
                Paragraph(e[1], body_style),
                Paragraph(e[2], body_style),
                Paragraph(e[3], body_style),
        ])

        event_table = Table(event_data, colWidths=[130, 50, 80, 200])
        event_table.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0),  colors.HexColor("#2c3e50")),
            ("TEXTCOLOR",   (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",    (0, 0), (-1, -1), FONT_NAME),
            ("FONTSIZE",    (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.HexColor("#f9f9f9"), colors.white]),
            ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("PADDING",     (0, 0), (-1, -1), 8),
        ]))
        story.append(event_table)
    else:
        story.append(Paragraph("이번 주 이벤트가 없습니다.", body_style))

    # PDF 저장
    doc.build(story)
    print(f"✅ 리포트 생성 완료 → {filename}")
    return filename

# 테스트 실행
if __name__ == "__main__":
    generate_report()