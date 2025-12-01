import os, re, threading
from tkinter import Tk, Frame, Listbox, Button, Menu, simpledialog, filedialog, messagebox
from yt_dlp import YoutubeDL

PRIMARY_COLOR="#007aff"; SECONDARY_COLOR="#34c759"; BACKGROUND_COLOR="#f5f5f5"; TEXT_COLOR="#1c1c1e"

pending_success=0
pending_errors=[]
active_downloads=0
lock=threading.Lock()

def make_bar(p):
    l=25
    f=int((p/100)*l)
    return "█"*f + "░"*(l-f)

def check_all_finished(root):
    global active_downloads,pending_success,pending_errors
    if active_downloads==0:
        msg=""
        if pending_success>0: msg+=f"{pending_success} descargas completadas con éxito.\n"
        if pending_errors: msg+="\nErrores:\n"+"\n".join(pending_errors)
        if msg: root.after(0,lambda:messagebox.showinfo("Proceso finalizado",msg))
        pending_success=0; pending_errors=[]

class DownloadManager:
    def __init__(self,root):
        self.root=root; self.downloads=[]

    def add_download(self,url,folder,ext):
        d={"url":url,"progress":0,"status":"Pendiente","output_folder":folder,"file_extension":ext,"title":"Video"}
        self.downloads.append(d); return d

    def update_progress(self,d,p):
        d["progress"]=p; d["status"]="CARGANDO"
        self.update_list()

    def update_list(self):
        listbox.delete(0,"end")
        for d in self.downloads:
            bar=make_bar(d["progress"])
            listbox.insert("end",f"{d['title']} - [{d['url']}] - [{bar}] [{d['status']}] ")

    def download_playlist(self,url,folder,ext):
        global active_downloads
        try:
            with YoutubeDL({'quiet':True,'extract_flat':True}) as ydl:
                info=ydl.extract_info(url,download=False)
                urls=[e['url'] for e in info.get('entries',[])]
                with lock: active_downloads+=len(urls)
                for u in urls: threading.Thread(target=self.download_file,args=(u,folder,ext)).start()
        except Exception as e: messagebox.showerror("Error",f"Error al procesar la lista: {e}")

    def download_file(self,url,folder,ext):
        global pending_success,pending_errors,active_downloads
        d=self.add_download(url,folder,ext); d["status"]="En progreso"
        self.root.after(0,self.update_list)

        try:
            info=YoutubeDL({'quiet':True}).extract_info(url,download=False)
            d["title"]=info.get("title","Video")
        except:
            d["title"]="Video"

        try:
            ydl_opts={
                'outtmpl':os.path.join(folder,'%(title)s.%(ext)s'),
                'format':'bestaudio/best' if ext=='mp3' else 'bestvideo+bestaudio',
                'postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3'}] if ext=='mp3' else []
            }
            with YoutubeDL(ydl_opts) as ydl: ydl.download([url])
            d["status"]="COMPLETADO"; d["progress"]=100
            with lock: pending_success+=1
        except Exception as e:
            d["status"]="ERROR"
            with lock: pending_errors.append(f"{url} → {str(e)}")
        finally:
            with lock: active_downloads-=1
            self.root.after(0,self.update_list)
            self.root.after(300,lambda:check_all_finished(self.root))

    def download_from_url(self,url,folder,ext):
        global active_downloads
        if "playlist" in url.lower():
            threading.Thread(target=self.download_playlist,args=(url,folder,ext)).start()
        else:
            with lock: active_downloads+=1
            threading.Thread(target=self.download_file,args=(url,folder,ext)).start()

    def remove_download(self,i):
        if 0<=i<len(self.downloads):
            del self.downloads[i]; self.update_list()

def is_valid_url(url): return re.match(r"(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+",url) is not None

def ask_file_extension():
    ext=simpledialog.askstring("Formato","Elija el formato de descarga (mp3 o mp4):")
    if ext and ext.lower() in ['mp3','mp4']: return ext.lower()
    messagebox.showerror("Error","Formato inválido."); return None

def download_from_url_prompt(dm):
    url=simpledialog.askstring("URL","Introduce la URL del video o playlist:")
    if not url or not is_valid_url(url): return messagebox.showerror("Error","URL inválida.")
    folder=filedialog.askdirectory(title="Seleccionar carpeta")
    if not folder: return
    ext=ask_file_extension()
    if ext: dm.download_from_url(url,folder,ext)

def load_txt_file(dm):
    fp=filedialog.askopenfilename(title="Seleccionar archivo .txt",filetypes=[("Archivos de texto","*.txt")])
    if not fp: return
    with open(fp,"r") as f: urls=[u.strip() for u in f.readlines()]
    folder=filedialog.askdirectory(title="Seleccionar carpeta")
    if not folder: return
    ext=ask_file_extension()
    if not ext: return
    for u in urls:
        if is_valid_url(u): dm.download_from_url(u,folder,ext)
        else:
            with lock: pending_errors.append(f"URL inválida: {u}")

def on_right_click(e,dm):
    sel=listbox.curselection()
    if sel:
        i=sel[0]; m=Menu(listbox,tearoff=0)
        m.add_command(label="Eliminar",command=lambda:dm.remove_download(i))
        m.post(e.x_root,e.y_root)

def main():
    global listbox
    root=Tk(); root.title("Xpedian Downloader")
    w,h=800,400; sw,sh=root.winfo_screenwidth(),root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{int(sw/2-w/2)}+{int(sh/2-h/2)}")
    root.configure(bg=BACKGROUND_COLOR)
    dm=DownloadManager(root)

    frame=Frame(root,bg=BACKGROUND_COLOR); frame.pack(pady=20,padx=20,fill="both",expand=True)
    listbox=Listbox(frame,bg=BACKGROUND_COLOR,fg=TEXT_COLOR,font=("Helvetica",12),selectbackground=PRIMARY_COLOR,activestyle="none")
    listbox.pack(pady=10,padx=10,fill="both",expand=True)

    def open_location(event):
        sel=listbox.curselection()
        if sel:
            item=dm.downloads[sel[0]]
            os.startfile(item["output_folder"])

    listbox.bind("<Double-1>",open_location)
    listbox.bind("<Button-3>",lambda e:on_right_click(e,dm))

    bf=Frame(root,bg=BACKGROUND_COLOR); bf.pack(pady=10)
    Button(bf,text="Descargar desde URL",bg=PRIMARY_COLOR,fg="white",font=("Helvetica",14),command=lambda:download_from_url_prompt(dm)).pack(side="left",padx=10)
    Button(bf,text="Cargar archivo .txt",bg=SECONDARY_COLOR,fg="white",font=("Helvetica",14),command=lambda:load_txt_file(dm)).pack(side="left",padx=10)

    root.mainloop()

if __name__=="__main__": main()
