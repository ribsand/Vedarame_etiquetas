import sys
import os
import math
import json
import platform
import subprocess
import csv
from datetime import datetime, date
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, Toplevel, ttk

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
    "fundo":       "#F6F7F9",
    "card":        "#FFFFFF",
    "cast":        "#6B3A3A",
    "cast_light":  "#F9F1F1",
    "verde":       "#16A34A",
    "verde_light": "#F0FDF4",
    "azul":        "#4D6CBF",
    "azul_light":  "#EFF6FF",
    "borda":       "#E4E7EC",
    "subtexto":    "#6B7280",
    "texto":       "#111827",
    "input_bg":    "#F6F7F9",
    "erro":        "#DC2626",
    "erro_light":  "#FEF2F2",
    "ok":          "#16A34A",
    "ok_light":    "#F0FDF4",
}


# ─────────────────────────────────────────────
#  CONFIG ETIQUETAS
# ─────────────────────────────────────────────
CONFIG_ETIQUETAS = {
    "Transporte (A5)": {
        "tamanho":        A5,
        "logo_width":     10 * cm,
        "offset_cod":     6.0 * cm,
        "offset_cliente": 8.0 * cm,
        "offset_zona":    11.5 * cm,
        "fonte_cod":      18,
        "fonte_cliente":  24,
        "fonte_zona":     26,
        "fonte_vol_num":  85,
    },
    "Caixa (10x5cm)": {
        "tamanho":        (10 * cm, 5 * cm),
        "logo_width":     3.2 * cm,
        "offset_cod":     1.7 * cm,
        "offset_cliente": 2.3 * cm,
        "offset_zona":    2.9 * cm,
        "fonte_cod":      9,
        "fonte_cliente":  10,
        "fonte_zona":     10,
    },
}

TIPOS = list(CONFIG_ETIQUETAS.keys())


# ─────────────────────────────────────────────
#  CAMINHOS
# ─────────────────────────────────────────────
PASTA_USER        = Path.home()
CAMINHO_HISTORICO = PASTA_USER / "Vedarame_Historico.json"
CAMINHO_PDF       = PASTA_USER / "Vedarame_Etiquetas.pdf"
LIMITE_HISTORICO  = 500


def obter_caminho_logo() -> str | None:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    candidatos = [
        base / "Vedarame_Logo.png",
        Path(__file__).parent / "Vedarame_Logo.png",
    ]
    for c in candidatos:
        if c.exists():
            return str(c)
    return None


def abrir_ficheiro(caminho: Path):
    """Abre qualquer ficheiro no programa padrão do sistema operativo."""
    sistema = platform.system()
    try:
        if sistema == "Darwin":
            subprocess.run(["open", str(caminho)], check=False)
        elif sistema == "Windows":
            os.startfile(str(caminho))
        else:
            subprocess.run(["xdg-open", str(caminho)], check=False)
    except Exception as e:
        print(f"[AVISO] Não foi possível abrir o ficheiro: {e}")


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
    dados = carregar_historico()
    dados.append(entrada)
    if len(dados) > LIMITE_HISTORICO:
        dados = dados[-LIMITE_HISTORICO:]
    try:
        with open(CAMINHO_HISTORICO, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[AVISO] Erro ao guardar histórico: {e}")


def exportar_historico_csv(dados: list) -> Path | None:
    """
    Exporta a lista de registos para CSV.
    Recebe os dados já em memória — não relê o ficheiro.
    Devolve o caminho do ficheiro criado, ou None em caso de erro.
    """
    if not dados:
        return None
    caminho = PASTA_USER / f"Vedarame_Historico_{date.today().strftime('%Y%m%d')}.csv"
    try:
        with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "data_hora", "tipo", "codigo", "cliente", "zona", "vols", "encomendas"
            ])
            writer.writeheader()
            for r in dados:
                row = dict(r)
                row["encomendas"] = ", ".join(r.get("encomendas", []))
                writer.writerow(row)
        return caminho
    except Exception as e:
        print(f"[AVISO] Erro ao exportar CSV: {e}")
        return None


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
    prefixo = "CLIENTE: "
    fonte   = "Helvetica-Bold"
    margem  = 0.5 * cm if e_caixa else 1.0 * cm

    c.setFont(fonte, tam_fonte)
    larg_pref = stringWidth(prefixo, fonte, tam_fonte)
    c.drawString(x, y_base, prefixo)

    x_nome    = x + larg_pref + 3
    larg_disp = largura_maxima - x_nome - margem

    if e_caixa:
        fs = tam_fonte
        while stringWidth(texto, fonte, fs) > larg_disp and fs > 6:
            fs -= 0.5
        c.setFont(fonte, fs)
        c.drawString(x_nome, y_base, texto)
    else:
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
    try:
        conf    = CONFIG_ETIQUETAS[tipo]
        lp, ap  = conf["tamanho"]
        e_caixa = "Caixa" in tipo
        x_base  = 0.8 * cm if e_caixa else 1.2 * cm

        c = canvas.Canvas(str(CAMINHO_PDF), pagesize=(lp, ap))

        encs_ord = sorted(encomendas,
                          key=lambda x: (0, int(x), "") if x.isdigit() else (1, 0, x))

        for i in range(1, vols_total + 1):
            _desenhar_logo(c, lp, ap, tipo)

            c.setFont("Helvetica-Bold", conf["fonte_cod"])
            c.drawString(x_base, ap - conf["offset_cod"], f"CÓD CLIENTE: {cod}")

            if mostrar_nome:
                _escrever_cliente(c, nome, x_base,
                                  ap - conf["offset_cliente"],
                                  lp, conf["fonte_cliente"], e_caixa)

            c.setFont("Helvetica-Bold", conf["fonte_zona"])
            c.drawString(x_base, ap - conf["offset_zona"], f"ZONA: {zona}")

            if e_caixa:
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
                yt = ap - 15 * cm

                c.setFont("Helvetica-Bold", 20)
                c.drawCentredString(lp / 4, yt, "VOL:")
                c.setFont("Helvetica-Bold", conf["fonte_vol_num"])
                c.drawCentredString(lp / 4, yt - 3.0 * cm, f"{i}/{vols_total}")

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
def _make_btn(parent, texto: str, cmd, cor: str,
              font_size: int = 11, pady_val: int = 8, **pack_kw):
    if USAR_MACBUTTON:
        b = MacButton(parent, text=texto, command=cmd,
                      bg=cor, fg="white", height=40)
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


def _criar_secao(parent, titulo: str):
    frame = tk.Frame(parent, bg=COR["card"])
    frame.pack(fill="x", padx=20, pady=(22, 2))
    tk.Label(frame, text=titulo.upper(),
             font=("Helvetica", 10, "bold"),
             bg=COR["card"], fg=COR["subtexto"]).pack(anchor="w")
    tk.Frame(parent, bg=COR["borda"], height=1).pack(fill="x", padx=20, pady=(4, 10))


# ─────────────────────────────────────────────
#  CAMPO DE INPUT COM VALIDAÇÃO VISUAL
# ─────────────────────────────────────────────
class CampoInput:
    """Campo de entrada com feedback visual de validação em tempo real."""

    def __init__(self, parent, label: str, obrigatorio: bool = False,
                 ao_enter=None, cor_foco: str = None):
        self.obrigatorio = obrigatorio
        self.cor_foco    = cor_foco or COR["cast"]
        self._valido     = True

        self.frame = tk.Frame(parent, bg=COR["card"])
        self.frame.pack(pady=4, padx=20, fill="x")

        linha_label = tk.Frame(self.frame, bg=COR["card"])
        linha_label.pack(fill="x")
        tk.Label(linha_label, text=label,
                 font=("Helvetica", 9, "bold"),
                 bg=COR["card"], fg=COR["subtexto"]).pack(side="left")
        self.lbl_erro = tk.Label(linha_label, text="",
                                  font=("Helvetica", 9),
                                  bg=COR["card"], fg=COR["erro"])
        self.lbl_erro.pack(side="right")

        self.entry = tk.Entry(self.frame,
                              font=("Helvetica", 12),
                              bg=COR["input_bg"],
                              relief="flat",
                              highlightthickness=1,
                              highlightbackground=COR["borda"],
                              highlightcolor=self.cor_foco,
                              justify="center")
        self.entry.pack(pady=2, ipady=8, fill="x")

        self.entry.bind("<KeyRelease>", self._validar)
        self.entry.bind("<FocusOut>",   self._validar)
        if ao_enter:
            self.entry.bind("<Return>", ao_enter)

    def _validar(self, event=None):
        if not self.obrigatorio:
            return
        vazio = self.entry.get().strip() == ""
        if vazio:
            self.entry.config(highlightbackground=COR["erro"],
                              highlightcolor=COR["erro"],
                              bg=COR["erro_light"])
            self.lbl_erro.config(text="campo obrigatório")
            self._valido = False
        else:
            self.entry.config(highlightbackground=COR["ok"],
                              highlightcolor=self.cor_foco,
                              bg=COR["ok_light"])
            self.lbl_erro.config(text="")
            self._valido = True

    def get(self) -> str:
        return self.entry.get().strip().upper()

    def set(self, valor: str):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, valor)
        self._validar()

    def limpar(self):
        self.entry.delete(0, tk.END)
        self.entry.config(highlightbackground=COR["borda"],
                          highlightcolor=self.cor_foco,
                          bg=COR["input_bg"])
        self.lbl_erro.config(text="")
        self._valido = True

    def focus(self):
        self.entry.focus()

    @property
    def valido(self) -> bool:
        if self.obrigatorio:
            return self.entry.get().strip() != ""
        return True


# ─────────────────────────────────────────────
#  APLICAÇÃO PRINCIPAL
# ─────────────────────────────────────────────
class AppVedarame:
    def __init__(self):
        self.encomendas: list[str] = []
        self._ultimo_pdf_existe = False

        self.app = tk.Tk()
        self.app.title("Vedarame Expedição")
        self.app.geometry("520x900")
        self.app.resizable(True, True)
        self.app.minsize(480, 720)
        self.app.after(100, lambda: self.app.geometry("520x900"))
        self.app.configure(bg=COR["card"])

        # Atalhos de teclado
        self.app.bind("<Command-p>", lambda e: self._gerar_etiquetas())
        self.app.bind("<Control-p>", lambda e: self._gerar_etiquetas())
        self.app.bind("<Command-r>", lambda e: self._reimprimir())
        self.app.bind("<Control-r>", lambda e: self._reimprimir())

        self._construir_ui()
        # Activa reimprimir se existir PDF de sessão anterior
        self._ultimo_pdf_existe = CAMINHO_PDF.exists()
        self._actualizar_btn_reimprimir()
        self.app.mainloop()

    # ── Construção da UI ──────────────────────
    def _construir_ui(self):
        self._ui_header()
        self._ui_tipo_etiqueta()
        self._ui_dados_cliente()
        self._ui_encomendas_scan()
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
        tk.Label(inner, text="V.2026",
                 font=("Helvetica", 9),
                 bg=COR["cast"], fg="#C4A0A0").pack(side="right", pady=2)
        tk.Label(header, text="Expedição",
                 font=("Helvetica", 12),
                 bg=COR["cast"], fg="#E8C8C8").pack(anchor="w", padx=20, pady=(0, 12))

    def _ui_tipo_etiqueta(self):
        frame = tk.Frame(self.app, bg=COR["card"])
        frame.pack(fill="x", padx=20, pady=(12, 4))
        tk.Label(frame, text="TIPO DE ETIQUETA",
                 font=("Helvetica", 10, "bold"),
                 bg=COR["card"], fg=COR["subtexto"]).pack(anchor="w", pady=(0, 5))
        self.combo_tipo = ttk.Combobox(frame, values=TIPOS, state="readonly",
                                       font=("Helvetica", 11))
        self.combo_tipo.current(0)
        self.combo_tipo.pack(fill="x", ipady=4)

    def _ui_dados_cliente(self):

        # ── Linha: Código + Volumes ────────────
        row = tk.Frame(self.app, bg=COR["card"])
        row.pack(fill="x", padx=20, pady=(20, 6))

        col_cod = tk.Frame(row, bg=COR["card"])
        col_cod.pack(side="left", fill="x", expand=True)

        # Código — construído manualmente para ficar sem padding lateral extra
        self.campo_cod = CampoInput(col_cod, "CÓDIGO CLIENTE", obrigatorio=True)
        self.campo_cod.frame.pack_forget()
        self.campo_cod.frame = tk.Frame(col_cod, bg=COR["card"])
        self.campo_cod.frame.pack(fill="x")
        _ll = tk.Frame(self.campo_cod.frame, bg=COR["card"])
        _ll.pack(fill="x")
        tk.Label(_ll, text="CÓDIGO CLIENTE", font=("Helvetica", 9, "bold"),
                 bg=COR["card"], fg=COR["subtexto"]).pack(side="left")
        self.campo_cod.lbl_erro = tk.Label(_ll, text="", font=("Helvetica", 9),
                                            bg=COR["card"], fg=COR["erro"])
        self.campo_cod.lbl_erro.pack(side="right")
        self.campo_cod.entry = tk.Entry(self.campo_cod.frame,
                                         font=("Helvetica", 15, "bold"), bg=COR["input_bg"],
                                         relief="flat", highlightthickness=1,
                                         highlightbackground=COR["borda"],
                                         highlightcolor=COR["cast"], justify="center")
        self.campo_cod.entry.pack(fill="x", ipady=10, pady=2)
        self.campo_cod.entry.bind("<KeyRelease>", self.campo_cod._validar)
        self.campo_cod.entry.bind("<FocusOut>",   self.campo_cod._validar)
        self.campo_cod.entry.bind("<Return>",      lambda e: self.campo_nome.focus())

        # Volumes
        col_vol = tk.Frame(row, bg=COR["card"])
        col_vol.pack(side="right", padx=(10, 0))
        tk.Label(col_vol, text="VOLUMES", font=("Helvetica", 9, "bold"),
                 bg=COR["card"], fg=COR["subtexto"]).pack(anchor="w")
        vol_ctrl = tk.Frame(col_vol, bg=COR["card"])
        vol_ctrl.pack()
        self.var_vols = tk.IntVar(value=1)

        def _ajustar(d):
            self.var_vols.set(max(1, min(99, self.var_vols.get() + d)))

        btn_style = dict(font=("Helvetica", 13, "bold"), fg=COR["cast"],
                         bg=COR["cast_light"], relief="flat", bd=0,
                         highlightthickness=0, width=2, cursor="hand2",
                         activebackground=COR["borda"], activeforeground=COR["cast"])
        tk.Button(vol_ctrl, text="−", command=lambda: _ajustar(-1),
                  **btn_style).pack(side="left", ipady=4)
        self.ent_vols = tk.Entry(vol_ctrl, textvariable=self.var_vols,
                                  font=("Helvetica", 16, "bold"),
                                  bg=COR["card"], fg=COR["texto"],
                                  relief="flat", bd=0, highlightthickness=0,
                                  justify="center", width=3)
        self.ent_vols.pack(side="left", ipady=4)

        def _validar_vol(event=None):
            try:
                self.var_vols.set(max(1, min(99, int(self.ent_vols.get()))))
            except ValueError:
                self.var_vols.set(1)

        self.ent_vols.bind("<FocusOut>", _validar_vol)
        self.ent_vols.bind("<Return>",   _validar_vol)
        tk.Button(vol_ctrl, text="+", command=lambda: _ajustar(1),
                  **btn_style).pack(side="left", ipady=4)

        # Nome
        self.campo_nome = CampoInput(self.app, "NOME DO CLIENTE",
                                      ao_enter=lambda e: self.campo_zona.focus())
        self.campo_nome.entry.config(font=("Helvetica", 15, "bold"))
        self.campo_nome.entry.pack_forget()
        self.campo_nome.entry.pack(pady=0, ipady=10, fill="x")

        # Checkbox imprimir nome
        self.var_mostrar_nome = tk.BooleanVar(value=True)
        tk.Checkbutton(self.app, text="Imprimir nome na etiqueta",
                       variable=self.var_mostrar_nome,
                       bg=COR["card"], fg=COR["subtexto"], font=("Helvetica", 11),
                       activebackground=COR["card"], activeforeground=COR["cast"],
                       bd=0, highlightthickness=0).pack(anchor="w", padx=20, pady=(0, 20))

        # Zona
        self.campo_zona = CampoInput(self.app, "ZONA / LOCALIDADE / CÓD. POSTAL",
                                      obrigatorio=True,
                                      ao_enter=lambda e: self.ent_scan.focus())
        self.campo_zona.entry.config(font=("Helvetica", 15, "bold"))
        self.campo_zona.entry.pack_forget()
        self.campo_zona.entry.pack(pady=2, ipady=10, fill="x")

    def _ui_encomendas_scan(self):

        frame_scan = tk.Frame(self.app, bg=COR["card"])
        frame_scan.pack(fill="x", padx=20, pady=(20, 4))

        linha_top = tk.Frame(frame_scan, bg=COR["card"])
        linha_top.pack(fill="x")
        tk.Label(linha_top, text="ENCOMENDAS", font=("Helvetica", 9, "bold"),
                 bg=COR["card"], fg=COR["subtexto"]).pack(side="left")
        self.lbl_contador = tk.Label(linha_top, text="0 encomendas",
                                      font=("Helvetica", 9),
                                      bg=COR["card"], fg=COR["subtexto"])
        self.lbl_contador.pack(side="right")

        self.ent_scan = tk.Entry(frame_scan, font=("Helvetica", 12),
                                  bg=COR["input_bg"], relief="flat",
                                  highlightthickness=1,
                                  highlightbackground=COR["borda"],
                                  highlightcolor=COR["cast"], justify="center")
        self.ent_scan.pack(fill="x", ipady=8, pady=(4, 2))
        self.ent_scan.bind("<Return>", self._processar_scan)

        tk.Label(frame_scan, text="Enter após cada leitura — duplicados ignorados",
                 font=("Helvetica", 10), bg=COR["card"],
                 fg=COR["subtexto"]).pack(anchor="w")

        # Área de badges com scroll horizontal
        frame_badges_outer = tk.Frame(self.app, bg=COR["card"],
                                       highlightthickness=1,
                                       highlightbackground=COR["borda"])
        frame_badges_outer.pack(fill="x", padx=20, pady=(6, 10))

        canvas_badges = tk.Canvas(frame_badges_outer, bg=COR["card"],
                                   height=46, highlightthickness=0)
        sb_h = ttk.Scrollbar(frame_badges_outer, orient="horizontal",
                               command=canvas_badges.xview)
        canvas_badges.configure(xscrollcommand=sb_h.set)

        self.frame_badges = tk.Frame(canvas_badges, bg=COR["card"])
        canvas_badges.create_window((0, 0), window=self.frame_badges, anchor="nw")
        self.frame_badges.bind(
            "<Configure>",
            lambda e: canvas_badges.configure(scrollregion=canvas_badges.bbox("all"))
        )
        canvas_badges.pack(fill="x")
        sb_h.pack(fill="x")
        self._canvas_badges = canvas_badges
        self._atualizar_badges()

    def _ui_botoes(self):
        frame = tk.Frame(self.app, bg=COR["card"])
        frame.pack(fill="x", padx=20, pady=(4, 6))

        # ── Botão principal ───────────────────
        _make_btn(frame, "GERAR E IMPRIMIR  (⌘P)",
                  self._gerar_etiquetas, COR["cast"],
                  font_size=13, pady_val=12, fill="x", pady=(0, 8))

        # ── Linha 2: HISTÓRICO + REIMPRIMIR ───
        # Dois botões com funções distintas e usadas no dia-a-dia
        row2 = tk.Frame(frame, bg=COR["card"])
        row2.pack(fill="x", pady=(0, 4))

        _make_btn(row2, "HISTÓRICO", self._abrir_historico, COR["azul"],
                  font_size=10, pady_val=6,
                  side="left", expand=True, fill="x", padx=(0, 3))

        # Reimprimir — começa desactivado até existir um PDF
        if USAR_MACBUTTON:
            self.btn_reimprimir = MacButton(
                row2, text="REIMPRIMIR  (⌘R)",
                command=self._reimprimir,
                bg="#A0AEC0", fg="white", height=40)
        else:
            self.btn_reimprimir = tk.Button(
                row2, text="REIMPRIMIR  (⌘R)",
                command=self._reimprimir,
                bg="#A0AEC0", fg="white",
                font=("Helvetica", 10, "bold"),
                relief="flat", bd=0, highlightthickness=0,
                activebackground="#A0AEC0", activeforeground="white",
                pady=6, state="disabled")
        self.btn_reimprimir.pack(side="left", expand=True, fill="x", padx=(3, 0))

        # ── Linha 3: LIMPAR — acção destrutiva, isolada e discreta ──
        row3 = tk.Frame(frame, bg=COR["card"])
        row3.pack(fill="x")
        _make_btn(row3, "LIMPAR CAMPOS", self._limpar_campos, COR["subtexto"],
                  font_size=10, pady_val=5, fill="x")

    def _ui_status(self):
        self.var_status = tk.StringVar(value="Pronto para usar")
        barra = tk.Frame(self.app, bg=COR["fundo"],
                         highlightthickness=1,
                         highlightbackground=COR["borda"])
        barra.pack(fill="x", side="bottom")

        sistema = platform.system()
        tag_so  = {"Darwin": "macOS", "Windows": "Windows"}.get(sistema, sistema)
        tk.Label(barra, text=tag_so, font=("Helvetica", 9),
                 bg=COR["fundo"], fg=COR["subtexto"]).pack(side="right", padx=8, pady=4)
        tk.Label(barra, textvariable=self.var_status, font=("Helvetica", 11),
                 bg=COR["fundo"], fg=COR["subtexto"]).pack(side="left", padx=12, pady=6)

    # ── Activar / desactivar botão Reimprimir ─
    def _actualizar_btn_reimprimir(self):
        if self._ultimo_pdf_existe:
            cor, estado = COR["verde"], "normal"
        else:
            cor, estado = "#A0AEC0", "disabled"
        try:
            if USAR_MACBUTTON:
                self.btn_reimprimir.config(bg=cor)
            else:
                self.btn_reimprimir.config(bg=cor, state=estado,
                                            activebackground=cor)
        except Exception:
            pass

    # ── Lógica de badges ──────────────────────
    def _atualizar_badges(self):
        for w in self.frame_badges.winfo_children():
            w.destroy()

        n = len(self.encomendas)
        if n == 0:
            self.lbl_contador.config(text="0 encomendas", fg=COR["subtexto"])
        elif n == 1:
            self.lbl_contador.config(text="1 encomenda", fg=COR["azul"])
        else:
            self.lbl_contador.config(text=f"{n} encomendas", fg=COR["azul"])

        if not self.encomendas:
            tk.Label(self.frame_badges, text="Nenhuma encomenda lida",
                     font=("Helvetica", 10, "italic"),
                     bg=COR["card"], fg="#A0AEC0").pack(side="left", padx=6, pady=10)
            return

        encs_ord = sorted(self.encomendas,
                          key=lambda x: (0, int(x), "") if x.isdigit() else (1, 0, x))

        for enc in encs_ord:
            badge = tk.Frame(self.frame_badges, bg=COR["azul_light"],
                             padx=8, pady=2,
                             highlightthickness=1,
                             highlightbackground="#BFDBFE")
            badge.pack(side="left", padx=4, pady=6)

            tk.Label(badge, text=enc, fg=COR["azul"], bg=COR["azul_light"],
                     font=("Helvetica", 10, "bold")).pack(side="left")

            btn_x = tk.Label(badge, text=" ✕", fg="#60A5FA", bg=COR["azul_light"],
                              font=("Helvetica", 10, "bold"), cursor="hand2")
            btn_x.pack(side="left", padx=(4, 0))
            btn_x.bind("<Button-1>", lambda e, s=enc: self._remover_enc(s))
            btn_x.bind("<Enter>",    lambda e, b=btn_x: b.config(fg="#EF4444"))
            btn_x.bind("<Leave>",    lambda e, b=btn_x: b.config(fg="#60A5FA"))

    def _remover_enc(self, enc: str):
        if enc in self.encomendas:
            self.encomendas.remove(enc)
            self._atualizar_badges()

    def _processar_scan(self, event=None):
        val = self.ent_scan.get().strip().upper()
        if val and val not in self.encomendas:
            self.encomendas.append(val)
            self._atualizar_badges()
            self.var_status.set(f"✓ Encomenda {val} adicionada")
            try:
                self.app.bell()
            except Exception:
                pass
        elif val in self.encomendas:
            self.var_status.set(f"⚠ {val} já foi adicionada")
        self.ent_scan.delete(0, tk.END)

    def _limpar_campos(self):
        self.campo_cod.limpar()
        self.campo_nome.limpar()
        self.campo_zona.limpar()
        self.var_vols.set(1)
        self.ent_scan.delete(0, tk.END)
        self.var_mostrar_nome.set(True)
        self.encomendas = []
        self._atualizar_badges()
        self.combo_tipo.current(0)
        self.var_status.set("Campos limpos")
        self.campo_cod.focus()

    # ── Reimprimir último PDF ─────────────────
    def _reimprimir(self):
        """Reabre o último PDF gerado sem alterar nenhum campo."""
        if CAMINHO_PDF.exists():
            abrir_ficheiro(CAMINHO_PDF)
            self.var_status.set(f"A reimprimir — {datetime.now().strftime('%H:%M')}")
        else:
            self.var_status.set("⚠ Nenhum PDF disponível para reimprimir")
            self._ultimo_pdf_existe = False
            self._actualizar_btn_reimprimir()

    # ── Geração de etiquetas ──────────────────
    def _gerar_etiquetas(self):
        tipo = self.combo_tipo.get()
        cod  = self.campo_cod.get()
        nome = self.campo_nome.get()
        zona = self.campo_zona.get()

        erros = []
        if not cod:
            erros.append("• Código de cliente em falta")
            self.campo_cod._validar()
        if not zona:
            erros.append("• Zona / Localidade em falta")
            self.campo_zona._validar()

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
            tipo=tipo, cod=cod, nome=nome, zona=zona,
            vols_total=vols_total,
            mostrar_nome=self.var_mostrar_nome.get(),
            encomendas=list(self.encomendas),
        )

        if ok:
            abrir_ficheiro(CAMINHO_PDF)
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
                f"✓ {vols_total} etiqueta(s) — {zona} — "
                f"{datetime.now().strftime('%H:%M')}"
            )
            self._ultimo_pdf_existe = True
            self._actualizar_btn_reimprimir()
            self._limpar_campos()
        else:
            messagebox.showerror("Erro", "Falha ao gerar PDF.")
            self.var_status.set("Erro ao gerar PDF")

    # ── Histórico ────────────────────────────
    def _abrir_historico(self):
        dados = carregar_historico()
        if not dados:
            messagebox.showinfo("Histórico", "Ainda não há registos guardados.")
            return

        jan = Toplevel(self.app)
        jan.title("Histórico de Etiquetas")
        jan.geometry("920x560")
        jan.configure(bg=COR["fundo"])
        jan.transient(self.app)
        jan.grab_set()

        # ── Filtros ───────────────────────────
        frame_filtros = tk.Frame(jan, bg=COR["fundo"])
        frame_filtros.pack(fill="x", padx=12, pady=(10, 4))

        tk.Label(frame_filtros, text="Filtrar:",
                 font=("Helvetica", 10, "bold"),
                 bg=COR["fundo"], fg=COR["subtexto"]).pack(side="left", padx=(0, 6))

        var_filtro = tk.StringVar()
        tk.Entry(frame_filtros, textvariable=var_filtro,
                 font=("Helvetica", 11), bg=COR["input_bg"],
                 relief="flat", highlightthickness=1,
                 highlightbackground=COR["borda"],
                 highlightcolor=COR["cast"], width=28).pack(side="left", ipady=5)
        tk.Label(frame_filtros, text="  (código, cliente ou zona)",
                 font=("Helvetica", 10),
                 bg=COR["fundo"], fg=COR["subtexto"]).pack(side="left")

        lbl_contagem = tk.Label(frame_filtros, text="",
                                 font=("Helvetica", 10),
                                 bg=COR["fundo"], fg=COR["azul"])
        lbl_contagem.pack(side="right")

        # ── Treeview ──────────────────────────
        frame_tv = tk.Frame(jan, bg=COR["fundo"])
        frame_tv.pack(expand=True, fill="both", padx=12, pady=4)

        cols     = ("DATA", "TIPO", "CÓD", "CLIENTE", "ZONA", "VOLS", "ENC")
        tv       = ttk.Treeview(frame_tv, columns=cols, show="headings",
                                 selectmode="browse")
        larguras = {"DATA": 120, "TIPO": 120, "CÓD": 80,
                    "CLIENTE": 220, "ZONA": 150, "VOLS": 55, "ENC": 100}
        _ordem   = {"col": None, "rev": False}

        def _ordenar(col):
            items = [(tv.set(k, col), k) for k in tv.get_children("")]
            rev = (_ordem["col"] == col) and not _ordem["rev"]
            items.sort(reverse=rev)
            for idx, (_, k) in enumerate(items):
                tv.move(k, "", idx)
            _ordem["col"] = col
            _ordem["rev"] = rev

        for col in cols:
            tv.heading(col, text=col, command=lambda c=col: _ordenar(c))
            tv.column(col, width=larguras.get(col, 100), anchor="center")
        tv.column("CLIENTE", anchor="w")

        sb = ttk.Scrollbar(frame_tv, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", expand=True, fill="both")
        sb.pack(side="right", fill="y")

        def _preencher(filtro=""):
            tv.delete(*tv.get_children())
            filtro = filtro.upper().strip()
            primeiro_item = None
            mostrados = 0
            for i in range(len(dados) - 1, max(-1, len(dados) - 501), -1):
                r   = dados[i]
                enc = ", ".join(r.get("encomendas", []))
                if filtro and not any(
                    filtro in str(r.get(f, "")).upper()
                    for f in ("codigo", "cliente", "zona")
                ):
                    continue
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
                mostrados += 1

            lbl_contagem.config(text=f"{mostrados} registo(s)")
            if primeiro_item:
                tv.selection_set(primeiro_item)
                tv.focus(primeiro_item)

        _preencher()
        var_filtro.trace_add("write", lambda *_: _preencher(var_filtro.get()))

        def recuperar(event=None):
            sel = tv.selection()
            if not sel:
                return
            reg = dados[int(sel[0])]
            self._limpar_campos()
            self.campo_cod.set(str(reg.get("codigo", "")))
            self.campo_nome.set(str(reg.get("cliente", "")))
            self.campo_zona.set(str(reg.get("zona", "")))
            self.var_vols.set(int(reg.get("vols", 1)))
            tipo_hist = reg.get("tipo", TIPOS[0])
            if tipo_hist in TIPOS:
                self.combo_tipo.set(tipo_hist)
            self.encomendas = list(reg.get("encomendas", []))
            self._atualizar_badges()
            self.var_status.set(
                f"Dados de '{reg.get('cliente', '')}' carregados do histórico"
            )
            jan.destroy()

        tv.bind("<Return>",   recuperar)
        tv.bind("<Double-1>", recuperar)
        jan.after(100, lambda: tv.focus_set())

        # ── Botões do histórico ───────────────
        frame_btns = tk.Frame(jan, bg=COR["fundo"])
        frame_btns.pack(fill="x", padx=12, pady=(0, 10))

        _make_btn(frame_btns, "CARREGAR SELECIONADO", recuperar,
                  COR["azul"], side="left", padx=(0, 4))
        _make_btn(frame_btns, "FECHAR", jan.destroy,
                  COR["subtexto"], side="left", padx=(0, 4))

        # Exportar CSV — passa os dados já em memória, sem reler o ficheiro
        def _exportar():
            caminho = exportar_historico_csv(dados)
            if caminho:
                self.var_status.set(f"CSV exportado — {caminho.name}")
                abrir_ficheiro(caminho)
            else:
                messagebox.showerror("Exportar CSV", "Erro ao criar o ficheiro CSV.")

        _make_btn(frame_btns, "EXPORTAR CSV", _exportar,
                  COR["subtexto"], side="right", padx=(4, 0))


# ─────────────────────────────────────────────
#  ENTRADA
# ─────────────────────────────────────────────
if __name__ == "__main__":
    AppVedarame()
