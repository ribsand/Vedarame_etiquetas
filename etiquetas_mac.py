import sys
import os
import math
import json
import platform
import subprocess
import urllib.request
from datetime import datetime, date
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, Toplevel, ttk

# --- CONFIGURAÇÃO DE ATUALIZAÇÃO ---
# Substitui pelo teu link RAW real do GitHub
URL_RAW_GITHUB = "https://raw.githubusercontent.com/ribsand/Vedarame_etiquetas/main/etiquetas_mac.py"
VERSAO_LOCAL = "1.0" 

def verificar_atualizacao():
    """Verifica silenciosamente se há uma versão nova no GitHub."""
    try:
        with urllib.request.urlopen(URL_RAW_GITHUB, timeout=5) as response:
            conteudo_novo = response.read().decode('utf-8')
            for linha in conteudo_novo.split('\n'):
                if 'VERSAO_LOCAL =' in linha:
                    versao_remota = linha.split('"')[1]
                    if versao_remota != VERSAO_LOCAL:
                        if messagebox.askyesno("Actualização", f"Nova versão disponível: {versao_remota}\nActualizar agora?"):
                            executar_update(conteudo_novo)
                    break
    except:
        pass # Falha silenciosa se não houver internet

def executar_update(novo_codigo):
    """Substitui o script atual e reinicia a app."""
    try:
        caminho_atual = os.path.abspath(sys.argv[0])
        with open(caminho_atual, 'w', encoding='utf-8') as f:
            f.write(novo_codigo)
        messagebox.showinfo("Sucesso", "Aplicação actualizada! A reiniciar...")
        os.execv(sys.executable, ['python3'] + sys.argv)
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao actualizar: {e}")

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
    messagebox.showerror("Erro", "Instale reportlab: pip3 install reportlab")
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
    # Caminho específico para o Mac do André
    caminho_direto = Path('/Users/andreribeiro/Desktop/Vedarame/Programa Etiquetas/Vedarame_Logo.png')
    if caminho_direto.exists(): return str(caminho_direto)
    return None

# --- LÓGICA DE DESENHO ---
def escrever_cliente_inteligente(c, texto, x, y_base, largura_maxima, tam_fonte_base, e_caixa):
    prefixo = "CLIENTE: "
    f_bold = "Helvetica-Bold"
    margem_direita = 0.5 * cm if e_caixa else 1 * cm
    c.setFont(f_bold, tam_fonte_base)
    larg_pref = stringWidth(prefixo, f_bold, tam_fonte_base)
    c.drawString(x, y_base, prefixo)
    x_nome = x + larg_pref + 3
    larg_disponivel = largura_maxima - x_nome - margem_direita
    if e_caixa:
        f_size = tam_fonte_base
        while stringWidth(texto, f_bold, f_size) > larg_disponivel and f_size > 6:
            f_size -= 0.5
        c.setFont(f_bold, f_size)
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
            with open(CAMINHO_HISTORICO, 'r', encoding='utf-8') as f: return json.load(f)
        except: return []
    return []

def abrir_historico():
    dados = carregar_historico()
    if not dados:
        messagebox.showinfo("Info", "Histórico vazio."); return
    
    jan = Toplevel(app); jan.title("Histórico Recente (25)"); jan.geometry("1100x600")
    jan.configure(bg=COR_FUNDO); jan.transient(app); jan.grab_set()

    cols = ("DATA", "TIPO", "CÓD", "CLIENTE", "NOME?", "ZONA", "VOLS", "ENCOMENDAS")
    tv = ttk.Treeview(jan, columns=cols, show="headings")
    for col in cols: tv.heading(col, text=col); tv.column(col, anchor="center", width=100)
    tv.column("CLIENTE", width=200, anchor="w"); tv.column("ENCOMENDAS", width=200, anchor="w")
    tv.pack(expand=True, fill="both", padx=20, pady=20)

    inicio = max(0, len(dados) - 25)
    for i in range(len(dados) - 1, inicio - 1, -1):
        r = dados[i]
        visto = "[✓]" if r.get('mostrar_nome', True) else "[  ]"
        tv.insert("", "end", iid=str(i), values=(r.get('data_hora'), r.get('tipo'), r.get('codigo'), r.get('cliente'), visto, r.get('zona'), r.get('vols'), ", ".join(r.get('encomendas', []))))

    def recuperar():
        sel = tv.selection()
        if not sel: return
        reg = dados[int(sel[0])]
        limpar_campos()
        ent_cod.insert(0, reg.get('codigo', ''))
        ent_nome.insert(0, reg.get('cliente', ''))
        ent_zona.insert(0, reg.get('zona', ''))
        ent_vols.delete(0, tk.END); ent_vols.insert(0, reg.get('vols', '1'))
        var_mostrar_nome.set(reg.get('mostrar_nome', True))
        combo_tipo.set(reg.get('tipo', 'Transporte (A5)'))
        global lista_encomendas_temp
        lista_encomendas_temp = list(reg.get('encomendas', []))
        atualizar_badges(); jan.destroy(); ent_encomenda.focus_set()

    tv.bind("<Double-1>", lambda e: recuperar())
    if USAR_MACBUTTON: MacButton(jan, text="CARREGAR", command=recuperar, bg=COR_AZUL, fg="white", height=40).pack(pady=10)

# --- FUNÇÕES GERAIS ---
def atualizar_badges():
    for w in frame_tags.winfo_children(): w.destroy()
    for enc in sorted(lista_encomendas_temp, key=lambda x: int(x) if x.isdigit() else x):
        tag = tk.Frame(frame_tags, bg=COR_AZUL, padx=5, pady=2); tag.pack(side="left", padx=2)
        tk.Label(tag, text=enc, fg="white", bg=COR_AZUL, font=("Helvetica", 8, "bold")).pack(side="left")
        tk.Button(tag, text="✕", fg="white", bg=COR_AZUL, bd=0, command=lambda e=enc: [lista_encomendas_temp.remove(e), atualizar_badges()]).pack(side="left")

def processar_scan(event=None):
    val = ent_encomenda.get().strip().upper()
    if val and val not in lista_encomendas_temp:
        lista_encomendas_temp.append(val); atualizar_badges()
    ent_encomenda.delete(0, tk.END)

def limpar_campos():
    global lista_encomendas_temp
    ent_cod.delete(0, tk.END); ent_nome.delete(0, tk.END); ent_zona.delete(0, tk.END)
    ent_vols.delete(0, tk.END); ent_vols.insert(0, "1"); ent_encomenda.delete(0, tk.END)
    var_mostrar_nome.set(True); lista_encomendas_temp = []; atualizar_badges(); ent_cod.focus()

def gerar_etiquetas():
    try:
        tipo = combo_tipo.get(); conf = CONFIG_ETIQUETAS[tipo]
        c = canvas.Canvas(str(CAMINHO_PDF), pagesize=conf["tamanho"])
        lp, ap = conf["tamanho"]; vols = int(ent_vols.get())
        
        for i in range(1, vols + 1):
            logo = obter_caminho_logo()
            if logo:
                img = ImageReader(logo); iw, ih = img.getSize(); aspect = ih/iw
                dw = conf["logo_width"]; dh = dw * aspect
                c.drawImage(img, (lp-dw)/2, ap-dh-(1.2*cm), width=dw, height=dh, mask='auto')
            
            c.setFont("Helvetica-Bold", conf["fonte_cod"])
            c.drawString(1.2*cm, ap-conf["offset_cod"], f"CÓD CLIENTE: {ent_cod.get().upper()}")
            if var_mostrar_nome.get():
                escrever_cliente_inteligente(c, ent_nome.get().upper(), 1.2*cm, ap-conf["offset_cliente"], lp, conf["fonte_cliente"], "Caixa" in tipo)
            
            c.setFont("Helvetica-Bold", conf["fonte_zona"])
            c.drawString(1.2*cm, ap-conf["offset_zona"], f"ZONA: {ent_zona.get().upper()}")
            
            if "Caixa" not in tipo:
                c.setFont("Helvetica-Bold", 20); c.drawCentredString(lp/4, ap-15*cm, "VOL:")
                c.setFont("Helvetica-Bold", conf["fonte_vol_num"]); c.drawCentredString(lp/4, ap-18*cm, f"{i}/{vols}")
                encs = sorted(lista_encomendas_temp, key=lambda x: int(x) if x.isdigit() else x)[:9]
                c.setFont("Helvetica-Bold", 20); c.drawCentredString(lp*0.72, ap-15*cm, "ENC:")
                c.setFont("Helvetica-Bold", 18)
                for idx, e in enumerate(encs):
                    c.drawCentredString(lp*0.72 + (idx//3-1)*1.9*cm, ap-16.2*cm-(idx%3*1*cm), str(e))
            
            c.setFont("Helvetica", 7); c.drawCentredString(lp/2, 0.5*cm, date.today().strftime('%d/%m/%Y'))
            c.showPage()
        
        c.save()
        subprocess.run(["open", str(CAMINHO_PDF)])
        
        h = carregar_historico()
        h.append({'data_hora': datetime.now().strftime("%d/%m/%Y %H:%M"), 'tipo': tipo, 'codigo': ent_cod.get(), 'cliente': ent_nome.get(), 'zona': ent_zona.get(), 'vols': ent_vols.get(), 'encomendas': list(lista_encomendas_temp), 'mostrar_nome': var_mostrar_nome.get()})
        with open(CAMINHO_HISTORICO, 'w') as f: json.dump(h[-50:], f)
        limpar_campos()
    except Exception as e: messagebox.showerror("Erro", str(e))

# --- INTERFACE ---
lista_encomendas_temp = []
app = tk.Tk(); app.title(f"Vedarame Mac - V{VERSAO_LOCAL}"); app.geometry("450x850"); app.configure(bg=COR_CARD)
app.after(1000, verificar_atualizacao)

def criar_in(txt):
    f = tk.Frame(app, bg=COR_CARD); f.pack(pady=5, padx=40, fill="x")
    tk.Label(f, text=txt, font=("Helvetica", 8, "bold"), bg=COR_CARD, fg=COR_SUBTEXTO).pack(anchor="w")
    e = tk.Entry(f, font=("Helvetica", 12), bg=COR_INPUT_BG, bd=0, highlightthickness=1, highlightbackground=COR_BORDA, justify="center")
    e.pack(pady=2, ipady=8, fill="x"); return e

tk.Label(app, text="VEDARAME", font=("Helvetica", 24, "bold"), bg=COR_CARD, fg=COR_CAST).pack(pady=20)
combo_tipo = ttk.Combobox(app, values=list(CONFIG_ETIQUETAS.keys()), state="readonly"); combo_tipo.current(0); combo_tipo.pack(pady=5)
ent_cod = criar_in("CÓDIGO CLIENTE"); ent_nome = criar_in("NOME CLIENTE")
var_mostrar_nome = tk.BooleanVar(value=True); tk.Checkbutton(app, text="Imprimir Nome", variable=var_mostrar_nome, bg=COR_CARD).pack()
ent_zona = criar_in("ZONA / LOCALIDADE"); ent_vols = criar_in("Nº VOLUMES"); ent_vols.insert(0, "1")
ent_encomenda = criar_in("SCAN ENCOMENDA (ENTER)"); ent_encomenda.bind("<Return>", processar_scan)
frame_tags = tk.Frame(app, bg=COR_CARD); frame_tags.pack(pady=10, padx=40, fill="x")

if USAR_MACBUTTON:
    MacButton(app, text="GERAR E IMPRIMIR", command=gerar_etiquetas, bg=COR_VERDE, fg="white", height=50).pack(pady=10, padx=40, fill="x")
    MacButton(app, text="HISTÓRICO", command=abrir_historico, bg=COR_AZUL, fg="white", height=40).pack(pady=5, padx=40, fill="x")
    MacButton(app, text="LIMPAR", command=limpar_campos, bg=COR_SUBTEXTO, fg="white", height=40).pack(pady=5, padx=40, fill="x")

app.mainloop()