import requests
import json
import os
import time
import base64
import mimetypes
from PIL import Image
import io
import subprocess
from tools import TOOLS, TOOL_REGISTRY

API_URL = os.environ.get('SHANGHAITECH_API_URL')
API_KEY = os.environ.get('CHATGPT5p5_API_KEY')

if not API_URL or not API_KEY:
    raise Exception("请先配置环境变量 SHANGHAITECH_API_URL 与 CHATGPT5p5_API_KEY")

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

messages = [{
    "role":
    "system",
    "content": ("你是一个电机控制助手，通过工具控制 Newport Picomotor 压电电机。\n"
                "规则：\n"
                "1. 执行任何运动前，必须先调用 motor_connect(cont_stus=1) 建立连接。\n"
                "2. 用户描述方向时，正数 = 正向，负数 = 反向。\n"
                "3. 只回答与电机控制相关的问题。")
}]
type_delay = 0.01

# ── 图片工具────────────────────────────────────────────────────────────────


def clipboard_img_to_b64():
    proc = subprocess.Popen(["pngpaste", "-"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    png_bytes, err = proc.communicate()
    if proc.returncode != 0 or len(png_bytes) < 100:
        raise Exception(f"剪贴板无图片: {err.decode('utf-8', 'ignore')}")
    img = Image.open(io.BytesIO(png_bytes))
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    return f"data:image/jpeg;base64,{b64}"


def make_image_message(img_b64, question):
    return {
        "role":
        "user",
        "content": [
            {
                "type": "text",
                "text": question
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": img_b64
                }
            },
        ]
    }


# ── 核心：流式请求 + tool_calls 累积────────────────────────────────────────


def call_api_streaming(msgs):
    """
    发起一次流式请求，返回 (full_content, tool_calls, finish_reason)。
    tool_calls 是列表，格式与 OpenAI 一致；失败时返回 (None, None, None)。
    """
    payload = {
        "stream": True,
        "model": "GPT-5.5",
        "messages": msgs,
        "tools": TOOLS,
        "tool_choice": "auto",
    }
    response = requests.post(API_URL,
                             headers=headers,
                             json=payload,
                             stream=True)

    if response.status_code != 200:
        print(f"API 错误 {response.status_code}: {response.text}")
        return None, None, None

    print("AI：", end="", flush=True)
    full_content = ""
    tool_calls_acc = {}  # index -> {id, name, arguments}
    finish_reason = None

    for line in response.iter_lines():
        if not line:
            continue
        raw = line.decode("utf-8")
        if not raw.startswith("data:"):
            continue
        json_str = raw[5:].strip()
        if json_str == "[DONE]":
            break
        try:
            chunk = json.loads(json_str)
            choice = chunk["choices"][0]
            delta = choice["delta"]
            if choice.get("finish_reason"):
                finish_reason = choice["finish_reason"]

            # 普通文本内容
            content = delta.get("content") or ""
            if content:
                for char in content:
                    print(char, end="", flush=True)
                    time.sleep(type_delay)
                full_content += content

            # 累积 tool_calls（分块到达，需拼接）
            for tc in delta.get("tool_calls", []):
                idx = tc["index"]
                if idx not in tool_calls_acc:
                    tool_calls_acc[idx] = {
                        "id": "",
                        "name": "",
                        "arguments": ""
                    }
                if tc.get("id"):
                    tool_calls_acc[idx]["id"] = tc["id"]
                fn = tc.get("function", {})
                if fn.get("name"):
                    tool_calls_acc[idx]["name"] += fn["name"]
                if fn.get("arguments"):
                    tool_calls_acc[idx]["arguments"] += fn["arguments"]

            if finish_reason in ("stop", "tool_calls"):
                break
        except Exception:
            continue

    print()

    tool_calls = [{
        "id": tool_calls_acc[i]["id"],
        "type": "function",
        "function": {
            "name": tool_calls_acc[i]["name"],
            "arguments": tool_calls_acc[i]["arguments"],
        }
    } for i in sorted(tool_calls_acc)]
    return full_content, tool_calls, finish_reason


def run_turn(msgs):
    """
    执行一个完整的对话轮次（含 tool_calls 循环）。
    将所有新消息追加进 msgs，返回是否成功。
    """
    while True:
        content, tool_calls, finish_reason = call_api_streaming(msgs)
        if content is None:
            return False

        # 构造 assistant 消息
        assistant_msg = {"role": "assistant", "content": content or None}
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        msgs.append(assistant_msg)

        if not tool_calls or finish_reason == "stop":
            print()
            return True

        # 执行工具并收集结果
        print()
        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            try:
                fn_args = json.loads(tc["function"]["arguments"] or "{}")
            except Exception:
                fn_args = {}

            print(f"  [工具调用] {fn_name}({fn_args})")
            result = TOOL_REGISTRY[fn_name](
                **fn_args) if fn_name in TOOL_REGISTRY else f"未知工具: {fn_name}"
            print(f"  [工具结果] {result}\n")

            msgs.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })
        # 继续循环，让模型消化工具结果后继续回复


# ── 主循环────────────────────────────────────────────────────────────────────

print("=== 交互指令说明 ===")
print("q                     退出对话")
print("img:/xxx/xx.jpg       读取本地图片文件")
print("clipimg               剪贴板图片，默认提问：详细解读这张图片")
print("clipimg:你的问题      剪贴板图片 + 自定义提问")
print("普通文字直接输入聊天\n")

while True:
    user_input = input("你：").strip()
    if user_input.lower() == 'q':
        print("再见！")
        break
    if not user_input:
        continue

    if user_input.startswith("clipimg"):
        question = user_input[7:].lstrip(":").strip() or "详细解读这张图片"
        try:
            img_b64 = clipboard_img_to_b64()
            messages.append(make_image_message(img_b64, question))
        except Exception as err:
            print(f"剪贴板图片读取失败：{err}")
            continue

    elif user_input.startswith("img:"):
        img_path = user_input[4:].strip()
        try:
            with open(img_path, "rb") as f:
                raw_bytes = f.read()
            mime_type, _ = mimetypes.guess_type(img_path)
            if not mime_type or not mime_type.startswith("image/"):
                mime_type = "image/jpeg"
            b64_str = base64.b64encode(raw_bytes).decode("utf-8")
            img_b64 = f"data:{mime_type};base64,{b64_str}"
            messages.append(make_image_message(img_b64, "描述并分析这张图片"))
        except Exception as err:
            print(f"本地图片读取失败：{err}")
            continue

    else:
        messages.append({"role": "user", "content": user_input})

    mark = len(messages)
    success = run_turn(messages)
    if not success:
        del messages[mark - 1:]  # 回滚本轮所有消息
