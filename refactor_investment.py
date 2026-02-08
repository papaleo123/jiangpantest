import os
import shutil
from datetime import datetime

print("=" * 70)
print("开始重构：添加投资明细表功能")
print("=" * 70)

# 备份函数
def backup_file(filepath):
    if os.path.exists(filepath):
        backup_name = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(filepath, backup_name)
        print(f"✅ 已备份: {filepath} -> {backup_name}")
        return True
    return False

# ========== 1. 修改 src/types/index.ts ==========
print("\n1. 修改 src/types/index.ts...")
types_file = 'src/types/index.ts'

if os.path.exists(types_file):
    backup_file(types_file)
    
    with open(types_file, 'r') as f:
        content = f.read()
    
    # 在文件末尾添加 InvestmentItem 类型（如果不存在）
    if 'InvestmentItem' not in content:
        new_types = '''
// 投资明细项
export interface InvestmentItem {
  name: string;           // 项目名称
  amount: number;         // 金额（万元）
  taxRate: number;        // 增值税率（%）
  category: 'equipment' | 'civil' | 'install' | 'other';
}

// 修改 InputParams 中的投资相关字段
// 注意：以下注释用于指导修改，实际字段在 hooks 中处理
'''
        content += new_types
        
        with open(types_file, 'w') as f:
            f.write(content)
        print("   ✅ 已添加 InvestmentItem 类型")
    else:
        print("   ⚠️  InvestmentItem 已存在，跳过")
else:
    print("   ❌ 文件不存在")

# ========== 2. 创建 InvestmentBreakdown 组件 ==========
print("\n2. 创建 InvestmentBreakdown 组件...")
component_dir = 'src/components'
os.makedirs(component_dir, exist_ok=True)

investment_component = '''import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Trash2 } from 'lucide-react';

interface InvestmentItem {
  name: string;
  amount: number;
  taxRate: number;
  category: 'equipment' | 'civil' | 'install' | 'other';
}

interface InvestmentBreakdownProps {
  items: InvestmentItem[];
  constructionPeriod: number;
  capacity: number;
  onItemsChange: (items: InvestmentItem[]) => void;
  onConstructionPeriodChange: (months: number) => void;
}

const DEFAULT_TAX_RATES = {
  equipment: 13,
  civil: 9,
  install: 9,
  other: 6,
};

export function InvestmentBreakdown({
  items,
  constructionPeriod,
  capacity,
  onItemsChange,
  onConstructionPeriodChange,
}: InvestmentBreakdownProps) {
  const [editingItems, setEditingItems] = useState<InvestmentItem[]>(
    items.length > 0 ? items : [
      { name: '储能系统设备', amount: 0, taxRate: 13, category: 'equipment' },
      { name: '土建工程', amount: 0, taxRate: 9, category: 'civil' },
      { name: '安装调试', amount: 0, taxRate: 9, category: 'install' },
    ]
  );

  const addItem = () => {
    const newItem: InvestmentItem = {
      name: '',
      amount: 0,
      taxRate: 13,
      category: 'equipment',
    };
    const updated = [...editingItems, newItem];
    setEditingItems(updated);
    onItemsChange(updated);
  };

  const removeItem = (index: number) => {
    const updated = editingItems.filter((_, i) => i !== index);
    setEditingItems(updated);
    onItemsChange(updated);
  };

  const updateItem = (index: number, field: keyof InvestmentItem, value: any) => {
    const updated = editingItems.map((item, i) => {
      if (i !== index) return item;
      
      if (field === 'category') {
        return {
          ...item,
          [field]: value,
          taxRate: DEFAULT_TAX_RATES[value as keyof typeof DEFAULT_TAX_RATES],
        };
      }
      
      return { ...item, [field]: value };
    });
    setEditingItems(updated);
    onItemsChange(updated);
  };

  const totalInvestment = editingItems.reduce((sum, item) => sum + item.amount, 0);
  
  const totalInputVAT = editingItems.reduce((sum, item) => {
    const taxExcluded = item.amount / (1 + item.taxRate / 100);
    return sum + (item.amount - taxExcluded);
  }, 0);

  const unitCost = capacity > 0 ? (totalInvestment * 10000) / (capacity * 1000000) : 0;

  return (
    <Card className="w-full mt-4">
      <CardHeader>
        <CardTitle className="text-lg flex items-center justify-between">
          <span>投资构成明细</span>
          <div className="text-sm font-normal text-slate-500">
            单位造价: {unitCost.toFixed(2)} 元/Wh
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 建设期设置 */}
        <div className="grid grid-cols-2 gap-4 pb-4 border-b">
          <div>
            <Label>建设期（月）</Label>
            <Input
              type="number"
              min={1}
              max={36}
              value={constructionPeriod}
              onChange={(e) => onConstructionPeriodChange(parseInt(e.target.value) || 12)}
              className="mt-1"
            />
            <p className="text-xs text-slate-500 mt-1">
              建设期内只产生成本，不产生收入
            </p>
          </div>
          <div className="text-right">
            <div className="text-sm text-slate-600">总投资（含税）</div>
            <div className="text-2xl font-bold text-blue-600">
              {totalInvestment.toFixed(2)} 万元
            </div>
            <div className="text-xs text-slate-500">
              进项税合计: {totalInputVAT.toFixed(2)} 万元
            </div>
          </div>
        </div>

        {/* 投资明细列表 */}
        <div className="space-y-3">
          {editingItems.map((item, index) => (
            <div key={index} className="grid grid-cols-12 gap-2 items-end bg-slate-50 p-3 rounded-lg">
              <div className="col-span-2">
                <Label className="text-xs">类别</Label>
                <Select
                  value={item.category}
                  onValueChange={(v) => updateItem(index, 'category', v)}
                >
                  <SelectTrigger className="h-8">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="equipment">设备</SelectItem>
                    <SelectItem value="civil">土建</SelectItem>
                    <SelectItem value="install">安装</SelectItem>
                    <SelectItem value="other">其他</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="col-span-4">
                <Label className="text-xs">项目名称</Label>
                <Input
                  value={item.name}
                  onChange={(e) => updateItem(index, 'name', e.target.value)}
                  placeholder="如：储能系统设备"
                  className="h-8"
                />
              </div>

              <div className="col-span-3">
                <Label className="text-xs">金额（万元）</Label>
                <Input
                  type="number"
                  value={item.amount}
                  onChange={(e) => updateItem(index, 'amount', parseFloat(e.target.value) || 0)}
                  className="h-8"
                />
              </div>

              <div className="col-span-2">
                <Label className="text-xs">税率</Label>
                <Select
                  value={item.taxRate.toString()}
                  onValueChange={(v) => updateItem(index, 'taxRate', parseInt(v))}
                >
                  <SelectTrigger className="h-8">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="13">13%</SelectItem>
                    <SelectItem value="9">9%</SelectItem>
                    <SelectItem value="6">6%</SelectItem>
                    <SelectItem value="3">3%</SelectItem>
                    <SelectItem value="0">0%</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="col-span-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeItem(index)}
                  className="h-8 text-red-500 hover:text-red-700"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>

              <div className="col-span-12 text-xs text-slate-500 mt-1">
                进项税: {((item.amount - item.amount / (1 + item.taxRate / 100))).toFixed(2)} 万元
              </div>
            </div>
          ))}
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={addItem}
          className="w-full"
        >
          <Plus className="w-4 h-4 mr-2" />
          添加投资项
        </Button>

        <div className="text-xs text-slate-500 bg-blue-50 p-3 rounded">
          <p>💡 不同成本类型适用不同增值税率：</p>
          <ul className="list-disc list-inside mt-1 space-y-1">
            <li>设备购置：13%</li>
            <li>建筑工程：9%</li>
            <li>安装劳务：9% 或 3%</li>
            <li>设计咨询：6%</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
'''

component_path = os.path.join(component_dir, 'InvestmentBreakdown.tsx')
with open(component_path, 'w', encoding='utf-8') as f:
    f.write(investment_component)
print(f"   ✅ 已创建: {component_path}")

# ========== 3. 修改 useStorageCalculation.ts ==========
print("\n3. 修改 useStorageCalculation.ts...")
calc_file = 'src/hooks/useStorageCalculation.ts'

if os.path.exists(calc_file):
    backup_file(calc_file)
    
    with open(calc_file, 'r') as f:
        content = f.read()
    
    # 修改默认值：添加 investmentItems 和 constructionPeriod
    if 'investmentItems:' not in content:
        # 替换默认值部分
        old_defaults = '''aug_price: 0.6,          // 补容单价
    residual_rate: 5,        // 残值率 5%'''
        
        new_defaults = '''aug_price: 0.6,          // 补容单价
    aug_dep_years: 15,        // 补容折旧年限
    residual_rate: 5,        // 残值率 5%
    constructionPeriod: 12,   // 建设期（月），默认12个月
    investmentItems: [        // 投资明细（默认示例）
      { name: '储能系统设备', amount: 9600, taxRate: 13, category: 'equipment' },
      { name: '土建工程', amount: 1800, taxRate: 9, category: 'civil' },
      { name: '安装调试', amount: 600, taxRate: 9, category: 'install' },
    ],'''
        
        content = content.replace(old_defaults, new_defaults)
        
        # 修改总投资计算逻辑（关键！）
        # 找到 // 投资参数 部分，替换为新的计算逻辑
        old_investment = '''    // 投资参数
    const totalInvGross = Wh * inputs.capex;                    // 总投资(含税)
    const vatRate = inputs.vat_rate / 100;
    const totalInvNet = totalInvGross / (1 + vatRate);          // 总投资(不含税)
    const inputVAT = totalInvGross - totalInvNet;               // 设备进项税'''
        
        new_investment = '''    // 投资参数（新的明细计算）
    const vatRate = inputs.vat_rate / 100;
    
    // 计算总投资和分项进项税（关键改进！）
    let totalInvGross = 0;      // 总投资含税
    let totalInvNet = 0;        // 总投资不含税  
    let totalInputVAT = 0;      // 总进项税
    
    // 计算各项投资的税额
    const investmentDetails = inputs.investmentItems.map(item => {
      const netAmount = item.amount / (1 + item.taxRate / 100);
      const itemVAT = item.amount - netAmount;
      totalInvGross += item.amount;
      totalInvNet += netAmount;
      totalInputVAT += itemVAT;
      return { ...item, netAmount, itemVAT };
    });
    
    // 设备进项税（用于抵扣）
    const inputVAT = totalInputVAT;'''
        
        content = content.replace(old_investment, new_investment)
        
        # 保存文件
        with open(calc_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("   ✅ 已修改投资计算逻辑")
    else:
        print("   ⚠️  investmentItems 已存在，跳过")
else:
    print("   ❌ 文件不存在")

# ========== 4. 修改 InputPanel.tsx ==========
print("\n4. 修改 InputPanel.tsx...")
panel_file = 'src/components/InputPanel.tsx'

if os.path.exists(panel_file):
    backup_file(panel_file)
    
    with open(panel_file, 'r') as f:
        content = f.read()
    
    # 添加导入
    if 'InvestmentBreakdown' not in content:
        # 在文件开头添加导入
        import_line = "import { InvestmentBreakdown } from './InvestmentBreakdown';"
        if 'import' in content:
            # 找到最后一个 import 后面添加
            lines = content.split('\\n')
            import_idx = -1
            for i, line in enumerate(lines):
                if line.startswith('import '):
                    import_idx = i
            if import_idx >= 0:
                lines.insert(import_idx + 1, import_line)
                content = '\\n'.join(lines)
        
        # 在合适位置添加组件（在补容设置后面）
        # 查找补容单价的输入框位置
        if 'aug_price' in content:
            # 在 aug_price 输入框后面添加 InvestmentBreakdown
            # 简单做法：在文件末尾的 return 之前添加
            # 或者找到合适的位置插入
            
            # 这里采用在 "立即计算" 按钮之前插入
            old_button = '<Button.*onClick={calculate}.*立即计算'
            if '立即计算' in content:
                # 在立即计算按钮之前插入
                content = content.replace(
                    'onClick={calculate}',
                    'onClick={calculate}\\n          className="mb-4"'
                )
                
                # 添加 InvestmentBreakdown 组件（在按钮之前）
                component_usage = '''
      <InvestmentBreakdown
        items={inputs.investmentItems || []}
        constructionPeriod={inputs.constructionPeriod || 12}
        capacity={inputs.capacity}
        onItemsChange={(items) => updateInput('investmentItems', items)}
        onConstructionPeriodChange={(months) => updateInput('constructionPeriod', months)}
      />
      
      <Button'''
                
                content = content.replace(
                    '<Button',
                    component_usage,
                    1  # 只替换第一个
                )
        
        with open(panel_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("   ✅ 已添加 InvestmentBreakdown 组件")
    else:
        print("   ⚠️  InvestmentBreakdown 已导入，跳过")
else:
    print("   ❌ 文件不存在")

print("\n" + "=" * 70)
print("重构完成！请执行以下命令：")
print("=" * 70)
print("1. git add .")
print("2. git commit -m 'feat: 添加投资明细表和建设期设置'")
print("3. git push")
print("\n注意：")
print("- 系统已添加默认投资明细（设备80%/土建15%/安装5%）")
print("- 建设期默认12个月，可根据实际情况调整")
print("- 不同成本类型适用不同增值税率")
