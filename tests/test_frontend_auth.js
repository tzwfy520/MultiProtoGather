// 前端认证和添加服务器测试脚本
// 在浏览器控制台中运行此脚本来测试认证和API调用

console.log('=== 前端认证和API测试 ===');

// 1. 检查localStorage中的认证信息
console.log('1. 检查认证信息:');
const accessToken = localStorage.getItem('access_token');
const refreshToken = localStorage.getItem('refresh_token');
const userInfo = localStorage.getItem('user_info');

console.log('Access Token:', accessToken ? '存在' : '不存在');
console.log('Refresh Token:', refreshToken ? '存在' : '不存在');
console.log('User Info:', userInfo ? JSON.parse(userInfo) : '不存在');

if (!accessToken) {
    console.error('❌ 未找到访问令牌，请先登录');
} else {
    console.log('✅ 访问令牌存在');
}

// 2. 测试API调用
console.log('\n2. 测试API调用:');

// 创建测试用的服务器数据
const testServerData = {
    name: '前端测试服务器-' + Math.floor(Math.random() * 10000),
    ip_address: '192.168.1.' + Math.floor(Math.random() * 255),
    port: 22,
    username: 'root',
    os_type: 'linux',
    description: '前端测试创建的服务器'
};

console.log('测试数据:', testServerData);

// 使用fetch测试API调用
fetch('http://localhost:8000/api/v1/resources/servers/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
    },
    body: JSON.stringify(testServerData)
})
.then(response => {
    console.log('响应状态:', response.status);
    console.log('响应头:', response.headers);
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
})
.then(data => {
    console.log('✅ API调用成功!');
    console.log('返回数据:', data);
})
.catch(error => {
    console.error('❌ API调用失败:', error);
    
    // 如果是401错误，可能是token过期
    if (error.message.includes('401')) {
        console.log('可能是token过期，尝试刷新token...');
        
        fetch('http://localhost:8000/api/v1/users/token/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                refresh: refreshToken
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.access) {
                localStorage.setItem('access_token', data.access);
                console.log('✅ Token刷新成功');
            } else {
                console.error('❌ Token刷新失败');
            }
        })
        .catch(refreshError => {
            console.error('❌ Token刷新失败:', refreshError);
        });
    }
});

// 3. 检查表单元素
console.log('\n3. 检查表单元素:');
setTimeout(() => {
    const addButton = document.querySelector('[data-testid="add-server-button"]') || 
                     document.querySelector('button:contains("添加服务器")') ||
                     document.querySelector('.ant-btn:contains("添加")');
    
    if (addButton) {
        console.log('✅ 找到添加按钮:', addButton);
        console.log('按钮事件监听器:', getEventListeners ? getEventListeners(addButton) : '无法检查事件监听器');
    } else {
        console.log('❌ 未找到添加按钮');
    }
    
    const modal = document.querySelector('.ant-modal');
    if (modal) {
        console.log('✅ 找到模态框:', modal);
    } else {
        console.log('❌ 未找到模态框');
    }
}, 1000);

console.log('\n=== 测试完成 ===');
console.log('请查看上述输出结果，并尝试手动点击添加服务器按钮');