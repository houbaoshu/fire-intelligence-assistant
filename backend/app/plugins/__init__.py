"""服务端插件框架（M8）。

- 插件契约：模块级 ``PLUGIN``（``Plugin`` 数据类：name / version /
  description / hooks），内置插件位于 ``app/plugins/builtin/*.py``。
- 钩子执行点（平台定义）：
    - ``on_task_terminal``：任务进入终态（completed/failed/cancelled）后触发，
      上下文 ``{"task_id", "task_type", "status", "error_message"}``；
    - ``on_qa_answer``：法规问答产出回答后触发，上下文
      ``{"question", "answer", "sources"}``，钩子可就地修改 ``answer``。
- 启用状态存 plugins 表（DB 为唯一事实来源），禁用即不执行；
  钩子异常只记日志，绝不阻断主流程。
"""

from app.plugins.registry import Plugin, builtin_plugins, run_hook

__all__ = ["Plugin", "builtin_plugins", "run_hook"]
