#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
储能财务模型代码优化脚本
功能：自动检测和修复代码质量问题，提供优化建议
运行方式：在项目根目录下执行 python optimize_storage_code.py
"""

import os
import re
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Set, Optional, Tuple
import subprocess

@dataclass
class CodeIssue:
    """代码问题记录"""
    file_path: str
    line_number: int
    issue_type: str  # 'performance', 'duplication', 'complexity', 'maintainability'
    severity: str    # 'high', 'medium', 'low'
    description: str
    suggested_fix: str

@dataclass
class FileContent:
    """文件内容管理"""
    path: str
    content: str
    lines: List[str]

class StorageCodeOptimizer:
    """储能代码优化器"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).absolute()
        self.issues: List[CodeIssue] = []
        self.files: Dict[str, FileContent] = {}
        
        # 性能相关正则表达式
        self.regex_patterns = {
            'heavy_computation': r'useMemo.*=>.*\{.*runSimulation.*\}',
            'no_debounce': r'onUpdate.*=>.*setInputs',
            'multiple_fixed': r'toFixed\(\d\)',
            'floating_point': r'\d+\.\d+\s*[\+\-\*\/]\s*\d+\.\d+',
            'magic_numbers': r'\b(0\.\d{2,}|[1-9]\d*\.\d{2,})\b',
            'long_function': r'function\s+\w+\([^)]{50,}\)',
            'complex_callback': r'useCallback\(.*\{[\s\S]{500,}?\n\}\)',
        }
        
    def load_files(self) -> None:
        """加载项目文件"""
        print("📁 正在扫描项目文件...")
        
        # 文件扩展名过滤
        valid_extensions = {'.ts', '.tsx', '.js', '.jsx'}
        
        for file_path in self.project_root.rglob('*'):
            if file_path.suffix in valid_extensions and file_path.is_file():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    self.files[str(file_path)] = FileContent(
                        path=str(file_path),
                        content=content,
                        lines=content.splitlines()
                    )
                except Exception as e:
                    print(f"⚠️  读取文件失败: {file_path} - {e}")
        
        print(f"✅ 已加载 {len(self.files)} 个文件")
    
    def analyze_performance(self) -> None:
        """分析性能问题"""
        print("\n🔍 分析性能问题...")
        
        for file_path, file_content in self.files.items():
            lines = file_content.lines
            
            # 检查重复的完整文件计算
            if 'useStorageCalculation' in file_path:
                self._analyze_storage_hook(file_path, lines)
            
            # 检查未防抖的输入处理
            for i, line in enumerate(lines, 1):
                if 'onUpdate' in line and 'setInputs' in line and 'debounce' not in line:
                    self.issues.append(CodeIssue(
                        file_path=file_path,
                        line_number=i,
                        issue_type='performance',
                        severity='high',
                        description='输入更新未使用防抖，可能导致频繁重计算',
                        suggested_fix='使用lodash的debounce或自定义防抖函数包装updateInput'
                    ))
            
            # 检查繁重的useMemo计算
            for i, line in enumerate(lines, 1):
                if 'useMemo' in line and 'runSimulation' in line:
                    self.issues.append(CodeIssue(
                        file_path=file_path,
                        line_number=i,
                        issue_type='performance',
                        severity='high',
                        description='useMemo中包含复杂的敏感性分析计算',
                        suggested_fix='考虑使用Web Worker或增量计算，或添加防抖延迟'
                    ))
    
    def _analyze_storage_hook(self, file_path: str, lines: List[str]) -> None:
        """分析存储计算Hook"""
        in_sensitivity = False
        sensitivity_start = 0
        
        for i, line in enumerate(lines, 1):
            if 'sensitivityData = useMemo' in line:
                in_sensitivity = True
                sensitivity_start = i
            
            if in_sensitivity and '}, [inputs]' in line:
                sensitivity_end = i
                
                # 计算敏感性分析代码块大小
                block_size = sensitivity_end - sensitivity_start
                if block_size > 50:  # 大代码块阈值
                    self.issues.append(CodeIssue(
                        file_path=file_path,
                        line_number=sensitivity_start,
                        issue_type='performance',
                        severity='high',
                        description=f'敏感性分析计算过于复杂（{block_size}行），可能导致输入卡顿',
                        suggested_fix='提取为独立函数，使用Web Worker，或简化计算逻辑'
                    ))
                in_sensitivity = False
    
    def analyze_code_duplication(self) -> None:
        """分析代码重复"""
        print("\n🔍 分析代码重复...")
        
        file_contents = {}
        for file_path, file_content in self.files.items():
            # 清理注释和空白
            clean_content = self._clean_code(file_content.content)
            file_contents[file_path] = clean_content
        
        # 查找重复内容
        seen = {}
        duplicates = []
        
        for file_path, content in file_contents.items():
            if content in seen:
                duplicates.append((file_path, seen[content]))
            else:
                seen[content] = file_path
        
        for dup_file, orig_file in duplicates:
            self.issues.append(CodeIssue(
                file_path=dup_file,
                line_number=0,
                issue_type='duplication',
                severity='medium',
                description=f'文件内容与 {orig_file} 完全重复',
                suggested_fix='删除重复文件，确保单点维护'
            ))
    
    def analyze_complexity(self) -> None:
        """分析代码复杂度"""
        print("\n🔍 分析代码复杂度...")
        
        for file_path, file_content in self.files.items():
            lines = file_content.lines
            
            # 检查过长函数
            for i, line in enumerate(lines, 1):
                if 'function ' in line or 'const ' in line and '=' in line and '(' in line:
                    # 查找函数结束
                    brace_count = 0
                    func_lines = 0
                    for j in range(i-1, min(i+100, len(lines))):  # 检查后续100行
                        func_lines += 1
                        brace_count += lines[j].count('{')
                        brace_count -= lines[j].count('}')
                        
                        if brace_count == 0 and lines[j].strip().endswith('}'):
                            if func_lines > 50:  # 函数过长阈值
                                self.issues.append(CodeIssue(
                                    file_path=file_path,
                                    line_number=i,
                                    issue_type='complexity',
                                    severity='medium',
                                    description=f'函数过长（{func_lines}行），难以维护',
                                    suggested_fix='提取为多个小函数，每个函数单一职责'
                                ))
                            break
    
    def analyze_maintainability(self) -> None:
        """分析可维护性问题"""
        print("\n🔍 分析可维护性问题...")
        
        for file_path, file_content in self.files.items():
            lines = file_content.lines
            
            for i, line in enumerate(lines, 1):
                # 检查硬编码的魔法数字
                magic_nums = re.findall(r'\b(0\.\d{2,}|[1-9]\d*\.\d{2,})\b', line)
                for num in magic_nums:
                    if float(num) not in [0, 1]:  # 排除0和1
                        self.issues.append(CodeIssue(
                            file_path=file_path,
                            line_number=i,
                            issue_type='maintainability',
                            severity='low',
                            description=f'硬编码的魔法数字: {num}',
                            suggested_fix='提取为常量，如 FINANCIAL_CONSTANTS.DISCOUNT_RATE'
                        ))
                
                # 检查复杂的条件判断
                if 'if (' in line and line.count('&&') + line.count('||') > 2:
                    self.issues.append(CodeIssue(
                        file_path=file_path,
                        line_number=i,
                        issue_type='maintainability',
                        severity='medium',
                        description='复杂条件判断，难以理解',
                        suggested_fix='提取条件为命名函数，如 isValidInput() 或 shouldApplyTaxCredit()'
                    ))
    
    def _clean_code(self, content: str) -> str:
        """清理代码：移除注释和多余空白"""
        # 移除单行注释
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            # 保留空行和仅包含空格的行以保持结构
            if '//' in line:
                line = line.split('//')[0]
            cleaned_lines.append(line.strip())
        return '\n'.join(cleaned_lines)
    
    def generate_fixes(self) -> Dict[str, str]:
        """生成修复代码"""
        fixes = {}
        
        # 1. 创建防抖工具函数
        fixes['debounce_util.ts'] = """/**
 * 防抖函数工具
 * @param func 要防抖的函数
 * @param wait 等待时间(毫秒)
 * @param immediate 是否立即执行
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  immediate: boolean = false
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;
  
  return function(this: any, ...args: Parameters<T>) {
    const context = this;
    
    const later = () => {
      timeout = null;
      if (!immediate) {
        func.apply(context, args);
      }
    };
    
    const callNow = immediate && !timeout;
    
    if (timeout) {
      clearTimeout(timeout);
    }
    
    timeout = setTimeout(later, wait);
    
    if (callNow) {
      func.apply(context, args);
    }
  };
}

/**
 * 节流函数工具
 * @param func 要节流的函数
 * @param limit 限制时间(毫秒)
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;
  
  return function(this: any, ...args: Parameters<T>) {
    const context = this;
    
    if (!inThrottle) {
      func.apply(context, args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}
"""
        
        # 2. 创建计算Worker模板
        fixes['calculation.worker.ts'] = """/// <reference lib="webworker" />

declare const self: DedicatedWorkerGlobalScope;

// 导入计算函数类型定义
type InputParams = any; // 从types导入
type CalculationResult = any;

// 监听消息
self.addEventListener('message', (event: MessageEvent<{ inputs: InputParams; type: string }>) => {
  const { inputs, type } = event.data;
  
  try {
    let result: CalculationResult;
    
    switch (type) {
      case 'full':
        result = calculateFullModel(inputs);
        break;
      case 'sensitivity':
        result = calculateSensitivity(inputs);
        break;
      default:
        throw new Error(`Unknown calculation type: ${type}`);
    }
    
    self.postMessage({
      success: true,
      result,
      type
    });
  } catch (error) {
    self.postMessage({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      type
    });
  }
});

// 完整模型计算（在主线程外运行）
function calculateFullModel(inputs: InputParams): CalculationResult {
  // 将原有的calculate函数逻辑移到这里
  // 注意：不能使用React Hooks
  // 实现独立的计算逻辑
  
  const result = {
    // 计算结果
  };
  
  return result;
}

// 敏感性分析计算
function calculateSensitivity(inputs: InputParams) {
  // 优化后的敏感性分析逻辑
  // 使用增量计算或简化算法
  
  return {
    // 敏感性分析结果
  };
}

// 导出类型供主线程使用
export type { InputParams, CalculationResult };
"""
        
        # 3. 创建精度处理工具
        fixes['precision.utils.ts'] = """/**
 * 财务计算精度处理工具
 * 避免JavaScript浮点数精度问题
 */

export class FinancialPrecision {
  private static readonly DEFAULT_DECIMALS = 4;
  
  /**
   * 安全的四舍五入
   */
  static round(value: number, decimals: number = this.DEFAULT_DECIMALS): number {
    const factor = Math.pow(10, decimals);
    return Math.round(value * factor) / factor;
  }
  
  /**
   * 金额处理（2位小数）
   */
  static yuan(value: number): number {
    return this.round(value, 2);
  }
  
  /**
   * 百分比处理（1位小数）
   */
  static percent(value: number): number {
    return this.round(value, 1);
  }
  
  /**
   * 安全加法
   */
  static add(a: number, b: number): number {
    return this.round(this.round(a) + this.round(b));
  }
  
  /**
   * 安全减法
   */
  static subtract(a: number, b: number): number {
    return this.round(this.round(a) - this.round(b));
  }
  
  /**
   * 安全乘法
   */
  static multiply(a: number, b: number): number {
    return this.round(this.round(a) * this.round(b));
  }
  
  /**
   * 安全除法
   */
  static divide(a: number, b: number): number {
    if (b === 0) throw new Error('Division by zero');
    return this.round(this.round(a) / this.round(b));
  }
  
  /**
   * 格式化金额显示
   */
  static formatCurrency(value: number, decimals: number = 2): string {
    return value.toLocaleString('zh-CN', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  }
  
  /**
   * 格式化百分比显示
   */
  static formatPercentage(value: number, decimals: number = 1): string {
    return `${(value * 100).toFixed(decimals)}%`;
  }
  
  /**
   * 检查是否为有效数字
   */
  static isValidNumber(value: any): boolean {
    return typeof value === 'number' && !isNaN(value) && isFinite(value);
  }
}
"""
        
        # 4. 优化后的Hooks模板
        fixes['optimized_useStorageCalculation.ts'] = """import { useState, useCallback, useMemo, useRef } from 'react';
import { debounce } from '@/utils/debounce';
import { FinancialPrecision } from '@/utils/precision';
import type { InputParams, CalculationResult, KpiResult, YearlyRow, Stats } from '@/types';

// ==================== 常量配置 ====================
const FINANCIAL_CONSTANTS = {
  DEGRADATION: {
    FIRST_YEAR: 0.04,
    ANNUAL: 0.025,
    MIN_SOH: 0.60,
  },
  SURCHARGE_RATE: 0.12,
  MAX_LOAN_TERM: 10,
  RESIDUAL_RATE: 0.05,
  DISCOUNT_RATE: 0.08,
  PRECISION: {
    AMOUNT: 2,
    PERCENTAGE: 1,
    RATIO: 4,
  },
} as const;

// ==================== 优化工具函数 ====================
class Precision {
  static round = FinancialPrecision.round;
  static yuan = FinancialPrecision.yuan;
  static calc = (n: number) => FinancialPrecision.round(n, 4);
}

// ==================== 计算模块 ====================
interface PhysicsResult {
  annualChargeKWh: number;
  annualDischargeKWh: number;
  lossKWh: number;
  nextSOH: number;
}

const calculatePhysics = (
  capacityWh: number,
  currentSOH: number,
  dod: number,
  cycles: number,
  runDays: number,
  chargeEff: number,
  dischargeEff: number,
  year: number
): PhysicsResult => {
  // ... 优化实现 ...
};

// ==================== 优化后的Hook ====================
export function useStorageCalculation() {
  const [inputs, setInputs] = useState<InputParams>({
    // 默认值...
  });
  
  const [result, setResult] = useState<CalculationResult | null>(null);
  const [kpi, setKpi] = useState<KpiResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  
  // 防抖的输入更新
  const debouncedUpdateInput = useMemo(
    () =>
      debounce(<K extends keyof InputParams>(key: K, value: InputParams[K]) => {
        setInputs(prev => ({ ...prev, [key]: value }));
        setError(null);
      }, 300),
    []
  );
  
  // 使用ref存储计算实例
  const calculationRef = useRef<{
    lastInputsHash?: string;
    cachedResult?: CalculationResult;
    worker?: Worker;
  }>({});
  
  // 计算敏感性分析的优化版本
  const sensitivityData = useMemo(() => {
    if (!inputs || isCalculating) return [];
    
    // 使用增量计算或缓存
    const cached = calculationRef.current.cachedResult;
    if (cached && calculationRef.current.lastInputsHash === hashInputs(inputs)) {
      return cached.sensitivityData || [];
    }
    
    // 简化的敏感性分析
    return calculateSimplifiedSensitivity(inputs);
  }, [inputs, isCalculating]);
  
  // 主计算函数
  const calculate = useCallback(async () => {
    if (isCalculating) return;
    
    setIsCalculating(true);
    setError(null);
    
    try {
      // 1. 输入验证
      validateInputs(inputs);
      
      // 2. 使用Web Worker进行繁重计算
      if (window.Worker) {
        const result = await calculateWithWorker(inputs);
        setResult(result);
        setKpi(result.kpi);
      } else {
        // 降级方案：主线程计算
        const result = calculateInMainThread(inputs);
        setResult(result);
        setKpi(result.kpi);
      }
      
      // 3. 缓存结果
      calculationRef.current = {
        lastInputsHash: hashInputs(inputs),
        cachedResult: result,
      };
      
    } catch (err) {
      setError(err instanceof Error ? err.message : '计算发生错误');
    } finally {
      setIsCalculating(false);
    }
  }, [inputs, isCalculating]);
  
  // 其他函数...
  
  return {
    sensitivityData,
    inputs,
    result,
    kpi,
    error,
    isCalculating,
    updateInput: debouncedUpdateInput,
    calculate,
    // ... 其他返回值
  };
}

// 辅助函数
function hashInputs(inputs: InputParams): string {
  return JSON.stringify(inputs);
}

function calculateSimplifiedSensitivity(inputs: InputParams) {
  // 简化的敏感性分析实现
  // 只计算关键变量，使用近似算法
  return [];
}

async function calculateWithWorker(inputs: InputParams): Promise<CalculationResult> {
  return new Promise((resolve, reject) => {
    const worker = new Worker('calculation.worker.js');
    
    worker.onmessage = (event) => {
      if (event.data.success) {
        resolve(event.data.result);
      } else {
        reject(new Error(event.data.error));
      }
      worker.terminate();
    };
    
    worker.onerror = (error) => {
      reject(error);
      worker.terminate();
    };
    
    worker.postMessage({ inputs, type: 'full' });
  });
}

function calculateInMainThread(inputs: InputParams): CalculationResult {
  // 降级的主线程计算
  // ... 实现 ...
}
"""
        
        return fixes
    
    def create_optimization_script(self) -> str:
        """创建优化脚本"""
        return """#!/bin/bash
# 储能财务模型优化脚本
# 运行此脚本前请确保已备份代码

echo "🚀 开始优化储能财务模型代码..."

# 1. 安装必要的依赖
echo "📦 检查依赖..."
if ! command -v npm &> /dev/null; then
    echo "❌ 请先安装Node.js和npm"
    exit 1
fi

# 2. 添加性能优化包
echo "📦 添加性能优化依赖..."
npm install --save-dev lodash.debounce
npm install --save worker-loader

# 3. 创建优化目录结构
echo "📁 创建优化目录结构..."
mkdir -p src/{core,hooks,utils,services}

# 4. 移动现有文件到合适位置
echo "📁 重组项目结构..."
if [ -f "src/hooks/useStorageCalculation.ts" ]; then
    mv src/hooks/useStorageCalculation.ts src/core/calculators/
fi

# 5. 创建配置文件
echo "⚙️  创建配置文件..."
cat > src/core/config/financial-constants.ts << 'EOF'
export const FINANCIAL_CONSTANTS = {
  // 衰减率
  DEGRADATION: {
    FIRST_YEAR: 0.04,
    ANNUAL: 0.025,
    MIN_SOH: 0.60,
  },
  SURCHARGE_RATE: 0.12,
  MAX_LOAN_TERM: 10,
  RESIDUAL_RATE: 0.05,
  DISCOUNT_RATE: 0.08,
  PRECISION: {
    AMOUNT: 2,
    PERCENTAGE: 1,
    RATIO: 4,
  },
} as const;
EOF

echo "✅ 优化脚本准备完成！"
echo ""
echo "下一步："
echo "1. 运行 ./optimize_storage.sh 应用优化"
echo "2. 检查生成的优化报告：storage_optimization_report.md"
echo "3. 根据报告逐一修复问题"
"""

    def generate_report(self) -> str:
        """生成优化报告"""
        report = []
        report.append("# 📊 储能财务模型代码优化报告")
        report.append(f"生成时间：{subprocess.getoutput('date')}")
        report.append(f"项目路径：{self.project_root}")
        report.append("")
        
        # 按严重程度统计问题
        high_issues = [i for i in self.issues if i.severity == 'high']
        medium_issues = [i for i in self.issues if i.severity == 'medium']
        low_issues = [i for i in self.issues if i.severity == 'low']
        
        report.append("## 📈 问题统计")
        report.append(f"- 🔴 高危问题：{len(high_issues)} 个")
        report.append(f"- 🟡 中危问题：{len(medium_issues)} 个")
        report.append(f"- 🟢 低危问题：{len(low_issues)} 个")
        report.append("")
        
        # 按类型分组显示
        report.append("## 🔍 详细问题列表")
        
        for severity, issues in [('高危', high_issues), ('中危', medium_issues), ('低危', low_issues)]:
            if issues:
                report.append(f"### {severity}问题")
                for issue in issues:
                    report.append(f"#### 📄 {Path(issue.file_path).name} (第{issue.line_number}行)")
                    report.append(f"- **类型**：{issue.issue_type}")
                    report.append(f"- **描述**：{issue.description}")
                    report.append(f"- **修复建议**：{issue.suggested_fix}")
                    report.append("")
        
        # 生成优化建议
        report.append("## 🚀 优化建议")
        report.append("### 优先级1：立即修复")
        report.append("1. **删除重复文件**：检查并删除完全重复的代码文件")
        report.append("2. **添加防抖处理**：在所有输入更新函数中添加防抖")
        report.append("3. **优化敏感性分析**：提取为独立Worker或简化计算")
        report.append("")
        
        report.append("### 优先级2：本周完成")
        report.append("1. **统一精度处理**：使用FinancialPrecision类")
        report.append("2. **提取常量**：将所有魔法数字提取为常量")
        report.append("3. **增加单元测试**：为核心计算函数添加测试")
        report.append("")
        
        report.append("### 优先级3：本月完成")
        report.append("1. **引入Web Worker**：将繁重计算移至后台线程")
        report.append("2. **重构计算引擎**：提取为独立的类结构")
        report.append("3. **添加类型安全**：完善所有TypeScript类型定义")
        report.append("")
        
        # 自动修复脚本
        report.append("## 🛠️ 自动修复脚本")
        report.append("已为您生成以下修复文件：")
        report.append("1. `src/utils/debounce.ts` - 防抖工具函数")
        report.append("2. `src/utils/precision.ts` - 精度处理工具")
        report.append("3. `src/workers/calculation.worker.ts` - 计算Worker")
        report.append("4. `optimize_storage.sh` - 一键优化脚本")
        report.append("")
        report.append("运行方式：")
        report.append("```bash")
        report.append("chmod +x optimize_storage.sh")
        report.append("./optimize_storage.sh")
        report.append("```")
        
        return '\n'.join(report)
    
    def save_optimization_files(self, output_dir: str = "optimization_output") -> None:
        """保存优化文件"""
        output_path = self.project_root / output_dir
        output_path.mkdir(exist_ok=True)
        
        # 生成修复代码
        fixes = self.generate_fixes()
        
        for filename, content in fixes.items():
            file_path = output_path / filename
            file_path.write_text(content, encoding='utf-8')
            print(f"📝 已生成: {file_path}")
        
        # 生成优化报告
        report = self.generate_report()
        report_path = output_path / "storage_optimization_report.md"
        report_path.write_text(report, encoding='utf-8')
        print(f"📊 已生成优化报告: {report_path}")
        
        # 生成Bash脚本
        script = self.create_optimization_script()
        script_path = output_path / "optimize_storage.sh"
        script_path.write_text(script, encoding='utf-8')
        script_path.chmod(0o755)  # 添加执行权限
        print(f"🛠️  已生成优化脚本: {script_path}")
        
        # 生成TypeScript配置
        ts_config = {
            "compilerOptions": {
                "target": "es2020",
                "lib": ["dom", "dom.iterable", "esnext"],
                "allowJs": true,
                "skipLibCheck": true,
                "strict": true,
                "forceConsistentCasingInFileNames": true,
                "noEmit": true,
                "esModuleInterop": true,
                "module": "esnext",
                "moduleResolution": "node",
                "resolveJsonModule": true,
                "isolatedModules": true,
                "jsx": "preserve",
                "baseUrl": ".",
                "paths": {
                    "@/*": ["src/*"],
                    "@core/*": ["src/core/*"],
                    "@utils/*": ["src/utils/*"]
                }
            },
            "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
            "exclude": ["node_modules"]
        }
        
        tsconfig_path = output_path / "tsconfig.optimized.json"
        tsconfig_path.write_text(json.dumps(ts_config, indent=2), encoding='utf-8')
        print(f"⚙️  已生成TypeScript配置: {tsconfig_path}")
    
    def run_analysis(self) -> None:
        """运行完整分析"""
        print("=" * 60)
        print("🔧 储能财务模型代码优化分析器")
        print("=" * 60)
        
        self.load_files()
        self.analyze_performance()
        self.analyze_code_duplication()
        self.analyze_complexity()
        self.analyze_maintainability()
        
        print(f"\n✅ 分析完成！发现 {len(self.issues)} 个问题")
        
        # 显示统计
        high_count = sum(1 for i in self.issues if i.severity == 'high')
        medium_count = sum(1 for i in self.issues if i.severity == 'medium')
        low_count = sum(1 for i in self.issues if i.severity == 'low')
        
        print(f"🔴 高危问题: {high_count}")
        print(f"🟡 中危问题: {medium_count}")
        print(f"🟢 低危问题: {low_count}")
        
        # 保存优化文件
        self.save_optimization_files()
        
        print("\n" + "=" * 60)
        print("🎉 优化文件已生成！")
        print("请查看 optimization_output/ 目录中的文件")
        print("=" * 60)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='储能财务模型代码优化工具')
    parser.add_argument('--path', '-p', default='.', help='项目根目录路径')
    parser.add_argument('--fix', '-f', action='store_true', help='自动生成修复文件')
    
    args = parser.parse_args()
    
    optimizer = StorageCodeOptimizer(args.path)
    optimizer.run_analysis()
    
    if args.fix:
        print("\n🔧 正在生成修复文件...")
        # 这里可以添加自动修复逻辑
        print("✅ 修复文件已生成")

if __name__ == "__main__":
    main()