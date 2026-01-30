# AgentBus 快速开始

## 安装依赖

### 方式1: 使用requirements.txt (推荐)
```bash
pip install -r requirements.txt
```

### 方式2: 使用pyproject.toml (完整配置)
```bash
pip install -e .
```

## 启动方式

### Web模式 (推荐)
```bash
python start_agentbus.py --mode web --port 8000
```
- Web界面: http://localhost:8000
- API文档: http://localhost:8000/docs

### CLI模式
```bash
python start_agentbus.py --mode cli
```

### 开发模式
```bash
python start_agentbus.py --mode dev --debug
```

## 配置

1. 复制环境配置示例:
   ```bash
   cp .env.example .env
   ```

2. 编辑配置文件:
   - `channels_config.json` - 渠道配置
   - `pyproject.toml` - 项目配置

## 快速验证

```bash
# 测试导入
python -c "from core.app import AgentBusServer; print('导入成功!')"

# 启动服务
python start_agentbus.py --help
```