import re
import os

print("=" * 60)
print("开始修复：添加补容折旧年限设置")
print("=" * 60)

# ========== 1. 修改 types/index.ts ==========
print("\n1. 修改 types/index.ts...")

with open('src/types/index.ts', 'r') as f:
    content = f.read()

# 查找 InputParams 接口，添加 aug_dep_years
if 'aug_dep_years' not in content:
    # 在 aug_price 后添加 aug_dep_years
    content = content.replace(
        'aug_price: number;',
        'aug_price: number;\n  aug_dep_years: number;'
    )
    
    with open('src/types/index.ts', 'w') as f:
        f.write(content)
    print("   ✅ 已添加 aug_dep_years 字段")
else:
    print("   ⚠️  字段已存在，跳过")

# ========== 2. 修改 useStorageCalculation.ts ==========
print("\n2. 修改 useStorageCalculation.ts...")

with open('src/hooks/useStorageCalculation.ts', 'r') as f:
    content = f.read()

# 2.1 修改默认值，添加 aug_dep_years: 15
if 'aug_dep_years: 15' not in content and 'aug_dep_years:' not in content:
    content = content.replace(
        'aug_price: 0.6,          // 补容单价',
        'aug_price: 0.6,          // 补容单价\n    aug_dep_years: 15,        // 补容折旧年限'
    )
    print("   ✅ 已添加 aug_dep_years 默认值")

# 2.2 修改折旧计算逻辑
if 'Math.max(1, inputs.dep_years - year + 1)' in content:
    content = content.replace(
        'life: Math.max(1, inputs.dep_years - year + 1),',
        'life: inputs.aug_dep_years,'
    )
    print("   ✅ 已修改折旧年限计算逻辑")
else:
    print("   ⚠️  折旧逻辑已修改或不存在")

with open('src/hooks/useStorageCalculation.ts', 'w') as f:
    f.write(content)

# ========== 3. 修改 InputPanel.tsx ==========
print("\n3. 修改 InputPanel.tsx...")

with open('src/components/InputPanel.tsx', 'r') as f:
    content = f.read()

# 查找补容单价输入框的位置，在其后添加补容折旧年限
if 'aug_dep_years' not in content:
    # 查找补容单价的输入框模式
    pattern = r'(label="补容单价.*?tooltip=".*?".*?value=\{inputs\.aug_price\}.*?(?:onChange|onBlur).*?(\s+\}))'
    
    match = re.search(pattern, content, re.DOTALL)
    if match:
        # 在匹配到的闭合标签后添加新的输入框
        old_section = match.group(0)
        
        new_input = '''          <NumberInput
            label="补容折旧年限 (年)"
            tooltip="补容设备的折旧年限，通常与初始投资相同"
            value={inputs.aug_dep_years}
            min={1}
            max={30}
            onChange={(v) => {
              updateInput('aug_dep_years', v);
              if (v > 0 && inputs.aug_year > 0) {
                setTimeout(calculate, 0);
              }
            }}
          />'''
        
        # 在匹配到的最后一个 } 后面添加
        insert_pos = match.end()
        content = content[:insert_pos] + '\n' + new_input + content[insert_pos:]
        
        with open('src/components/InputPanel.tsx', 'w') as f:
            f.write(content)
        print("   ✅ 已添加补容折旧年限输入框")
    else:
        print("   ❌ 未找到补容单价输入框，请手动添加")
else:
    print("   ⚠️  输入框已存在，跳过")

print("\n" + "=" * 60)
print("修复完成！")
print("=" * 60)
print("\n请执行以下命令提交：")
print("  git add .")
print("  git commit -m 'feat: 添加补容折旧年限设置'")
print("  git push")
