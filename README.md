# 小红书 图片+文案 帖子生成器 (RedNote Image Post Generator)

一个基于AI的工具，用于生成小红书风格的黑白铅笔素描图片及配套文案。

## 功能特点

- 🎨 生成独特的黑白铅笔素描风格图片
- 📝 自动生成适配小红书风格的文案
- 🌐 支持中英文输入
- 🎲 随机建筑/景观提示词生成
- 💾 PWA支持，可安装为本地应用
- 🔄 异步任务处理，支持并发生成

## 技术栈

- **后端框架**: Flask
- **AI模型**: 
  - 图片生成: Hugging Face
  - 文案生成: Google Gemini
- **前端**: HTML5, CSS3, JavaScript
- **其他特性**: PWA, 异步任务处理

## 安装说明

1. 克隆项目
```bash
git clone https://github.com/wayne0926/RedNoteImagePostGenerator
cd RedNoteImagePostGenerator
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 环境变量配置
创建 `.env` 文件并配置以下变量：
```
# 必需配置
HF_API_KEY=你的HuggingFace API密钥
GEMINI_API_KEY=你的Google Gemini API密钥

# OpenAI配置（可选，用于备选翻译服务）
OPENAI_API_KEY=你的OpenAI API密钥
OPENAI_BASE_URL=https://api.siliconflow.cn/v1/  # 默认使用siliconflow提供的API服务

# 其他可选配置
AI_PROVIDER=gemini  # AI提供商选择，目前仅支持gemini
```

4. 运行应用
```bash
python app.py
```

## 使用方法

1. 访问 `http://localhost:5000`
2. 在输入框中输入你想要生成的图片描述
3. 点击生成按钮
4. 等待图片和文案生成完成
5. 可以下载生成的图片或复制生成的文案

## API 接口

### 提交生成请求
- **POST** `/submit_prompt`
- 请求体: `{"prompt_suffix": "你的提示词"}`

### 获取生成状态
- **GET** `/get_status`
- 查询参数: `task_id`

### 生成文案
- **POST** `/generate_caption`
- 请求体: `{"prompt": "图片描述"}`

### 获取随机提示词
- **GET** `/random_prompt`

## 注意事项

- 图片生成可能需要一些时间，请耐心等待
- API密钥请妥善保管，不要泄露
- 建议使用现代浏览器以获得最佳体验

## 许可证

MIT License

Copyright (c) 2024 RedNote Image Post Generator

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进项目。