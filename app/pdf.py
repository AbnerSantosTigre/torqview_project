import os
import tempfile
import platform
import subprocess
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

def gerar_pdf(caminho, grafico_widget, dados_coletados, porta, intervalo, picos):
    temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    grafico_widget.grab().save(temp_img.name, 'png')
    temp_img.close()

    c = canvas.Canvas(caminho, pagesize=A4)
    largura, altura = A4

    def cabecalho(c, altura):
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        c.setFont("Helvetica-Bold", 18)
        c.setFillColor(colors.red)
        c.drawCentredString(largura/2, altura - 2.5*cm, "RELATÓRIO DE TORQUE - TORQVIEW")
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        c.drawRightString(largura - 2*cm, altura - 2*cm, f"Gerado em: {agora}")
        return altura - 5*cm

    y = cabecalho(c, altura)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, y, f"Porta: {porta}  Leituras: {len(dados_coletados)}  Intervalo: {intervalo}s")
    y -= 1*cm

    c.drawImage(temp_img.name, 2*cm, y - 8*cm, width=16*cm, height=8*cm)
    y -= 9*cm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, y, "Estatísticas:")
    y -= 0.7*cm

    c.setFont("Helvetica", 10)
    c.drawString(2*cm, y, f"Mínimo: {min(dados_coletados):.2f}  Máximo: {max(dados_coletados):.2f}  Média: {sum(dados_coletados)/len(dados_coletados):.2f}")
    y -= 1*cm

    if picos:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2*cm, y, "Picos Registrados:")
        y -= 0.7*cm

        dados = [["Pico", "Porta", "Sentido", "Hora"]] + picos
        tabela = Table(dados, colWidths=[3*cm, 3*cm, 3*cm, 3*cm])
        estilo = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d32f2f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ])
        tabela.setStyle(estilo)
        tabela.wrapOn(c, largura, altura)
        tabela.drawOn(c, 2*cm, y - len(dados)*0.6*cm)

    c.save()
    os.unlink(temp_img.name)

    try:
        if platform.system() == "Windows":
            os.startfile(caminho)
        elif platform.system() == "Darwin":
            subprocess.call(["open", caminho])
        else:
            subprocess.call(["xdg-open", caminho])
    except Exception:
        pass
