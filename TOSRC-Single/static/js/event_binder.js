// 事件绑定管理器
// 负责将HTML中的内联事件处理器转换为JavaScript动态绑定

class EventBinder {
    constructor() {
        this.bindings = [];
        this.initialized = false;
    }

    // 初始化所有事件绑定
    init() {
        if (this.initialized) return;
        
        console.log("初始化事件绑定...");
        
        // Tab切换按钮
        this.bindTabEvents();
        
        // 场景管理按钮
        this.bindSceneEvents();
        
        // 搜索输入框
        this.bindSearchEvents();
        
        // 版本管理按钮
        this.bindVersionEvents();
        
        // 灰度发布按钮
        this.bindGrayEvents();
        
        // 审计日志按钮
        this.bindAuditEvents();
        
        // 导入导出按钮
        this.bindImportExportEvents();
        
        // 模态框关闭按钮
        this.bindModalEvents();
        
        this.initialized = true;
        console.log("事件绑定初始化完成");
    }

    // 绑定Tab切换事件
    bindTabEvents() {
        const tabButtons = {
            'scene': 'sceneTab',
            'version': 'versionTab',
            'gray': 'grayTab',
            'audit': 'auditTab',
            'samples': 'samplesTab'
        };

        Object.entries(tabButtons).forEach(([tabName, tabId]) => {
            const button = document.querySelector(`[data-tab="${tabName}"]`);
            if (button) {
                button.addEventListener('click', () => {
                    if (typeof switchTab === 'function') {
                        switchTab(tabName);
                    }
                });
                this.bindings.push({ element: button, event: 'click', tabName });
            }
        });
    }

    // 绑定场景管理事件
    bindSceneEvents() {
        // 新增场景按钮
        const addSceneBtn = document.getElementById('addSceneBtn');
        if (addSceneBtn) {
            addSceneBtn.addEventListener('click', () => {
                if (typeof openAddSceneModal === 'function') {
                    openAddSceneModal();
                }
            });
            this.bindings.push({ element: addSceneBtn, event: 'click', action: 'openAddSceneModal' });
        }

        // 导入场景按钮
        const importSceneBtn = document.getElementById('importSceneBtn');
        if (importSceneBtn) {
            importSceneBtn.addEventListener('click', () => {
                if (typeof openImportModal === 'function') {
                    openImportModal();
                }
            });
            this.bindings.push({ element: importSceneBtn, event: 'click', action: 'openImportModal' });
        }

        // 导出场景按钮
        const exportSceneBtn = document.getElementById('exportSceneBtn');
        if (exportSceneBtn) {
            exportSceneBtn.addEventListener('click', () => {
                if (typeof exportScenes === 'function') {
                    exportScenes();
                }
            });
            this.bindings.push({ element: exportSceneBtn, event: 'click', action: 'exportScenes' });
        }

        // 重载配置按钮
        const reloadConfigBtn = document.getElementById('reloadConfigBtn');
        if (reloadConfigBtn) {
            reloadConfigBtn.addEventListener('click', () => {
                if (typeof reloadConfig === 'function') {
                    reloadConfig();
                }
            });
            this.bindings.push({ element: reloadConfigBtn, event: 'click', action: 'reloadConfig' });
        }
    }

    // 绑定搜索事件
    bindSearchEvents() {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            // 使用防抖技术，避免频繁触发搜索
            let debounceTimer;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    if (typeof searchScenes === 'function') {
                        searchScenes(e.target.value);
                    }
                }, 300); // 300ms防抖
            });
            
            this.bindings.push({ element: searchInput, event: 'input', action: 'searchScenes' });
        }
    }

    // 绑定版本管理事件
    bindVersionEvents() {
        const createVersionBtn = document.getElementById('createVersionBtn');
        if (createVersionBtn) {
            createVersionBtn.addEventListener('click', () => {
                if (typeof openCreateVersionModal === 'function') {
                    openCreateVersionModal();
                }
            });
            this.bindings.push({ element: createVersionBtn, event: 'click', action: 'openCreateVersionModal' });
        }
    }

    // 绑定灰度发布事件
    bindGrayEvents() {
        const createGrayBtn = document.getElementById('createGrayBtn');
        if (createGrayBtn) {
            createGrayBtn.addEventListener('click', () => {
                if (typeof openCreateGrayModal === 'function') {
                    openCreateGrayModal();
                }
            });
            this.bindings.push({ element: createGrayBtn, event: 'click', action: 'openCreateGrayModal' });
        }
    }

    // 绑定审计日志事件
    bindAuditEvents() {
        const loadAuditBtn = document.getElementById('loadAuditBtn');
        if (loadAuditBtn) {
            loadAuditBtn.addEventListener('click', () => {
                if (typeof loadAuditLogs === 'function') {
                    loadAuditLogs();
                }
            });
            this.bindings.push({ element: loadAuditBtn, event: 'click', action: 'loadAuditLogs' });
        }
    }

    // 绑定导入导出事件
    bindImportExportEvents() {
        // 导入类型切换
        const jsonTabBtn = document.getElementById('jsonTabBtn');
        const csvTabBtn = document.getElementById('csvTabBtn');
        
        if (jsonTabBtn) {
            jsonTabBtn.addEventListener('click', () => {
                if (typeof switchImportType === 'function') {
                    switchImportType('json');
                }
            });
            this.bindings.push({ element: jsonTabBtn, event: 'click', action: 'switchImportType-json' });
        }
        
        if (csvTabBtn) {
            csvTabBtn.addEventListener('click', () => {
                if (typeof switchImportType === 'function') {
                    switchImportType('csv');
                }
            });
            this.bindings.push({ element: csvTabBtn, event: 'click', action: 'switchImportType-csv' });
        }

        // 文件拖拽区域
        const fileDropArea = document.getElementById('fileDropArea');
        if (fileDropArea) {
            fileDropArea.addEventListener('click', () => {
                const fileInput = document.getElementById('csvFileInput');
                if (fileInput) {
                    fileInput.click();
                }
            });
            this.bindings.push({ element: fileDropArea, event: 'click', action: 'triggerFileInput' });
        }

        // 导入操作按钮
        const importActionBtn = document.getElementById('importActionBtn');
        if (importActionBtn) {
            importActionBtn.addEventListener('click', () => {
                if (typeof processImport === 'function') {
                    processImport();
                }
            });
            this.bindings.push({ element: importActionBtn, event: 'click', action: 'processImport' });
        }
    }

    // 绑定模态框事件
    bindModalEvents() {
        // 场景模态框关闭
        const closeSceneModalBtn = document.getElementById('closeSceneModalBtn');
        if (closeSceneModalBtn) {
            closeSceneModalBtn.addEventListener('click', () => {
                if (typeof closeSceneModal === 'function') {
                    closeSceneModal();
                }
            });
            this.bindings.push({ element: closeSceneModalBtn, event: 'click', action: 'closeSceneModal' });
        }

        // 场景模态框取消按钮
        const cancelSceneModalBtn = document.getElementById('cancelSceneModalBtn');
        if (cancelSceneModalBtn) {
            cancelSceneModalBtn.addEventListener('click', () => {
                if (typeof closeSceneModal === 'function') {
                    closeSceneModal();
                }
            });
            this.bindings.push({ element: cancelSceneModalBtn, event: 'click', action: 'closeSceneModal' });
        }

        // 场景模态框内部按钮
        this.bindSceneModalInternalEvents();

        // 导入模态框关闭
        const closeImportModalBtn = document.getElementById('closeImportModalBtn');
        if (closeImportModalBtn) {
            closeImportModalBtn.addEventListener('click', () => {
                if (typeof closeImportModal === 'function') {
                    closeImportModal();
                }
            });
            this.bindings.push({ element: closeImportModalBtn, event: 'click', action: 'closeImportModal' });
        }

        // 导入模态框取消按钮
        const cancelImportModalBtn = document.getElementById('cancelImportModalBtn');
        if (cancelImportModalBtn) {
            cancelImportModalBtn.addEventListener('click', () => {
                if (typeof closeImportModal === 'function') {
                    closeImportModal();
                }
            });
            this.bindings.push({ element: cancelImportModalBtn, event: 'click', action: 'closeImportModal' });
        }

        // 版本创建模态框关闭
        const closeCreateVersionModalBtn = document.getElementById('closeCreateVersionModalBtn');
        if (closeCreateVersionModalBtn) {
            closeCreateVersionModalBtn.addEventListener('click', () => {
                if (typeof closeCreateVersionModal === 'function') {
                    closeCreateVersionModal();
                }
            });
            this.bindings.push({ element: closeCreateVersionModalBtn, event: 'click', action: 'closeCreateVersionModal' });
        }

        // 版本创建模态框取消按钮
        const cancelCreateVersionModalBtn = document.getElementById('cancelCreateVersionModalBtn');
        if (cancelCreateVersionModalBtn) {
            cancelCreateVersionModalBtn.addEventListener('click', () => {
                if (typeof closeCreateVersionModal === 'function') {
                    closeCreateVersionModal();
                }
            });
            this.bindings.push({ element: cancelCreateVersionModalBtn, event: 'click', action: 'closeCreateVersionModal' });
        }
    }

    // 绑定场景模态框内部事件
    bindSceneModalInternalEvents() {
        // 添加意图规则按钮
        const addIntentRuleBtn = document.getElementById('addIntentRuleBtn');
        if (addIntentRuleBtn) {
            addIntentRuleBtn.addEventListener('click', () => {
                if (typeof addIntentRule === 'function') {
                    addIntentRule();
                }
            });
            this.bindings.push({ element: addIntentRuleBtn, event: 'click', action: 'addIntentRule' });
        }

        // 添加实体规则按钮
        const addEntityRuleBtn = document.getElementById('addEntityRuleBtn');
        if (addEntityRuleBtn) {
            addEntityRuleBtn.addEventListener('click', () => {
                if (typeof addEntityRule === 'function') {
                    addEntityRule();
                }
            });
            this.bindings.push({ element: addEntityRuleBtn, event: 'click', action: 'addEntityRule' });
        }

        // 添加路由规则按钮
        const addRouteRuleBtn = document.getElementById('addRouteRuleBtn');
        if (addRouteRuleBtn) {
            addRouteRuleBtn.addEventListener('click', () => {
                if (typeof addRouteRule === 'function') {
                    addRouteRule();
                }
            });
            this.bindings.push({ element: addRouteRuleBtn, event: 'click', action: 'addRouteRule' });
        }
    }

    // 获取绑定统计
    getStats() {
        return {
            totalBindings: this.bindings.length,
            bindings: this.bindings.map(b => ({
                element: b.element.id || b.element.className || 'unknown',
                event: b.event,
                action: b.action || b.tabName || 'unknown'
            }))
        };
    }

    // 清理所有事件绑定
    cleanup() {
        this.bindings.forEach(binding => {
            if (binding.element && binding.event) {
                // 创建新元素替换旧元素来移除事件监听器
                const newElement = binding.element.cloneNode(true);
                binding.element.parentNode.replaceChild(newElement, binding.element);
            }
        });
        this.bindings = [];
        this.initialized = false;
        console.log("事件绑定已清理");
    }
}

// 创建全局实例
const eventBinder = new EventBinder();

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        eventBinder.init();
    });
} else {
    eventBinder.init();
}

// 导出供其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { EventBinder, eventBinder };
}