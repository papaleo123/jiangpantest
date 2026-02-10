import os
import re

def fix_input_panel_layout():
    target_file = 'src/components/InputPanel.tsx'
    
    if not os.path.exists(target_file):
        print(f"❌ 错误: 找不到文件 {target_file}")
        return

    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 修复双输入框太窄的问题 (贷款、税务、补容)
    # 查找: w-[100px] md:w-[115px] 且带有 flex gap-2 的容器
    # 替换为: w-[170px] md:w-[200px] 让两个框有足够空间
    
    # 原始 CSS 特征片段
    narrow_dual_container = 'className="flex gap-2 w-[100px] md:w-[115px]"'
    # 新的宽容器 CSS
    wide_dual_container = 'className="flex gap-2 w-[170px] md:w-[200px]"'
    
    if narrow_dual_container in content:
        content = content.replace(narrow_dual_container, wide_dual_container)
        print("✅ 已修复: 加宽了'贷款/税务/补容'的双输入框容器")
    else:
        print("ℹ️ 提示: 未找到窄双输入框代码，可能已经修复过？")

    # 2. 修复 '日循环次数' 和 '年运行天数' 在手机上挤在一起的问题
    # 查找: grid grid-cols-2 gap-2
    # 替换为: grid grid-cols-1 sm:grid-cols-2 gap-2 (手机单列，平板以上双列)
    
    grid_pattern = 'className="grid grid-cols-2 gap-2"'
    responsive_grid = 'className="grid grid-cols-1 sm:grid-cols-2 gap-2"'
    
    if grid_pattern in content:
        content = content.replace(grid_pattern, responsive_grid)
        print("✅ 已修复: '日循环次数/年运行天数' 现在会在手机端自动换行")
    else:
        print("ℹ️ 提示: 未找到 Grid 布局代码，可能已修复")

    # 3. 微调：如果某些单行输入框在新的宽容器下显得太宽，保持 InputGroup 不变
    # 注意：InputGroup 使用的是 "w-[100px] md:w-[115px]" (没有 flex gap-2)
    # 所以上面的替换不会影响普通的单行输入框，这是我们想要的。

    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("\n🚀 布局修复完成！")
    print("👉 请运行 'npm run dev' 查看效果。")
    print("   1. 贷款、税务那一栏现在应该能清楚看到数字了。")
    print("   2. 循环次数那一行在手机上应该会变成上下两行，不再拥挤。")

if __name__ == "__main__":
    fix_input_panel_layout()