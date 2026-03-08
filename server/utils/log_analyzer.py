"""
日志分析工具
用于分析系统日志，诊断问题
"""

import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any


class LogAnalyzer:
    """日志分析器"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)

    def analyze_recent_errors(self, hours: int = 24) -> Dict[str, Any]:
        """分析最近的错误"""
        error_log = self.log_dir / "error.log"
        if not error_log.exists():
            return {"error": "No error log found"}

        errors = []
        error_counts = defaultdict(int)
        model_errors = defaultdict(int)

        try:
            with open(error_log, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        if "ERROR |" in line:
                            data = json.loads(line.split("ERROR |")[1])
                            error_time = datetime.fromisoformat(data.get("timestamp", ""))

                            # 检查时间范围
                            if datetime.now() - error_time < timedelta(hours=hours):
                                errors.append(data)

                                # 统计错误类型
                                error_type = data.get("error_type", "Unknown")
                                error_counts[error_type] += 1

                                # 统计模型相关错误
                                context = data.get("context", {})
                                model_id = context.get("model_id", "unknown")
                                if model_id != "unknown":
                                    model_errors[model_id] += 1
                    except:
                        continue

        except Exception as e:
            return {"error": str(e)}

        return {
            "total_errors": len(errors),
            "error_types": dict(error_counts),
            "model_errors": dict(model_errors),
            "recent_errors": errors[-5:] if errors else []
        }

    def analyze_performance(self, operation: str = None, hours: int = 24) -> Dict[str, Any]:
        """分析性能指标"""
        perf_log = self.log_dir / "performance.log"
        if not perf_log.exists():
            return {"error": "No performance log found"}

        operations = defaultdict(lambda: {"durations": [], "errors": 0})

        try:
            with open(perf_log, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        if "PERF |" in line:
                            data = json.loads(line.split("PERF |")[1])
                            op = data.get("operation")
                            duration = data.get("duration_ms")
                            status = data.get("status", "success")

                            if op and duration:
                                operations[op]["durations"].append(duration)
                                if status == "error":
                                    operations[op]["errors"] += 1
                    except:
                        continue

        except Exception as e:
            return {"error": str(e)}

        # 计算统计信息
        summary = {}
        for op, data in operations.items():
            durations = data["durations"]
            if durations:
                summary[op] = {
                    "count": len(durations),
                    "avg_ms": round(sum(durations) / len(durations), 2),
                    "min_ms": round(min(durations), 2),
                    "max_ms": round(max(durations), 2),
                    "median_ms": round(sorted(durations)[len(durations)//2], 2),
                    "errors": data["errors"]
                }

        if operation:
            return summary.get(operation, {"error": f"No data for operation: {operation}"})

        return summary

    def analyze_llama_server_events(self, hours: int = 24) -> Dict[str, Any]:
        """分析 llama-server 事件"""
        system_log = self.log_dir / "system.log"
        if not system_log.exists():
            return {"error": "No system log found"}

        events = defaultdict(int)
        crashes = []
        restarts = []

        try:
            with open(system_log, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        if "LLAMA_SERVER |" in line:
                            data = json.loads(line.split("LLAMA_SERVER |")[1])
                            event_type = data.get("event", "unknown")
                            events[event_type] += 1

                            if event_type == "process_crashed":
                                crashes.append(data)
                            elif event_type == "process_started":
                                restarts.append(data)
                    except:
                        continue

        except Exception as e:
            return {"error": str(e)}

        return {
            "event_summary": dict(events),
            "crash_count": len(crashes),
            "restart_count": len(restarts),
            "recent_crashes": crashes[-5:] if crashes else [],
            "recent_restarts": restarts[-5:] if restarts else []
        }

    def analyze_model_loading(self) -> Dict[str, Any]:
        """分析模型加载情况"""
        app_log = self.log_dir / "app.log"
        if not app_log.exists():
            return {"error": "No app log found"}

        model_events = defaultdict(lambda: {"load_count": 0, "error_count": 0, "last_status": None})

        try:
            with open(app_log, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        if "MODEL |" in line:
                            data = json.loads(line.split("MODEL |")[1])
                            model_id = data.get("model_id", "unknown")
                            event = data.get("event", "unknown")

                            if event == "loaded":
                                model_events[model_id]["load_count"] += 1
                                model_events[model_id]["last_status"] = "loaded"
                            elif event == "initialize_start":
                                model_events[model_id]["last_status"] = "loading"

                        if "ERROR |" in line:
                            data = json.loads(line.split("ERROR |")[1])
                            context = data.get("context", {})
                            model_id = context.get("model_id", "unknown")
                            if model_id != "unknown":
                                model_events[model_id]["error_count"] += 1
                    except:
                        continue

        except Exception as e:
            return {"error": str(e)}

        return dict(model_events)

    def generate_report(self, hours: int = 24) -> str:
        """生成综合分析报告"""
        report = []
        report.append("=" * 80)
        report.append(f"系统日志分析报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"分析时间范围: 最近 {hours} 小时")
        report.append("=" * 80)

        # 1. 错误分析
        report.append("\n【错误分析】")
        errors = self.analyze_recent_errors(hours)
        if "error" in errors:
            report.append(f"  无法分析错误: {errors['error']}")
        else:
            report.append(f"  总错误数: {errors['total_errors']}")
            report.append(f"  错误类型分布:")
            for error_type, count in sorted(errors['error_types'].items(), key=lambda x: -x[1]):
                report.append(f"    - {error_type}: {count}")
            if errors['model_errors']:
                report.append(f"  模型错误分布:")
                for model_id, count in sorted(errors['model_errors'].items(), key=lambda x: -x[1]):
                    report.append(f"    - {model_id}: {count}")

        # 2. 性能分析
        report.append("\n【性能分析】")
        perf = self.analyze_performance(hours=hours)
        if "error" in perf:
            report.append(f"  无法分析性能: {perf['error']}")
        else:
            for op, stats in sorted(perf.items()):
                report.append(f"  {op}:")
                report.append(f"    调用次数: {stats['count']}")
                report.append(f"    平均耗时: {stats['avg_ms']}ms")
                report.append(f"    最小/最大: {stats['min_ms']}ms / {stats['max_ms']}ms")
                report.append(f"    错误数: {stats['errors']}")

        # 3. llama-server 事件
        report.append("\n【LLama-Server 事件】")
        server_events = self.analyze_llama_server_events(hours)
        if "error" in server_events:
            report.append(f"  无法分析事件: {server_events['error']}")
        else:
            report.append(f"  崩溃次数: {server_events['crash_count']}")
            report.append(f"  重启次数: {server_events['restart_count']}")
            report.append(f"  事件统计:")
            for event, count in sorted(server_events['event_summary'].items(), key=lambda x: -x[1]):
                report.append(f"    - {event}: {count}")

        # 4. 模型加载情况
        report.append("\n【模型加载情况】")
        models = self.analyze_model_loading()
        if "error" in models:
            report.append(f"  无法分析模型: {models['error']}")
        else:
            for model_id, stats in sorted(models.items()):
                report.append(f"  {model_id}:")
                report.append(f"    加载次数: {stats['load_count']}")
                report.append(f"    错误次数: {stats['error_count']}")
                report.append(f"    最后状态: {stats['last_status']}")

        report.append("\n" + "=" * 80)
        return "\n".join(report)

    def tail_logs(self, lines: int = 50, log_type: str = "app") -> List[str]:
        """查看日志尾部"""
        log_file = self.log_dir / f"{log_type}.log"
        if not log_file.exists():
            return [f"Log file not found: {log_file}"]

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if len(all_lines) > lines else all_lines
        except Exception as e:
            return [f"Error reading log: {e}"]


# 命令行接口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="日志分析工具")
    parser.add_argument("--log-dir", default="logs", help="日志目录")
    parser.add_argument("--report", action="store_true", help="生成综合报告")
    parser.add_argument("--errors", action="store_true", help="分析错误")
    parser.add_argument("--performance", action="store_true", help="分析性能")
    parser.add_argument("--server-events", action="store_true", help="分析 llama-server 事件")
    parser.add_argument("--models", action="store_true", help="分析模型加载")
    parser.add_argument("--tail", type=int, help="查看日志尾部 N 行")
    parser.add_argument("--log-type", default="app", help="日志类型 (app/error/performance/system)")
    parser.add_argument("--hours", type=int, default=24, help="分析最近 N 小时")

    args = parser.parse_args()

    analyzer = LogAnalyzer(args.log_dir)

    if args.report:
        print(analyzer.generate_report(args.hours))
    elif args.errors:
        print(json.dumps(analyzer.analyze_recent_errors(args.hours), indent=2, ensure_ascii=False))
    elif args.performance:
        print(json.dumps(analyzer.analyze_performance(hours=args.hours), indent=2, ensure_ascii=False))
    elif args.server_events:
        print(json.dumps(analyzer.analyze_llama_server_events(args.hours), indent=2, ensure_ascii=False))
    elif args.models:
        print(json.dumps(analyzer.analyze_model_loading(), indent=2, ensure_ascii=False))
    elif args.tail:
        for line in analyzer.tail_logs(args.tail, args.log_type):
            print(line, end='')
    else:
        print(analyzer.generate_report(args.hours))
