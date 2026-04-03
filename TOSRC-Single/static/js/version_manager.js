// 版本管理模块
let currentVersions = [];

// 加载版本列表
async function loadVersions() {
    try {
        const response = await fetch(`${API_BASE_URL}/config/versions?env=${CURRENT_ENV}`);
        const result = await response.json();
        
        if (result.code !== 200 || !result.data) {
            console.error("加载版本列表失败，返回数据为空");
            return;
        }
        
        const versions = result.data;
        currentVersions = versions;
        renderVersionList(versions);
    } catch (e) {
        console.error("加载版本列表失败", e);
    }
}

// 渲染版本列表
function renderVersionList(versions) {
    const tbody = document.getElementById("versionList");
    tbody.innerHTML = "";
    
    if (versions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-6 py-4 text-center text-gray-500">
                    暂无版本记录，请点击上方创建新版本按钮创建
                </td>
            </tr>
        `;
        return;
    }
    
    versions.forEach(version => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-gray-50";
        tr.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="font-medium text-gray-900">${version.version_id}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-gray-900">${version.version_name}</div>
            </td>
            <td class="px-6 py-4">
                <div class="text-gray-900 text-sm">${version.description || "-"}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                ${version.created_at || "-"}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <span class="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">
                    ${version.env || CURRENT_ENV}
                </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button onclick="rollbackVersion('${version.version_id}')" class="text-orange-600 hover:text-orange-900">
                    <i class="fas fa-undo mr-1"></i>回滚
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// 打开创建版本弹窗
function openCreateVersionModal() {
    document.getElementById("createVersionForm").reset();
    showModal("createVersionModal");
}

// 创建新版本
async function createVersion(event) {
    event.preventDefault();
    
    const versionName = document.getElementById("versionName").value.trim();
    const description = document.getElementById("versionDescription").value.trim();
    
    if (!versionName) {
        showError("版本名称不能为空");
        return;
    }
    
    try {
        await fetchAPI(`/config/version?env=${CURRENT_ENV}`, {
            method: "POST",
            body: JSON.stringify({
                version_name: versionName,
                description: description
            })
        });
        
        hideModal("createVersionModal");
        showSuccess("版本创建成功");
        loadVersions();
    } catch (e) {
        console.error("创建版本失败", e);
        showError(`创建版本失败：${e.message}`);
    }
}

// 回滚版本
async function rollbackVersion(versionId) {
    if (!confirm(`确定要回滚到版本【${versionId}】吗？当前配置将被覆盖！`)) {
        return;
    }
    
    try {
        await fetchAPI(`/config/rollback/${versionId}?env=${CURRENT_ENV}`, {
            method: "POST"
        });
        
        showSuccess("回滚成功");
        loadVersions();
        // 回滚后重新加载场景列表
        loadScenes();
    } catch (e) {
        console.error("回滚版本失败", e);
        showError(`回滚版本失败：${e.message}`);
    }
}

// 页面加载完成后绑定事件
document.addEventListener("DOMContentLoaded", () => {
    // 绑定表单提交事件
    const versionForm = document.getElementById("versionForm");
    if (versionForm) {
        versionForm.addEventListener("submit", createVersion);
    }
    
    // 切换到版本管理标签时加载版本列表
    document.querySelector('[onclick="switchTab(\'version\')"]').addEventListener("click", () => {
        loadVersions();
    });
});
