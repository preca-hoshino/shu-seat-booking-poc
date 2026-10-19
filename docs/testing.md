# 测试

> [文档索引](README.md)

运行离线测试：

```bash
python -m unittest discover -s tests -v
```

测试覆盖登录会话与 Cookie、四类 there 资源的请求组装、超星座位查询与操作，以及失败时的凭据保存和重试行为。超星退座测试检查 GET 方法、预约 ID、首页 Referer 和无 `data` 的成功响应。模拟响应只验证客户端逻辑，不代表实时服务状态。

在可访问服务的环境中，先执行 `python login.py --check` 或重新登录，再运行只读查询。创建预约前使用 `book --dry-run` 检查参数；写操作后重新查询详情与最近预约，确认最终状态。
