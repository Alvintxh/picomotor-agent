import json
import os
import threading

from openai import OpenAI

import tools
from display import print_motor_status
from tools import TOOL_REGISTRY

client = OpenAI(api_key=os.environ.get('DEEPSEEK_API_KEY'),
                base_url="https://api.deepseek.com")

PLANNER_PROMPT = """你是一个电机控制规划器。根据用户指令和当前状态，制定完整的执行计划。

可用工具：
- motor_connect(cont_stus: int)：建立连接，cont_stus=1 连接，0 断开
- motor_status()：查询连接状态，无参数
- move_rel(axis: str, dist: float)：相对步进运动，axis 为轴名，dist 为步数

以 JSON 格式输出计划，不要输出任何其他内容：
{
  "steps": [
    {"step": 1, "description": "步骤说明", "tool": "工具名", "args": {...}},
    {"step": 2, "description": "步骤说明", "tool": "工具名", "args": {...}}
  ]
}

注意：
- 当前已连接时无需重复调用 motor_connect
- motor_status 无参数时 args 填 {}
- 一次规划所有步骤，不要遗漏
"""

SUMMARIZER_PROMPT = """根据执行结果，用简洁的自然语言向用户汇报任务完成情况。"""


def plan(user_prompt: str, motor_state: str) -> list:
    response = client.chat.completions.create(
        model="deepseek-v4-pro",  # type: ignore[arg-type]
        messages=[  # type: ignore[arg-type]
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": f"[当前电机状态：{motor_state}]\n{user_prompt}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=1000)
    content = response.choices[0].message.content or "{}"
    try:
        return json.loads(content).get("steps", [])
    except json.JSONDecodeError:
        return []


def execute(steps: list) -> list:
    results = []
    for step in steps:
        tool_name = step.get("tool", "")
        args = step.get("args", {})
        description = step.get("description", "")

        print(f"\n步骤 {step.get('step')}：{description}")
        print(f"  调用：{tool_name}({args})")

        fn = TOOL_REGISTRY.get(tool_name)
        if fn is None:
            result = f"错误：未知工具 {tool_name}"
        else:
            try:
                result = fn(**args)  # type: ignore[arg-type]
                if result is None:
                    result = "完成"
            except Exception as e:
                result = f"执行失败：{e}"

        print(f"  结果：{result}")
        print_motor_status(tools.motors, tools.connected)
        results.append({
            "step": step.get("step"),
            "description": description,
            "result": str(result)
        })

    return results


def summarize(user_prompt: str, results: list) -> str:
    results_text = "\n".join(
        [f"步骤{r['step']} {r['description']}：{r['result']}" for r in results])
    response = client.chat.completions.create(
        model="deepseek-v4-pro",  # type: ignore[arg-type]
        messages=[  # type: ignore[arg-type]
            {"role": "system", "content": SUMMARIZER_PROMPT},
            {"role": "user", "content": f"用户指令：{user_prompt}\n\n执行结果：\n{results_text}"},
        ],
        temperature=0.1,
        max_tokens=500)
    return response.choices[0].message.content or ""


def run_agent(user_prompt: str):
    motor_state = "已连接" if tools.connected else "未连接"

    print("\n[Planner] 规划中...")
    steps = plan(user_prompt, motor_state)

    if not steps:
        print("[Planner] 规划失败，未生成执行步骤")
        return

    print(f"\n[Planner] 计划共 {len(steps)} 步：")
    for s in steps:
        print(f"  {s.get('step')}. {s.get('description')}")

    confirm = input("\n确认执行以上计划？(y/n)：").strip().lower()
    if confirm != "y":
        print("已取消执行。")
        return

    print("\n[Executor] 执行中...")
    results = execute(steps)

    print("\n[Summarizer] 汇报中...")
    summary = summarize(user_prompt, results)
    print(f"\nAgent：{summary}")


def agent_loop():
    while True:
        try:
            user_input = input("\n请输入指令（输入 q 退出）：")
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.strip().lower() == "q":
            break
        if user_input.strip():
            run_agent(user_input)


if __name__ == "__main__":
    from gui import run_gui
    t = threading.Thread(target=agent_loop, daemon=True)
    t.start()
    run_gui()
