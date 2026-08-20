# 英文视频 → 中英双语字幕视频

一个可以直接部署到 **GitHub + Render** 的 Web 应用：

**上传英文视频 → Whisper 自动识别 → Google 免费网页翻译 → FFmpeg 烧录中英双语字幕 → 下载 MP4**

## 特点

- 不需要 OpenAI API Key
- 不需要 Google Translate API Key
- 不需要手动安装 Python
- Render 自动安装 Python 依赖
- Render 自动安装 FFmpeg
- Render 自动下载 Whisper 模型
- 自动 HTTPS
- 手机/电脑浏览器都可以使用
- 英文字幕在底部，中文翻译在上方
- 输出 MP4

## 一键部署

### 第一步：上传到 GitHub

新建一个 GitHub Repository，例如：

`bilingual-video-translator`

把本项目所有文件上传到仓库根目录，并确保 `render.yaml` 也在根目录。

### 第二步：Render

打开 Render Dashboard：

https://dashboard.render.com/

选择：

**New → Blueprint**

连接刚刚的 GitHub Repository。

Render 会自动读取：

`render.yaml`

然后创建 Web Service。

不需要手动填写 Python、Build Command、Start Command。

### 第三步：等待首次部署

第一次部署会：

1. 安装 Python 依赖
2. 安装 FFmpeg
3. 安装中文字体
4. 下载 Whisper `tiny.en` 模型
5. 启动 Flask/Gunicorn
6. Render 自动提供 HTTPS 地址

首次 Build 会比普通 Flask 项目慢，因为需要下载 Whisper 模型。

## 使用

打开 Render 给你的：

`https://你的项目名.onrender.com`

上传英文视频，点击：

**开始生成双语字幕**

完成后点击：

**下载双语字幕视频**

## 默认模型

当前使用：

`tiny.en`

优点是体积小、CPU 运行相对容易，适合 Render Free。

如果你希望识别质量更高，可以把 Render 环境变量：

`WHISPER_MODEL=base.en`

或者：

`WHISPER_MODEL=small.en`

但模型越大，内存和处理时间要求越高。

## 关于 Google 免费翻译

本项目使用 `deep-translator` 调用 Google Translate 的公开网页翻译方式，不需要 Google Cloud Translation API Key。

因此：

- 不需要 API Key
- 不需要 Google Cloud 项目
- 不产生 Google Cloud Translation API 费用

但这是网页翻译方式，不是 Google 官方 Cloud Translation API。Google 可能随时调整网页接口或限流。

## Render Free 注意事项

Render 免费 Web Service 会在连续 15 分钟没有请求后休眠，再次访问时需要重新唤醒，官方说明首次恢复可能约 1 分钟。

免费实例使用临时文件系统，所以：

- 上传的视频不是永久保存
- 生成的视频不是永久保存
- 服务重启/重新部署后临时文件会消失

因此这个版本定位为：

**免费测试 / 个人使用 / 小规模使用**

而不是永久视频存储服务。

## 文件限制

默认最大上传：

`500 MB`

可以在 Render Environment Variables 修改：

`MAX_UPLOAD_MB`

## 本地运行

需要 Python 3.11 和 FFmpeg。

安装：

```bash
pip install -r requirements.txt
python download_model.py
python app.py
```

浏览器打开：

http://127.0.0.1:10000

## 项目结构

```text
bilingual-video-translator/
├── app.py
├── processor.py
├── download_model.py
├── requirements.txt
├── render.yaml
├── .python-version
├── .gitignore
├── README.md
├── templates/
│   └── index.html
└── static/
    ├── app.js
    └── style.css
```

## License

MIT
