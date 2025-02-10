from flask import Flask, request, jsonify, render_template, make_response, send_from_directory
from huggingface_hub import InferenceClient
from PIL import Image
import io
import threading
import time
import uuid
import base64
import logging  # Import the logging module
from openai import OpenAI # Remove OpenAI import
from dotenv import load_dotenv
import os
from typing import Dict, Literal
import re
import json
from google import genai
from google.genai import types
from flask_cors import CORS  # Add this import at the top


# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO) # Set logging level to INFO (you can adjust as needed)
logger = logging.getLogger(__name__) # Get a logger instance

# --- Configuration ---
HF_API_KEY = os.getenv("HF_API_KEY")
MODEL_NAME = "Ethanxaf/sx"
PREFIX_PROMPT = "shou_xin, a monochromatic pencil sketch of a "
IMAGE_FOLDER = "generated_images"

# OpenAI配置 - Remove OpenAI Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

# 添加新的配置
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")  # 默认使用 gemini

# 验证必要的环境变量
if not HF_API_KEY or not GEMINI_API_KEY: # Modify required API keys
    logger.error("缺少必要的API密钥配置")
    raise ValueError("请在.env文件中配置HF_API_KEY和 GEMINI_API_KEY") # Modify error message

# --- Global Variables ---
hf_client = InferenceClient(provider="hf-inference", api_key=HF_API_KEY)
prompt_queue = []
generated_images = {}
processing_tasks = {}
task_timestamps = {}  # 新增：用于存储任务时间戳
caption_results: Dict[str, Dict] = {}  # 存储文案生成结果

# OpenAI client - Remove OpenAI client
openai_client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
)

# 初始化 Gemini 客户端
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)



# --- Image Generation Function ---
def generate_image_task(task_id, full_prompt):
    processing_tasks[task_id] = "processing"
    task_timestamps[task_id]["start_time"] = time.time()
    try:
        # 使用 Hugging Face 生成图片
        image = hf_client.text_to_image(full_prompt, model=MODEL_NAME)

        # Convert PIL Image to data URL
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        image_data_url = f"data:image/png;base64,{base64.b64encode(img_byte_arr).decode('utf-8')}"

        # 在这里添加原始提示词
        generated_images[task_id] = {
            "url": image_data_url,
            "original_prompt": next((item["original_prompt"] for item in prompt_queue if item["task_id"] == task_id), None)
        }
        processing_tasks[task_id] = "completed"
        task_timestamps[task_id]["end_time"] = time.time()

    except Exception as e:
        logger.error(f"Error generating image for prompt '{full_prompt}': {e}")
        processing_tasks[task_id] = "error"
        generated_images[task_id] = {"error": str(e)}
        task_timestamps[task_id]["end_time"] = time.time()

def translate_to_english(chinese_text):
    try:
        response = openai_client.chat.completions.create( # Keep OpenAI for translation if needed, otherwise remove
            model="google/gemma-2-9b-it",
            messages=[
                {"role": "system", "content": "你是一个翻译助手,请将用户的中文输入翻译成英文。只需要返回翻译结果,不需要任何解释。"},
                {"role": "user", "content": chinese_text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"翻译失败: {str(e)}")
        raise Exception("翻译服务暂时不可用")

def generate_caption_with_provider(
    prompt: str,
    provider: Literal["gemini"] = "gemini"
) -> Dict[str, str]:
    """统一的文案生成函数，支持多个提供商"""

    system_prompt = """你是一个专业的小红书图片文案创作者。
    请基于用户的图片描述创作文案，必须包含标题和正文。

    要求：
    1. 必须严格按照JSON格式输出
    2. 不要添加任何其他解释文字
    3. 标题应该简短有力，8-20字
    4. 我的图片是黑白铅笔画，但是禁止提到任何有关绘画的内容
    5. 无需加入话题标签
    6. 不要使用任何表情符号
    

    输出格式示例：
    {
        "title": "这里是标题文本",
        "content": "这里是正文内容"
    }
    """

    try:
        if provider == "gemini":
            response = client.models.generate_content(
                config=types.GenerateContentConfig(
                    temperature=2,
                ),
                model="gemini-2.0-flash",
                contents=f"{system_prompt}\n\n请为这张图片创作文案，图片描述：{prompt}。记住只输出JSON格式，不要其他文字。"
            )
            caption_text = response.text

        # Remove openai part completely

        # 处理返回的文本
        # logger.info(f"AI原始返回 ({provider}): {caption_text}")

        # 尝试提取和解析JSON
        json_match = re.search(r'\{[\s\S]*\}', caption_text)
        if json_match:
            caption_text = json_match.group()

        caption_data = json.loads(caption_text)

        # 验证JSON结构
        if not isinstance(caption_data, dict):
            raise ValueError("返回的不是有效的对象格式")

        if 'title' not in caption_data or 'content' not in caption_data:
            raise ValueError("缺少必要的字段(title或content)")

        return caption_data

    except Exception as e:
        logger.error(f"{provider} 生成失败: {str(e)}")
        raise

def generate_caption_with_retry(original_prompt: str, max_retries: int = 3) -> Dict[str, str]:
    """带重试机制的文案生成函数"""
    last_error = None

    for attempt in range(max_retries):
        try:
            # 使用配置的 AI 提供商 - now always Gemini
            return generate_caption_with_provider(original_prompt, "gemini") # Hardcode provider to "gemini"

        except Exception as e:
            last_error = e
            logger.error(f"第{attempt + 1}次尝试失败: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"等待重试...")
                time.sleep(1)
            continue

    # Remove OpenAI fallback logic completely

    raise Exception(f"经过{max_retries}次尝试后仍然失败: {str(last_error)}")

def generate_random_landmark_prompt():
    system_prompt = """You are a professional AI art prompt creator.
    Please randomly generate a prompt for generating a black and white sketch of a building or landscape anywhere in the world.
    
    Requirements:

    1. The prompt should be specific and visually evocative.
    2. It must be a real building or landscape.
    3. No need to specify the creative form; only return the generated prompt.
    4. It can be any building or landscape in any corner of the world.
    5. The more random, the better; do not repeat.


    
    Only return the generated prompt, no other explanation."""
    
    try:
        response = client.models.generate_content(
            config=types.GenerateContentConfig(
                temperature=2,
            ),
            model="gemini-2.0-flash-lite-preview-02-05",
            contents=system_prompt
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"生成随机提示词失败: {str(e)}")
        raise

def translate_to_chinese(english_text):
    """将英文文本翻译成中文"""
    try:
        response = client.models.generate_content(
            config=types.GenerateContentConfig(
                temperature=0.1,
            ),
            model="gemini-2.0-flash",
            contents=f"Translate the following English text to Chinese. Only return the translation, no explanations:\n\n{english_text}"
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"翻译失败: {str(e)}")
        raise Exception("翻译服务暂时不可用")

# --- API Endpoints ---

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/submit_prompt', methods=['POST'])
def submit_prompt():
    data = request.get_json()
    if not data or 'prompt_suffix' not in data:
        logger.warning("收到无效的提交请求: 缺少 'prompt_suffix'")
        return jsonify({"error": "请求体中缺少 'prompt_suffix'"}), 400

    chinese_prompt = data['prompt_suffix']
    try:
        # 先翻译成英文
        english_prompt = translate_to_english(chinese_prompt)
        logger.info(f"翻译结果: '{chinese_prompt}' -> '{english_prompt}'")

        # 构建完整提示词
        full_prompt = PREFIX_PROMPT + english_prompt
        task_id = str(uuid.uuid4())

        prompt_queue.append({
            "task_id": task_id,
            "prompt": full_prompt,
            "original_prompt": chinese_prompt  # 保存原始中文提示词
        })

        processing_tasks[task_id] = "queued"
        task_timestamps[task_id] = {
            "start_time": None,
            "end_time": None
        }

        thread = threading.Thread(target=generate_image_task, args=(task_id, full_prompt))
        thread.daemon = True
        thread.start()

        return jsonify({
            "message": "提示词已提交并加入队列处理",
            "task_id": task_id,
            "translated_prompt": english_prompt
        }), 202

    except Exception as e:
        logger.error(f"处理提示词时出错: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/get_status', methods=['GET'])
def get_status():
    task_id = request.args.get('task_id')
    if task_id:
        status = processing_tasks.get(task_id, "unknown")
        image_data = generated_images.get(task_id, None)
        timestamps = task_timestamps.get(task_id, {"start_time": None, "end_time": None})

        # 从队列中获取原始提示词
        original_prompt = next((item["original_prompt"] for item in prompt_queue if item["task_id"] == task_id), None)

        return jsonify({
            "status": status,
            "image_url": image_data["url"] if isinstance(image_data, dict) and "url" in image_data else image_data,
            "timestamps": timestamps,
            "original_prompt": original_prompt
        })
    else:
        task_statuses = {}
        for task_id_key in processing_tasks:
            image_data = generated_images.get(task_id_key, None)
            # 从队列中获取原始提示词
            original_prompt = next((item["original_prompt"] for item in prompt_queue if item["task_id"] == task_id_key), None)

            task_statuses[task_id_key] = {
                "status": processing_tasks[task_id_key],
                "image_url": image_data["url"] if isinstance(image_data, dict) and "url" in image_data else image_data,
                "timestamps": task_timestamps.get(task_id_key, {"start_time": None, "end_time": None}),
                "original_prompt": original_prompt
            }
        return jsonify(task_statuses)


@app.route('/generate_caption', methods=['POST'])
def generate_caption():
    data = request.get_json()
    task_id = data.get('task_id')
    original_prompt = data.get('original_prompt')

    logger.info(f"收到文案生成请求: task_id={task_id}, prompt={original_prompt}")

    if not task_id or not original_prompt:
        logger.warning("缺少必要参数")
        return jsonify({"error": "缺少必要参数"}), 400

    try:
        logger.info("开始生成文案...")
        caption_results[task_id] = {"status": "processing"}

        # 使用重试机制生成文案
        caption_data = generate_caption_with_retry(original_prompt)

        caption_results[task_id] = {
            "status": "completed",
            "caption": caption_data
        }

        logger.info(f"文案生成成功: {str(caption_data)[:100]}...")
        return jsonify({
            "status": "success",
            "caption": caption_data
        })

    except Exception as e:
        logger.error(f"生成文案时出错: {str(e)}")
        return jsonify({
            "error": str(e),
            "detail": "请重试，如果问题持续存在请联系管理员"
        }), 500

@app.route('/random_prompt', methods=['GET'])
def get_random_prompt():
    try:
        random_prompt = generate_random_landmark_prompt()
        # 将英文提示词翻译成中文
        chinese_prompt = translate_to_chinese(random_prompt)
        return jsonify({
            "prompt": chinese_prompt,
            "original_english": random_prompt  # 可选：如果你想保存原始英文
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/static/sw.js')
def service_worker():
    response = make_response(send_from_directory('static', 'sw.js'))
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'
    return response

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

if __name__ == '__main__':
    import os
    if not os.path.exists(IMAGE_FOLDER):
        os.makedirs(IMAGE_FOLDER)

    app.run(debug=True, host='0.0.0.0')
