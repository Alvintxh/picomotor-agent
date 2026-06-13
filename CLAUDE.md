# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the agents

```bash
# ReAct 版（主版本）
python agent.py

# Plan & Execute 版
python agent_plan_execute.py

# Tool-Use 版（备份）
python agent_tool_use.py
```

需要设置环境变量 `DEEPSEEK_API_KEY`，使用 DeepSeek API（base_url: `https://api.deepseek.com`，model: `deepseek-v4-pro`）。

## 架构

### 层次结构

```
motor.py         # Motor 类：单轴电机仿真，持有 is_connected / current_pos / limits / speed
tools.py         # 工具层：module-level motors dict + connected bool，封装 motor_connect / motor_status / move_rel
                 # TOOL_REGISTRY（工具名→函数）供 agent 调用；TOOLS（JSON Schema）供模型理解
agent*.py        # Agent 层：三种架构实现，共用 tools.py 和 gui.py
display.py       # rich 终端表格，在每次工具调用后打印电机状态
gui.py           # Dear PyGui 窗口，独立主线程运行，轮询 tools.motors 刷新
```

### 三种 Agent 架构对比

| 文件 | 架构 | 特点 |
|---|---|---|
| `agent.py` | ReAct | 文本格式推理链，`stop=["\nObservation:"]` 截断，正则解析 Action |
| `agent_tool_use.py` | Tool-Use | 结构化 `tool_calls` 字段，无需文本解析 |
| `agent_plan_execute.py` | Plan & Execute | 先规划（JSON输出）→人工确认→顺序执行→汇总，模型只在规划和汇总时调用 |

### 状态共享

`tools.connected`（全局连接状态）和 `tools.motors`（按轴名索引的 Motor 实例）是跨模块共享的运行时状态。GUI 线程直接读这两个变量刷新界面，无需 IPC。`motor_connect` 调用时同步更新所有已存在 Motor 的 `is_connected`；新轴第一次 `move_rel` 时通过 `get_motor()` 懒创建并继承当前连接状态。

### GUI 线程模型

macOS Cocoa 要求 GUI 必须在主线程。所有 agent 文件的 `__main__` 都把 agent 输入循环放在 `daemon` 子线程，`run_gui()` 在主线程执行。

## 命名约定

- 属性名用 `is_connected`（不是 `isconnected` 或 `_connected`）
- 模块级变量不用下划线前缀
