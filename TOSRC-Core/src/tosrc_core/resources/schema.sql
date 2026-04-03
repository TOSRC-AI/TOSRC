-- ==============================
-- TOSRC 通用核心数据库表结构
-- 单租户/多租户通用，SQLite/MySQL兼容
-- 完全按照生产级标准设计，无冗余，支持全量功能
-- ==============================

-- 1. 意图表（核心）
CREATE TABLE IF NOT EXISTS intents (
    intent_id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_code VARCHAR(100) NOT NULL UNIQUE,
    intent_name VARCHAR(100) NOT NULL,
    parent_id INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 500,
    is_enabled INTEGER DEFAULT 1,
    description TEXT,
    is_builtin INTEGER DEFAULT 0,
    industry_code VARCHAR(64) DEFAULT '',
    tenant_id VARCHAR(64) DEFAULT '',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_intent_parent_id ON intents(parent_id);
CREATE INDEX IF NOT EXISTS idx_intent_code ON intents(intent_code);
CREATE INDEX IF NOT EXISTS idx_intent_industry ON intents(industry_code);
CREATE INDEX IF NOT EXISTS idx_intent_tenant ON intents(tenant_id);

-- 2. 实体类型表（核心）
CREATE TABLE IF NOT EXISTS entity_types (
    entity_code VARCHAR(100) PRIMARY KEY,
    entity_name VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) DEFAULT 'enum', -- enum/extract/custom
    extract_pattern VARCHAR(256),
    description TEXT,
    is_builtin INTEGER DEFAULT 0,
    industry_code VARCHAR(64) DEFAULT '',
    tenant_id VARCHAR(64) DEFAULT '',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_entity_industry ON entity_types(industry_code);
CREATE INDEX IF NOT EXISTS idx_entity_tenant ON entity_types(tenant_id);

-- 3. 实体值表（核心，存储实体枚举值）
CREATE TABLE IF NOT EXISTS entity_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_code VARCHAR(100) NOT NULL,
    value VARCHAR(128) NOT NULL,
    alias TEXT, -- 别名，多个用逗号分隔
    weight FLOAT DEFAULT 1.0,
    is_enabled INTEGER DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_code, value)
);
CREATE INDEX IF NOT EXISTS idx_entity_value_code ON entity_values(entity_code);
CREATE INDEX IF NOT EXISTS idx_entity_value ON entity_values(value);

-- 4. 实体关键词匹配表（核心，支持快速匹配）
CREATE TABLE IF NOT EXISTS entity_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_code VARCHAR(100) NOT NULL,
    keyword VARCHAR(128) NOT NULL,
    weight FLOAT DEFAULT 1.0,
    is_enabled INTEGER DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_code, keyword)
);
CREATE INDEX IF NOT EXISTS idx_ek_keyword ON entity_keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_ek_entity_code ON entity_keywords(entity_code);

-- 5. 意图-实体关联表（核心，槽位填充规则）
CREATE TABLE IF NOT EXISTS intent_entity_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_code VARCHAR(100) NOT NULL,
    entity_code VARCHAR(100) NOT NULL,
    is_required INTEGER DEFAULT 0, -- 0=可选 1=必填
    priority INTEGER DEFAULT 10,
    UNIQUE(intent_code, entity_code)
);
CREATE INDEX IF NOT EXISTS idx_iem_intent ON intent_entity_mapping(intent_code);
CREATE INDEX IF NOT EXISTS idx_iem_entity ON intent_entity_mapping(entity_code);

-- 6. 对话路由记录表
CREATE TABLE IF NOT EXISTS route_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    intent_code VARCHAR(100),
    intent_name VARCHAR(100),
    entities TEXT,
    confidence FLOAT DEFAULT 0.0,
    cost_time INTEGER DEFAULT 0,
    scene VARCHAR(64) DEFAULT 'default',
    tenant_id VARCHAR(64) DEFAULT '',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_route_create_time ON route_records(create_time);
CREATE INDEX IF NOT EXISTS idx_route_tenant ON route_records(tenant_id);

-- 7. 规则包表
CREATE TABLE IF NOT EXISTS rule_packages (
    package_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene VARCHAR(100) NOT NULL UNIQUE,
    scene_name VARCHAR(100) NOT NULL,
    file_path VARCHAR(500),
    entity_rule_count INTEGER DEFAULT 0,
    intent_rule_count INTEGER DEFAULT 0,
    emotion_rule_count INTEGER DEFAULT 0,
    is_enabled INTEGER DEFAULT 1,
    last_modify_time INTEGER DEFAULT 0,
    industry_code VARCHAR(64) DEFAULT '',
    tenant_id VARCHAR(64) DEFAULT '',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rule_scene ON rule_packages(scene);

-- 8. 插件表
CREATE TABLE IF NOT EXISTS plugins (
    plugin_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    version VARCHAR(50) NOT NULL,
    scene VARCHAR(100),
    status VARCHAR(20) DEFAULT 'disabled',
    description TEXT,
    author VARCHAR(100),
    install_path VARCHAR(500),
    config TEXT,
    industry_code VARCHAR(64) DEFAULT '',
    tenant_id VARCHAR(64) DEFAULT '',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 9. 系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    config_id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT,
    config_group VARCHAR(50) NOT NULL,
    description TEXT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_config_key ON system_config(config_key);

-- 10. 自动学习样本表
CREATE TABLE IF NOT EXISTS learning_samples (
    sample_id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    intent_code VARCHAR(100),
    entities TEXT,
    is_annotated INTEGER DEFAULT 0,
    confidence FLOAT DEFAULT 0.0,
    tenant_id VARCHAR(64) DEFAULT '',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sample_annotated ON learning_samples(is_annotated);
CREATE INDEX IF NOT EXISTS idx_sample_tenant ON learning_samples(tenant_id);

-- 11. 意图神经元表（仿生语义核心，高级功能）
CREATE TABLE IF NOT EXISTS intent_neurons (
    neuron_id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_code VARCHAR(100) NOT NULL,
    activation_threshold FLOAT DEFAULT 0.7,
    weight FLOAT DEFAULT 1.0,
    is_enabled INTEGER DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_neuron_intent ON intent_neurons(intent_code);

-- 12. 突触权重表（神经元连接权重，高级功能）
CREATE TABLE IF NOT EXISTS synapse_weights (
    synapse_id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_code VARCHAR(100) NOT NULL,
    keyword VARCHAR(200) NOT NULL,
    weight FLOAT DEFAULT 1.0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(intent_code, keyword)
);
CREATE INDEX IF NOT EXISTS idx_synapse_intent ON synapse_weights(intent_code);
CREATE INDEX IF NOT EXISTS idx_synapse_keyword ON synapse_weights(keyword);