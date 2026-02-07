import os
import re

def patch_kpi_cards():
    target_file = 'src/components/KpiCards.tsx'
    if not os.path.exists(target_file):
        print(f"❌ 找不到文件: {target_file}")
        return False

    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 修改接口定义，增加 stats 属性
    # 查找 interface KpiCardsProps
    if 'stats?: any;' not in content:
        content = re.sub(
            r'interface KpiCardsProps \{([^}]+)\}',
            r'interface KpiCardsProps {\1  stats?: any;\n}',
            content
        )
        print("✅ [KpiCards] 接口已更新，增加 stats 支持")

    # 2. 修改“总放电量”的取值逻辑
    # 目标：优先从 stats.total_discharge_kwh 取值，并除以 10000 换算成“万”
    # 原逻辑可能是 (kpi as any)?.total_discharge
    discharge_logic = r'value=\{safeFormat\(\(kpi as any\)\?\.total_discharge, 0\)\}'
    new_discharge_logic = r'value={safeFormat((stats?.total_discharge_kwh || 0) / 10000, 0)}'
    
    if re.search(discharge_logic, content):
        content = re.sub(discharge_logic, new_discharge_logic, content)
        print("✅ [KpiCards] 总放电量取值逻辑已修正 (自动 /10000)")

    # 3. 修改“总投资”的取值逻辑
    # 目标：优先从 stats.total_inv_gross 取值，并除以 10000
    inv_logic = r'value=\{safeFormat\(\(kpi as any\)\?\.total_inv, 0\)\}'
    new_inv_logic = r'value={safeFormat((stats?.total_inv_gross || 0) / 10000, 0)}'
    
    if re.search(inv_logic, content):
        content = re.sub(inv_logic, new_inv_logic, content)
        print("✅ [KpiCards] 总投资取值逻辑已修正 (自动 /10000)")

    # 4. 解构 props 时加上 stats
    # 查找 function KpiCards({ kpi }: KpiCardsProps)
    if 'stats' not in content and 'function KpiCards' in content:
        content = content.replace(
            'function KpiCards({ kpi }: KpiCardsProps)', 
            'function KpiCards({ kpi, stats }: KpiCardsProps)'
        )

    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(content)
    return True

def patch_app_usage():
    # 尝试在常见的入口文件中寻找 KpiCards 的调用
    possible_files = ['src/App.tsx', 'src/Main.tsx', 'src/pages/Dashboard.tsx', 'src/pages/Home.tsx']
    target_file = None
    
    for p in possible_files:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                if 'KpiCards' in f.read():
                    target_file = p
                    break
    
    if not target_file:
        print("⚠️ 未找到调用 KpiCards 的父组件文件，请手动检查 App.tsx")
        return

    print(f"🔎 正在修补父组件: {target_file}")
    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 智能替换：查找 <KpiCards kpi={result.kpi} /> 这一类的写法
    # 并自动追加 stats={result.stats}
    # 正则逻辑：找到 kpi={变量.kpi}，提取变量名，然后追加 stats={变量.stats}
    
    def replacer(match):
        full_tag = match.group(0)
        variable_ref = match.group(1) # 例如 result.kpi 中的 result
        
        # 如果已经有 stats 了，就不加了
        if 'stats=' in full_tag:
            return full_tag
            
        base_var = variable_ref.split('.kpi')[0] # 提取 result
        return f'<KpiCards kpi={{{variable_ref}}} stats={{{base_var}.stats}} />'

    # 匹配模式：kpi={result.kpi} 或 kpi={data.kpi}
    pattern = r'<KpiCards[^>]*kpi=\{([^}]+)\}[^>]*/>'
    
    if re.search(pattern, content):
        new_content = re.sub(pattern, replacer, content)
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ 已在 {target_file} 中注入 stats 数据流")
    else:
        print("⚠️ 没找到标准的 <KpiCards kpi={...} /> 调用，可能需要你手动修改 App.tsx")

if __name__ == "__main__":
    if patch_kpi_cards():
        patch_app_usage()
    print("\n🚀 修复完成！请运行 'npm run dev' 验证最后两个卡片是否显示数据。")