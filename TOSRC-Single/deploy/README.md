# LLM Router 监控部署指南
## 一键启动整套环境
### 1. 部署说明
使用Docker Compose一键启动整套环境，包含：
- LLM Router 核心服务
- Prometheus 监控采集
- Grafana 可视化仪表盘
### 2. 启动命令
```bash
cd deploy
docker-compose up -d
```
### 3. 访问地址
| 服务 | 地址 | 账号/密码 |
|------|------|-----------|
| LLM Router | http://localhost:8765 | 无 |
| Prometheus | http://localhost:9090 | 无 |
| Grafana | http://localhost:3000 | admin / admin123 |
### 4. 监控大盘说明
Grafana已经自动预配置了LLM Router监控大盘，包含以下核心面板：
#### 概览指标
- **QPS**：每秒请求数
- **P95响应时间**：95%的请求响应时间
- **错误率**：5xx错误请求占比
- **服务健康状态**：整体服务健康状态（1=健康，0=异常）
#### 流量分析
- **请求量趋势（按路由来源）**：按规则/模型/默认来源区分的请求趋势
- **路由目标分布**：各下游服务的请求占比
#### 业务指标
- **命中率趋势**：规则命中率、模型命中率、默认路由率
- **加载的规则数量**：当前规则引擎加载的规则总数
- **模型引擎状态**：模型引擎是否正常运行
### 5. 告警规则
系统内置了7条核心告警规则：
| 告警名称 | 严重级别 | 触发条件 |
|---------|---------|----------|
| LLMServiceDown | 严重 | 服务整体不可用超过1分钟 |
| RuleEngineDown | 严重 | 规则引擎不可用超过1分钟 |
| ModelEngineDown | 警告 | 模型引擎不可用超过2分钟（自动降级为纯规则模式） |
| HighErrorRate | 警告 | 最近5分钟错误率超过5% |
| HighLatency | 警告 | 最近5分钟P95响应时间超过500ms |
| HighDefaultRouteRate | 警告 | 最近10分钟默认路由占比超过20% |
| NoRulesLoaded | 严重 | 规则引擎未加载任何规则 |
### 6. 常用操作命令
```bash
# 启动服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f llm-router
docker-compose logs -f prometheus
docker-compose logs -f grafana

# 停止服务
docker-compose down

# 停止服务并删除数据卷（慎用，会丢失历史监控数据）
docker-compose down -v
```
### 7. 自定义配置
#### 修改Grafana密码
编辑`docker-compose.yml`中的`GF_SECURITY_ADMIN_PASSWORD`环境变量
#### 修改Prometheus采集间隔
编辑`prometheus/prometheus.yml`中的`scrape_interval`配置
#### 修改告警阈值
编辑`prometheus/alert_rules.yml`中的对应规则表达式
### 8. 手动导入仪表盘
如果仪表盘未自动加载，可手动导入：
1. 登录Grafana
2. 点击左侧菜单 → Dashboards → Import
3. 上传`deploy/grafana/dashboards/llm-router-overview.json`
4. 选择Prometheus数据源，点击Import
