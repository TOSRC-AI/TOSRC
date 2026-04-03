// 导入导出管理模块
let importType = "json";
let csvFileData = null;

// 打开导入弹窗
function openImportModal() {
    importType = "json";
    document.getElementById("jsonTab").classList.add("bg-blue-600", "text-white");
    document.getElementById("jsonTab").classList.remove("bg-gray-200", "text-gray-700");
    document.getElementById("csvTab").classList.add("bg-gray-200", "text-gray-700");
    document.getElementById("csvTab").classList.remove("bg-blue-600", "text-white");
    document.getElementById("jsonImportSection").classList.remove("hidden");
    document.getElementById("csvImportSection").classList.add("hidden");
    document.getElementById("importActionBtn").classList.add("hidden");
    document.getElementById("importTypeInfo").classList.add("hidden");
    document.getElementById("csvPreview").classList.add("hidden");
    document.getElementById("importJson").value = "";
    showModal("importModal");
}

// 切换导入类型
function switchImportType(type) {
    importType = type;
    
    if (type === "json") {
        document.getElementById("jsonTab").classList.add("bg-blue-600", "text-white");
        document.getElementById("jsonTab").classList.remove("bg-gray-200", "text-gray-700");
        document.getElementById("csvTab").classList.add("bg-gray-200", "text-gray-700");
        document.getElementById("csvTab").classList.remove("bg-blue-600", "text-white");
        document.getElementById("jsonImportSection").classList.remove("hidden");
        document.getElementById("csvImportSection").classList.add("hidden");
        document.getElementById("importActionBtn").classList.add("hidden");
        document.getElementById("importTypeInfo").classList.add("hidden");
    } else {
        document.getElementById("csvTab").classList.add("bg-blue-600", "text-white");
        document.getElementById("csvTab").classList.remove("bg-gray-200", "text-gray-700");
        document.getElementById("jsonTab").classList.add("bg-gray-200", "text-gray-700");
        document.getElementById("jsonTab").classList.remove("bg-blue-600", "text-white");
        document.getElementById("csvImportSection").classList.remove("hidden");
        document.getElementById("jsonImportSection").classList.add("hidden");
        document.getElementById("importActionBtn").classList.add("hidden");
        document.getElementById("importTypeInfo").classList.add("hidden");
    }
}

// 关闭导入弹窗
function closeImportModal() {
    hideModal("importModal");
}

// CSV文件选择
function handleCSVFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        const content = e.target.result;
        parseCSVFile(content, file.name);
    };
    reader.readAsText(file, "UTF-8");
}

// 解析CSV文件
function parseCSVFile(content, fileName) {
    try {
        const lines = content.split("\n").filter(line => line.trim());
        if (lines.length < 2) {
            showError("CSV文件格式错误，至少需要表头和数据行");
            return;
        }
        
        const headers = lines[0].split(",").map(h => h.trim());
        const dataRows = lines.slice(1).map(line => {
            const values = line.split(",").map(v => v.trim());
            const row = {};
            headers.forEach((header, index) => {
                row[header] = values[index] || "";
            });
            return row;
        });
        
        csvFileData = dataRows;
        
        // 显示预览
        document.getElementById("csvFileName").textContent = `文件：${fileName}，共 ${dataRows.length} 条数据`;
        document.getElementById("csvPreview").classList.remove("hidden");
        
        // 渲染表头
        const headerRow = document.getElementById("csvHeaderRow");
        headerRow.innerHTML = "";
        headers.forEach(header => {
            const th = document.createElement("th");
            th.className = "px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border";
            th.textContent = header;
            headerRow.appendChild(th);
        });
        
        // 渲染预览数据（最多5行）
        const previewRows = document.getElementById("csvPreviewRows");
        previewRows.innerHTML = "";
        const previewCount = Math.min(5, dataRows.length);
        for (let i = 0; i < previewCount; i++) {
            const tr = document.createElement("tr");
            headers.forEach(header => {
                const td = document.createElement("td");
                td.className = "px-3 py-2 text-sm border";
                td.textContent = dataRows[i][header] || "";
                tr.appendChild(td);
            });
            previewRows.appendChild(tr);
        }
        
        // 显示导入按钮
        document.getElementById("importActionBtn").classList.remove("hidden");
        document.getElementById("importActionBtn").textContent = "导入场景配置";
        document.getElementById("importTypeInfo").classList.remove("hidden");
        document.getElementById("importTypeText").textContent = `已识别为：场景配置文件，共 ${dataRows.length} 条数据`;
    } catch (e) {
        console.error("解析CSV文件失败", e);
        showError(`解析CSV文件失败：${e.message}`);
    }
}

// 处理导入
async function processImport() {
    if (importType === "json") {
        const jsonData = document.getElementById("importJson").value.trim();
        if (!jsonData) {
            showError("请输入JSON数据");
            return;
        }
        
        try {
            const scenes = JSON.parse(jsonData);
            await importScenes(scenes);
        } catch (e) {
            console.error("解析JSON失败", e);
            showError(`JSON格式错误：${e.message}`);
        }
    } else if (importType === "csv" && csvFileData) {
        await importCSVData(csvFileData);
    } else {
        showError("请先选择CSV文件");
    }
}

// 导入场景数据
async function importScenes(scenes) {
    try {
        const response = await fetch(`${API_BASE_URL}/config/import?env=${CURRENT_ENV}&import_type=json`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ json_data: JSON.stringify(scenes) })
        });
        
        const result = await response.json();
        if (result.code === 200) {
            showSuccess(`导入成功，共导入${result.message.match(/\d+/)?.[0] || 0}个场景`);
            closeImportModal();
            loadScenes();
        } else {
            showError(`导入失败：${result.message}`);
        }
    } catch (e) {
        console.error("导入场景失败", e);
        showError(`导入场景失败：${e.message}`);
    }
}

// 导入CSV数据
async function importCSVData(dataRows) {
    try {
        // 将CSV数据转换为场景配置格式
        const scenes = dataRows.map(row => {
            return {
                scene_id: row.scene_id || row["场景ID"],
                config: {
                    base: {
                        scene_id: row.scene_id || row["场景ID"],
                        scene_name: row.scene_name || row["场景名称"],
                        description: row.description || row["场景描述"],
                        priority: parseInt(row.priority || row["优先级"]) || 1,
                        enabled: (row.enabled || row["是否启用"]) === "true" || (row.enabled || row["是否启用"]) === true
                    },
                    intents: [],
                    entities: [],
                    routes: []
                }
            };
        });
        
        await importScenes(scenes);
    } catch (e) {
        console.error("导入CSV数据失败", e);
        showError(`导入CSV数据失败：${e.message}`);
    }
}

// 导出场景
async function exportScenes() {
    try {
        const response = await fetch(`${API_BASE_URL}/config/export?env=${CURRENT_ENV}`);
        if (!response.ok) {
            throw new Error(`导出失败：${response.statusText}`);
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `scenes_export_${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showSuccess("导出成功");
    } catch (e) {
        console.error("导出场景失败", e);
        showError(`导出场景失败：${e.message}`);
    }
}

// 页面加载完成后绑定事件
document.addEventListener("DOMContentLoaded", () => {
    // 绑定CSV文件选择事件
    const csvFileInput = document.getElementById("csvFileInput");
    if (csvFileInput) {
        csvFileInput.addEventListener("change", handleCSVFileSelect);
    }
});
