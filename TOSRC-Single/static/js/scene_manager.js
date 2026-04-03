// 场景管理模块
let currentScenes = [];
let editSceneId = null;

// 加载场景列表
async function loadScenes() {
    try {
        const response = await fetch(`${API_BASE_URL}/config/scenes?env=${CURRENT_ENV}`);
        const result = await response.json();
        
        if (result.code !== 200 || !result.data) {
            showError("加载场景列表失败，返回数据为空");
            return;
        }
        
        const scenes = result.data;
        currentScenes = scenes;
        renderSceneList(scenes);
    } catch (e) {
        console.error("加载场景列表失败", e);
        showError(`加载场景列表失败：${e.message}`);
    }
}

// 渲染场景列表
function renderSceneList(scenes) {
    const tbody = document.getElementById("sceneList");
    const sceneCountEl = document.getElementById("sceneCount");
    
    sceneCountEl.textContent = scenes.length;
    tbody.innerHTML = "";
    
    if (scenes.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-6 py-4 text-center text-gray-500">
                    暂无场景配置，请点击上方新增场景按钮创建
                </td>
            </tr>
        `;
        return;
    }
    
    scenes.forEach(scene => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-gray-50";
        tr.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="font-medium text-gray-900">${scene.scene_id || scene["场景ID"]}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-gray-900">${scene.scene_name || scene["场景名称"]}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-gray-900">${scene.priority || scene["优先级"] || 1}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <span class="px-2 py-1 text-xs rounded-full ${(scene.enabled || scene["是否启用"]) ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}">
                    ${(scene.enabled || scene["是否启用"]) ? "启用" : "禁用"}
                </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                ${scene.updated_at || "-"}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button onclick="editScene('${scene.scene_id || scene["场景ID"]}')" class="text-blue-600 hover:text-blue-900 mr-3">
                    <i class="fas fa-edit mr-1"></i>编辑
                </button>
                <button onclick="deleteScene('${scene.scene_id || scene["场景ID"]}')" class="text-red-600 hover:text-red-900">
                    <i class="fas fa-trash mr-1"></i>删除
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// 搜索场景
function searchScenes() {
    const keyword = document.getElementById("searchInput").value.trim().toLowerCase();
    if (!keyword) {
        renderSceneList(currentScenes);
        return;
    }
    
    const filteredScenes = currentScenes.filter(scene => {
        const sceneId = (scene.scene_id || scene["场景ID"] || "").toLowerCase();
        const sceneName = (scene.scene_name || scene["场景名称"] || "").toLowerCase();
        return sceneId.includes(keyword) || sceneName.includes(keyword);
    });
    
    renderSceneList(filteredScenes);
}

// 新增场景
function openAddSceneModal() {
    editSceneId = null;
    document.getElementById("sceneModalTitle").textContent = "新增场景";
    document.getElementById("sceneForm").reset();
    document.getElementById("editSceneId").value = "";
    showModal("sceneModal");
}

// 编辑场景
async function editScene(sceneId) {
    try {
        const sceneConfig = await fetchAPI(`/config/scene/${sceneId}?env=${CURRENT_ENV}`);
        if (!sceneConfig) {
            showError("加载场景配置失败");
            return;
        }
        
        editSceneId = sceneId;
        document.getElementById("sceneModalTitle").textContent = "编辑场景";
        document.getElementById("editSceneId").value = sceneId;
        document.getElementById("sceneId").value = sceneId;
        document.getElementById("sceneName").value = sceneConfig.base?.scene_name || sceneConfig.base?.["场景名称"] || "";
        document.getElementById("scenePriority").value = sceneConfig.base?.priority || sceneConfig.base?.["优先级"] || 1;
        document.getElementById("sceneEnable").value = (sceneConfig.base?.enabled || sceneConfig.base?.["是否启用"]) ? "true" : "false";
        document.getElementById("sceneDesc").value = sceneConfig.base?.description || sceneConfig.base?.["场景描述"] || "";
        
        showModal("sceneModal");
    } catch (e) {
        console.error("加载场景配置失败", e);
        showError(`加载场景配置失败：${e.message}`);
    }
}

// 删除场景
async function deleteScene(sceneId) {
    if (!confirm(`确定要删除场景【${sceneId}】吗？删除后无法恢复！`)) {
        return;
    }
    
    try {
        await fetchAPI(`/config/scene/${sceneId}?env=${CURRENT_ENV}`, {
            method: "DELETE"
        });
        
        showSuccess("删除成功");
        loadScenes();
    } catch (e) {
        console.error("删除场景失败", e);
        showError(`删除场景失败：${e.message}`);
    }
}

// 保存场景
async function saveScene(event) {
    event.preventDefault();
    
    const sceneId = document.getElementById("sceneId").value.trim();
    if (!sceneId) {
        showError("场景ID不能为空");
        return;
    }
    
    const sceneData = {
        base: {
            scene_id: sceneId,
            scene_name: document.getElementById("sceneName").value.trim(),
            priority: parseInt(document.getElementById("scenePriority").value) || 1,
            enabled: document.getElementById("sceneEnable").value === "true",
            description: document.getElementById("sceneDesc").value.trim()
        },
        intents: [],
        entities: [],
        routes: []
    };
    
    try {
        await fetchAPI(`/config/scene/${sceneId}?env=${CURRENT_ENV}`, {
            method: "POST",
            body: JSON.stringify(sceneData)
        });
        
        hideModal("sceneModal");
        showSuccess("保存成功");
        loadScenes();
    } catch (e) {
        console.error("保存场景失败", e);
        showError(`保存场景失败：${e.message}`);
    }
}

// 重载配置
async function reloadConfig() {
    if (!confirm("确定要重载所有场景配置吗？重载后新配置将即时生效！")) {
        return;
    }
    
    try {
        await fetchAPI("/config/reload", {
            method: "POST"
        });
        
        showSuccess("配置重载成功");
        loadScenes();
    } catch (e) {
        console.error("重载配置失败", e);
        showError(`重载配置失败：${e.message}`);
    }
}

// 页面加载完成后自动加载场景列表
document.addEventListener("DOMContentLoaded", () => {
    loadScenes();
    
    // 绑定表单提交事件
    document.getElementById("sceneForm").addEventListener("submit", saveScene);
});
