// 全局配置
const API_BASE_URL = "/api/v1";
const CURRENT_ENV = "dev";

// 通用API请求封装
async function fetchAPI(url, options = {}) {
    const defaultOptions = {
        headers: {
            "Content-Type": "application/json"
        },
        credentials: "same-origin"
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    const response = await fetch(`${API_BASE_URL}${url}`, mergedOptions);
    const result = await response.json();
    
    if (result.code !== 200) {
        console.error(`API请求失败：${url}`, result);
        return null;
    }
    
    return result.data;
}

// Tab切换逻辑
function switchTab(tabName) {
    // 切换Tab按钮样式
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.classList.remove("tab-active");
    });
    document.querySelector(`[onclick="switchTab('${tabName}')"]`).classList.add("tab-active");
    
    // 切换内容显示
    document.querySelectorAll(".tab-content").forEach(content => {
        content.classList.add("hidden");
    });
    document.getElementById(`${tabName}Tab`).classList.remove("hidden");
}

// 通用弹窗方法
function showModal(modalId) {
    document.getElementById(modalId).style.display = "block";
}

function hideModal(modalId) {
    document.getElementById(modalId).style.display = "none";
}

// 点击外部关闭弹窗
window.onclick = function(event) {
    const modals = document.querySelectorAll(".modal");
    modals.forEach(modal => {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    });
}

// 通用提示
function showSuccess(message) {
    alert(`✅ ${message}`);
}

function showError(message) {
    alert(`❌ ${message}`);
}

// 格式化时间
function formatTime(timestamp) {
    if (!timestamp) return "";
    const date = new Date(timestamp);
    return date.toLocaleString("zh-CN");
}
