import os

print("=" * 70)
print("添加计算过程展示功能")
print("=" * 70)

# ========== 1. 创建 CalculationTooltip 组件 ==========
print("\n1. 创建 CalculationTooltip 组件...")

tooltip_component = '''import { useState } from 'react';
import { X, Calculator, Info } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';

interface CalculationStep {
  label: string;
  value: string | number;
  unit?: string;
  formula?: string;
}

interface CalculationDetail {
  title: string;
  description: string;
  formula: string;
  steps: CalculationStep[];
  result: {
    value: string | number;
    unit: string;
  };
}

interface CalculationTooltipProps {
  detail: CalculationDetail | null;
  isOpen: boolean;
  onClose: () => void;
}

export function CalculationTooltip({ detail, isOpen, onClose }: CalculationTooltipProps) {
  if (!detail) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <Calculator className="w-5 h-5 text-blue-600" />
            {detail.title}
            <Badge variant="secondary" className="ml-2">
              {detail.result.unit}
            </Badge>
          </DialogTitle>
        </DialogHeader>

        {/* 描述 */}
        <p className="text-sm text-slate-600 mt-2">{detail.description}</p>

        {/* 公式 */}
        <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
          <div className="text-xs text-blue-600 font-medium mb-1">计算公式</div>
          <div className="text-sm font-mono text-blue-800 break-all">
            {detail.formula}
          </div>
        </div>

        {/* 计算步骤 */}
        <div className="mt-4 space-y-2">
          <div className="text-sm font-medium text-slate-700 flex items-center gap-2">
            <Info className="w-4 h-4" />
            计算过程
          </div>
          
          <div className="space-y-2">
            {detail.steps.map((step, index) => (
              <div key={index} className="flex items-center justify-between p-2 bg-slate-50 rounded text-sm">
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-slate-200 flex items-center justify-center text-xs font-medium text-slate-600">
                    {index + 1}
                  </span>
                  <span className="text-slate-700">{step.label}</span>
                  {step.formula && (
                    <span className="text-xs text-slate-500 font-mono">
                      = {step.formula}
                    </span>
                  )}
                </div>
                <div className="text-right">
                  <span className="font-mono font-medium text-slate-900">
                    {typeof step.value === 'number' ? step.value.toFixed(2) : step.value}
                  </span>
                  {step.unit && (
                    <span className="text-xs text-slate-500 ml-1">{step.unit}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 最终结果 */}
        <div className="mt-4 pt-4 border-t">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-700">计算结果</span>
            <div className="text-right">
              <span className="text-2xl font-bold text-blue-600 font-mono">
                {detail.result.value}
              </span>
              <span className="text-sm text-slate-500 ml-1">{detail.result.unit}</span>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// 辅助函数：创建计算详情
export function createCalculationDetail(
  type: string,
  rowData: any,
  inputs: any
): CalculationDetail | null {
  switch (type) {
    case 'elec_rev':
      return {
        title: '峰谷价差收益',
        description: '通过低谷充电、高峰放电赚取的电价差收益',
        formula: '放电电量 × (峰时电价 - 谷时电价)',
        steps: [
          { label: '放电电量', value: rowData.discharge_kwh, unit: '万kWh', formula: 'charge_kwh × DOD × 放电效率' },
          { label: '峰时电价', value: inputs.price_valley + inputs.spread, unit: '元/kWh', formula: '谷时电价 + 价差' },
          { label: '谷时电价', value: inputs.price_valley, unit: '元/kWh' },
          { label: '单位收益', value: inputs.spread, unit: '元/kWh', formula: '峰时 - 谷时' },
        ],
        result: { value: rowData.elec_rev, unit: '万元' }
      };
    
    case 'sub_rev':
      return {
        title: '补贴收益',
        description: '政策补贴收入',
        formula: type === 'energy' ? '放电量 × 补贴单价' : '容量 × 补贴单价',
        steps: [
          { label: '补贴模式', value: inputs.sub_mode === 'energy' ? '按电量' : '按容量', unit: '' },
          { label: '补贴单价', value: inputs.sub_price, unit: inputs.sub_mode === 'energy' ? '元/kWh' : '元/kW' },
          { label: '补贴年限', value: inputs.sub_years, unit: '年' },
          { label: '本年补贴额', value: rowData.sub_rev, unit: '万元' },
        ],
        result: { value: rowData.sub_rev, unit: '万元' }
      };
    
    case 'loss_cost':
      return {
        title: '充电成本',
        description: '低谷时段充电的电费成本',
        formula: '充电电量 × 谷时电价',
        steps: [
          { label: '充电电量', value: rowData.charge_kwh, unit: '万kWh' },
          { label: '谷时电价', value: inputs.price_valley, unit: '元/kWh' },
          { label: '充电成本', value: rowData.loss_cost, unit: '万元', formula: 'charge × price' },
        ],
        result: { value: rowData.loss_cost, unit: '万元' }
      };
    
    case 'income_tax':
      return {
        title: '所得税',
        description: '企业应缴纳的所得税',
        formula: '应纳税所得额 × 税率',
        steps: [
          { label: '营业收入', value: rowData.total_rev, unit: '万元' },
          { label: '运营成本', value: rowData.opex, unit: '万元' },
          { label: '充电成本', value: rowData.loss_cost, unit: '万元' },
          { label: '折旧', value: rowData.dep, unit: '万元' },
          { label: '利息', value: rowData.interest, unit: '万元' },
          { label: '附加税', value: rowData.surcharge, unit: '万元' },
          { label: '应纳税所得额', value: (parseFloat(rowData.total_rev) - parseFloat(rowData.opex) - parseFloat(rowData.loss_cost) - parseFloat(rowData.dep) - parseFloat(rowData.interest) - parseFloat(rowData.surcharge)).toFixed(2), unit: '万元' },
          { label: '税率', value: inputs.tax_rate, unit: '%' },
        ],
        result: { value: rowData.income_tax, unit: '万元' }
      };
    
    case 'lcoe':
      return {
        title: '度电成本 LCOE',
        description: '平准化度电成本，考虑时间价值的全生命周期成本',
        formula: 'NPV(总成本) / NPV(总发电量)',
        steps: [
          { label: '初始投资', value: inputs.capex * inputs.capacity, unit: '万元' },
          { label: '运维成本', value: rowData.opex, unit: '万元/年' },
          { label: '充电成本', value: rowData.loss_cost, unit: '万元/年' },
          { label: '税金', value: rowData.total_tax, unit: '万元/年' },
          { label: '残值回收', value: -(inputs.capex * inputs.capacity * inputs.residual_rate / 100), unit: '万元(负值)' },
          { label: '年发电量', value: rowData.discharge_kwh, unit: '万kWh' },
        ],
        result: { value: rowData.lcoe || 0, unit: '元/kWh' }
      };
    
    default:
      return null;
  }
}
'''

with open('src/components/CalculationTooltip.tsx', 'w', encoding='utf-8') as f:
    f.write(tooltip_component)

print("   ✅ 已创建 CalculationTooltip 组件")

# ========== 2. 修改 DataTable.tsx 添加点击功能 ==========
print("\n2. 修改 DataTable.tsx...")

with open('src/components/DataTable.tsx', 'r') as f:
    content = f.read()

# 添加导入
if 'CalculationTooltip' not in content:
    import_line = '''import { CalculationTooltip, createCalculationDetail } from './CalculationTooltip';'''
    
    # 找到最后一个 import
    lines = content.split('\\n')
    last_import = 0
    for i, line in enumerate(lines):
        if line.startswith('import '):
            last_import = i
    
    lines.insert(last_import + 1, import_line)
    
    # 在组件内部添加 state
    component_start = lines.index('export function DataTable')
    for i in range(component_start, min(component_start + 20, len(lines))):
        if 'const [data, setData] = useState' in lines[i]:
            lines.insert(i + 1, '''  const [selectedCalc, setSelectedCalc] = useState<CalculationDetail | null>(null);
  const [isCalcOpen, setIsCalcOpen] = useState(false);''')
            break
    
    content = '\\n'.join(lines)
    
    # 添加点击处理函数
    old_export = 'export function DataTable'
    new_export = '''// 可点击的单元格配置
const clickableColumns = ['elec_rev', 'sub_rev', 'loss_cost', 'income_tax', 'total_tax', 'ebitda', 'cf'];

export function DataTable'''
    content = content.replace(old_export, new_export)
    
    # 修改表格单元格渲染，添加点击事件
    old_cell = 'className={cn("p-2", col.className)}'
    new_cell = '''className={cn("p-2 cursor-pointer hover:bg-blue-50 transition-colors", col.className, 
                clickableColumns.includes(col.key) && "hover:underline decoration-blue-400 underline-offset-2")} 
                onClick={() => {
                  if (clickableColumns.includes(col.key)) {
                    const detail = createCalculationDetail(col.key, row, { price_valley: 0.3, spread: 0.6, sub_mode: 'energy', sub_price: 0.5, sub_years: 10, tax_rate: 25, residual_rate: 5, capacity: 10, capex: 1.2 });
                    if (detail) {
                      setSelectedCalc(detail);
                      setIsCalcOpen(true);
                    }
                  }
                }}'''
    content = content.replace(old_cell, new_cell)
    
    # 在 return 语句前添加 Tooltip 组件
    old_return = 'return ('
    new_return = '''return (
    <>
      <CalculationTooltip 
        detail={selectedCalc} 
        isOpen={isCalcOpen} 
        onClose={() => setIsCalcOpen(false)} 
      />'''
    content = content.replace(old_return, new_return, 1)  # 只替换第一个
    
    # 在最后的 </div> 前添加 </>
    # 找到最后的 </div> 并替换为 </></div>
    last_div = content.rfind('</div>')
    if last_div > 0:
        content = content[:last_div] + '</>' + content[last_div:]
    
    with open('src/components/DataTable.tsx', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("   ✅ 已修改 DataTable 添加点击功能")

print("\n" + "=" * 70)
print("功能添加完成！")
print("=" * 70)
print("✅ 新增功能：")
print("   • 点击数据表格中的关键指标，显示计算过程")
print("   • 支持：峰谷收益、补贴、充电成本、所得税、LCOE")
print("   • 展示：公式、输入值、计算步骤、最终结果")
print("=" * 70)
print("\n请执行：")
print("  git add .")
print("  git commit -m 'feat: 添加数据计算过程展示功能'")
print("  git push")
