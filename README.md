# 🦉 OwlDNS

[![Project Status](https://img.shields.io/badge/status-ready-success.svg)](#)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#)
[![Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)](#)

**OwlDNS** 是一个极简、轻量、且具备“反重力（Antigravity）”哲学的 Python 异步 DNS 服务端程序。

## ✨ 特性

- **Antigravity 风格**: 代码精简到极致，无冗余，高解耦。
- **异步驱动**: 基于 Python `asyncio` 构建，轻松处理高并发网络请求。
- **自定义解析**: 支持通过简单的字典配置静态 A 记录解析。
- **上游转发**: 支持可选的上游 DNS 转发（如 `8.8.8.8`），处理本地未命中的查询。
- **零配置安装**: 支持 Poetry 和 Pip 安装，提供开箱即用的命令行工具。
- **高测试覆盖**: 核心逻辑 100% 测试覆盖，整体覆盖率高达 99%。

## 🚀 快速开始

### 1. 安装

使用 Poetry 进行安装：

```bash
git clone <your-repo-url>
cd OwlDNS
poetry install
```

或者使用 pip：

```bash
pip install .
```

### 2. 使用命令行 (CLI)

默认运行（监听 `127.0.0.1:5353`）：

```bash
owldns
```

自定义配置（端口、上游服务器、静态解析记录）：

```bash
owldns --host 0.0.0.0 --port 5353 --upstream 1.1.1.1 --record example.com=1.2.3.4 --record mytest.lan=192.168.1.100
```

### 3. 作为库调用

```python
import asyncio
from owldns import OwlDNSServer

async def main():
    # 初始化服务器
    server = OwlDNSServer(
        host="127.0.0.1",
        port=5353,
        records={"hello.world": "10.0.0.1"},
        upstream="8.8.8.8"
    )
    # 启动异步循环
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
```

## 🧪 测试

OwlDNS 极度重视稳定性，您可以运行以下命令查看覆盖率报告：

```bash
poetry run pytest --cov=owldns --cov-report=term-missing tests/
```

## 📄 开源协议

本项目采用 [MIT](LICENSE) 协议。
