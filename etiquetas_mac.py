import sys
import os
import math
import json
import platform
import subprocess
from datetime import datetime, date
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, Toplevel, ttk

# --- AMBIENTE E CONFIGS ---
os.environ['NSRequiresAquaSystemAppearance'] = 'True'

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.units import cm
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.lib.utils import ImageReader
except ImportError:
    _root = tk.Tk(); _root.withdraw()
    messagebox.showerror("Erro", "Instale reportlab: pip install reportlab")
    sys.exit(1)

try:
    from tkmacosx import Button as MacButton
    USAR_MACBUTTON = True
except ImportError:
    USAR_MACBUTTON = False

COR_FUNDO = "#F8FAFC"
COR_CAST = "#744242"
COR_CARD = "#FFFFFF"
COR_TEXTO = "#1E293B"
COR_SUBTEXTO = "#64748B"
COR_AZUL = "#3B82F6"
COR_VERDE = "#10B981"
COR_BORDA = "#E2E8F0"
COR_INPUT_BG = "#F1F5F9"

CONFIG_ETIQUETAS = {
    "Transporte (A5)": {
        "tamanho": A5, "logo_width": 10 * cm,
        "offset_cod": 5.5 * cm, "offset_cliente": 8.0 * cm, "offset_zona": 11.5 * cm,
        "fonte_cod": 16, "fonte_cliente": 24, "fonte_zona": 30, "fonte_vol_num": 85
    },
    "Caixa (10x5cm)": {
        "tamanho": (10 * cm, 5 * cm), "logo_width": 3.5 * cm,
        "offset_cod": 2.2 * cm, "offset_cliente": 3.1 * cm, "offset_zona": 4 * cm,
        "fonte_cod": 9, "fonte_cliente": 12, "fonte_zona": 12, "fonte_enc_val": 9
    }
}

PASTA_USER = Path.home()
CAMINHO_HISTORICO = PASTA_USER / "Vedarame_Historico.json"
CAMINHO_PDF = PASTA_USER / "Vedarame_Etiquetas_Temp.pdf"

def obter_caminho_logo():
    caminho_direto = Path('/Users/andreribeiro/Desktop/Vedarame/Programa Etiquetas/Vedarame_Logo.png')
    if caminho_direto.exists(): return str(caminho_direto)
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    caminho_rel = base / "Vedarame_Logo.png"
    return str(caminho_rel) if caminho_rel.exists() else None

# --- LÓGICA DE DESENHO ---
def escrever_cliente_inteligente(c, texto, x, y_base, largura_maxima, tam_fonte_base, e_caixa):
    prefixo = "CLIENTE: "
    f_bold = "Helvetica-Bold"
    margem_direita = 0.5 * cm if e_caixa else 1 * cm
    espaco_entre = 3 
    c.setFont(f_bold, tam_fonte_base)
    larg_pref = stringWidth(prefixo, f_bold, tam_fonte_base)
    c.drawString(x, y_base, prefixo)
    x_nome = x + larg_pref + espaco_entre
    larg_disponivel = largura_maxima - x_nome - margem_direita
    if e_caixa:
        f_size_nome = tam_fonte_base
        while stringWidth(texto, f_bold, f_size_nome) > larg_disponivel and f_size_nome > 6:
            f_size_nome -= 0.5
        c.setFont(f_bold, f_size_nome)
        c.drawString(x_nome, y_base, texto)
    else:
        palavras = texto.split()
        l1, idx = "", 0
        for i, p in enumerate(palavras):
            teste = f"{l1} {p}".strip()
            if stringWidth(teste, f_bold, tam_fonte_base) <= larg_disponivel:
                l1, idx = teste, i + 1
            else: break
        c.setFont(f_bold, tam_fonte_base)
        c.drawString(x_nome, y_base, l1)
        l2 = " ".join(palavras[idx:])
        if l2:
            larg_disponivel_l2 = largura_maxima - x - margem_direita
            f_l2 = tam_fonte_base
            while stringWidth(l2, f_bold, f_l2) > larg_disponivel_l2 and f_l2 > 12:
                f_l2 -= 0.5
            c.setFont(f_bold, f_l2)
            c.drawString(x, y_base - (f_l2 + 6), l2)

# --- SISTEMA DE HISTÓRICO ---

def carregar_historico():
    if CAMINHO_HISTORICO.exists():
        try:
            with open(CAMINHO_HISTORICO, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return []
    return []

def abrir_historico():
    dados = carregar_historico()
    if not dados:
        messagebox.showinfo("Informação", "Histórico vazio.")
        return
    
    jan = Toplevel(app)
    jan.title("Histórico Recente (Últimas 25)")
    jan.geometry("1200x600")
    jan.configure(bg=COR_FUNDO)
    jan.transient(app); jan.grab_set()

    style = ttk.Style()
    style.configure("Treeview", background=COR_INPUT_BG, fieldbackground=COR_INPUT_BG, rowheight=30)

    frame_tv = tk.Frame(jan, bg=COR_FUNDO)
    frame_tv.pack(expand=True, fill="both", padx=20, pady=(20, 10))

    cols = ("DATA", "TIPO", "CÓD", "CLIENTE", "NOME?", "ZONA", "VOLS", "ENCOMENDAS")
    tv = ttk.Treeview(frame_tv, columns=cols, show="headings", selectmode="browse")
    
    tv.heading("DATA", text="DATA/HORA"); tv.column("DATA", width=130, anchor="center")
    tv.heading("TIPO", text="TIPO"); tv.column("TIPO", width=110, anchor="center")
    tv.heading("CÓD", text="CÓD"); tv.column("CÓD", width=70, anchor="center")
    tv.heading("CLIENTE", text="CLIENTE"); tv.column("CLIENTE", width=200, anchor="w")
    tv.heading("NOME?", text="NOME?"); tv.column("NOME?", width=60, anchor="center")
    tv.heading("ZONA", text="ZONA"); tv.column("ZONA", width=120, anchor="center")
    tv.heading("VOLS", text="VOLS"); tv.column("VOLS", width=50, anchor="center")
    tv.heading("ENCOMENDAS", text="ENCOMENDAS ASSOCIADAS"); tv.column("ENCOMENDAS", width=250, anchor="w")

    sb = ttk.Scrollbar(frame_tv, orient="vertical", command=tv.yview)
    tv.configure(yscrollcommand=sb.set)
    tv.pack(side="left", expand=True, fill="both"); sb.pack(side="right", fill="y")

    # Inserir últimos 25 com ícone de visto
    inicio = max(0, len(dados) - 25)
    for i in range(len(dados) - 1, inicio - 1, -1):
        r = dados[i]
        lista_encs = ", ".join(r.get('encomendas', []))
        # Ícone de Visto ou Vazio
        visto = "[✓]" if r.get('mostrar_nome', True) else "[  ]"
        
        tv.insert("", "end", iid=str(i), values=(
            r.get('data_hora', ''), r.get('tipo', ''), 
            r.get('codigo', ''), r.get('cliente', ''), 
            visto, r.get('zona', ''), 
            r.get('vols', '1'), lista_encs
        ))

    def recuperar_selecao(event=None):
        global lista_encomendas_temp
        item_sel = tv.selection()
        if not item_sel: return
        
        idx = int(item_sel[0])
        reg = dados[idx]
        
        limpar_campos()
        ent_cod.insert(0, str(reg.get('codigo', '')))
        ent_nome.insert(0, str(reg.get('cliente', '')))
        ent_zona.insert(0, str(reg.get('zona', '')))
        ent_vols.delete(0, tk.END)
        ent_vols.insert(0, str(reg.get('vols', '1')))
        var_mostrar_nome.set(reg.get('mostrar_nome', True))
        
        tipo_hist = reg.get('tipo', "Transporte (A5)")
        if tipo_hist in CONFIG_ETIQUETAS:
            combo_tipo.set(tipo_hist)
        
        lista_encomendas_temp = list(reg.get('encomendas', []))
        atualizar_badges()
        jan.destroy()
        ent_encomenda.focus_set()

    tv.bind("<Double-1>", recuperar_selecao)
    tv.bind("<Return>", recuperar_selecao)
    
    btn_frame = tk.Frame(jan, bg=COR_FUNDO)
    btn_frame.pack(fill="x", padx=20, pady=(0, 20))
    if USAR_MACBUTTON:
        MacButton(btn_frame, text="CARREGAR REGISTO SELECIONADO", command=recuperar_selecao, bg=COR_AZUL, fg="white", height=45).pack(fill="x")
    else:
        tk.Button(btn_frame, text="CARREGAR REGISTO SELECIONADO", command=recuperar_selecao, bg=COR_AZUL, fg="white", font=("Helvetica", 10, "bold"), pady=10).pack(fill="x")

# --- LÓGICA GERAL (MANTIDA) ---

def atualizar_badges():
    for w in frame_tags.winfo_children(): w.destroy()
    sorted_badges = sorted(lista_encomendas_temp, key=lambda x: int(x) if x.isdigit() else x)
    for enc in sorted_badges:
        tag = tk.Frame(frame_tags, bg=COR_AZUL, padx=6, pady=2); tag.pack(side="left", padx=2, pady=2)
        tk.Label(tag, text=enc, fg="white", bg=COR_AZUL, font=("Helvetica", 8, "bold")).pack(side="left")
        tk.Button(tag, text="✕", fg="#BFDBFE", bg=COR_AZUL, bd=0, command=lambda e=enc: [lista_encomendas_temp.remove(e), atualizar_badges()]).pack(side="left", padx=(4,0))

def processar_scan(event=None):
    val = ent_encomenda.get().strip().upper()
    if val and val not in lista_encomendas_temp:
        lista_encomendas_temp.append(val); atualizar_badges()
    ent_encomenda.delete(0, tk.END)

def navegar(event):
    if event.keysym == 'Return':
        event.widget.tk_focusNext().focus()
        return 'break'

def limpar_campos():
    global lista_encomendas_temp
    ent_cod.delete(0, tk.END); ent_nome.delete(0, tk.END); ent_zona.delete(0, tk.END)
    ent_vols.delete(0, tk.END); ent_vols.insert(0, "1"); ent_encomenda.delete(0, tk.END)
    var_mostrar_nome.set(True)
    lista_encomendas_temp = []; atualizar_badges(); ent_cod.focus()

def desenhar_logo_seguro(c, lp, ap, tipo):
    logo_path = obter_caminho_logo()
    if not logo_path: return
    try:
        conf = CONFIG_ETIQUETAS[tipo]
        img = ImageReader(logo_path)
        img_w, img_h = img.getSize()
        aspect = img_h / float(img_w)
        draw_w = conf["logo_width"]
        draw_h = draw_w * aspect
        x, y = (lp - draw_w) / 2, ap - draw_h - (0.5 * cm if "Caixa" in tipo else 1.2 * cm)
        c.drawImage(img, x, y, width=draw_w, height=draw_h, mask='auto', preserveAspectRatio=True)
    except: pass

def gerar_etiquetas():
    try:
        tipo = combo_tipo.get(); conf = CONFIG_ETIQUETAS[tipo]
        lp, ap = conf["tamanho"]; c = canvas.Canvas(str(CAMINHO_PDF), pagesize=(lp, ap))
        vols_total = int(ent_vols.get()); e_caixa = "Caixa" in tipo
        mostrar_nome_at = var_mostrar_nome.get()
        
        for i in range(1, vols_total + 1):
            desenhar_logo_seguro(c, lp, ap, tipo)
            c.setFont("Helvetica-Bold", conf["fonte_cod"])
            c.drawString(1.2*cm, ap - conf["offset_cod"], f"CÓD CLIENTE: {ent_cod.get().upper()}")
            if mostrar_nome_at:
                escrever_cliente_inteligente(c, ent_nome.get().upper(), 1.2*cm, ap - conf["offset_cliente"], lp, conf["fonte_cliente"], e_caixa)
            c.setFont("Helvetica-Bold", conf["fonte_zona"])
            c.drawString(1.2*cm, ap - conf["offset_zona"], f"ZONA: {ent_zona.get().upper()}")
            
            if not e_caixa:
                yt = ap - 15*cm
                c.setFont("Helvetica-Bold", 20); c.drawCentredString(lp/4, yt, "VOL:")
                c.setFont("Helvetica-Bold", conf["fonte_vol_num"]); c.drawCentredString(lp/4, yt-3.0*cm, f"{i}/{vols_total}")
                centro_x = lp * 0.72
                c.setFont("Helvetica-Bold", 20); c.drawCentredString(centro_x, yt, "ENC:")
                encs = sorted(lista_encomendas_temp, key=lambda x: int(x) if x.isdigit() else x)[:9]
                if encs:
                    esp_x, esp_y, in_y = 1.9 * cm, 1 * cm, yt - 1.2 * cm
                    num_cols = math.ceil(len(encs) / 3)
                    off_x = (num_cols - 1) * esp_x / 2
                    c.setFont("Helvetica-Bold", 18)
                    for idx, e in enumerate(encs):
                        col, lin = idx // 3, idx % 3
                        c.drawCentredString((centro_x - off_x) + (col * esp_x), in_y - (lin * esp_y), str(e))
            c.setFont("Helvetica", 7); c.drawCentredString(lp/2, 0.3*cm, date.today().strftime('%d/%m/%Y'))
            c.showPage()
        
        c.save()
        if platform.system() == "Darwin": subprocess.run(["open", str(CAMINHO_PDF)])
        else: os.startfile(str(CAMINHO_PDF))
        
        hist = carregar_historico()
        hist.append({
            'data_hora': datetime.now().strftime("%d/%m/%Y %H:%M"), 
            'tipo': tipo, 'codigo': ent_cod.get(), 
            'cliente': ent_nome.get(), 'zona': ent_zona.get(), 
            'vols': ent_vols.get(), 'encomendas': list(lista_encomendas_temp),
            'mostrar_nome': mostrar_nome_at
        })
        with open(CAMINHO_HISTORICO, 'w', encoding='utf-8') as f: json.dump(hist[-50:], f, indent=4)
        limpar_campos()
    except Exception as e: messagebox.showerror("Erro", str(e))

# --- ESTRUTURA APP ---
lista_encomendas_temp = []
app = tk.Tk(); app.title("Vedarame Expedição"); app.geometry("450x880"); app.configure(bg=COR_CARD)

def criar_input(label, highlight=COR_AZUL):
    f = tk.Frame(app, bg=COR_CARD); f.pack(pady=5, padx=40, fill="x")
    tk.Label(f, text=label, font=("Helvetica", 8, "bold"), bg=COR_CARD, fg=COR_SUBTEXTO).pack(anchor="w")
    e = tk.Entry(f, font=("Helvetica", 12), bg=COR_INPUT_BG, relief="flat", highlightthickness=1, highlightbackground=COR_BORDA, highlightcolor=highlight, justify="center")
    e.pack(pady=2, ipady=8, fill="x"); e.bind('<Return>', navegar); return e

tk.Label(app, text="VEDARAME", font=("Helvetica", 22, "bold"), bg=COR_CARD, fg=COR_CAST).pack(pady=(20,0))
combo_tipo = ttk.Combobox(app, values=list(CONFIG_ETIQUETAS.keys()), state="readonly"); combo_tipo.current(0); combo_tipo.pack(pady=10)
ent_cod = criar_input("CÓDIGO CLIENTE"); ent_nome = criar_input("NOME CLIENTE")
var_mostrar_nome = tk.BooleanVar(value=True); tk.Checkbutton(app, text="Imprimir Nome", variable=var_mostrar_nome, bg=COR_CARD, font=("Helvetica", 9)).pack(anchor="w", padx=40)
ent_zona = criar_input("ZONA / LOCALIDADE"); ent_vols = criar_input("Nº VOLUMES"); ent_vols.delete(0, tk.END); ent_vols.insert(0, "1")
ent_encomenda = criar_input("SCAN ENCOMENDA", COR_VERDE); ent_encomenda.bind('<Return>', processar_scan)
frame_tags = tk.Frame(app, bg=COR_CARD); frame_tags.pack(fill="x", padx=40, pady=10)

if USAR_MACBUTTON:
    MacButton(app, text="GERAR E IMPRIMIR", command=gerar_etiquetas, bg=COR_VERDE, fg="white", height=45).pack(pady=10, padx=40, fill="x")
    fb = tk.Frame(app, bg=COR_CARD); fb.pack(padx=40, fill="x")
    MacButton(fb, text="HISTÓRICO", command=abrir_historico, bg=COR_AZUL, fg="white", height=35).pack(side="left", expand=True, fill="x", padx=2)
    MacButton(fb, text="LIMPAR", command=limpar_campos, bg=COR_SUBTEXTO, fg="white", height=35).pack(side="left", expand=True, fill="x", padx=2)
else:
    tk.Button(app, text="GERAR E IMPRIMIR", command=gerar_etiquetas, bg=COR_VERDE, fg="white", font=("Helvetica", 11, "bold")).pack(pady=10, padx=40, fill="x")
    fb = tk.Frame(app, bg=COR_CARD); fb.pack(padx=40, fill="x")
    tk.Button(fb, text="HISTÓRICO", command=abrir_historico, bg=COR_AZUL, fg="white").pack(side="left", expand=True, fill="x", padx=2)
    tk.Button(fb, text="LIMPAR", command=limpar_campos, bg=COR_SUBTEXTO, fg="white").pack(side="left", expand=True, fill="x", padx=2)

app.mainloop()