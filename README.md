# LocalAIUpscaler

Windows 本地 AI 图片放大器。

## 自动编译
上传本项目全部文件后，打开 GitHub 仓库的 **Actions** → **Build Windows Portable EXE**。
等待构建完成，在构建页面底部 **Artifacts** 下载 `LocalAIUpscaler-Windows`。

最终 `LocalAIUpscaler.exe` 不要求用户安装 Python。

支持 2× / 4× / 8× / 16×。8×、16×通过两阶段 Real-ESRGAN 放大完成。
图片在本地处理，不发送到 Bigjpg。
