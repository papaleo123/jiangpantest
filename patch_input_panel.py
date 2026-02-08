import re

with open('src/components/InputPanel.tsx', 'r') as f:
    content = f.read()

print("修改 InputPanel.tsx...")

# 1. 添加导入
if 'InvestmentBreakdown' not in content:
    # 在文件开头添加导入
    import_line = """import { InvestmentBreakdown, InvestmentItem } from './InvestmentBreakdown';"""
    
    # 找到最后一个 import 语句后添加
    lines = content.split('\\n')
    last_import_idx = -1
    for i, line in enumerate(lines):
        if line.startswith('import '):
            last_import_idx = i
    
    if last_import_idx >= 0:
        lines.insert(last_import_idx + 1, import_line)
        content = '\\n'.join(lines)
        print("  ✅ 添加导入语句")

# 2. 在合适位置添加组件（在 capex 输入后）
# 找到 capex 或系统造价的输入框，在其后添加

old_capex_section = '''        <NumberInput
          label="系统造价 (元/Wh)"
          tooltip="储能系统单位造价，含设备、建安、调试等"
          value={inputs.capex}
          min={0.5}
          max={3.0}
          step={0.05}
          onChange={(v) => updateInput('capex', v)}
        />'''

new_capex_section = '''        <NumberInput
          label="系统造价 (元/Wh)"
          tooltip="储能系统单位造价，含设备、建安、调试等"
          value={inputs.capex}
          min={0.5}
          max={3.0}
          step={0.05}
          onChange={(v) => updateInput('capex', v)}
        />
        
        {/* 投资明细（可选） */}
        <InvestmentBreakdown
          items={inputs.investmentItems || []}
          constructionPeriod={inputs.constructionPeriod || 12}
          capacity={inputs.capacity}
          onChange={(items, period) => {
            updateInput('investmentItems', items);
            updateInput('constructionPeriod', period);
            // 如果有明细，同步更新 capex（用于显示）
            if (items.length > 0) {
              const total = items.reduce((sum, item) => sum + (item.amount || 0), 0);
              const capexPerWh = (total * 10000) / (inputs.capacity * 1000000);
              updateInput('capex', capexPerWh);
            }
          }}
        />'''

if old_capex_section in content:
    content = content.replace(old_capex_section, new_capex_section)
    print("  ✅ 添加 InvestmentBreakdown 组件")
else:
    print("  ⚠️  未找到 capex 输入框，请手动添加组件")

with open('src/components/InputPanel.tsx', 'w') as f:
    f.write(content)

print("✅ InputPanel 修改完成！")
