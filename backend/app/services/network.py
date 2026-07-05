import socket
import subprocess
from dataclasses import asdict, dataclass

from app.core.config import get_settings


VIRTUAL_KEYWORDS = ("vmware", "virtual", "docker", "hyper-v", "loopback", "wsl", "蓝牙")


@dataclass
class NetworkCandidate:
    name: str
    ip: str
    selected: bool = False


def _is_private_ipv4(ip: str) -> bool:
    return (
        ip.startswith("10.")
        or ip.startswith("192.168.")
        or any(ip.startswith(f"172.{index}.") for index in range(16, 32))
    )


def list_network_candidates() -> list[dict[str, object]]:
    hostname = socket.gethostname()
    ips: set[str] = set()
    try:
        for item in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ips.add(item[4][0])
    except socket.gaierror:
        pass
    try:
        ips.update(socket.gethostbyname_ex(hostname)[2])
    except socket.gaierror:
        pass

    filtered = sorted(ip for ip in ips if not ip.startswith("127.") and _is_private_ipv4(ip))
    candidates = [
        NetworkCandidate(name=f"本机网络 {index + 1}", ip=ip, selected=index == 0)
        for index, ip in enumerate(filtered)
    ]
    if not candidates:
        candidates.append(NetworkCandidate(name="本机回环地址", ip="127.0.0.1", selected=True))
    return [asdict(candidate) for candidate in candidates]


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) != 0


def choose_access_port() -> dict[str, object]:
    settings = get_settings()
    for port in [settings.server.port, *settings.server.fallback_ports]:
        if is_port_available(port):
            return {"port": port, "available": True, "fallback_used": port != settings.server.port}
    return {"port": settings.server.port, "available": False, "fallback_used": False}


def get_access_info(selected_ip: str | None = None, selected_port: int | None = None) -> dict[str, object]:
    candidates = list_network_candidates()
    ip = selected_ip or str(candidates[0]["ip"])
    port_info = choose_access_port()
    port = selected_port or int(port_info["port"])
    return {
        "candidates": candidates,
        "selected_ip": ip,
        "port": port,
        "access_url": f"http://{ip}:{port}",
        "port_status": port_info,
        "firewall": check_firewall(port),
    }


def check_firewall(port: int) -> dict[str, object]:
    try:
        completed = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name=TeachingAssist-{port}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=3,
        )
        rule_exists = completed.returncode == 0 and "No rules match" not in completed.stdout
    except Exception:
        rule_exists = False

    return {
        "port": port,
        "rule_exists": rule_exists,
        "status": "allowed_rule_found" if rule_exists else "manual_check_required",
        "message": "请确认 Windows 防火墙允许本程序访问专用网络。如需自动添加入站规则，请以管理员权限运行。",
        "admin_command": f'netsh advfirewall firewall add rule name="TeachingAssist-{port}" dir=in action=allow protocol=TCP localport={port}',
    }
