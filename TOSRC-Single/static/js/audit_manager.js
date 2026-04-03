// 审计日志管理模块
let currentAuditLogs = [];

// 加载审计日志
async function loadAuditLogs() {
    try {
        const actionFilter = document.getElementById("actionFilter").value;
        const response = await fetch(`${API_BASE_URL}/audit/logs?action=${actionFilter}&limit=100`);
        const result = await response.json();
        
        if (result.code !== 200 || !result.data) {
            console.error("加载审计日志失败，返回数据为空");
            return;
        }
        
        const logs = result.data;
        currentAuditLogs = logs;
        renderAuditLogs(logs);
    } catch (e) {
        console.error("加载审计日志失败", e);
    }
}

// 渲染审计日志
function renderAuditLogs(logs) {
    const tbody = document.getElementById("auditLogList");
    tbody.innerHTML = "";
    
    if (logs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="px-6 py-4 text-center text-gray-500">
                    暂无操作审计日志
                </td>
            </tr>
        `;
        return;
    }
    
    logs.forEach(log => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-gray-50";
        tr.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-gray-500 text-sm">
                ${log.timestamp || "-"}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <span class="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">
                    ${getActionLabel(log.action)}
                </span>
            </td>
            <td class="px-6 py-4">
                <div class="text-gray-900 text-sm">${log.description || "-"}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-gray-500 text-sm">
                ${log.operator || log.user_id || "system"}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// 获取操作类型中文标签
function getActionLabel(action) {
    const labels = {
        "scene_create": "创建场景",
        "scene_update": "修改场景",
        "scene_delete": "删除场景",
        "batch_import": "批量导入",
        "config_reload": "配置重载",
        "version_create": "创建版本",
        "version_rollback": "版本回滚",
        "gray_create": "创建灰度",
        "gray_status_change": "灰度状态变更",
        "sample_annotate": "样本标注"
    };
    return labels[action] || action;
}

// 页面加载完成后绑定事件
document.addEventListener("DOMContentLoaded", () => {
    // 切换到审计日志标签时加载日志
    document.querySelector('[onclick="switchTab(\'audit\')"]').addEventListener("click", () => {
        loadAuditLogs();
    });
});
