"""LocalAIUpscaler - Windows portable GUI and Real-ESRGAN NCNN/Vulkan runner.

Anime model workaround: never use '-s 2' on realesrgan-x4plus-anime.
Run its native 4x mode and downsample with Pillow/Lanczos instead.
"""
import os
import subprocess
import tempfile
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image

APPDIR = Path(__file__).resolve().parent
ENGINE = APPDIR / "engine" / "realesrgan-ncnn-vulkan.exe"
MODELS = APPDIR / "engine" / "models"
ANIME_MODEL = "realesrgan-x4plus-anime"


def upscale_once(source, destination, model, scale):
    """Perform exactly one upscaling pass in the NCNN/Vulkan executable."""
    cmd = [
        str(ENGINE),
        "-i", str(source),
        "-o", str(destination),
        "-n", model,
        "-m", str(MODELS),
        "-s", str(scale),
        "-f", "png",
    ]
    options = {
        "capture_output": True,
        "text": True,
        "errors": "replace",
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
    }
    result = subprocess.run(cmd, **options)
    if result.returncode != 0 or not Path(destination).is_file():
        details = (result.stderr or result.stdout or "未生成输出图片").strip()
        raise RuntimeError(f"Real-ESRGAN 执行失败（代码 {result.returncode}）\n{details[-1800:]}")


def shrink_to(source, destination, width, height):
    """Downscale with a high-quality filter, preserving transparency."""
    with Image.open(source) as image:
        if image.size == (width, height):
            image.save(destination, format="PNG")
        else:
            smaller = image.resize((width, height), resample=Image.Resampling.LANCZOS)
            smaller.save(destination, format="PNG")
            smaller.close()


def original_size(source):
    with Image.open(source) as image:
        return image.size


def upscale_image(source, destination, model, target):
    """Produce exactly the requested 2x/4x/8x/16x image.

    For anime, only issue -s 4 to the NCNN backend to avoid the reported
    mosaic/tile corruption with -s 2, even when using animevideov3.
    """
    source = Path(source)
    destination = Path(destination)
    anime = model == ANIME_MODEL

    if target == 4:
        upscale_once(source, destination, model, 4)
        return

    if target == 2:
        if not anime:
            # Preserve previously working 2x behavior of the standard model.
            upscale_once(source, destination, model, 2)
        else:
            width, height = original_size(source)
            with tempfile.TemporaryDirectory(prefix="localai-") as td:
                temp4 = Path(td) / "anime4x.png"
                upscale_once(source, temp4, model, 4)
                shrink_to(temp4, destination, width * 2, height * 2)
        return

    if target == 8:
        with tempfile.TemporaryDirectory(prefix="localai-") as td:
            middle = Path(td) / "middle.png"
            if anime:
                # Avoid creating a huge 16x image just to shrink to 8x.
                # 4x model -> Lanczos back to 2x -> 4x model = final 8x.
                width, height = original_size(source)
                first4 = Path(td) / "first4x.png"
                upscale_once(source, first4, model, 4)
                shrink_to(first4, middle, width * 2, height * 2)
                upscale_once(middle, destination, model, 4)
            else:
                upscale_once(source, middle, model, 4)
                upscale_once(middle, destination, model, 2)
        return

    if target == 16:
        with tempfile.TemporaryDirectory(prefix="localai-") as td:
            middle = Path(td) / "middle.png"
            upscale_once(source, middle, model, 4)
            upscale_once(middle, destination, model, 4)
        return

    raise ValueError(f"不支持的放大倍率：{target}")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Local AI Upscaler · 动漫修复版")
        self.geometry("650x445")
        self.files = []
        self.running = False

        tk.Label(self, text="Local AI Upscaler", font=("Segoe UI", 20, "bold")).pack(pady=(18, 4))
        tk.Label(self, text="本地 AI 图片放大 · 不上传图片 · 2× / 4× / 8× / 16×").pack()
        actions = tk.Frame(self)
        actions.pack(pady=14)
        tk.Button(actions, text="添加图片", width=14, command=self.add).pack(side="left", padx=5)
        tk.Button(actions, text="清空", width=10, command=self.clear).pack(side="left", padx=5)
        self.listbox = tk.Listbox(self, height=9)
        self.listbox.pack(fill="both", expand=True, padx=20)

        opts = tk.Frame(self)
        opts.pack(pady=10)
        tk.Label(opts, text="放大倍数：").pack(side="left")
        self.scale = tk.StringVar(value="4")
        ttk.Combobox(opts, textvariable=self.scale,
                     values=["2", "4", "8", "16"], width=6, state="readonly").pack(side="left")
        tk.Label(opts, text="   模型：").pack(side="left")
        self.model = tk.StringVar(value="realesrgan-x4plus")
        ttk.Combobox(opts, textvariable=self.model,
                     values=["realesrgan-x4plus", ANIME_MODEL],
                     width=24, state="readonly").pack(side="left")
        self.status = tk.StringVar(value="就绪")
        tk.Label(self, textvariable=self.status).pack()
        self.start_button = tk.Button(self, text="开始放大", font=("Segoe UI", 11, "bold"),
                                      height=2, command=self.start)
        self.start_button.pack(fill="x", padx=20, pady=(8, 18))

    def add(self):
        for path in filedialog.askopenfilenames(
                filetypes=[("图片文件", "*.png *.jpg *.jpeg *.webp")]):
            if path not in self.files:
                self.files.append(path)
                self.listbox.insert("end", path)

    def clear(self):
        if not self.running:
            self.files.clear()
            self.listbox.delete(0, "end")

    def start(self):
        if self.running:
            return
        if not self.files:
            messagebox.showwarning("提示", "请先添加图片")
            return
        if not ENGINE.is_file() or not MODELS.is_dir():
            messagebox.showerror("缺少引擎", "程序包中未找到 Real-ESRGAN 引擎或模型文件。")
            return
        outdir = filedialog.askdirectory(title="选择输出文件夹")
        if not outdir:
            return
        target = int(self.scale.get())
        model = self.model.get()
        files = list(self.files)
        self.running = True
        self.start_button.configure(state="disabled")
        threading.Thread(target=self.run, args=(outdir, files, model, target), daemon=True).start()

    def run(self, outdir, files, model, target):
        try:
            for index, source in enumerate(files, 1):
                filename = Path(source).name
                self.after(0, self.status.set, f"处理中 {index}/{len(files)}：{filename}")
                destination = Path(outdir) / f"{Path(source).stem}_{target}x.png"
                upscale_image(source, destination, model, target)
            self.after(0, self.finish, None, len(files))
        except Exception as exc:
            self.after(0, self.finish, str(exc), len(files))

    def finish(self, error, count):
        self.running = False
        self.start_button.configure(state="normal")
        if error:
            self.status.set("失败")
            messagebox.showerror("错误", error)
        else:
            self.status.set("完成")
            messagebox.showinfo("完成", f"已完成 {count} 张图片")


if __name__ == "__main__":
    App().mainloop()
