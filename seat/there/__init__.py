"""本校 there 四入口预约系统（图书馆 / 24H 学习空间 / 延长智能中心 / 科学与艺术中心）。

- `config`       四入口与 nine 个实测端点的协议常量
- `models`       bootstrap / profile / 请求体解析与组装
- `client`       移动页面会话解析 + 业务 HTTP 客户端 + 节流提交
- `credentials`  凭据读写（仅 there 域 Cookie）与私有文件原子写
- `ui`           终端表格渲染与输出脱敏

导入模块不联网。与 `seat.chaoxing`（超星/学习通）完全独立。
"""

__all__ = ["client", "config", "credentials", "models", "ui"]
