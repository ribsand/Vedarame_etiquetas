import sys
import os
import math
import json
import subprocess
import urllib.request
import ssl
from datetime import datetime, date
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, Toplevel, ttk

# ─────────────────────────────────────────────
#  VERSÃO E ATUALIZAÇÃO
# ─────────────────────────────────────────────
URL_RAW_GITHUB = "https://raw.githubusercontent.com/ribsand/Vedarame_etiquetas/refs/heads/main/etiquetas_mac.py"
VERSAO_LOCAL = "1.0.1"

def _parse_versao(v: str):
    """Converte string de versão em tuplo de inteiros para comparação segura."""
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except ValueError:
        return (0,)

def verificar_atualizacao():
    """Verifica se existe uma versão mais recente no GitHub."""
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(URL_RAW_GITHUB, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            conteudo_novo = response.read().decode("utf-8")
            for linha in conteudo_novo.split("\n"):
                if "VERSAO_LOCAL =" in linha:
                    partes = linha.split('"')
                    if len(partes) < 2:
                        return
                    versao_remota = partes[1]
                    if _parse_versao(versao_remota) > _parse_versao(VERSAO_LOCAL):
                        if messagebox.askyesno(
                            "Atualização",
                            f"Nova versão disponível: {versao_remota}\nActualizar agora?"
                        ):
                            executar_update(conteudo_novo)
                    return
    except Exception as e:
        print(f"[INFO] Verificação de atualização falhou: {e}")

def executar_update(novo_codigo: str):
    """Substitui o ficheiro atual e reinicia a aplicação de forma segura."""
    try:
        caminho_atual = os.path.abspath(sys.argv[0])
        
        # 1. Criar um backup do ficheiro atual por segurança
        caminho_backup = caminho_atual + ".bak"
        if os.path.exists(caminho_atual):
            os.replace(caminho_atual, caminho_backup)

        # 2. Gravar o novo código
        with open(caminho_atual, "w", encoding="utf-8") as f:
            f.write(novo_codigo)
        
        # 3. No macOS/Linux, garantir que o ficheiro é executável
        if sys.platform != "win32":
            os.chmod(caminho_atual, 0o755)

        messagebox.showinfo("Sucesso", "Aplicação atualizada! A reiniciar...")
        
        # 4. Reiniciar usando subprocess (mais limpo que execv)
        subprocess.Popen([sys.executable, caminho_atual] + sys.argv[1:])
        os._exit(0) 

    except Exception as e:
        # Se falhar, tenta restaurar o backup
        if 'caminho_backup' in locals() and os.path.exists(caminho_backup):
            os.replace(caminho_backup, caminho_atual)
        messagebox.showerror("Erro", f"Falha ao atualizar: {e}")


# ─────────────────────────────────────────────
#  AMBIENTE
# ─────────────────────────────────────────────
os.environ["NSRequiresAquaSystemAppearance"] = "True"

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.units import cm
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.lib.utils import ImageReader
except ImportError:
    _root = tk.Tk()
    _root.withdraw()
    messagebox.showerror("Erro", "Instale reportlab: pip install reportlab")
    sys.exit(1)

try:
    from tkmacosx import Button as MacButton
    USAR_MACBUTTON = True
except ImportError:
    USAR_MACBUTTON = False


# ─────────────────────────────────────────────
#  PALETA DE CORES
# ─────────────────────────────────────────────
COR = {
    "fundo":      "#F6F7F9",
    "card":       "#FFFFFF",
    "cast":       "#6B3A3A",
    "cast_light": "#F9F1F1",
    "verde":      "#16A34A",
    "verde_light":"#F0FDF4",
    "azul":       "#1D4ED8",
    "azul_light": "#EFF6FF",
    "borda":      "#E4E7EC",
    "subtexto":   "#6B7280",
    "texto":      "#111827",
    "input_bg":   "#F6F7F9",
}


# ─────────────────────────────────────────────
#  CONFIG ETIQUETAS
# ─────────────────────────────────────────────
CONFIG_ETIQUETAS = {
    "Transporte (A5)": {
        "tamanho": A5,
        "logo_width":     10 * cm,
        "offset_cod":     5.5 * cm,
        "offset_cliente": 8.0 * cm,
        "offset_zona":    11.5 * cm,
        "fonte_cod":      16,
        "fonte_cliente":  24,
        "fonte_zona":     30,
        "fonte_vol_num":  85,
    },
    "Caixa (10x5cm)": {
        "tamanho": (10 * cm, 5 * cm),
        "logo_width":     3.2 * cm,
        "offset_cod":     1.7 * cm,
        "offset_cliente": 2.3 * cm,
        "offset_zona":    2.9 * cm,
        "fonte_cod":      9,
        "fonte_cliente":  11,
        "fonte_zona":     11,
    },
}

TIPOS = list(CONFIG_ETIQUETAS.keys())


# ─────────────────────────────────────────────
#  CAMINHOS
# ─────────────────────────────────────────────
PASTA_USER       = Path.home()
CAMINHO_HISTORICO = PASTA_USER / "Vedarame_Historico.json"
CAMINHO_PDF       = PASTA_USER / "Vedarame_Etiquetas_Temp.pdf"


def obter_caminho_logo() -> str | None:
    """Devolve o caminho para o logo, procurando em locais padrão."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    candidatos = [
        base / "Vedarame_Logo.png",
        Path(__file__).parent / "Vedarame_Logo.png",
    ]
    for c in candidatos:
        if c.exists():
            return str(c)
    return None


# ─────────────────────────────────────────────
#  HISTÓRICO
# ─────────────────────────────────────────────
def carregar_historico() -> list:
    if not CAMINHO_HISTORICO.exists():
        return []
    try:
        with open(CAMINHO_HISTORICO, "r", encoding="utf-8") as f:
            dados = json.load(f)
            return dados if isinstance(dados, list) else []
    except Exception as e:
        print(f"[AVISO] Erro ao ler histórico: {e}")
        return []

def guardar_historico(entrada: dict):
    """Acrescenta uma entrada ao histórico e guarda."""
    dados = carregar_historico()
    dados.append(entrada)
    try:
        with open(CAMINHO_HISTORICO, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[AVISO] Erro ao guardar histórico: {e}")


# ─────────────────────────────────────────────
#  GERAÇÃO DE PDF
# ─────────────────────────────────────────────
def _desenhar_logo(c, lp: float, ap: float, tipo: str):
    path = obter_caminho_logo()
    if not path:
        return
    try:
        conf = CONFIG_ETIQUETAS[tipo]
        img  = ImageReader(path)
        iw, ih = img.getSize()
        dw = conf["logo_width"]
        dh = dw * (ih / float(iw))
        margem_topo = 0.15 * cm if "Caixa" in tipo else 1.2 * cm
        y = ap - dh - margem_topo
        c.drawImage(img, (lp - dw) / 2, y, width=dw, height=dh,
                    mask="auto", preserveAspectRatio=True)
    except Exception as e:
        print(f"[AVISO] Não foi possível desenhar logo: {e}")


def _escrever_cliente(c, texto: str, x: float, y_base: float,
                       largura_maxima: float, tam_fonte: int, e_caixa: bool):
    """Escreve o prefixo 'CLIENTE:' + nome com ajuste automático de tamanho."""
    prefixo = "CLIENTE: "
    fonte   = "Helvetica-Bold"
    margem  = 0.5 * cm if e_caixa else 1.0 * cm

    c.setFont(fonte, tam_fonte)
    larg_pref = stringWidth(prefixo, fonte, tam_fonte)
    c.drawString(x, y_base, prefixo)

    x_nome        = x + larg_pref + 3
    larg_disp     = largura_maxima - x_nome - margem

    if e_caixa:
        # Caixa: texto numa linha, reduz fonte se necessário
        fs = tam_fonte
        while stringWidth(texto, fonte, fs) > larg_disp and fs > 6:
            fs -= 0.5
        c.setFont(fonte, fs)
        c.drawString(x_nome, y_base, texto)
    else:
        # A5: tenta duas linhas
        palavras = texto.split()
        linha1, idx = "", 0
        for i, p in enumerate(palavras):
            teste = f"{linha1} {p}".strip()
            if stringWidth(teste, fonte, tam_fonte) <= larg_disp:
                linha1, idx = teste, i + 1
            else:
                break
        c.setFont(fonte, tam_fonte)
        c.drawString(x_nome, y_base, linha1)

        linha2 = " ".join(palavras[idx:])
        if linha2:
            larg_disp2 = largura_maxima - x - margem
            fs2 = tam_fonte
            while stringWidth(linha2, fonte, fs2) > larg_disp2 and fs2 > 12:
                fs2 -= 0.5
            c.setFont(fonte, fs2)
            c.drawString(x, y_base - (fs2 + 6), linha2)


def gerar_pdf(tipo: str, cod: str, nome: str, zona: str,
              vols_total: int, mostrar_nome: bool,
              encomendas: list) -> bool:
    """
    Gera o PDF de etiquetas.
    Devolve True em caso de sucesso, False em caso de erro.
    """
    try:
        conf    = CONFIG_ETIQUETAS[tipo]
        lp, ap  = conf["tamanho"]
        e_caixa = "Caixa" in tipo
        x_base  = 0.8 * cm if e_caixa else 1.2 * cm

        c = canvas.Canvas(str(CAMINHO_PDF), pagesize=(lp, ap))

        encs_ord = sorted(encomendas, key=lambda x: (0, int(x), "") if x.isdigit() else (1, 0, x))

        for i in range(1, vols_total + 1):
            _desenhar_logo(c, lp, ap, tipo)

            # Código
            c.setFont("Helvetica-Bold", conf["fonte_cod"])
            c.drawString(x_base, ap - conf["offset_cod"], f"CÓD CLIENTE: {cod}")

            # Nome
            if mostrar_nome:
                _escrever_cliente(c, nome, x_base,
                                  ap - conf["offset_cliente"],
                                  lp, conf["fonte_cliente"], e_caixa)

            # Zona
            c.setFont("Helvetica-Bold", conf["fonte_zona"])
            c.drawString(x_base, ap - conf["offset_zona"], f"ZONA: {zona}")

            if e_caixa:
                # ── LAYOUT CAIXA ──────────────────────────────
                y_vols = ap - 3.4 * cm
                c.setFont("Helvetica-Bold", 9)
                c.drawString(x_base, y_vols, f"VOL: {i}/{vols_total}")
                if encs_ord:
                    texto_encs = "ENC: " + ", ".join(encs_ord)
                    fs = 9
                    while stringWidth(texto_encs, "Helvetica-Bold", fs) > (lp - 1.6 * cm) and fs > 6:
                        fs -= 0.5
                    c.setFont("Helvetica-Bold", fs)
                    c.drawString(x_base, y_vols - 0.5 * cm, texto_encs)
            else:
                # ── LAYOUT A5 ─────────────────────────────────
                yt = ap - 15 * cm

                # Volume
                c.setFont("Helvetica-Bold", 20)
                c.drawCentredString(lp / 4, yt, "VOL:")
                c.setFont("Helvetica-Bold", conf["fonte_vol_num"])
                c.drawCentredString(lp / 4, yt - 3.0 * cm, f"{i}/{vols_total}")

                # Encomendas — grelha 3 × N
                cx = lp * 0.72
                c.setFont("Helvetica-Bold", 20)
                c.drawCentredString(cx, yt, "ENC:")
                if encs_ord:
                    esp_x, esp_y = 1.9 * cm, 1.0 * cm
                    in_y        = yt - 1.2 * cm
                    num_cols    = math.ceil(len(encs_ord[:9]) / 3)
                    off_x       = (num_cols - 1) * esp_x / 2
                    c.setFont("Helvetica-Bold", 18)
                    for idx_e, e in enumerate(encs_ord[:9]):
                        col = idx_e // 3
                        row = idx_e % 3
                        c.drawCentredString((cx - off_x) + col * esp_x,
                                            in_y - row * esp_y, str(e))

            # Data centrada no rodapé
            c.setFont("Helvetica", 6 if e_caixa else 7)
            c.drawCentredString(lp / 2, 0.2 * cm,
                                date.today().strftime("%d/%m/%Y"))
            c.showPage()

        c.save()
        return True

    except Exception as e:
        print(f"[ERRO] Falha ao gerar PDF: {e}")
        return False


# ─────────────────────────────────────────────
#  HELPERS DE INTERFACE
# ─────────────────────────────────────────────
def _btn(parent, texto: str, comando, cor: str, fg: str = "white",
         height: int = 35, **pack_opts):
    """Cria um botão compatível com macOS e Linux."""
    if USAR_MACBUTTON:
        from tkmacosx import Button as MacButton
        b = MacButton(parent, text=texto, command=comando,
                      bg=cor, fg=fg, height=height)
    else:
        b = tk.Button(parent, text=texto, command=comando,
                      bg=cor, fg=fg, relief="flat",
                      font=("Helvetica", 11, "bold"), pady=6)
    b.pack(**pack_opts)
    return b


def _criar_secao(parent, titulo: str):
    """Cria um separador visual com título de secção."""
    frame = tk.Frame(parent, bg=COR["card"])
    frame.pack(fill="x", padx=20, pady=(8, 2))
    tk.Label(frame, text=titulo.upper(),
             font=("Helvetica", 8, "bold"),
             bg=COR["card"], fg=COR["subtexto"]).pack(anchor="w")
    sep = tk.Frame(parent, bg=COR["borda"], height=1)
    sep.pack(fill="x", padx=20, pady=(2, 6))


def _criar_input(parent, label: str, cor_foco: str = None) -> tk.Entry:
    """Cria um campo de input com label."""
    cor_foco = cor_foco or COR["cast"]
    frame = tk.Frame(parent, bg=COR["card"])
    frame.pack(pady=4, padx=20, fill="x")
    tk.Label(frame, text=label,
             font=("Helvetica", 8, "bold"),
             bg=COR["card"], fg=COR["subtexto"]).pack(anchor="w")
    entry = tk.Entry(frame,
                     font=("Helvetica", 12),
                     bg=COR["input_bg"],
                     relief="flat",
                     highlightthickness=1,
                     highlightbackground=COR["borda"],
                     highlightcolor=cor_foco,
                     justify="center")
    entry.pack(pady=2, ipady=8, fill="x")
    return entry


# ─────────────────────────────────────────────
#  APLICAÇÃO PRINCIPAL
# ─────────────────────────────────────────────
class AppVedarame:
    def __init__(self):
        self.encomendas: list[str] = []

        # ── Janela principal ──────────────────
        self.app = tk.Tk()
        self.app.title("Vedarame Expedição")
        self.app.geometry("520x900")
        self.app.resizable(True, True)
        self.app.minsize(480, 700)
        self.app.after(100, lambda: self.app.geometry("520x900"))
        self.app.configure(bg=COR["card"])
        self.app.after(1500, verificar_atualizacao)

        self._construir_ui()
        self.app.mainloop()

    # ── Construção da UI ──────────────────────
    def _construir_ui(self):
        self._ui_header()
        self._ui_tipo()
        self._ui_cliente()
        self._ui_scan()
        self._ui_botoes()
        self._ui_status()

    def _ui_header(self):
        header = tk.Frame(self.app, bg=COR["cast"])
        header.pack(fill="x")
        inner = tk.Frame(header, bg=COR["cast"])
        inner.pack(fill="x", padx=20, pady=14)
        tk.Label(inner, text="VEDARAME",
                 font=("Helvetica", 20, "bold"),
                 bg=COR["cast"], fg="white").pack(side="left")
        tk.Label(inner, text=f"v{VERSAO_LOCAL}",
                 font=("Helvetica", 9),
                 bg=COR["cast"], fg="#C4A0A0").pack(side="right", pady=2)
        tk.Label(header, text="Expedição",
                 font=("Helvetica", 11),
                 bg=COR["cast"], fg="#E8C8C8").pack(anchor="w", padx=20, pady=(0, 12))

    def _ui_tipo(self):
        frame = tk.Frame(self.app, bg=COR["card"])
        frame.pack(fill="x", padx=20, pady=(12, 4))
        tk.Label(frame, text="TIPO DE ETIQUETA",
                 font=("Helvetica", 8, "bold"),
                 bg=COR["card"], fg=COR["subtexto"]).pack(anchor="w", pady=(0, 5))
        self.combo_tipo = ttk.Combobox(frame, values=TIPOS, state="readonly",
                                       font=("Helvetica", 11))
        self.combo_tipo.current(0)
        self.combo_tipo.pack(fill="x", ipady=4)

    def _ui_cliente(self):
        _criar_secao(self.app, "● Dados do Cliente")

        # Código + Volumes na mesma linha
        row = tk.Frame(self.app, bg=COR["card"])
        row.pack(fill="x", padx=20, pady=(0, 4))

        # Código
        col_cod = tk.Frame(row, bg=COR["card"])
        col_cod.pack(side="left", fill="x", expand=True)
        tk.Label(col_cod, text="CÓDIGO CLIENTE",
                 font=("Helvetica", 8, "bold"),
                 bg=COR["card"], fg=COR["subtexto"]).pack(anchor="w")
        self.ent_cod = tk.Entry(col_cod, font=("Helvetica", 12),
                                bg=COR["input_bg"], relief="flat",
                                highlightthickness=1,
                                highlightbackground=COR["borda"],
                                highlightcolor=COR["cast"], justify="center")
        self.ent_cod.pack(fill="x", ipady=8, pady=2)
        self.ent_cod.bind("<Return>", lambda e: self.ent_nome.focus())

        # Volumes
        col_vol = tk.Frame(row, bg=COR["card"])
        col_vol.pack(side="right", padx=(10, 0))
        tk.Label(col_vol, text="VOLUMES",
                 font=("Helvetica", 8, "bold"),
                 bg=COR["card"], fg=COR["subtexto"]).pack(anchor="w")
        vol_ctrl = tk.Frame(col_vol, bg=COR["card"])
        vol_ctrl.pack()

        self.var_vols = tk.IntVar(value=1)

        def _ajustar(d):
            v = max(1, min(99, self.var_vols.get() + d))
            self.var_vols.set(v)

        btn_style = dict(font=("Helvetica", 13, "bold"), fg=COR["cast"],
                         bg=COR["cast_light"], relief="flat",
                         bd=0, highlightthickness=0, width=2,
                         cursor="hand2", activebackground=COR["borda"],
                         activeforeground=COR["cast"])
        tk.Button(vol_ctrl, text="−", command=lambda: _ajustar(-1),
                  **btn_style).pack(side="left", ipady=4)
        tk.Label(vol_ctrl, textvariable=self.var_vols,
                 font=("Helvetica", 16, "bold"),
                 bg=COR["card"], fg=COR["texto"], width=3).pack(side="left")
        tk.Button(vol_ctrl, text="+", command=lambda: _ajustar(1),
                  **btn_style).pack(side="left", ipady=4)

        # Nome
        self.ent_nome = _criar_input(self.app, "NOME CLIENTE")
        self.ent_nome.bind("<Return>", lambda e: self.ent_zona.focus())

        # Checkbox imprimir nome — sem selectcolor para evitar barra preta no macOS
        self.var_mostrar_nome = tk.BooleanVar(value=True)
        tk.Checkbutton(self.app, text="Imprimir nome na etiqueta",
                       variable=self.var_mostrar_nome,
                       bg=COR["card"], fg=COR["subtexto"],
                       font=("Helvetica", 10),
                       activebackground=COR["card"],
                       activeforeground=COR["cast"],
                       bd=0, highlightthickness=0).pack(anchor="w", padx=20, pady=(0, 6))

        # Zona
        self.ent_zona = _criar_input(self.app, "ZONA / LOCALIDADE")
        self.ent_zona.bind("<Return>", lambda e: self.ent_scan.focus())

    def _ui_scan(self):
        _criar_secao(self.app, "● Scan de Encomendas")

        frame_scan = tk.Frame(self.app, bg=COR["card"])
        frame_scan.pack(fill="x", padx=20, pady=(0, 4))
        tk.Label(frame_scan, text="REFERÊNCIA / SCAN",
                 font=("Helvetica", 8, "bold"),
                 bg=COR["card"], fg=COR["subtexto"]).pack(anchor="w")
        self.ent_scan = tk.Entry(frame_scan,
                                 font=("Helvetica", 12, "bold"),
                                 bg=COR["verde_light"],
                                 relief="flat",
                                 highlightthickness=1,
                                 highlightbackground=COR["verde"],
                                 highlightcolor=COR["verde"],
                                 justify="center")
        self.ent_scan.pack(fill="x", ipady=9, pady=2)
        self.ent_scan.bind("<Return>", self._processar_scan)
        tk.Label(frame_scan, text="Prima Enter após cada leitura — duplicados ignorados",
                 font=("Helvetica", 8), bg=COR["card"],
                 fg=COR["subtexto"]).pack(anchor="w")

        # Área de badges com altura reservada
        self.frame_badges = tk.Frame(self.app, bg=COR["card"], height=40)
        self.frame_badges.pack(fill="x", padx=20, pady=(4, 10))
        self.frame_badges.pack_propagate(False)
        self._atualizar_badges()

    def _ui_botoes(self):
        frame = tk.Frame(self.app, bg=COR["card"])
        frame.pack(fill="x", padx=20, pady=(4, 6))

        # Botão principal — usa tkmacosx se disponível, caso contrário tk padrão com cor forçada
        def _make_btn(parent, texto, cmd, cor, font_size=13, pady_val=12, **pack_kw):
            if USAR_MACBUTTON:
                from tkmacosx import Button as MacButton
                b = MacButton(parent, text=texto, command=cmd,
                              bg=cor, fg="white", height=48)
            else:
                b = tk.Button(parent, text=texto, command=cmd,
                              bg=cor, fg="white",
                              font=("Helvetica", font_size, "bold"),
                              relief="flat", bd=0,
                              highlightthickness=0,
                              activebackground=cor,
                              activeforeground="white",
                              pady=pady_val)
            b.pack(**pack_kw)
            return b

        _make_btn(frame, "GERAR E IMPRIMIR", self._gerar_etiquetas,
                  COR["verde"], fill="x", pady=(0, 8))

        # Botões secundários
        row2 = tk.Frame(frame, bg=COR["card"])
        row2.pack(fill="x")

        sec_btns = [
            ("HISTORICO", self._abrir_historico, COR["azul"]),
            ("LIMPAR",    self._limpar_campos,    COR["subtexto"]),
        ]
        for texto, cmd, cor in sec_btns:
            if USAR_MACBUTTON:
                from tkmacosx import Button as MacButton
                MacButton(row2, text=texto, command=cmd,
                          bg=cor, fg="white", height=36).pack(
                    side="left", expand=True, fill="x", padx=2)
            else:
                tk.Button(row2, text=texto, command=cmd,
                          bg=cor, fg="white",
                          font=("Helvetica", 10, "bold"),
                          relief="flat", bd=0,
                          highlightthickness=0,
                          activebackground=cor,
                          activeforeground="white",
                          pady=8).pack(
                    side="left", expand=True, fill="x", padx=2)

    def _ui_status(self):
        self.var_status = tk.StringVar(value="Pronto para usar")
        barra = tk.Frame(self.app, bg=COR["fundo"],
                         highlightthickness=1,
                         highlightbackground=COR["borda"])
        barra.pack(fill="x", side="bottom")
        tk.Label(barra, textvariable=self.var_status,
                 font=("Helvetica", 9), bg=COR["fundo"],
                 fg=COR["subtexto"]).pack(padx=12, pady=6, anchor="w")

    # ── Lógica de Interface ───────────────────
    def _atualizar_badges(self):
        for w in self.frame_badges.winfo_children():
            w.destroy()
        if not self.encomendas:
            tk.Label(self.frame_badges, text="Sem encomendas adicionadas",
                     font=("Helvetica", 9, "italic"),
                     bg=COR["card"], fg=COR["borda"]).pack(side="left", pady=6)
            return
        encs_ord = sorted(self.encomendas,
                          key=lambda x: (0, int(x), "") if x.isdigit() else (1, 0, x))
        for enc in encs_ord:
            tag = tk.Frame(self.frame_badges, bg=COR["azul_light"],
                           highlightthickness=1,
                           highlightbackground="#BFDBFE")
            tag.pack(side="left", padx=2, pady=4)
            tk.Label(tag, text=enc, fg=COR["azul"], bg=COR["azul_light"],
                     font=("Helvetica", 9, "bold")).pack(side="left", padx=(6, 2))
            tk.Button(tag, text="✕", fg="#93C5FD", bg=COR["azul_light"],
                      bd=0, font=("Helvetica", 10),
                      command=lambda e=enc: self._remover_enc(e)).pack(side="left", padx=(0, 4))

    def _remover_enc(self, enc: str):
        self.encomendas.remove(enc)
        self._atualizar_badges()

    def _processar_scan(self, event=None):
        val = self.ent_scan.get().strip().upper()
        if val and val not in self.encomendas:
            self.encomendas.append(val)
            self._atualizar_badges()
            self.var_status.set(f"Encomenda {val} adicionada")
        elif val in self.encomendas:
            self.var_status.set(f"⚠ {val} já foi adicionada")
        self.ent_scan.delete(0, tk.END)

    def _limpar_campos(self):
        self.ent_cod.delete(0, tk.END)
        self.ent_nome.delete(0, tk.END)
        self.ent_zona.delete(0, tk.END)
        self.var_vols.set(1)
        self.ent_scan.delete(0, tk.END)
        self.var_mostrar_nome.set(True)
        self.encomendas = []
        self._atualizar_badges()
        self.combo_tipo.current(0)
        self.var_status.set("Campos limpos")
        self.ent_cod.focus()

    # ── Geração ──────────────────────────────
    def _gerar_etiquetas(self):
        tipo   = self.combo_tipo.get()
        cod    = self.ent_cod.get().strip().upper()
        nome   = self.ent_nome.get().strip().upper()
        zona   = self.ent_zona.get().strip().upper()

        # Validação
        erros = []
        if not cod:
            erros.append("• Código de cliente em falta")
        if not zona:
            erros.append("• Zona / Localidade em falta")
        try:
            vols_total = self.var_vols.get()
            if vols_total < 1:
                raise ValueError
        except (ValueError, tk.TclError):
            erros.append("• Número de volumes inválido")
            vols_total = 1

        if erros:
            messagebox.showerror("Dados incompletos",
                                 "Por favor corrige:\n" + "\n".join(erros))
            return

        self.var_status.set(f"A gerar {vols_total} etiqueta(s)…")
        self.app.update_idletasks()

        ok = gerar_pdf(
            tipo=tipo,
            cod=cod,
            nome=nome,
            zona=zona,
            vols_total=vols_total,
            mostrar_nome=self.var_mostrar_nome.get(),
            encomendas=list(self.encomendas),
        )

        if ok:
            subprocess.run(["open", str(CAMINHO_PDF)], check=False)
            guardar_historico({
                "data_hora":  datetime.now().strftime("%d/%m/%Y %H:%M"),
                "tipo":       tipo,
                "codigo":     cod,
                "cliente":    nome,
                "zona":       zona,
                "vols":       vols_total,
                "encomendas": list(self.encomendas),
            })
            self.var_status.set(
                f"✓ {vols_total} etiqueta(s) gerada(s) — {zona} — "
                f"{datetime.now().strftime('%H:%M')}"
            )
            self._limpar_campos()
        else:
            messagebox.showerror("Erro", "Falha ao gerar PDF. Consulte o terminal para detalhes.")
            self.var_status.set("Erro ao gerar PDF")

    # ── Histórico ────────────────────────────
    def _abrir_historico(self):
        dados = carregar_historico()
        if not dados:
            messagebox.showinfo("Histórico", "Ainda não há registos guardados.")
            return

        jan = Toplevel(self.app)
        jan.title("Histórico de Etiquetas")
        jan.geometry("860x480")
        jan.configure(bg=COR["fundo"])
        jan.transient(self.app)
        jan.grab_set()

        # Treeview
        frame_tv = tk.Frame(jan, bg=COR["fundo"])
        frame_tv.pack(expand=True, fill="both", padx=12, pady=12)

        cols = ("DATA",  "TIPO", "CÓD", "CLIENTE", "ZONA", "VOLS", "ENC")
        tv   = ttk.Treeview(frame_tv, columns=cols, show="headings",
                             selectmode="browse")
        larguras = {"DATA": 120, "TIPO": 120, "CÓD": 80,
                    "CLIENTE": 220, "ZONA": 140, "VOLS": 55, "ENC": 80}
        for col in cols:
            tv.heading(col, text=col)
            tv.column(col, width=larguras.get(col, 100), anchor="center")
        tv.column("CLIENTE", anchor="w")

        sb = ttk.Scrollbar(frame_tv, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", expand=True, fill="both")
        sb.pack(side="right", fill="y")

        # Inserir — os mais recentes primeiro
        primeiro_item = None
        for i in range(len(dados) - 1, max(-1, len(dados) - 51), -1):
            r   = dados[i]
            enc = ", ".join(r.get("encomendas", []))
            iid = tv.insert("", "end", iid=str(i), values=(
                r.get("data_hora", ""),
                r.get("tipo", ""),
                r.get("codigo", ""),
                r.get("cliente", ""),
                r.get("zona", ""),
                r.get("vols", "1"),
                enc,
            ))
            if primeiro_item is None:
                primeiro_item = iid

        def recuperar(event=None):
            sel = tv.selection()
            if not sel:
                return
            reg = dados[int(sel[0])]
            self._limpar_campos()
            self.ent_cod.insert(0,  str(reg.get("codigo",  "")))
            self.ent_nome.insert(0, str(reg.get("cliente", "")))
            self.ent_zona.insert(0, str(reg.get("zona",    "")))
            self.var_vols.set(int(reg.get("vols", 1)))
            tipo_hist = reg.get("tipo", TIPOS[0])
            if tipo_hist in TIPOS:
                self.combo_tipo.set(tipo_hist)
            self.encomendas = list(reg.get("encomendas", []))
            self._atualizar_badges()
            self.var_status.set(f"Dados de {reg.get('cliente','')} carregados do histórico")
            jan.destroy()

        tv.bind("<Return>",    recuperar)
        tv.bind("<Double-1>",  recuperar)

        if primeiro_item:
            tv.selection_set(primeiro_item)
            tv.focus(primeiro_item)

        jan.after(100, lambda: tv.focus_set())

        frame_btns = tk.Frame(jan, bg=COR["fundo"])
        frame_btns.pack(fill="x", padx=12, pady=(0, 10))

        if USAR_MACBUTTON:
            from tkmacosx import Button as MacButton
            MacButton(frame_btns, text="CARREGAR SELECIONADO",
                      command=recuperar, bg=COR["azul"],
                      fg="white", height=38).pack(side="left", padx=4)
            MacButton(frame_btns, text="FECHAR",
                      command=jan.destroy, bg=COR["subtexto"],
                      fg="white", height=38).pack(side="left", padx=4)
        else:
            tk.Button(frame_btns, text="CARREGAR SELECIONADO",
                      command=recuperar, bg=COR["azul"], fg="white",
                      font=("Helvetica", 10, "bold"),
                      relief="flat", padx=12, pady=6).pack(side="left", padx=4)
            tk.Button(frame_btns, text="FECHAR",
                      command=jan.destroy, bg=COR["subtexto"], fg="white",
                      font=("Helvetica", 10, "bold"),
                      relief="flat", padx=12, pady=6).pack(side="left", padx=4)


# ─────────────────────────────────────────────
#  ENTRADA
# ─────────────────────────────────────────────
if __name__ == "__main__":
    AppVedarame()
