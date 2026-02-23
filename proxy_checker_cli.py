#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理检测工具 - 命令行版本
支持批量检测、统计成功率、平均延迟
"""

import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector
import time
import re
import argparse
import sys
from typing import List, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProxyResult:
    """代理检测结果"""
    proxy: str
    protocol: str
    status: str
    latency: float
    error: str = ""


class ProxyCheckerCLI:
    """代理检测命令行版本"""
    
    def __init__(self, test_url: str = "http://www.google.com", 
                 timeout: int = 10, 
                 concurrency: int = 10,
                 verbose: bool = False):
        self.test_url = test_url
        self.timeout = timeout
        self.concurrency = concurrency
        self.verbose = verbose
        self.results: List[ProxyResult] = []
        
    async def check_proxy(self, proxy: str, protocol: str = "http") -> ProxyResult:
        """检测单个代理"""
        proxy_url = f"{protocol}://{proxy}"
        start_time = time.time()
        
        # 确保测试 URL 有协议前缀
        test_url = self.test_url
        if not test_url.startswith(('http://', 'https://')):
            test_url = f'http://{test_url}'
        
        try:
            timeout_obj = aiohttp.ClientTimeout(total=self.timeout)
            
            # 根据协议类型选择不同的连接方式
            if protocol.lower() == 'socks5':
                # SOCKS5 代理使用 ProxyConnector
                connector = ProxyConnector.from_url(proxy_url)
                async with aiohttp.ClientSession(connector=connector, timeout=timeout_obj) as session:
                    async with session.get(test_url) as response:
                        latency = (time.time() - start_time) * 1000
                        
                        if response.status == 200:
                            return ProxyResult(
                                proxy=proxy,
                                protocol=protocol,
                                status="success",
                                latency=latency
                            )
                        else:
                            return ProxyResult(
                                proxy=proxy,
                                protocol=protocol,
                                status="failed",
                                latency=latency,
                                error=f"HTTP {response.status}"
                            )
            else:
                # HTTP/HTTPS 代理使用标准方式
                connector = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(connector=connector, timeout=timeout_obj) as session:
                    async with session.get(test_url, proxy=proxy_url) as response:
                        latency = (time.time() - start_time) * 1000
                        
                        if response.status == 200:
                            return ProxyResult(
                                proxy=proxy,
                                protocol=protocol,
                                status="success",
                                latency=latency
                            )
                        else:
                            return ProxyResult(
                                proxy=proxy,
                                protocol=protocol,
                                status="failed",
                                latency=latency,
                                error=f"HTTP {response.status}"
                            )
                        
        except asyncio.TimeoutError:
            return ProxyResult(
                proxy=proxy,
                protocol=protocol,
                status="timeout",
                latency=self.timeout * 1000,
                error="连接超时"
            )
        except Exception as e:
            return ProxyResult(
                proxy=proxy,
                protocol=protocol,
                status="failed",
                latency=0,
                error=str(e)
            )
    
    async def check_proxies_batch(self, proxies: List[Tuple[str, str]]) -> List[ProxyResult]:
        """批量检测代理"""
        self.results = []
        total = len(proxies)
        
        print(f"\n开始检测 {total} 个代理...")
        print(f"测试 URL: {self.test_url}")
        print(f"超时: {self.timeout}s | 并发: {self.concurrency}")
        print("-" * 80)
        
        semaphore = asyncio.Semaphore(self.concurrency)
        
        async def check_with_semaphore(idx, proxy, protocol):
            async with semaphore:
                result = await self.check_proxy(proxy, protocol)
                self.results.append(result)
                
                # 实时输出
                current = len(self.results)
                status_symbol = "✓" if result.status == "success" else "✗"
                
                if self.verbose or result.status == "success":
                    print(f"[{current}/{total}] {status_symbol} {protocol}://{proxy} - "
                          f"{result.latency:.2f}ms" if result.status == "success" 
                          else f"{result.error}")
                elif current % 10 == 0:
                    print(f"[{current}/{total}] 进度: {current/total*100:.1f}%")
                
                return result
        
        tasks = [check_with_semaphore(i, proxy, protocol) 
                 for i, (proxy, protocol) in enumerate(proxies)]
        await asyncio.gather(*tasks)
        
        return self.results
    
    def get_statistics(self):
        """获取统计信息"""
        if not self.results:
            return None
        
        total = len(self.results)
        success = [r for r in self.results if r.status == "success"]
        success_count = len(success)
        
        avg_latency = sum(r.latency for r in success) / success_count if success_count > 0 else 0
        min_latency = min((r.latency for r in success), default=0)
        max_latency = max((r.latency for r in success), default=0)
        
        return {
            "total": total,
            "success": success_count,
            "failed": total - success_count,
            "success_rate": (success_count / total * 100) if total > 0 else 0,
            "avg_latency": avg_latency,
            "min_latency": min_latency,
            "max_latency": max_latency
        }
    
    def print_statistics(self):
        """打印统计信息"""
        stats = self.get_statistics()
        if not stats:
            return
        
        print("\n" + "=" * 80)
        print("统计信息")
        print("=" * 80)
        print(f"总计:     {stats['total']}")
        print(f"成功:     {stats['success']} ({stats['success_rate']:.2f}%)")
        print(f"失败:     {stats['failed']}")
        print(f"平均延迟: {stats['avg_latency']:.2f}ms")
        print(f"最快延迟: {stats['min_latency']:.2f}ms")
        print(f"最慢延迟: {stats['max_latency']:.2f}ms")
        print("=" * 80)
    
    def export_results(self, output_file: str, format: str = "txt"):
        """导出结果"""
        if not self.results:
            print("没有可导出的结果")
            return
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                if format == "txt":
                    self._export_txt(f)
                elif format == "csv":
                    self._export_csv(f)
                elif format == "json":
                    self._export_json(f)
            
            print(f"\n结果已导出到: {output_file}")
        except Exception as e:
            print(f"导出失败: {e}")
    
    def _export_txt(self, f):
        """导出为文本格式"""
        stats = self.get_statistics()
        
        f.write("=" * 80 + "\n")
        f.write(f"代理检测报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        if stats:
            f.write("【统计信息】\n")
            f.write(f"总计: {stats['total']}\n")
            f.write(f"成功: {stats['success']} ({stats['success_rate']:.2f}%)\n")
            f.write(f"失败: {stats['failed']}\n")
            f.write(f"平均延迟: {stats['avg_latency']:.2f}ms\n")
            f.write(f"最快延迟: {stats['min_latency']:.2f}ms\n")
            f.write(f"最慢延迟: {stats['max_latency']:.2f}ms\n\n")
        
        # 成功的代理
        f.write("【可用代理】\n")
        success_proxies = [r for r in self.results if r.status == "success"]
        success_proxies.sort(key=lambda x: x.latency)
        
        for r in success_proxies:
            f.write(f"{r.protocol}://{r.proxy} - {r.latency:.2f}ms\n")
        
        # 失败的代理
        f.write("\n【失败代理】\n")
        failed_proxies = [r for r in self.results if r.status != "success"]
        
        for r in failed_proxies:
            f.write(f"{r.protocol}://{r.proxy} - {r.error}\n")
    
    def _export_csv(self, f):
        """导出为 CSV 格式"""
        f.write("代理,协议,状态,延迟(ms),错误信息\n")
        for r in self.results:
            f.write(f"{r.proxy},{r.protocol},{r.status},{r.latency:.2f},{r.error}\n")
    
    def _export_json(self, f):
        """导出为 JSON 格式"""
        import json
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "statistics": self.get_statistics(),
            "results": [
                {
                    "proxy": r.proxy,
                    "protocol": r.protocol,
                    "status": r.status,
                    "latency": r.latency,
                    "error": r.error
                }
                for r in self.results
            ]
        }
        
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_proxies(text: str) -> List[Tuple[str, str]]:
    """解析代理列表"""
    proxies = []
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # 匹配 protocol://username:password@ip:port 格式
        match = re.match(r'(http|https|socks5)://([^@]+@)?(.+)', line)
        if match:
            protocol = match.group(1)
            auth = match.group(2) or ""  # username:password@ 或空
            proxy = match.group(3)       # ip:port
            proxies.append((auth + proxy, protocol))
        # 匹配 username:password@ip:port 格式 (默认 http)
        elif re.match(r'[^@]+@[\d.]+:\d+', line):
            proxies.append((line, "http"))
        # 匹配 ip:port 格式 (默认 http)
        elif re.match(r'[\d.]+:\d+', line):
            proxies.append((line, "http"))
    
    return proxies


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="代理检测工具 - 批量检测代理可用性和延迟",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从文件检测
  python proxy_checker_cli.py -i proxies.txt
  
  # 指定并发和超时
  python proxy_checker_cli.py -i proxies.txt -c 20 -t 15
  
  # 导出结果为 CSV
  python proxy_checker_cli.py -i proxies.txt -o result.csv --format csv
  
  # 详细输出
  python proxy_checker_cli.py -i proxies.txt -v
        """
    )
    
    parser.add_argument("-i", "--input", required=True, help="代理列表文件")
    parser.add_argument("-o", "--output", help="输出文件 (可选)")
    parser.add_argument("--format", choices=["txt", "csv", "json"], 
                       default="txt", help="输出格式 (默认: txt)")
    parser.add_argument("-u", "--url", default="http://www.google.com", 
                       help="测试 URL (默认: http://www.google.com)")
    parser.add_argument("-t", "--timeout", type=int, default=10, 
                       help="超时时间/秒 (默认: 10)")
    parser.add_argument("-c", "--concurrency", type=int, default=10, 
                       help="并发数 (默认: 10)")
    parser.add_argument("-v", "--verbose", action="store_true", 
                       help="详细输出")
    
    args = parser.parse_args()
    
    # 读取代理列表
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"错误: 无法读取文件 {args.input}: {e}")
        sys.exit(1)
    
    proxies = parse_proxies(content)
    
    if not proxies:
        print(f"错误: 未找到有效的代理地址")
        sys.exit(1)
    
    # 创建检测器
    checker = ProxyCheckerCLI(
        test_url=args.url,
        timeout=args.timeout,
        concurrency=args.concurrency,
        verbose=args.verbose
    )
    
    # 运行检测
    try:
        asyncio.run(checker.check_proxies_batch(proxies))
    except KeyboardInterrupt:
        print("\n\n检测被中断")
        sys.exit(1)
    
    # 显示统计
    checker.print_statistics()
    
    # 导出结果
    if args.output:
        checker.export_results(args.output, args.format)
    
    # 成功的代理列表
    success_proxies = [r for r in checker.results if r.status == "success"]
    if success_proxies:
        print("\n可用代理列表:")
        success_proxies.sort(key=lambda x: x.latency)
        for r in success_proxies[:10]:  # 只显示前 10 个最快的
            print(f"  {r.protocol}://{r.proxy} - {r.latency:.2f}ms")
        
        if len(success_proxies) > 10:
            print(f"  ... 还有 {len(success_proxies) - 10} 个可用代理")


if __name__ == "__main__":
    main()
