"""超星（学习通）座位预约系统。

覆盖：`office.chaoxing.com` 的选座、续约、签到、暂离与查询端点，
两种 submit 防伪签名（enc）、
`.credentials.chaoxing.json` 凭据（换会话已外置到 vendor 子模块）。

支持座位查询、预约、续约、签到、暂离、回座与退座。

模块分工：
    config      主机、机构号、路径与规则常量
    enc         submit 签名与盐解析
    client      会话校验 + 端点封装 + 节流提交
    credentials 凭据读写（仅 chaoxing.com 域 Cookie）
    ui          终端呈现

换会话（newsso → 5read → login6）由 vendor 子模块 `systems/chaoxing.com/`
（config.py + client.py）实现，座位侧经 sso/runner.py 的 `chaoxing_redeem` 调用，
并从共享会话导出 chaoxing.com 域凭据。
"""

__all__ = ["config", "enc", "client", "credentials", "ui"]
