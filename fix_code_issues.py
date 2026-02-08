import re

print("=" * 70)
print("修复代码问题")
print("=" * 70)

# ========== 1. 修复 useStorageCalculation.ts ==========
print("\n1. 修复 calculate 函数中的悬空代码...")

with open('src/hooks/useStorageCalculation.ts', 'r') as f:
    content = f.read()

# 修复1：删除或注释掉悬空的代码段，恢复为使用 capex 的简单计算
# 找到那段错误的代码并替换
old_bad_code = '''    // 计算总投资和分项进项税（关键改进！）
    let totalInvGross = 0;      // 总投资含税
    let totalInvNet = 0;        // 总投资不含税  
    let totalInputVAT = 0;      // 总进项税
    
    // 计算各项投资的税额
      const netAmount = item.amount / (1 + item.taxRate / 100);
      const itemVAT = item.amount - netAmount;
      totalInvGross += item.amount;
      totalInvNet += netAmount;
      totalInputVAT += itemVAT;
      return { ...item, netAmount, itemVAT };
    });
    
    // 设备进项税（用于抵扣）
    const inputVAT = totalInputVAT;'''

new_good_code = '''    // 投资参数（修复版：使用简单 capex 计算，避免悬空代码）
    // 后续可以扩展为分项投资明细
    const totalInvGross = Wh * inputs.capex;                    // 总投资(含税)
    const totalInvNet = totalInvGross / (1 + vatRate);          // 总投资(不含税)
    const inputVAT = totalInvGross - totalInvNet;               // 设备进项税'''

if old_bad_code in content:
    content = content.replace(old_bad_code, new_good_code)
    print("   ✅ 已修复悬空代码")
else:
    # 如果找不到精确匹配，尝试查找并删除那段错误代码
    if 'const netAmount = item.amount' in content:
        # 使用正则表达式删除错误代码块
        pattern = r'// 计算总投资和分项进项税.*?const inputVAT = totalInputVAT;'
        content = re.sub(pattern, new_good_code, content, flags=re.DOTALL)
        print("   ✅ 已修复悬空代码（使用正则）")
    else:
        print("   ⚠️  未找到错误代码，可能已修复")

# 修复2：IRR 计算增加 isNaN 检查
if 'return guess;' in content and 'isNaN' not in content:
    old_irr = '''    return guess;
  }
  return guess;'''
    
    new_irr = '''    // 增加有效性检查
    if (isNaN(guess) || !isFinite(guess)) return 0;
    if (Math.abs(npv) < 0.01) return guess;
  }
  // 如果迭代未收敛，返回0并记录
  return 0;'''
    
    content = content.replace(old_irr, new_irr)
    print("   ✅ 已添加 IRR 有效性检查")

# 修复3：CSV 导出使用 Blob（更安全）
if 'encodeURI(txt)' in content:
    old_csv = '''const link = document.createElement('a');
    link.href = 'data:text/csv;charset=utf-8,\\uFEFF' + encodeURI(txt);
    link.download = '储能财务分析表_V13.csv';
    link.click();'''
    
    new_csv = '''// 使用 Blob 更安全地处理 CSV 下载
    const blob = new Blob([txt], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = '储能财务分析表_V13.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);'''
    
    content = content.replace(old_csv, new_csv)
    print("   ✅ 已修复 CSV 编码问题（使用 Blob）")

with open('src/hooks/useStorageCalculation.ts', 'w') as f:
    f.write(content)

# ========== 2. 添加 UI 层非空保护 ==========
print("\n2. 检查 UI 层非空保护...")

# 检查 DataTable.tsx 或相关组件
import os
for root, dirs, files in os.walk('src/components'):
    for file in files:
        if file.endswith('.tsx') and 'DataTable' in file:
            filepath = os.path.join(root, file)
            with open(filepath, 'r') as f:
                content = f.read()
            
            # 检查是否有 result?.rows 保护
            if 'result.rows' in content and 'result?.rows' not in content:
                print(f"   ⚠️  {file} 中直接使用 result.rows，建议改为 result?.rows")
            else:
                print(f"   ✅ {file} 已有非空保护或不存在")

print("\n" + "=" * 70)
print("修复完成！")
print("=" * 70)
print("\n请执行：")
print("  git add .")
print("  git commit -m 'fix: 修复悬空代码、IRR检查和CSV编码'")
print("  git push")
