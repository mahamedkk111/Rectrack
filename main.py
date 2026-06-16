import os
import csv
import sqlite3
from datetime import datetime

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.list import MDList, OneLineListItem, IconLeftWidget

from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import NoTransition
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.clock import Clock

# ── Window setup ──────────────────────────────────────────────────────────────
Window.keyboard_anim_args = {"d": 0.2, "t": "in_out_expo"}
Window.softinput_mode = "below_target"   # WhatsApp-style: content shifts up

# ── Storage paths ─────────────────────────────────────────────────────────────
POS_FOLDER_PATH = "/storage/emulated/0/pos file"
DB_PATH         = os.path.join(POS_FOLDER_PATH, "pos_data.db")
DOWNLOAD_PATH   = "/storage/emulated/0/Download/"

# ── DB helpers ────────────────────────────────────────────────────────────────

def ensure_pos_folder():
    os.makedirs(POS_FOLDER_PATH, exist_ok=True)

def get_db():
    ensure_pos_folder()
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
                    id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER,
                    type        TEXT,
                    amount      REAL,
                    note        TEXT,
                    dt          TEXT,
                    FOREIGN KEY(customer_id) REFERENCES customers(id))''')
    conn.commit()
    conn.close()

# ── CRUD ──────────────────────────────────────────────────────────────────────

def get_customers():
    conn = get_db()
    names = [r[0] for r in conn.execute(
        "SELECT name FROM customers ORDER BY name COLLATE NOCASE")]
    conn.close()
    return names

def add_customer_db(name):
    conn = get_db()
    try:
        conn.execute("INSERT INTO customers (name) VALUES (?)", (name,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_customer_db(name):
    conn = get_db()
    row = conn.execute("SELECT id FROM customers WHERE name=?", (name,)).fetchone()
    if row:
        cid = row[0]
        conn.execute("DELETE FROM transactions WHERE customer_id=?", (cid,))
        conn.execute("DELETE FROM customers WHERE id=?", (cid,))
        conn.commit()
    conn.close()

def rename_customer_db(old_name, new_name):
    conn = get_db()
    try:
        conn.execute("UPDATE customers SET name=? WHERE name=?", (new_name, old_name))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def add_transaction_db(customer_name, ttype, amount, note, dt):
    conn = get_db()
    row = conn.execute("SELECT id FROM customers WHERE name=?",
                       (customer_name,)).fetchone()
    if not row:
        conn.close()
        return False
    conn.execute(
        "INSERT INTO transactions (customer_id, type, amount, note, dt) VALUES (?,?,?,?,?)",
        (row[0], ttype, amount, note, dt.strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return True

def edit_transaction_db(trans_id, amount, note):
    conn = get_db()
    conn.execute("UPDATE transactions SET amount=?, note=? WHERE id=?",
                 (amount, note, trans_id))
    conn.commit()
    conn.close()

def delete_transaction_db(trans_id):
    conn = get_db()
    conn.execute("DELETE FROM transactions WHERE id=?", (trans_id,))
    conn.commit()
    conn.close()

def get_transactions_db(customer_name, date_from=None, date_to=None):
    conn = get_db()
    row = conn.execute("SELECT id FROM customers WHERE name=?",
                       (customer_name,)).fetchone()
    if not row:
        conn.close()
        return []
    cid = row[0]
    query  = ("SELECT id, type, amount, note, dt FROM transactions "
              "WHERE customer_id=?")
    params = [cid]
    if date_from:
        query  += " AND dt >= ?"
        params.append(date_from.strftime("%Y-%m-%d 00:00:00"))
    if date_to:
        query  += " AND dt <= ?"
        params.append(date_to.strftime("%Y-%m-%d 23:59:59"))
    query += " ORDER BY dt, id"
    txs = []
    for tid, ttype, amount, note, dt_str in conn.execute(query, params):
        txs.append({"id": tid, "type": ttype, "amount": float(amount),
                    "note": note or "",
                    "dt": datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")})
    conn.close()
    return txs

def get_balance(customer_name, date_from=None, date_to=None):
    bal = 0
    for t in get_transactions_db(customer_name, date_from, date_to):
        bal += t["amount"] if t["type"] == "Deposit" else -t["amount"]
    return bal

def get_total_balance():
    return sum(get_balance(n) for n in get_customers())

def get_sorted_customers_by_balance():
    return sorted([(n, get_balance(n)) for n in get_customers()],
                  key=lambda x: x[1], reverse=True)

def fmt(value):
    return "{:,.2f}".format(value)

# ── Export ────────────────────────────────────────────────────────────────────

def export_to_csv(customer_name):
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    path = os.path.join(DOWNLOAD_PATH, f"{customer_name}_transactions.csv")
    txs  = get_transactions_db(customer_name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Time", "Type", "Amount", "Note", "Running Balance"])
        running = 0
        for t in txs:
            running += t["amount"] if t["type"] == "Deposit" else -t["amount"]
            w.writerow([t["dt"].strftime("%Y-%m-%d"), t["dt"].strftime("%H:%M:%S"),
                        t["type"], t["amount"], t["note"], running])
    return path

def export_all_balances_csv():
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    path = os.path.join(DOWNLOAD_PATH, "all_customers_balances.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Customer Name", "Balance"])
        for name, bal in get_sorted_customers_by_balance():
            w.writerow([name, fmt(bal)])
    return path

def export_to_excel(customer_name):
    try:
        import xlsxwriter
    except ImportError:
        return None, "xlsxwriter not installed"
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    path     = os.path.join(DOWNLOAD_PATH, f"{customer_name}_transactions.xlsx")
    txs      = get_transactions_db(customer_name)
    workbook = xlsxwriter.Workbook(path)
    ws       = workbook.add_worksheet()
    for col, h in enumerate(["Date","Time","Type","Amount","Note","Running Balance"]):
        ws.write(0, col, h)
    running = 0
    for row, t in enumerate(txs, 1):
        running += t["amount"] if t["type"] == "Deposit" else -t["amount"]
        ws.write(row, 0, t["dt"].strftime("%Y-%m-%d"))
        ws.write(row, 1, t["dt"].strftime("%H:%M:%S"))
        ws.write(row, 2, t["type"])
        ws.write(row, 3, t["amount"])
        ws.write(row, 4, t["note"])
        ws.write(row, 5, running)
    workbook.close()
    return path, None

def export_all_balances_excel():
    try:
        import xlsxwriter
    except ImportError:
        return None, "xlsxwriter not installed"
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    path     = os.path.join(DOWNLOAD_PATH, "all_customers_balances.xlsx")
    workbook = xlsxwriter.Workbook(path)
    ws       = workbook.add_worksheet()
    ws.write(0, 0, "Customer Name")
    ws.write(0, 1, "Balance")
    for row, (name, bal) in enumerate(get_sorted_customers_by_balance(), 1):
        ws.write(row, 0, name)
        ws.write(row, 1, bal)
    workbook.close()
    return path, None

BUSINESS_NAME = "M KK BIZ HUB"

def export_to_pdf(customer_name, date_from=None, date_to=None):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Table, TableStyle, HRFlowable)
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    except ImportError:
        return None, "reportlab not installed"

    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    safe_name = customer_name.replace(" ", "_")
    path = os.path.join(DOWNLOAD_PATH, f"{safe_name}_statement.pdf")

    txs     = get_transactions_db(customer_name, date_from, date_to)
    opening = 0.0
    if date_from:
        # opening balance = full balance before date_from
        all_txs = get_transactions_db(customer_name)
        for t in all_txs:
            if t["dt"] < date_from:
                opening += t["amount"] if t["type"] == "Deposit" else -t["amount"]
    closing = opening + sum(
        t["amount"] if t["type"] == "Deposit" else -t["amount"] for t in txs)
    total_in  = sum(t["amount"] for t in txs if t["type"] == "Deposit")
    total_out = sum(t["amount"] for t in txs if t["type"] == "Withdraw")

    # ── Colours ───────────────────────────────────────────────────────────────
    DARK_BG   = colors.HexColor("#1A237E")   # deep blue header
    MID_BG    = colors.HexColor("#283593")
    LIGHT_ROW = colors.HexColor("#E8EAF6")
    ALT_ROW   = colors.HexColor("#F5F5F5")
    GREEN     = colors.HexColor("#2E7D32")
    RED       = colors.HexColor("#C62828")
    GREY_LINE = colors.HexColor("#9E9E9E")

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm, bottomMargin=12*mm,
    )
    W = A4[0] - 30*mm   # usable width

    # ── Styles ────────────────────────────────────────────────────────────────
    biz_style  = ParagraphStyle("biz",  fontSize=20, textColor=colors.white,
                                 alignment=TA_CENTER, fontName="Helvetica-Bold",
                                 spaceAfter=2)
    sub_style  = ParagraphStyle("sub",  fontSize=9,  textColor=colors.HexColor("#B3C2F2"),
                                 alignment=TA_CENTER, fontName="Helvetica")
    title_style= ParagraphStyle("title",fontSize=11, textColor=colors.white,
                                 alignment=TA_CENTER, fontName="Helvetica-Bold",
                                 spaceBefore=6, spaceAfter=4)
    label_s    = ParagraphStyle("lbl",  fontSize=8,  textColor=colors.HexColor("#616161"),
                                 fontName="Helvetica")
    value_s    = ParagraphStyle("val",  fontSize=10, textColor=colors.black,
                                 fontName="Helvetica-Bold")
    normal_s   = ParagraphStyle("norm", fontSize=8,  textColor=colors.black,
                                 fontName="Helvetica")
    th_style   = ParagraphStyle("th",   fontSize=8,  textColor=colors.white,
                                 fontName="Helvetica-Bold", alignment=TA_CENTER)
    note_style = ParagraphStyle("note", fontSize=7,  textColor=colors.HexColor("#757575"),
                                 fontName="Helvetica-Oblique")

    story = []

    # ── Header banner ─────────────────────────────────────────────────────────
    header_data = [[
        Paragraph(BUSINESS_NAME, biz_style),
    ]]
    header_tbl = Table(header_data, colWidths=[W])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), DARK_BG),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
    ]))
    story.append(header_tbl)

    # Sub-header: Statement of Account
    sub_data = [[Paragraph("ACCOUNT STATEMENT", title_style)]]
    sub_tbl  = Table(sub_data, colWidths=[W])
    sub_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), MID_BG),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(sub_tbl)
    story.append(Spacer(1, 4*mm))

    # ── Account summary box ───────────────────────────────────────────────────
    generated_str = datetime.now().strftime("%Y-%m-%d  %H:%M")
    period_str    = "All Dates"
    if date_from or date_to:
        df = date_from.strftime("%Y-%m-%d") if date_from else "—"
        dt = date_to.strftime("%Y-%m-%d")   if date_to   else "—"
        period_str = f"{df}  to  {dt}"

    def info_cell(label, value, val_color=colors.black):
        return [Paragraph(label, label_s),
                Paragraph(f'<font color="{val_color.hexval() if hasattr(val_color,"hexval") else "black"}">{value}</font>', value_s)]

    summary_data = [
        [Paragraph("Account Holder", label_s), Paragraph(customer_name, value_s),
         Paragraph("Issued By",      label_s), Paragraph(BUSINESS_NAME, value_s)],
        [Paragraph("Period",         label_s), Paragraph(period_str,    value_s),
         Paragraph("Generated",      label_s), Paragraph(generated_str, value_s)],
        [Paragraph("Opening Balance",label_s), Paragraph(fmt(opening),  value_s),
         Paragraph("Closing Balance",label_s), Paragraph(fmt(closing),  value_s)],
        [Paragraph("Total Deposits", label_s), Paragraph(fmt(total_in), ParagraphStyle("g", fontSize=10, textColor=GREEN, fontName="Helvetica-Bold")),
         Paragraph("Total Withdrawals", label_s), Paragraph(fmt(total_out), ParagraphStyle("r", fontSize=10, textColor=RED, fontName="Helvetica-Bold"))],
    ]
    col_w = W / 4
    sum_tbl = Table(summary_data, colWidths=[col_w*0.9, col_w*1.1, col_w*0.9, col_w*1.1])
    sum_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), LIGHT_ROW),
        ("BOX",           (0,0), (-1,-1), 0.5, GREY_LINE),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#BDBDBD")),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(sum_tbl)
    story.append(Spacer(1, 4*mm))

    # ── Transactions table ────────────────────────────────────────────────────
    col_widths = [W*0.14, W*0.09, W*0.12, W*0.13, W*0.30, W*0.13, W*0.09]
    headers = [Paragraph(h, th_style) for h in
               ["Date", "Time", "Type", "Amount", "Note", "Running Bal", "Ref#"]]
    table_data = [headers]

    running = opening
    for idx, t in enumerate(txs, 1):
        amt_signed = t["amount"] if t["type"] == "Deposit" else -t["amount"]
        running   += amt_signed
        amt_color  = GREEN if t["type"] == "Deposit" else RED
        run_color  = GREEN if running >= 0 else RED

        amt_p = Paragraph(
            f'<font color="{"#2E7D32" if t["type"]=="Deposit" else "#C62828"}">'
            f'{"+" if t["type"]=="Deposit" else "-"}{fmt(t["amount"])}</font>',
            ParagraphStyle("a", fontSize=8, fontName="Helvetica-Bold", alignment=TA_RIGHT))
        run_p = Paragraph(
            f'<font color="{"#2E7D32" if running>=0 else "#C62828"}">{fmt(running)}</font>',
            ParagraphStyle("rb", fontSize=8, fontName="Helvetica-Bold", alignment=TA_RIGHT))

        row = [
            Paragraph(t["dt"].strftime("%Y-%m-%d"), normal_s),
            Paragraph(t["dt"].strftime("%H:%M"),    normal_s),
            Paragraph(t["type"],                     normal_s),
            amt_p,
            Paragraph(t["note"] or "",               note_style),
            run_p,
            Paragraph(str(idx),                      ParagraphStyle("ref", fontSize=7,
                        fontName="Helvetica", alignment=TA_CENTER,
                        textColor=colors.HexColor("#9E9E9E"))),
        ]
        table_data.append(row)

    if not txs:
        table_data.append([Paragraph("No transactions in this period.", normal_s)]
                          + [""] * 6)

    tx_tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    row_styles = [
        ("BACKGROUND",    (0,0),  (-1,0),  DARK_BG),
        ("TEXTCOLOR",     (0,0),  (-1,0),  colors.white),
        ("FONTNAME",      (0,0),  (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),  (-1,0),  8),
        ("ALIGN",         (0,0),  (-1,-1), "LEFT"),
        ("VALIGN",        (0,0),  (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),  (-1,-1), 4),
        ("BOTTOMPADDING", (0,0),  (-1,-1), 4),
        ("LEFTPADDING",   (0,0),  (-1,-1), 4),
        ("RIGHTPADDING",  (0,0),  (-1,-1), 4),
        ("BOX",           (0,0),  (-1,-1), 0.5, GREY_LINE),
        ("LINEBELOW",     (0,0),  (-1,-1), 0.3, colors.HexColor("#E0E0E0")),
    ]
    for i in range(1, len(table_data)):
        bg = ALT_ROW if i % 2 == 0 else colors.white
        row_styles.append(("BACKGROUND", (0,i), (-1,i), bg))

    tx_tbl.setStyle(TableStyle(row_styles))
    story.append(tx_tbl)
    story.append(Spacer(1, 6*mm))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width=W, thickness=0.5, color=GREY_LINE))
    story.append(Spacer(1, 2*mm))
    footer_style = ParagraphStyle("foot", fontSize=7, textColor=colors.HexColor("#9E9E9E"),
                                  alignment=TA_CENTER, fontName="Helvetica-Oblique")
    story.append(Paragraph(
        f"This statement was generated by {BUSINESS_NAME} on {generated_str}. "
        f"For queries, contact your account manager.",
        footer_style))

    doc.build(story)
    return path, None

# ── Reusable snackbar ─────────────────────────────────────────────────────────

def snack(msg):
    Snackbar(text=msg, snackbar_x=dp(8), snackbar_y=dp(8),
             size_hint_x=0.95).open()

# ── Dialog helpers ────────────────────────────────────────────────────────────

def confirm_dialog(title, text, on_confirm):
    dlg = MDDialog(
        title=title, text=text,
        buttons=[
            MDFlatButton(text="CANCEL",
                         on_release=lambda x: dlg.dismiss()),
            MDRaisedButton(text="CONFIRM", md_bg_color=(0.898, 0.224, 0.208, 1),
                           on_release=lambda x: (dlg.dismiss(), on_confirm())),
        ])
    dlg.open()

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN MENU SCREEN
# ══════════════════════════════════════════════════════════════════════════════

class MainMenu(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name            = "main"
        self.selected_customer = None
        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self):
        root = MDBoxLayout(orientation="vertical")

        # Top bar
        self.toolbar = MDTopAppBar(
            title="Point of Sale",
            md_bg_color=(0.129, 0.588, 0.953, 1),
            specific_text_color=(1, 1, 1, 1),
            elevation=4,
        )
        root.add_widget(self.toolbar)

        # Total balance card
        self.total_card = MDCard(
            padding=dp(8), size_hint=(1, None), height=dp(44),
            md_bg_color=(0.102, 0.737, 0.612, 1), radius=[0],
        )
        self.total_label = MDLabel(
            text="Total: 0.00", theme_text_color="Custom",
            text_color=(1, 1, 1, 1), font_style="Subtitle1", halign="center",
        )
        self.total_card.add_widget(self.total_label)
        root.add_widget(self.total_card)

        # Scrollable body
        scroll = MDScrollView(size_hint=(1, 1))
        body   = MDBoxLayout(orientation="vertical", padding=dp(12),
                             spacing=dp(10), size_hint_y=None)
        body.bind(minimum_height=body.setter("height"))

        # ── Add customer row ───────────────────────────────────────────────
        add_card = MDCard(padding=dp(8), size_hint=(1, None),
                          height=dp(62), radius=[dp(8)])
        add_row  = MDBoxLayout(spacing=dp(8))
        self.add_name_input = MDTextField(
            hint_text="New customer name", size_hint=(0.75, None),
            height=dp(42), mode="rectangle", font_size=sp(13),
        )
        add_btn = MDRaisedButton(
            text="ADD", size_hint=(0.25, None), height=dp(42),
            md_bg_color=(0.259, 0.647, 0.278, 1),
            on_release=self.add_customer, font_size=sp(12),
        )
        add_row.add_widget(self.add_name_input)
        add_row.add_widget(add_btn)
        add_card.add_widget(add_row)
        body.add_widget(add_card)

        # ── Search bar ─────────────────────────────────────────────────────
        search_card = MDCard(padding=dp(8), size_hint=(1, None),
                             height=dp(62), radius=[dp(8)])
        self.search_input = MDTextField(
            hint_text="Search customer…", size_hint=(1, None),
            height=dp(42), mode="rectangle", font_size=sp(13),
            icon_right="magnify",
        )
        self.search_input.bind(text=self.on_search)
        search_card.add_widget(self.search_input)
        body.add_widget(search_card)

        # ── Transaction row ────────────────────────────────────────────────
        trans_card = MDCard(padding=dp(8), size_hint=(1, None),
                            height=dp(62), radius=[dp(8)])
        trans_row  = MDBoxLayout(spacing=dp(6))
        self.amount_input = MDTextField(
            hint_text="Amount", input_filter="float",
            size_hint=(0.28, None), height=dp(42), mode="rectangle",
            font_size=sp(13),
        )
        self.note_input = MDTextField(
            hint_text="Note (optional)", size_hint=(0.42, None),
            height=dp(42), mode="rectangle", font_size=sp(13),
        )
        cin_btn = MDRaisedButton(
            text="C IN", size_hint=(0.15, None), height=dp(42),
            md_bg_color=(0.259, 0.647, 0.278, 1),
            on_release=lambda x: self.add_transaction("Deposit"),
            font_size=sp(11),
        )
        cout_btn = MDRaisedButton(
            text="C OUT", size_hint=(0.15, None), height=dp(42),
            md_bg_color=(1.0, 0.596, 0.0, 1),
            on_release=lambda x: self.add_transaction("Withdraw"),
            font_size=sp(11),
        )
        trans_row.add_widget(self.amount_input)
        trans_row.add_widget(self.note_input)
        trans_row.add_widget(cin_btn)
        trans_row.add_widget(cout_btn)
        trans_card.add_widget(trans_row)
        body.add_widget(trans_card)

        # ── Action buttons ─────────────────────────────────────────────────
        action_card = MDCard(padding=dp(8), size_hint=(1, None),
                             height=dp(56), radius=[dp(8)])
        action_row  = MDBoxLayout(spacing=dp(6))
        for label, color, cb in [
            ("DETAILS",      (0.224, 0.286, 0.671, 1), self.goto_customer),
            ("CSV",          (0.0,   0.588, 0.533, 1), self.export_csv),
            ("EXCEL",        (0.486, 0.122, 0.635, 1), self.export_excel),
        ]:
            btn = MDRaisedButton(text=label, size_hint=(0.33, None),
                                 height=dp(40), md_bg_color=color,
                                 on_release=cb, font_size=sp(11))
            action_row.add_widget(btn)
        action_card.add_widget(action_row)
        body.add_widget(action_card)

        # ── Export-all row ─────────────────────────────────────────────────
        export_card = MDCard(padding=dp(8), size_hint=(1, None),
                             height=dp(56), radius=[dp(8)])
        export_row  = MDBoxLayout(spacing=dp(6))
        for label, color, cb in [
            ("ALL CSV",   (0.298, 0.686, 0.314, 1), self.export_all_csv),
            ("ALL EXCEL", (0.557, 0.141, 0.667, 1), self.export_all_excel),
        ]:
            btn = MDRaisedButton(text=label, size_hint=(0.5, None),
                                 height=dp(40), md_bg_color=color,
                                 on_release=cb, font_size=sp(11))
            export_row.add_widget(btn)
        export_card.add_widget(export_row)
        body.add_widget(export_card)

        # ── All customers balance list ──────────────────────────────────────
        body.add_widget(MDLabel(
            text="All Customers", font_style="Caption",
            size_hint=(1, None), height=dp(24),
            theme_text_color="Secondary",
        ))

        self.balances_list = MDBoxLayout(
            orientation="vertical", size_hint=(1, None),
            spacing=dp(3),
        )
        self.balances_list.bind(minimum_height=self.balances_list.setter("height"))
        body.add_widget(self.balances_list)

        scroll.add_widget(body)
        root.add_widget(scroll)
        self.add_widget(root)

    # ── Logic ──────────────────────────────────────────────────────────────

    def refresh(self):
        self.selected_customer = None
        self.update_balances_list()
        self.update_total_label()

    def update_total_label(self):
        total = get_total_balance()
        color = (0.102, 0.737, 0.612, 1) if total >= 0 else (0.898, 0.224, 0.208, 1)
        self.total_card.md_bg_color = color
        self.total_label.text = f"Total Balance: {fmt(total)}"

    def on_search(self, instance, value):
        self.update_balances_list(filter_text=value.strip().lower())

    def update_balances_list(self, filter_text=""):
        self.balances_list.clear_widgets()
        customers = get_sorted_customers_by_balance()
        if filter_text:
            customers = [(n, b) for n, b in customers
                         if filter_text in n.lower()]
        if not customers:
            self.balances_list.add_widget(MDLabel(
                text="No customers found.", halign="center",
                size_hint=(1, None), height=dp(36),
                theme_text_color="Secondary", font_style="Caption",
            ))
            return
        for name, bal in customers:
            card = MDCard(
                size_hint=(1, None), height=dp(44), radius=[dp(6)],
                padding=(dp(12), 0), ripple_behavior=True,
                md_bg_color=(0.15, 0.15, 0.2, 1),
            )
            card.bind(on_release=lambda x, n=name: self._open_customer_menu(n))
            row = MDBoxLayout()
            name_lbl = MDLabel(
                text=f"[b]{name}[/b]", markup=True,
                theme_text_color="Custom", text_color=(1, 1, 1, 1),
                size_hint=(0.6, 1), font_style="Body2",
            )
            bal_color = (0.302, 0.847, 0.396, 1) if bal >= 0 else (1, 0.42, 0.42, 1)
            bal_lbl = MDLabel(
                text=f"[b]{fmt(bal)}[/b]", markup=True,
                theme_text_color="Custom", text_color=bal_color,
                size_hint=(0.4, 1), halign="right", font_style="Body2",
            )
            row.add_widget(name_lbl)
            row.add_widget(bal_lbl)
            card.add_widget(row)
            self.balances_list.add_widget(card)

    def _open_customer_menu(self, name):
        """Show an action dialog when a customer card is tapped."""
        self.selected_customer = name
        bal = get_balance(name)
        bal_color = "#4DDA65" if bal >= 0 else "#FF6B6B"

        dlg = [None]

        content = MDBoxLayout(
            orientation="vertical", spacing=dp(4),
            size_hint_y=None, padding=(0, dp(4), 0, dp(4)),
        )
        content.bind(minimum_height=content.setter("height"))

        menu_items = [
            ("View Details",    "account-details",   (0.224, 0.286, 0.671, 1), self.goto_customer),
            ("C IN",            "cash-plus",          (0.259, 0.647, 0.278, 1), lambda: self._menu_transaction("Deposit")),
            ("C OUT",           "cash-minus",         (1.0,   0.596, 0.0,   1), lambda: self._menu_transaction("Withdraw")),
            ("Export CSV",      "file-delimited",     (0.0,   0.588, 0.533, 1), self._menu_export_csv),
            ("Export Excel",    "microsoft-excel",    (0.486, 0.122, 0.635, 1), self._menu_export_excel),
            ("Export PDF",      "file-pdf-box",       (0.827, 0.184, 0.184, 1), self._menu_export_pdf),
            ("Delete Customer", "delete",             (0.898, 0.224, 0.208, 1), lambda: self._menu_delete(name)),
        ]

        for label, icon, color, cb in menu_items:
            item = MDCard(
                size_hint=(1, None), height=dp(44),
                md_bg_color=(0.18, 0.18, 0.25, 1),
                radius=[dp(6)], padding=(dp(8), 0),
                ripple_behavior=True,
            )
            item_row = MDBoxLayout(spacing=dp(10))
            icon_lbl = MDLabel(
                text=f"[color={self._hex(color)}][/color]",
                markup=True, size_hint=(None, 1), width=dp(32),
                theme_text_color="Custom", text_color=color,
            )
            txt_lbl = MDLabel(
                text=label, font_style="Body2",
                theme_text_color="Custom", text_color=(1, 1, 1, 1),
            )
            item_row.add_widget(icon_lbl)
            item_row.add_widget(txt_lbl)
            item.add_widget(item_row)

            def make_cb(callback):
                def on_tap(x):
                    dlg[0].dismiss()
                    callback()
                return on_tap

            item.bind(on_release=make_cb(cb))
            content.add_widget(item)

        dlg[0] = MDDialog(
            title=f"[b]{name}[/b]  [color={bal_color}]{fmt(bal)}[/color]",
            type="custom",
            content_cls=content,
            buttons=[MDFlatButton(
                text="CLOSE",
                on_release=lambda x: dlg[0].dismiss(),
            )],
        )
        dlg[0].open()

    @staticmethod
    def _hex(rgba):
        return "{:02X}{:02X}{:02X}".format(
            int(rgba[0]*255), int(rgba[1]*255), int(rgba[2]*255))

    def _menu_transaction(self, ttype):
        """Called from menu — uses amount/note fields already filled in."""
        self.add_transaction(ttype)

    def _menu_export_csv(self):
        if not self._require_selected():
            return
        path = export_to_csv(self.selected_customer)
        snack(f"CSV saved: {path}")

    def _menu_export_pdf(self):
        if not self._require_selected():
            return
        path, err = export_to_pdf(self.selected_customer)
        snack(f"PDF saved: {path}" if path else f"Error: {err}")

    def _menu_export_excel(self):
        if not self._require_selected():
            return
        path, err = export_to_excel(self.selected_customer)
        snack(f"Excel saved: {path}" if path else f"Error: {err}")

    def _menu_delete(self, name):
        def do_del():
            delete_customer_db(name)
            self.selected_customer = None
            self.refresh()
            snack(f"'{name}' deleted.")
        confirm_dialog(
            "Delete Customer",
            f"Delete '{name}' and all their transactions?",
            do_del,
        )

    # ── Customer actions ───────────────────────────────────────────────────

    def add_customer(self, *_):
        name = self.add_name_input.text.strip()
        if not name:
            snack("Enter a customer name.")
            return
        if add_customer_db(name):
            snack(f"'{name}' added.")
            self.add_name_input.text = ""
            self.refresh()
        else:
            snack(f"'{name}' already exists.")

    def _require_selected(self):
        if not self.selected_customer:
            snack("Tap a customer from the list first.")
            return False
        if self.selected_customer not in get_customers():
            snack("Customer not found.")
            return False
        return True

    def add_transaction(self, ttype):
        if not self._require_selected():
            return
        try:
            amount = float(self.amount_input.text.strip())
            if amount <= 0:
                raise ValueError
        except ValueError:
            snack("Enter a valid amount.")
            return
        note = self.note_input.text.strip()
        add_transaction_db(self.selected_customer, ttype, amount, note, datetime.now())
        self.amount_input.text = ""
        self.note_input.text   = ""
        snack(f"{ttype} {fmt(amount)} added for {self.selected_customer}.")
        self.refresh()

    def goto_customer(self, *_):
        if not self._require_selected():
            return
        cs = self.manager.get_screen("customer")
        cs.set_customer(self.selected_customer)
        self.manager.current = "customer"

    def export_csv(self, *_):
        if not self._require_selected():
            return
        path = export_to_csv(self.selected_customer)
        snack(f"CSV saved: {path}")

    def export_excel(self, *_):
        if not self._require_selected():
            return
        path, err = export_to_excel(self.selected_customer)
        snack(f"Excel saved: {path}" if path else f"Error: {err}")

    def export_all_csv(self, *_):
        path = export_all_balances_csv()
        snack(f"CSV saved: {path}")

    def export_all_excel(self, *_):
        path, err = export_all_balances_excel()
        snack(f"Excel saved: {path}" if path else f"Error: {err}")


# ══════════════════════════════════════════════════════════════════════════════
#  CUSTOMER DETAIL SCREEN
# ══════════════════════════════════════════════════════════════════════════════

class CustomerScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name             = "customer"
        self.current_customer = None
        self.date_from        = None
        self.date_to          = None
        self._build_ui()

    def _build_ui(self):
        root = MDBoxLayout(orientation="vertical")

        # Toolbar
        self.toolbar = MDTopAppBar(
            title="Customer Details",
            md_bg_color=(0.129, 0.588, 0.953, 1),
            specific_text_color=(1, 1, 1, 1),
            left_action_items=[["arrow-left", lambda x: self.go_back()]],
            elevation=4,
        )
        root.add_widget(self.toolbar)

        # Balance card
        self.bal_card = MDCard(
            padding=dp(8), size_hint=(1, None), height=dp(44),
            md_bg_color=(0.102, 0.737, 0.612, 1), radius=[0],
        )
        self.bal_label = MDLabel(
            text="", theme_text_color="Custom",
            text_color=(1, 1, 1, 1), font_style="Subtitle1", halign="center",
        )
        self.bal_card.add_widget(self.bal_label)
        root.add_widget(self.bal_card)

        # ── Date filter row ────────────────────────────────────────────────
        filter_card = MDCard(padding=dp(8), size_hint=(1, None),
                             height=dp(62), radius=[0],
                             md_bg_color=(0.13, 0.13, 0.18, 1))
        filter_row  = MDBoxLayout(spacing=dp(6))

        self.from_input = MDTextField(
            hint_text="From YYYY-MM-DD", size_hint=(0.38, None),
            height=dp(42), mode="rectangle", font_size=sp(12),
        )
        self.to_input = MDTextField(
            hint_text="To YYYY-MM-DD", size_hint=(0.38, None),
            height=dp(42), mode="rectangle", font_size=sp(12),
        )
        filter_btn = MDRaisedButton(
            text="FILTER", size_hint=(0.14, None), height=dp(42),
            md_bg_color=(0.129, 0.588, 0.953, 1),
            on_release=self.apply_filter, font_size=sp(11),
        )
        clear_btn = MDFlatButton(
            text="CLEAR", size_hint=(0.10, None), height=dp(42),
            theme_text_color="Custom", text_color=(1, 1, 1, 1),
            on_release=self.clear_filter,
        )
        filter_row.add_widget(self.from_input)
        filter_row.add_widget(self.to_input)
        filter_row.add_widget(filter_btn)
        filter_row.add_widget(clear_btn)
        filter_card.add_widget(filter_row)
        root.add_widget(filter_card)

        # ── Export row (PDF respects date filter) ──────────────────────────
        exp_card = MDCard(padding=(dp(8), dp(4)), size_hint=(1, None),
                          height=dp(46), radius=[0],
                          md_bg_color=(0.11, 0.11, 0.16, 1))
        exp_row  = MDBoxLayout(spacing=dp(6))
        for label, color, cb in [
            ("CSV",   (0.0,   0.588, 0.533, 1), self.detail_export_csv),
            ("EXCEL", (0.486, 0.122, 0.635, 1), self.detail_export_excel),
            ("PDF",   (0.827, 0.184, 0.184, 1), self.detail_export_pdf),
        ]:
            b = MDRaisedButton(text=label, size_hint=(0.33, None), height=dp(36),
                               md_bg_color=color, on_release=cb, font_size=sp(11))
            exp_row.add_widget(b)
        exp_card.add_widget(exp_row)
        root.add_widget(exp_card)

        # Transaction list
        self.trans_scroll = MDScrollView(size_hint=(1, 1))
        self.trans_list   = MDBoxLayout(
            orientation="vertical", size_hint_y=None,
            spacing=dp(6), padding=dp(8),
        )
        self.trans_list.bind(minimum_height=self.trans_list.setter("height"))
        self.trans_scroll.add_widget(self.trans_list)
        root.add_widget(self.trans_scroll)

        self.add_widget(root)

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def set_customer(self, name):
        self.current_customer = name
        self.toolbar.title    = name
        self.date_from        = None
        self.date_to          = None
        self.from_input.text  = ""
        self.to_input.text    = ""
        self._refresh_view()

    def _refresh_view(self):
        bal = get_balance(self.current_customer, self.date_from, self.date_to)
        bal_color = (0.102, 0.737, 0.612, 1) if bal >= 0 else (0.898, 0.224, 0.208, 1)
        self.bal_card.md_bg_color = bal_color
        suffix = ""
        if self.date_from or self.date_to:
            df = self.date_from.strftime("%Y-%m-%d") if self.date_from else "…"
            dt = self.date_to.strftime("%Y-%m-%d")   if self.date_to   else "…"
            suffix = f"  [{df} → {dt}]"
        self.bal_label.text = f"Balance: {fmt(bal)}{suffix}"
        self._build_transactions()

    def apply_filter(self, *_):
        df = self.from_input.text.strip()
        dt = self.to_input.text.strip()
        try:
            self.date_from = datetime.strptime(df, "%Y-%m-%d") if df else None
            self.date_to   = datetime.strptime(dt, "%Y-%m-%d") if dt else None
        except ValueError:
            snack("Use format YYYY-MM-DD for dates.")
            return
        self._refresh_view()

    def clear_filter(self, *_):
        self.date_from       = None
        self.date_to         = None
        self.from_input.text = ""
        self.to_input.text   = ""
        self._refresh_view()

    def detail_export_csv(self, *_):
        path = export_to_csv(self.current_customer)
        snack(f"CSV saved: {path}")

    def detail_export_excel(self, *_):
        path, err = export_to_excel(self.current_customer)
        snack(f"Excel saved: {path}" if path else f"Error: {err}")

    def detail_export_pdf(self, *_):
        path, err = export_to_pdf(
            self.current_customer, self.date_from, self.date_to)
        snack(f"PDF saved: {path}" if path else f"Error: {err}")

    # ── Transaction cards ──────────────────────────────────────────────────

    def _build_transactions(self):
        self.trans_list.clear_widgets()
        records = get_transactions_db(
            self.current_customer, self.date_from, self.date_to)

        if not records:
            self.trans_list.add_widget(MDLabel(
                text="No transactions.", halign="center",
                size_hint=(1, None), height=dp(60),
                theme_text_color="Secondary",
            ))
            return

        running = 0
        for t in records:
            running += t["amount"] if t["type"] == "Deposit" else -t["amount"]

            card = MDCard(
                size_hint=(1, None), height=dp(90),
                padding=dp(8), radius=[dp(8)],
                md_bg_color=(0.15, 0.15, 0.22, 1),
            )
            row = MDBoxLayout(spacing=dp(8))

            # Left info
            left = MDBoxLayout(orientation="vertical", size_hint=(0.58, 1))
            dt   = t["dt"]

            type_color = (0.302, 0.847, 0.396, 1) if t["type"] == "Deposit" \
                         else (1.0, 0.596, 0.0, 1)

            left.add_widget(MDLabel(
                text=dt.strftime("%Y-%m-%d  %H:%M"),
                font_style="Caption", size_hint_y=None, height=dp(16),
                theme_text_color="Secondary",
            ))
            left.add_widget(MDLabel(
                text=f"[b][color={self._hex(type_color)}]{t['type']}: {fmt(t['amount'])}[/color][/b]",
                markup=True, font_style="Body2",
                size_hint_y=None, height=dp(22),
                theme_text_color="Custom", text_color=(1, 1, 1, 1),
            ))
            left.add_widget(MDLabel(
                text=f"[i]{t['note']}[/i]" if t["note"] else "",
                markup=True, font_style="Caption",
                size_hint_y=None, height=dp(16),
                theme_text_color="Secondary",
            ))
            run_color = (0.302, 0.847, 0.396, 1) if running >= 0 else (1, 0.42, 0.42, 1)
            left.add_widget(MDLabel(
                text=f"[color={self._hex(run_color)}]Running: {fmt(running)}[/color]",
                markup=True, font_style="Caption",
                size_hint_y=None, height=dp(16),
                theme_text_color="Custom", text_color=run_color,
            ))

            # Right buttons
            right = MDBoxLayout(orientation="vertical",
                                size_hint=(0.42, 1), spacing=dp(4))
            edit_btn = MDRaisedButton(
                text="EDIT", size_hint=(1, 0.5),
                md_bg_color=(1.0, 0.702, 0.0, 1),
                on_release=lambda x, tid=t["id"]: self.edit_trans(tid),
                font_size=sp(11),
            )
            del_btn = MDRaisedButton(
                text="DELETE", size_hint=(1, 0.5),
                md_bg_color=(0.898, 0.224, 0.208, 1),
                on_release=lambda x, tid=t["id"]: self.delete_trans(tid),
                font_size=sp(11),
            )
            right.add_widget(edit_btn)
            right.add_widget(del_btn)

            row.add_widget(left)
            row.add_widget(right)
            card.add_widget(row)
            self.trans_list.add_widget(card)

    @staticmethod
    def _hex(rgba):
        return "{:02X}{:02X}{:02X}".format(
            int(rgba[0]*255), int(rgba[1]*255), int(rgba[2]*255))

    # ── Edit / Delete dialogs ──────────────────────────────────────────────

    def edit_trans(self, trans_id):
        records = get_transactions_db(self.current_customer)
        t = next((x for x in records if x["id"] == trans_id), None)
        if not t:
            snack("Transaction not found.")
            return

        content = MDBoxLayout(orientation="vertical", spacing=dp(10),
                              size_hint_y=None, height=dp(140))
        amt_in = MDTextField(
            text=str(t["amount"]), hint_text="Amount",
            input_filter="float", mode="rectangle",
        )
        note_in = MDTextField(
            text=t["note"], hint_text="Note", mode="rectangle",
        )
        content.add_widget(amt_in)
        content.add_widget(note_in)

        dlg = [None]

        def do_save(*_):
            try:
                new_amt = float(amt_in.text)
                if new_amt <= 0:
                    raise ValueError
                edit_transaction_db(trans_id, new_amt, note_in.text)
                dlg[0].dismiss()
                self._refresh_view()
                self.manager.get_screen("main").refresh()
                snack("Transaction updated.")
            except ValueError:
                snack("Invalid amount.")

        dlg[0] = MDDialog(
            title="Edit Transaction",
            type="custom", content_cls=content,
            buttons=[
                MDFlatButton(text="CANCEL",
                             on_release=lambda x: dlg[0].dismiss()),
                MDRaisedButton(text="SAVE", on_release=do_save),
            ])
        dlg[0].open()

    def delete_trans(self, trans_id):
        def do_del():
            delete_transaction_db(trans_id)
            self._refresh_view()
            self.manager.get_screen("main").refresh()
            snack("Transaction deleted.")

        confirm_dialog("Delete Transaction",
                       "Are you sure you want to delete this transaction?",
                       do_del)

    def go_back(self):
        self.manager.get_screen("main").refresh()
        self.manager.current = "main"


# ══════════════════════════════════════════════════════════════════════════════
#  APP
# ══════════════════════════════════════════════════════════════════════════════

class POSApp(MDApp):
    def build(self):
        self.theme_cls.theme_style  = "Dark"
        self.theme_cls.primary_palette = "Blue"

        ensure_pos_folder()
        init_db()

        sm = MDScreenManager(transition=NoTransition())
        sm.add_widget(MainMenu())
        sm.add_widget(CustomerScreen())
        return sm

    def on_start(self):
        self.root.get_screen("main").refresh()


if __name__ == "__main__":
    POSApp().run()
