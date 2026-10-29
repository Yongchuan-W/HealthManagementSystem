"""统一的接口异常：由路由层捕获并转成 JSON 错误响应。"""


class ApiError(Exception):
    def __init__(self, status=400, message="请求有误", code=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code or "bad_request"
