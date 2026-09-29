import os, subprocess, threading, tempfile, shutil
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APPDIR = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(APPDIR, "engine", "realesrgan-ncnn-vulkan.exe")
MODELS = os.path.join(APPDIR, "engine", "models")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Local AI Upscaler")
        self.geometry("650x430")
        self.files=[]
        tk.Label(self,text="Local AI Upscaler",font=("Segoe UI",20,"bold")).pack(pady=(18,4))
        tk.Label(self,text="本地 AI 图片放大 · 不上传图片 · 2× / 4× / 8× / 16×").pack()
        bar=tk.Frame(self); bar.pack(pady=14)
        tk.Button(bar,text="添加图片",width=14,command=self.add).pack(side="left",padx=5)
        tk.Button(bar,text="清空",width=10,command=self.clear).pack(side="left",padx=5)
        self.list=tk.Listbox(self,height=9); self.list.pack(fill="both",expand=True,padx=20)
        opts=tk.Frame(self); opts.pack(pady=10)
        tk.Label(opts,text="放大倍数：").pack(side="left")
        self.scale=tk.StringVar(value="4")
        ttk.Combobox(opts,textvariable=self.scale,values=["2","4","8","16"],width=6,state="readonly").pack(side="left")
        tk.Label(opts,text="   模型：").pack(side="left")
        self.model=tk.StringVar(value="realesrgan-x4plus")
        ttk.Combobox(opts,textvariable=self.model,values=["realesrgan-x4plus","realesrgan-x4plus-anime"],width=24,state="readonly").pack(side="left")
        self.status=tk.StringVar(value="就绪")
        tk.Label(self,textvariable=self.status).pack()
        tk.Button(self,text="开始放大",font=("Segoe UI",11,"bold"),height=2,command=self.start).pack(fill="x",padx=20,pady=(8,18))
    def add(self):
        fs=filedialog.askopenfilenames(filetypes=[("Images","*.png *.jpg *.jpeg *.webp")])
        for f in fs:
            if f not in self.files: self.files.append(f); self.list.insert("end",f)
    def clear(self):
        self.files.clear(); self.list.delete(0,"end")
    def start(self):
        if not self.files: return messagebox.showwarning("提示","请先添加图片")
        if not os.path.exists(ENGINE): return messagebox.showerror("缺少引擎","程序包中未找到 Real-ESRGAN 引擎。")
        out=filedialog.askdirectory(title="选择输出文件夹")
        if not out: return
        threading.Thread(target=self.run,args=(out,),daemon=True).start()
    def call(self, inp, outp, s):
        cmd=[ENGINE,"-i",inp,"-o",outp,"-n",self.model.get(),"-s",str(s),"-f","png"]
        p=subprocess.run(cmd,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if p.returncode: raise RuntimeError("Real-ESRGAN 返回错误")
    def run(self,outdir):
        try:
            target=int(self.scale.get())
            for idx,src in enumerate(self.files,1):
                self.status.set(f"处理中 {idx}/{len(self.files)}：{os.path.basename(src)}")
                stem=Path(src).stem
                final=os.path.join(outdir,f"{stem}_{target}x.png")
                if target in (2,4):
                    self.call(src,final,target)
                else:
                    with tempfile.TemporaryDirectory() as td:
                        mid=os.path.join(td,"stage.png")
                        self.call(src,mid,4)
                        self.call(mid,final,2 if target==8 else 4)
            self.status.set("完成")
            messagebox.showinfo("完成",f"已完成 {len(self.files)} 张图片")
        except Exception as e:
            self.status.set("失败")
            messagebox.showerror("错误",str(e))

if __name__=="__main__": App().mainloop()
