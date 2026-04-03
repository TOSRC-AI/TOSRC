# LLM Router 通用底座框架
## 项目简介
基于「规则优先+轻量模型兜底」的核心原则，搭建的100%自主可控、无外部API依赖、多业务场景可插拔的LLM Router层通用底座框架，核心解决「意图识别+实体提取+内部数据路由」三大核心能力。
## 项目目录结构
```
ai-llm-router/
├── src/                     # 核心源代码目录
│   ├── __init__.py
│   ├── rule_engine.py       # 规则引擎模块
│   ├── router_decision.py   # 路由决策引擎模块
│   └── model_engine.py      # 轻量模型引擎模块
├── config/                  # 配置文件目录
│   └── rules.yaml           # 规则配置文件
├── test/                    # 测试用例目录
│   ├── __init__.py
│   ├── access_layer/        # 接入层测试用例
│   ├── rule_engine/         # 规则引擎测试用例
│   │   └── test_rule_engine.py
│   ├── model_engine/        # 模型引擎测试用例
│   │   └── test_model_engine.py
│   ├── router_engine/       # 路由决策引擎测试用例
│   │   └── test_router_decision.py
│   ├── data_layer/          # 数据层测试用例
│   └── integration/         # 全链路集成测试用例
│       └── test_api.py
├── docs/                    # 文档目录
├── logs/                    # 日志目录
├── scripts/                 # 脚本目录（启动/停止/检查等）
├── deploy/                  # 部署配置目录（Docker/K8s等）
├── main.py                  # 主入口文件（FastAPI服务）
├── requirements.txt         # 依赖清单
├── pyproject.toml           # 项目配置文件（pytest/black等）
├── .flake8                  # flake8编码规范配置
├── .gitignore               # Git忽略配置
└── README.md                # 项目说明文档
```
## 编码规范
### 检查与格式化
```bash
# 安装代码检查工具
pip install black flake8 pytest pytest-cov

# 代码格式化
black .

# 代码规范检查
flake8 .
```
### 规范说明
1. **Python代码**遵循PEP8规范，行长度最大120字符
2. **命名规范**：
   - 类名：大驼峰命名（如`RuleEngine`）
   - 函数名/变量名：蛇形命名（如`predict_intent`、`rule_config_path`）
   - 常量名：全大写下划线分隔（如`DEFAULT_ROUTE`）
3. **注释规范**：
   - 函数必须包含功能说明、入参、出参注释
   - 复杂逻辑必须添加注释说明
   - 配置文件必须添加注释说明每个配置项的含义
## 测试相关
```bash
# 运行所有测试
pytest

# 运行单个模块测试
pytest test/rule_engine/test_rule_engine.py -v

# 生成覆盖率报告
pytest --cov=src --cov-report=html
# 报告生成在 htmlcov/index.html
```
### 测试覆盖率要求
核心代码覆盖率≥90%
## 服务启动
```bash
# 开发模式启动
python main.py

# 生产模式启动
uvicorn main:app --host 0.0.0.0 --port 8765 --workers 4
```
服务地址：http://localhost:8765
接口文档：http://localhost:8765/docs
