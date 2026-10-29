import customtkinter as ctk, os, zipfile, threading, logging, sys, platform
from tkinter import filedialog, messagebox
from .parser import parse_chat_file, participants
from .media import media_kind

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
logger = logging.getLogger(__name__)


def abrir_pasta(caminho: str):
    try:
        if platform.system() == "Windows":
            os.startfile(caminho)
        elif platform.system() == "Darwin":
            import subprocess
            subprocess.run(["open", caminho])
        else:
            import subprocess
            subprocess.run(["xdg-open", caminho])
    except Exception as e:
        logger.error("Erro ao abrir pasta: %s", e)


def abrir_arquivo(caminho: str):
    try:
        if platform.system() == "Windows":
            os.startfile(caminho)
        elif platform.system() == "Darwin":
            import subprocess
            subprocess.run(["open", caminho])
        else:
            import subprocess
            subprocess.run(["xdg-open", caminho])
    except Exception as e:
        logger.error("Erro ao abrir arquivo: %s", e)


class WAReaderGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WA Chat Reader")
        self.geometry("580x520")
        self.pasta_selecionada = ""
        self.arquivo_zip = ""
        self.participantes = []
        self.formato_detectado = ""
        self.total_mensagens = 0
        self.periodo = ""

        self.label_titulo = ctk.CTkLabel(self, text="WA Chat Reader", font=("Segoe UI", 22, "bold"))
        self.label_titulo.pack(pady=20)

        self.frame_selecao = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_selecao.pack(pady=5)

        self.btn_pasta = ctk.CTkButton(self.frame_selecao, text="📁 Selecionar Pasta", command=self.selecionar_pasta, font=("Segoe UI", 12, "bold"))
        self.btn_pasta.grid(row=0, column=0, padx=8)

        self.btn_zip = ctk.CTkButton(self.frame_selecao, text="🗜️ Selecionar .zip", command=self.selecionar_zip, font=("Segoe UI", 12, "bold"))
        self.btn_zip.grid(row=0, column=1, padx=8)

        self.label_info = ctk.CTkLabel(self, text="Nenhuma seleção", font=("Segoe UI", 11))
        self.label_info.pack(pady=8)

        self.frame_opcao = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_opcao.pack(pady=5)

        self.label_quem = ctk.CTkLabel(self.frame_opcao, text="Quem é você?", font=("Segoe UI", 11))
        self.label_quem.grid(row=0, column=0, padx=5)
        self.opcao_participante = ctk.CTkOptionMenu(self.frame_opcao, values=["Ninguém / automático"], command=self.mudou_participante)
        self.opcao_participante.grid(row=0, column=1, padx=5)

        self.label_progresso = ctk.CTkLabel(self, text="", font=("Segoe UI", 10, "italic"), text_color="#aaaaaa")
        self.label_progresso.pack(pady=2)

        self.progressbar = ctk.CTkProgressBar(self, width=420)
        self.progressbar.pack(pady=12)
        self.progressbar.set(0)

        self.frame_botoes = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_botoes.pack(pady=15)

        self.btn_rapido = ctk.CTkButton(
            self.frame_botoes, text="⚡ Modo Rápido (Links Local)",
            command=lambda: self.iniciar_processamento_thread("rapido"),
            state="disabled", fg_color="#3b82f6", hover_color="#1d4ed8",
            font=("Segoe UI", 12, "bold"), width=200
        )
        self.btn_rapido.grid(row=0, column=0, padx=8)

        self.btn_portatil = ctk.CTkButton(
            self.frame_botoes, text="📦 Modo Portátil (Embed Base64)",
            command=lambda: self.iniciar_processamento_thread("portatil"),
            state="disabled", fg_color="#25D366", hover_color="#128C7E", text_color="black",
            font=("Segoe UI", 12, "bold"), width=200
        )
        self.btn_portatil.grid(row=0, column=1, padx=8)

    def selecionar_pasta(self):
        pasta = filedialog.askdirectory()
        if pasta:
            self.pasta_selecionada = pasta
            self.arquivo_zip = ""
            self.processar_pre_parse(pasta)

    def selecionar_zip(self):
        zip_path = filedialog.askopenfilename(filetypes=[("Zip files", "*.zip")])
        if zip_path:
            self.arquivo_zip = zip_path
            self.pasta_selecionada = ""
            # Extrair para pasta ao lado
            nome_zip = os.path.splitext(os.path.basename(zip_path))[0]
            pasta_dest = os.path.join(os.path.dirname(zip_path), nome_zip)
            try:
                if not os.path.exists(pasta_dest):
                    os.makedirs(pasta_dest)
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    for info in zf.infolist():
                        # Proteção zip-slip
                        destino = os.path.abspath(os.path.join(pasta_dest, info.filename))
                        if not destino.startswith(os.path.abspath(pasta_dest) + os.sep):
                            self.after(0, lambda: messagebox.showerror("Erro", "Arquivo zip contém caminho inválido (zip-slip)"))
                            return
                    zf.extractall(pasta_dest)
                self.pasta_selecionada = pasta_dest
                self.processar_pre_parse(pasta_dest)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erro", f"Falha ao extrair zip: {e}"))

    def processar_pre_parse(self, pasta):
        txt_path = None
        # Procurar arquivo
        for root, _, files in os.walk(pasta):
            for f in files:
                if f.lower() == "_chat.txt":
                    txt_path = os.path.join(root, f)
                    break
            if txt_path:
                break
        # Se não achou _chat.txt, procurar qualquer .txt preferindo Conversa/Chat
        if not txt_path:
            candidatos = []
            for root, _, files in os.walk(pasta):
                for f in files:
                    if f.lower().endswith(".txt"):
                        candidatos.append(os.path.join(root, f))
            if candidatos:
                # preferir nome com conversa/chat e maior
                def chave(p):
                    nome = os.path.basename(p).lower()
                    pref = ("chat" in nome or "conversa" in nome)
                    return (-pref, -os.path.getsize(p))
                candidatos.sort(key=chave)
                txt_path = candidatos[0]
        if not txt_path:
            self.after(0, lambda: messagebox.showerror("Erro", "Nenhum arquivo .txt de conversa encontrado na pasta."))
            return
        try:
            msgs = list(parse_chat_file(txt_path))
            self.total_mensagens = len(msgs)
            self.participantes = participants(msgs)
            # Atualizar opção de participantes
            valores = ["Ninguém / automático"] + self.participantes
            self.opcao_participante.configure(values=valores)
            self.opcao_participante.set("Ninguém / automático")
            # Detectar formato aproximado
            self.formato_detectado = "iOS" if any("[" in open(txt_path, encoding="utf-8-sig").readline() for ln in []) else "Android"
            # Simplificação: ler primeira linha
            with open(txt_path, "r", encoding="utf-8-sig") as f:
                first_line = f.readline()
            fmt = "iOS" if first_line.startswith("[") else ("Android 12h" if "PM" in first_line or "AM" in first_line else ("Android 24h" if " - " in first_line else "Android"))
            self.formato_detectado = fmt
            # Período
            if msgs:
                inicio = msgs[0].dt.strftime("%d/%m/%Y")
                fim = msgs[-1].dt.strftime("%d/%m/%Y")
                self.periodo = f"{inicio} → {fim}"
            self.label_info.configure(text=f"Formato: {fmt} | Mensagens: {len(msgs)} | Período: {self.periodo}")
            self.btn_rapido.configure(state="normal")
            self.btn_portatil.configure(state="normal")
        except Exception as e:
            logger.error("Pré-parse erro: %s", e)
            self.after(0, lambda: messagebox.showerror("Erro", f"Erro ao ler arquivo: {e}"))

    def mudou_participante(self, valor):
        if valor == "Ninguém / automático":
            self.autor_eu = None
        else:
            self.autor_eu = valor

    def iniciar_processamento_thread(self, modo):
        if not self.pasta_selecionada:
            return
        self.btn_rapido.configure(state="disabled")
        self.btn_portatil.configure(state="disabled")
        self.btn_pasta.configure(state="disabled")
        self.btn_zip.configure(state="disabled")
        self.progressbar.set(0)
        threading.Thread(target=self.processar, args=(modo,), daemon=True).start()

    def processar(self, modo):
        try:
            # Encontrar txt novamente (pasta pode ser zip extraído)
            txt_path = None
            for root, _, files in os.walk(self.pasta_selecionada):
                for f in files:
                    if f.lower() == "_chat.txt" or f.lower().endswith(".txt"):
                        # Preferir _chat.txt
                        if f.lower() == "_chat.txt" or not txt_path:
                            txt_path = os.path.join(root, f)
            if not txt_path:
                self.after(0, self.restaurar_botoes)
                self.after(0, lambda: messagebox.showerror("Erro", "Arquivo .txt não encontrado!"))
                return
            msgs = list(parse_chat_file(txt_path))
            total = len(msgs)
            # Nome saída
            nome_base = os.path.basename(self.pasta_selecionada or self.arquivo_zip or "Leitura")
            sufixo = "Rapido" if modo == "rapido" else "Portatil"
            nome_dest = f"Leitura_{nome_base}_{sufixo}.html"
            destino = os.path.join(os.path.dirname(self.pasta_selecionada or "."), nome_dest)
            # Atualizar progresso
            self.after(0, self.atualizar_progresso, 0.3, "Gerando HTML...")
            # Renderizar
            from .renderer import render_stream
            render_stream(msgs, destino, modo, self.pasta_selecionada or ".", self.autor_eu)
            self.after(0, self.atualizar_progresso, 1.0, "Concluído!")
            self.after(0, lambda: self.finalizar(destino, modo))
        except Exception as e:
            logger.error("Erro no processamento: %s", e)
            self.after(0, lambda: messagebox.showerror("Erro", f"Erro: {e}"))
            self.after(0, self.restaurar_botoes)

    def atualizar_progresso(self, valor, texto):
        self.progressbar.set(valor)
        self.label_progresso.configure(text=texto)

    def finalizar(self, caminho_saida, modo):
        messagebox.showinfo("Sucesso", f"Arquivo HTML gerado!\n{caminho_saida}")
        abrir_arquivo(caminho_saida)
        # Abrir pasta do arquivo também
        abrir_pasta(os.path.dirname(caminho_saida))
        self.restaurar_botoes()

    def restaurar_botoes(self):
        self.btn_rapido.configure(state="normal")
        self.btn_portatil.configure(state="normal")
        self.btn_pasta.configure(state="normal")
        self.btn_zip.configure(state="normal")


def run():
    app = WAReaderGUI()
    app.mainloop()
