// 测试错误弹框功能的脚本
// 在浏览器控制台中运行此脚本来测试错误处理

// 模拟API错误响应
const mockApiError = {
  response: {
    status: 400,
    data: {
      name: ['该字段不能为空。'],
      ip_address: ['请输入一个有效的IPv4或IPv6地址。'],
      username: ['该字段不能为空。'],
      non_field_errors: ['必须提供密码或私钥之一']
    }
  }
};

// 测试parseApiError函数
function testParseApiError() {
  console.log('=== 测试错误解析功能 ===');
  
  // 模拟getFieldDisplayName函数
  const getFieldDisplayName = (field) => {
    const fieldNames = {
      name: '服务器名称',
      ip_address: 'IP地址',
      ssh_port: 'SSH端口',
      username: '用户名',
      password: '密码',
      private_key: '私钥',
      os_type: '操作系统'
    };
    return fieldNames[field] || field;
  };

  // 模拟parseApiError函数
  const parseApiError = (error) => {
    if (!error.response?.data) {
      return '网络错误，请检查连接';
    }

    const errorData = error.response.data;
    const errorMessages = [];

    // 处理字段级错误
    Object.keys(errorData).forEach(field => {
      if (field === 'non_field_errors') {
        // 处理全局错误
        if (Array.isArray(errorData[field])) {
          errorMessages.push(...errorData[field]);
        }
      } else {
        // 处理字段错误
        const fieldErrors = errorData[field];
        if (Array.isArray(fieldErrors)) {
          const fieldName = getFieldDisplayName(field);
          fieldErrors.forEach(errorMsg => {
            errorMessages.push(`${fieldName}: ${errorMsg}`);
          });
        }
      }
    });

    return errorMessages.length > 0 ? errorMessages.join('\n') : '操作失败，请重试';
  };

  const result = parseApiError(mockApiError);
  console.log('解析结果:', result);
  
  return result;
}

// 测试Modal.error显示
function testModalError() {
  console.log('=== 测试Modal错误显示 ===');
  
  const errorMessage = testParseApiError();
  
  // 检查antd Modal是否可用
  if (typeof window !== 'undefined' && window.antd && window.antd.Modal) {
    window.antd.Modal.error({
      title: '添加服务器失败',
      content: React.createElement('div', {
        style: { whiteSpace: 'pre-line', maxHeight: '300px', overflow: 'auto' }
      }, errorMessage),
      width: 500,
    });
    console.log('Modal.error 已调用');
  } else {
    console.log('antd Modal 不可用，使用alert替代');
    alert('添加服务器失败:\n' + errorMessage);
  }
}

// 运行测试
console.log('开始测试错误弹框功能...');
testModalError();