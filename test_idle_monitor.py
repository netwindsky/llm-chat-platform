#!/usr/bin/env python3
"""
测试空闲监控功能

测试场景：
1. 加载模型
2. 等待空闲超时（默认60秒）
3. 验证模型是否自动卸载

可以通过修改配置文件或 API 来调整超时时间
"""

import asyncio
import time
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.services.idle_monitor import IdleMonitorManager, LlamaServerMonitor


async def test_idle_monitor():
    """测试空闲监控功能"""
    print("=" * 80)
    print("空闲监控功能测试")
    print("=" * 80)
    
    # 创建监控管理器
    monitor_manager = IdleMonitorManager()
    
    # 模拟卸载回调
    async def mock_unload_callback(port, model_id):
        print(f"\n🗑️  [回调] 卸载模型: {model_id} (端口: {port})")
        print(f"   时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    monitor_manager._backend_manager = type('obj', (object,), {
        'unload_model': mock_unload_callback
    })()
    
    # 测试1: 注册端口监控
    print("\n【测试1】注册端口监控")
    print("-" * 80)
    
    port = 38521
    timeout = 30  # 30秒超时（便于测试）
    
    monitor = monitor_manager.register_server(
        port=port,
        idle_timeout=timeout,
        enabled=True
    )
    
    monitor.set_model(f"test-model-{port}")
    print(f"✅ 已注册端口 {port} 的监控")
    print(f"   模型: test-model-{port}")
    print(f"   超时: {timeout}秒")
    
    # 测试2: 启动监控
    print("\n【测试2】启动监控")
    print("-" * 80)
    
    await monitor.start_monitoring()
    print(f"✅ 监控已启动")
    
    # 测试3: 模拟请求，更新最后请求时间
    print("\n【测试3】模拟请求")
    print("-" * 80)
    
    for i in range(3):
        print(f"\n请求 #{i+1}")
        monitor_manager.update_request_time(port)
        status = monitor.get_status()
        print(f"   最后请求时间: {time.strftime('%H:%M:%S', time.localtime(status['last_request_time']))}")
        print(f"   空闲时间: {status['idle_time']:.1f}秒")
        print(f"   是否空闲: {status['is_idle']}")
        
        if i < 2:  # 最后一次不等待
            wait_time = 10
            print(f"   等待 {wait_time} 秒...")
            await asyncio.sleep(wait_time)
    
    # 测试4: 等待空闲超时
    print("\n【测试4】等待空闲超时")
    print("-" * 80)
    print(f"等待模型空闲 {timeout} 秒后自动卸载...")
    print(f"开始时间: {time.strftime('%H:%M:%S')}")
    print(f"预计卸载时间: {time.strftime('%H:%M:%S', time.localtime(time.time() + timeout))}")
    
    # 等待超时 + 检查间隔
    await asyncio.sleep(timeout + 5)
    
    # 测试5: 检查状态
    print("\n【测试5】检查监控状态")
    print("-" * 80)
    
    all_status = monitor_manager.get_all_status()
    for p, status in all_status.items():
        print(f"\n端口 {p}:")
        print(f"   监控启用: {status['enabled']}")
        print(f"   超时时间: {status['idle_timeout']}秒")
        print(f"   模型ID: {status['model_id']}")
        print(f"   空闲时间: {status['idle_time']:.1f}秒")
        print(f"   是否空闲: {status['is_idle']}")
        print(f"   监控中: {status['monitoring']}")
    
    # 测试6: 停止监控
    print("\n【测试6】停止监控")
    print("-" * 80)
    
    await monitor_manager.shutdown_all()
    print("✅ 所有监控已停止")
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


async def test_api_endpoints():
    """测试 API 端点（需要服务器运行）"""
    print("\n" + "=" * 80)
    print("API 端点测试（需要服务器运行）")
    print("=" * 80)
    
    import httpx
    
    base_url = "http://localhost:8080/api/v1/models"
    
    async with httpx.AsyncClient() as client:
        # 1. 获取所有监控状态
        print("\n【API测试1】获取所有监控状态")
        try:
            response = await client.get(f"{base_url}/idle-monitor/status")
            print(f"状态: {response.status_code}")
            print(f"响应: {response.json()}")
        except Exception as e:
            print(f"❌ 错误: {e}")
        
        # 2. 获取指定端口状态
        print("\n【API测试2】获取端口 38521 状态")
        try:
            response = await client.get(f"{base_url}/idle-monitor/38521/status")
            print(f"状态: {response.status_code}")
            print(f"响应: {response.json()}")
        except Exception as e:
            print(f"❌ 错误: {e}")
        
        # 3. 更新配置
        print("\n【API测试3】更新端口 38521 配置")
        try:
            response = await client.post(
                f"{base_url}/idle-monitor/38521/config",
                json={"enabled": True, "timeout": 120}
            )
            print(f"状态: {response.status_code}")
            print(f"响应: {response.json()}")
        except Exception as e:
            print(f"❌ 错误: {e}")
        
        # 4. 重置计时器
        print("\n【API测试4】重置端口 38521 计时器")
        try:
            response = await client.post(f"{base_url}/idle-monitor/38521/reset")
            print(f"状态: {response.status_code}")
            print(f"响应: {response.json()}")
        except Exception as e:
            print(f"❌ 错误: {e}")


def print_usage():
    """打印使用说明"""
    print("""
使用方法:
  python test_idle_monitor.py [选项]

选项:
  unit      - 运行单元测试（不需要服务器）
  api       - 运行 API 测试（需要服务器运行）
  all       - 运行所有测试
  
示例:
  python test_idle_monitor.py unit    # 仅运行单元测试
  python test_idle_monitor.py api     # 仅运行 API 测试
  python test_idle_monitor.py all     # 运行所有测试

配置文件:
  configs/server.yaml 中的 idle_monitor 部分
  
  # 启用空闲监控（默认）
  idle_monitor:
    enabled: true
    timeout: 60        # 60秒超时
    
  # 禁用空闲监控
  idle_monitor:
    enabled: false
    
  # 按模型配置（在 models.yaml 中）
  - id: qwen3.5-9b-ud-q4
    idle_monitor_enabled: true    # 启用监控
    idle_timeout: 120             # 2分钟超时
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    option = sys.argv[1].lower()
    
    if option == "unit":
        asyncio.run(test_idle_monitor())
    elif option == "api":
        asyncio.run(test_api_endpoints())
    elif option == "all":
        asyncio.run(test_idle_monitor())
        asyncio.run(test_api_endpoints())
    else:
        print(f"未知选项: {option}")
        print_usage()
        sys.exit(1)
