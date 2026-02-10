import os

def fix_types_ts():
    """
    修复 src/types.ts:
    1. 添加 InvestmentItem 接口定义
    2. 在 InputParams 中添加 constructionPeriod 和 investmentItems 字段
    """
    file_path = os.path.join('src', 'types.ts')
    if not os.path.exists(file_path):
        print(f"❌ 未找到文件: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 添加 InvestmentItem 接口 (如果不存在)
    if 'interface InvestmentItem' not in content:
        print(f"正在修复 {file_path}: 添加 InvestmentItem 接口...")
        interface_def = """export interface InvestmentItem {
  id: string;
  name: string;
  amount: number;
  taxRate: number;
  category: string;
}

"""
        content = interface_def + content

    # 2. 添加 InputParams 缺失字段
    if 'constructionPeriod' not in content:
        print(f"正在修复 {file_path}: 为 InputParams 添加缺失字段...")
        # 尝试在 residual_rate 后面添加 (这是一个较安全的定位点)
        if 'residual_rate: number;' in content:
            content = content.replace(
                'residual_rate: number;', 
                'residual_rate: number;\n  constructionPeriod: number;\n  investmentItems?: InvestmentItem[];'
            )
        # 如果没找到分号结尾，尝试换行符 (兼容性处理)
        elif 'residual_rate: number' in content:
             content = content.replace(
                'residual_rate: number', 
                'residual_rate: number;\n  constructionPeriod: number;\n  investmentItems?: InvestmentItem[];'
            )
        else:
            print(f"⚠️ 警告: 无法自动定位插入点，请手动在 {file_path} 的 InputParams 中添加 constructionPeriod 和 investmentItems。")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ {file_path} 修复完成")

def fix_calculation_hook():
    """
    修复 src/hooks/useStorageCalculation.ts:
    1. 初始化 yearlyDischarge 变量
    2. 在循环中填充 yearlyDischarge 数据
    """
    file_path = os.path.join('src', 'hooks', 'useStorageCalculation.ts')
    if not os.path.exists(file_path):
        print(f"❌ 未找到文件: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    modified = False

    # 1. 初始化变量
    if 'const yearlyDischarge: number[]' not in content:
        print(f"正在修复 {file_path}: 初始化 yearlyDischarge...")
        target = 'const rows: YearlyRow[] = [];'
        injection = '\n    const yearlyDischarge: number[] = [0]; // 修复LCOE计算: 初始化发电量数组'
        if target in content:
            content = content.replace(target, target + injection)
            modified = True

    # 2. 填充数据
    if 'yearlyDischarge.push(annualDischargeKWh)' not in content:
        print(f"正在修复 {file_path}: 填充循环数据...")
        target = 'stats.total_loss_kwh += lossKWh;'
        injection = '\n      yearlyDischarge.push(annualDischargeKWh); // 修复LCOE计算: 记录年发电量'
        if target in content:
            content = content.replace(target, target + injection)
            modified = True

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ {file_path} 修复完成")
    else:
        print(f"ℹ️ {file_path} 似乎已经包含修复内容，跳过。")

def fix_input_panel():
    """
    修复 src/components/InputPanel.tsx:
    1. 删除顶部未使用的 import
    2. 删除文件末尾的错误代码
    """
    file_path = os.path.join('src', 'components', 'InputPanel.tsx')
    if not os.path.exists(file_path):
        print(f"❌ 未找到文件: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    removed_count = 0
    
    for line in lines:
        # 删除包含 InvestmentBreakdown 的 import 行 (无论是顶部还是底部)
        if "from './InvestmentBreakdown'" in line or 'import { InvestmentBreakdown' in line:
            removed_count += 1
            continue
        new_lines.append(line)

    if removed_count > 0:
        print(f"正在修复 {file_path}: 删除了 {removed_count} 行错误代码...")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"✅ {file_path} 修复完成")
    else:
        print(f"ℹ️ {file_path} 未发现需要清理的代码。")

if __name__ == "__main__":
    print("🚀 开始自动修复项目文件...")
    fix_types_ts()
    fix_calculation_hook()
    fix_input_panel()
    print("✨ 所有修复步骤执行完毕。请尝试重新 npm run build。")