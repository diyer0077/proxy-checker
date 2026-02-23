#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 代理检测工具
支持批量检测、统计成功率、平均延迟
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import requests
import time
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class ProxyResult:
    """代理检测结果"""
    proxy: str
    protocol: str  # http/https/socks5
    status: str  # success/failed/timeout
    latency: float  # 延迟(ms)
    error: str = ""


class ProxyChecker:
    """代理检测核心类"""
    
    def __init__(self, test_url: str = "http://www.google.com", timeout: int = 10):
        self.test_url = test_url
        self.timeout = timeout
        self.results: List[ProxyResult] = []
        
    def check_proxy(self, proxy: str, protocol: str = "http") -> ProxyResult:
        """检测单个代理（统一使用 requests）"""
        proxy_url = f"{protocol}://{proxy}"
        start_time = time.time()
        
        # 确保测试 URL 有协议前缀
        test_url = self.test_url
        if not test_url.startswith(('http://', 'https://')):
            test_url = f'http://{test_url}'
        
        try:
            # 所有协议统一使用 requests（支持 HTTP/HTTPS/SOCKS5）
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=self.timeout,
                verify=False  # 禁用 SSL 验证
            )
            
            latency = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
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
                    error=f"HTTP {response.status_code}"
                )
                
        except requests.exceptions.Timeout:
            return ProxyResult(
                proxy=proxy,
                protocol=protocol,
                status="timeout",
                latency=self.timeout * 1000,
                error="连接超时"
            )
        except requests.exceptions.ProxyError as e:
            return ProxyResult(
                proxy=proxy,
                protocol=protocol,
                status="failed",
                latency=0,
                error=f"代理错误: {str(e)[:50]}"
            )
        except Exception as e:
            return ProxyResult(
                proxy=proxy,
                protocol=protocol,
                status="failed",
                latency=0,
                error=str(e)[:50]  # 限制错误信息长度
            )
    
    def check_proxies_batch(self, proxies: List[Tuple[str, str]], 
                            concurrency: int = 10,
                            progress_callback=None) -> List[ProxyResult]:
        """批量检测代理（使用线程池）"""
        self.results = []
        total = len(proxies)
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            # 提交所有任务
            future_to_proxy = {
                executor.submit(self.check_proxy, proxy, protocol): (proxy, protocol)
                for proxy, protocol in proxies
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_proxy):
                result = future.result()
                self.results.append(result)
                
                if progress_callback:
                    progress_callback(len(self.results), total)
        
        return self.results
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        if not self.results:
            return {}
        
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


class ProxyCheckerGUI:
    """代理检测 GUI 界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("代理检测工具 v1.3")
        self.root.geometry("900x700")
        
        self.checker = ProxyChecker()
        self.is_checking = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置 UI"""
        # 顶部配置区域
        config_frame = ttk.LabelFrame(self.root, text="配置", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 测试 URL
        ttk.Label(config_frame, text="测试 URL:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.url_var = tk.StringVar(value="http://www.google.com")
        ttk.Entry(config_frame, textvariable=self.url_var, width=40).grid(row=0, column=1, padx=5)
        
        # 超时设置
        ttk.Label(config_frame, text="超时(秒):").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.timeout_var = tk.IntVar(value=10)
        ttk.Spinbox(config_frame, from_=5, to=60, textvariable=self.timeout_var, width=10).grid(row=0, column=3, padx=5)
        
        # 并发数
        ttk.Label(config_frame, text="并发数:").grid(row=0, column=4, sticky=tk.W, padx=5)
        self.concurrency_var = tk.IntVar(value=10)
        ttk.Spinbox(config_frame, from_=1, to=50, textvariable=self.concurrency_var, width=10).grid(row=0, column=5, padx=5)
        
        # 代理输入区域
        input_frame = ttk.LabelFrame(self.root, text="代理列表 (格式: IP:端口 或 协议://IP:端口)", padding=10)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 按钮区
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(btn_frame, text="📁 导入文件", command=self.load_from_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑️ 清空", command=self.clear_input).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📋 粘贴", command=self.paste_from_clipboard).pack(side=tk.LEFT, padx=2)
        
        # 输入框
        self.input_text = scrolledtext.ScrolledText(input_frame, height=10)
        self.input_text.pack(fill=tk.BOTH, expand=True)
        
        # 示例文本
        self.input_text.insert("1.0", "# 示例:\n192.168.1.1:8080\nhttp://192.168.1.2:8080\nsocks5://192.168.1.3:1080\n# 带账号密码:\nuser:pass@192.168.1.4:8080\nhttp://user:pass@192.168.1.5:8080\n")
        
        # 控制按钮
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.start_btn = ttk.Button(control_frame, text="🚀 开始检测", command=self.start_check)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="⏹️ 停止", command=self.stop_check, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="💾 导出结果", command=self.export_results).pack(side=tk.LEFT, padx=5)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(control_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.progress_label = ttk.Label(control_frame, text="就绪")
        self.progress_label.pack(side=tk.LEFT, padx=5)
        
        # 统计信息
        stats_frame = ttk.LabelFrame(self.root, text="统计信息", padding=10)
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.stats_label = ttk.Label(stats_frame, text="等待检测...", font=("", 10))
        self.stats_label.pack()
        
        # 结果显示
        result_frame = ttk.LabelFrame(self.root, text="检测结果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建表格
        columns = ("代理", "协议", "状态", "延迟(ms)", "备注")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.result_tree.heading(col, text=col)
            
        # 设置列宽
        self.result_tree.column("代理", width=200)
        self.result_tree.column("协议", width=80)
        self.result_tree.column("状态", width=80)
        self.result_tree.column("延迟(ms)", width=100)
        self.result_tree.column("备注", width=300)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=scrollbar.set)
        
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def parse_proxies(self, text: str) -> List[Tuple[str, str]]:
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
    
    def load_from_file(self):
        """从文件导入"""
        filename = filedialog.askopenfilename(
            title="选择代理列表文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.input_text.delete("1.0", tk.END)
                self.input_text.insert("1.0", content)
            except Exception as e:
                messagebox.showerror("错误", f"读取文件失败: {e}")
    
    def clear_input(self):
        """清空输入"""
        self.input_text.delete("1.0", tk.END)
    
    def paste_from_clipboard(self):
        """从剪贴板粘贴"""
        try:
            content = self.root.clipboard_get()
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", content)
        except:
            pass
    
    def start_check(self):
        """开始检测"""
        text = self.input_text.get("1.0", tk.END)
        proxies = self.parse_proxies(text)
        
        if not proxies:
            messagebox.showwarning("警告", "请输入至少一个代理!")
            return
        
        # 更新配置
        self.checker.test_url = self.url_var.get()
        self.checker.timeout = self.timeout_var.get()
        
        # 清空结果
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        # 更新 UI 状态
        self.is_checking = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.progress_label.config(text=f"0/{len(proxies)}")
        
        # 在新线程中运行异步任务
        thread = threading.Thread(target=self.run_check, args=(proxies,))
        thread.daemon = True
        thread.start()
    
    def run_check(self, proxies):
        """运行检测(在独立线程中)"""
        try:
            self.checker.check_proxies_batch(
                proxies,
                concurrency=self.concurrency_var.get(),
                progress_callback=self.update_progress
            )
        finally:
            self.root.after(0, self.check_complete)
    
    def update_progress(self, current, total):
        """更新进度"""
        def update():
            progress = (current / total) * 100
            self.progress_var.set(progress)
            self.progress_label.config(text=f"{current}/{total}")
            
            # 更新最新结果
            if self.checker.results:
                result = self.checker.results[-1]
                self.add_result_to_tree(result)
        
        self.root.after(0, update)
    
    def add_result_to_tree(self, result: ProxyResult):
        """添加结果到表格"""
        # 根据状态设置标签(用于着色)
        tag = result.status
        
        values = (
            result.proxy,
            result.protocol,
            "✓ 成功" if result.status == "success" else "✗ 失败" if result.status == "failed" else "⏱ 超时",
            f"{result.latency:.2f}" if result.latency > 0 else "-",
            result.error
        )
        
        self.result_tree.insert("", tk.END, values=values, tags=(tag,))
        
        # 设置颜色
        self.result_tree.tag_configure("success", foreground="green")
        self.result_tree.tag_configure("failed", foreground="red")
        self.result_tree.tag_configure("timeout", foreground="orange")
    
    def check_complete(self):
        """检测完成"""
        self.is_checking = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        # 显示统计信息
        stats = self.checker.get_statistics()
        if stats:
            stats_text = (
                f"总计: {stats['total']} | "
                f"成功: {stats['success']} | "
                f"失败: {stats['failed']} | "
                f"成功率: {stats['success_rate']:.1f}% | "
                f"平均延迟: {stats['avg_latency']:.2f}ms | "
                f"最快: {stats['min_latency']:.2f}ms | "
                f"最慢: {stats['max_latency']:.2f}ms"
            )
            self.stats_label.config(text=stats_text)
        
        messagebox.showinfo("完成", "代理检测完成!")
    
    def stop_check(self):
        """停止检测"""
        self.is_checking = False
        # 注意: 由于异步任务在独立线程中,这里只是更新 UI 状态
        # 实际的异步任务会在当前批次完成后自然结束
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
    
    def export_results(self):
        """导出结果"""
        if not self.checker.results:
            messagebox.showwarning("警告", "没有可导出的结果!")
            return
        
        filename = filedialog.asksaveasfilename(
            title="保存结果",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # 写入统计信息
                stats = self.checker.get_statistics()
                f.write("=" * 80 + "\n")
                f.write(f"代理检测报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                
                if stats:
                    f.write("【统计信息】\n")
                    f.write(f"总计: {stats['total']}\n")
                    f.write(f"成功: {stats['success']}\n")
                    f.write(f"失败: {stats['failed']}\n")
                    f.write(f"成功率: {stats['success_rate']:.2f}%\n")
                    f.write(f"平均延迟: {stats['avg_latency']:.2f}ms\n")
                    f.write(f"最快延迟: {stats['min_latency']:.2f}ms\n")
                    f.write(f"最慢延迟: {stats['max_latency']:.2f}ms\n\n")
                
                # 写入成功的代理
                f.write("【可用代理】\n")
                success_proxies = [r for r in self.checker.results if r.status == "success"]
                success_proxies.sort(key=lambda x: x.latency)  # 按延迟排序
                
                for r in success_proxies:
                    f.write(f"{r.protocol}://{r.proxy} - {r.latency:.2f}ms\n")
                
                # 写入失败的代理
                f.write("\n【失败代理】\n")
                failed_proxies = [r for r in self.checker.results if r.status != "success"]
                
                for r in failed_proxies:
                    f.write(f"{r.protocol}://{r.proxy} - {r.error}\n")
            
            messagebox.showinfo("成功", f"结果已保存到: {filename}")
            
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")


def main():
    """主函数"""
    root = tk.Tk()
    app = ProxyCheckerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
