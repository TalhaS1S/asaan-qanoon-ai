from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def generate_simple_pdf(title, body):
    buf=BytesIO()
    c=canvas.Canvas(buf,pagesize=A4)
    w,h=A4
    c.setTitle(title)
    c.setFont("Helvetica-Bold",16); c.drawString(50,h-60,title)
    c.setFont("Helvetica",10); y=h-90
    for raw in body.splitlines():
        line=raw.strip()
        if not line:
            y-=8; continue
        while len(line)>95:
            cut=line.rfind(" ",0,95)
            if cut<1: cut=95
            c.drawString(50,y,line[:cut]); line=line[cut:].strip(); y-=14
            if y<60:
                c.showPage(); c.setFont("Helvetica",10); y=h-60
        c.drawString(50,y,line); y-=14
        if y<60:
            c.showPage(); c.setFont("Helvetica",10); y=h-60
    c.save()
    return buf.getvalue()
