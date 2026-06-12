import json
import os
import re

from openai import OpenAI

import tools
from tools import TOOL_REGISTRY

client = OpenAI(api_key=os.environ.get('DEEPSEEK_API_KEY'),
                base_url="https://api.deepseek.com")

SYSTEM_PROMPT = """你是一个专业的电机控制Agent。

你可以使用以下工具：
- motor_connect(cont_stus: int)：与电机建立连接。cont_stus=1 连接，0 断开。
- motor_status()：查询电机当前连接状态。
- move_rel(axis: str, dist: float)：电机相对步进运动。axis 为轴名（如 X、Y、Z），dist 为步数（正数正向，负数负向）。

请严格按照以下格式进行推理和行动，每次只输出到 Action Input 为止，等待 Observation 后再继续：

Thought: 思考当前需要做什么
Action: 工具名称
Action Input: {"参数名": 参数值}

收到 Observation 后继续：

Thought: 根据结果思考下一步
Action: ...
Action Input: ...

直到任务完成，输出：

Thought: 任务已完成
Final Answer: 用自然语言回复用户

注意：
- Action Input 必须是合法的 JSON，无参数时填 {}
- motor_connect 返回"连接成功"即表示已连接，无需再调用 motor_status 确认
- 确认连接后直接执行后续任务，不要重复检查状态
- 完成所有任务后才输出 Final Answer
"""


def parse_action(text: str):
    action_match = re.search(r"Action:\s*(\w+)", text)
    input_match = re.search(r"Action Input:\s*(\{.*?\})", text, re.DOTALL)

    if not action_match:
        return None, None

    action = action_match.group(1).strip()
    action_input = {}
    if input_match:
        try:
            action_input = json.loads(input_match.group(1))
        except json.JSONDecodeError:
            pass

    return action, action_input


def run_agent(user_prompt: str):
    motor_state = "已连接" if tools.isconnected else "未连接"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"[当前电机状态：{motor_state}]\n{user_prompt}"},
    ]

    while True:
        try:
            response = client.chat.completions.create(
                model="deepseek-v4-pro",  # type: ignore[arg-type]
                messages=messages,  # type: ignore[arg-type]
                temperature=0.1,
                max_tokens=2000,
                stop=["\nObservation:"])
        except Exception as e:
            print(f"调用失败：{e}")
            break

        output = response.choices[0].message.content or ""
        print(output)
        messages.append({"role": "assistant", "content": output})

        if "Final Answer:" in output:
            break

        action, action_input = parse_action(output)
        if action is None:
            print("[警告] 未解析到 Action，Agent 意外终止")
            break

        fn = TOOL_REGISTRY.get(action)
        if fn is None:
            observation = f"错误：未知工具 {action}"
        else:
            try:
                result = fn(**action_input)  # type: ignore[arg-type]
                observation = str(result) if result is not None else "完成"
            except Exception as e:
                observation = f"工具执行失败：{e}"

        obs_text = f"Observation: {observation}"
        print(obs_text)
        messages.append({"role": "user", "content": obs_text})


if __name__ == "__main__":
    while True:
        try:
            user_input = input("\n请输入指令（输入 q 退出）：")
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.strip().lower() == "q":
            break
        if user_input.strip():
            run_agent(user_input)
