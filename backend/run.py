import os
import socket

import uvicorn

from app.core.config import get_settings


def is_port_available(host: str, port: int) -> bool:
    bind_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((bind_host, port)) != 0


def choose_port() -> int:
    settings = get_settings()
    candidates = [settings.server.port, *settings.server.fallback_ports]
    for port in candidates:
        if is_port_available(settings.server.host, port):
            return port
    raise RuntimeError(f"No available port in {candidates}")


if __name__ == "__main__":
    settings = get_settings()
    port = choose_port()
    # 把本次实际选定的监听端口告知应用，供运行期生成访问地址时使用，
    # 避免运行期重复探测端口时把本服务已占用的端口误判为不可用而 fallback 到错误端口。
    os.environ["TEACHING_ASSIST_ACTUAL_PORT"] = str(port)
    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=port,
        reload=settings.environment == "development",
    )
