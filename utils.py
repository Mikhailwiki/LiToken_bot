import io
import qrcode
import pymorphy3

from openpyxl import Workbook


async def make_qrcode(to_chat_id: int, amount: int) -> io.BytesIO:
    url = f'https://t.me/LiToken_bot?start=send_{to_chat_id}_{amount}'
    qrcode_img = qrcode.make(url)
    buf = io.BytesIO()
    qrcode_img.save(buf)
    buf.seek(0)
    return buf


async def agree_with_num(word: str, number: int) -> str:
    morph = pymorphy3.MorphAnalyzer()
    return morph.parse(word)[0].make_agree_with_number(number).word


async def get_table(table) -> io.BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = 'Пользователи и балансы'

    for row, (coins, username) in enumerate(table):
        row += 1
        ws[f'A{row}'] = username
        ws[f'B{row}'] = str(coins)

    excel_file = io.BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    return excel_file
