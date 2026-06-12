import json
import os

from openai import OpenAI

from tools import TOOL_REGISTRY, TOOLS

client = OpenAI(api_key=os.environ.get('DEEPSEEK_API_KEY'),
                base_url="https://api.deepseek.com")


def run_agent(user_prompt: str):
    """
    Agent 主循环
    - user_prompt: 用户的任务描述
    """

    system_prompt = """你是一个专业的电机控制Agent，你可以使用工具来控制电机的连接与相对运动。

    工作流程：
    1. 先使用 motor_status 来确定电机是否连接。
    2. 然后使用 motor_connect 来控制电机的连接。
    3. 最后使用 move_rel 控制电机相对运动。
    4. 运动完成后，用自然语言回复运动结果。

    注意：
    - 运动前需先确定电机是否连接，没有连接的话需要提醒用户手动连接，不要自己盲目连接。
    - 运动前先确认相关参数是否正确，不要盲目执行运动
    """

    messages = [{
        "role": "system",
        "content": system_prompt
    }, {
        "role": "user",
        "content": user_prompt
    }]

    while True:
        try:
            response = client.chat.completions.create(
                model="deepseek-v4-pro",  # type: ignore[arg-type]
                messages=messages,  # type: ignore[arg-type]
                tools=TOOLS,  # type: ignore[arg-type]
                tool_choice="auto",
                temperature=0.1,
                max_tokens=2000)
        except Exception as e:
            print(f"调用失败：{e}")
            break

        msg = response.choices[0].message
        messages.append(msg)  # type: ignore[arg-type]

        if not msg.tool_calls:
            print("模型完成回答，Tools 调用结束。")
            print(f"\nAgent：{msg.content}")
            break

        for tool_call in msg.tool_calls:
            name = tool_call.function.name  # type: ignore[union-attr]
            args = json.loads(
                tool_call.function.arguments)  # type: ignore[union-attr]

            print(f"调用工具：{name}，参数：{args}")

            fn = TOOL_REGISTRY.get(name)
            if fn is None:
                result = f"错误：未知工具 {name}"
            else:
                try:
                    result = fn(**args)
                    if result is None:
                        result = "运动完成"
                except Exception as e:
                    result = f"工具执行失败：{e}"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result)
            })


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
