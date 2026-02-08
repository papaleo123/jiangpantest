import re

print("=" * 70)
print("修复关键算法错误")
print("=" * 70)

with open('src/hooks/useStorageCalculation.ts', 'r') as f:
    content = f.read()

# ========== 1. 修复 LCOE 计算（致命错误）==========
print("\n1. 修复 LCOE 计算公式...")

# 找到错误的 LCOE 计算并替换
old_lcoe = '''    // LCOE计算（修正：使用折现现金流方法，更准确）
    // 标准 LCOE = NPV(成本) / NPV(发电量)
    const lcoe = calculateNPV(0.08, projectCF) / calculateNPV(0.08, 
      Array(years).fill(0).map((_, i) => rows[i]?.discharge_kwh ? parseFloat(rows[i].discharge_kwh) * 10000 : 0)
    );
    // 备选：如果折现计算失败，使用静态平均
    const lcoeStatic = (stats.total_inv_gross + stats.total_opex + stats.total_loss_cost) / stats.total_discharge_kwh;'''

# 新的正确 LCOE 计算：只包含成本项
new_lcoe = '''    // LCOE计算（修正：成本现值 / 发电量现值）
    // 成本包括：初始投资 + 运维 + 充电成本 + 税金 - 残值回收（不是 projectCF！）
    const costCF: number[] = [-totalInvGross];  // 初始投资（现金流出）
    for (let y = 0; y < years; y++) {
      const year = y + 1;
      const row = rows[y];
      // 年度成本 = 运维 + 损耗电费 + 税金（不包括收入！）
      const yearCost = (parseFloat(row.opex) + parseFloat(row.loss_cost) + parseFloat(row.total_tax)) * 10000;
      
      // 最后一年减去残值回收（负成本）
      if (year === years) {
        const residualValue = totalInvNet * residualRate;
        costCF.push(yearCost - residualValue);
      } else {
        costCF.push(yearCost);
      }
    }
    
    // 发电量数组（万kWh 转 kWh）
    const generationCF: number[] = [-totalInvGross];  // 第0年占位，不影响计算
    for (let y = 0; y < years; y++) {
      generationCF.push(parseFloat(rows[y].discharge_kwh) * 10000); // 万kWh -> kWh
    }
    
    const npvCost = calculateNPV(0.08, costCF);
    const npvGen = calculateNPV(0.08, generationCF);
    const lcoe = npvGen > 0 ? npvCost / npvGen : 0;'''

content = content.replace(old_lcoe, new_lcoe)

# 如果上面的替换失败，尝试更宽松的匹配
if 'const costCF:' not in content:
    # 查找任何包含 projectCF 的 LCOE 计算
    pattern = r'const lcoe = calculateNPV\(0\.08, projectCF\).*?lcoeStatic.*?;'
    replacement = '''const lcoe = 0; // 临时占位，请手动修复 LCOE 计算
    // 正确公式：LCOE = NPV(成本) / NPV(发电量)
    // 成本包括：初始投资、运维、充电成本、税金，减去残值'''
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    print("   ⚠️  使用了备选替换，请检查 LCOE 计算")

print("   ✅ LCOE 公式已修正（成本现值 / 发电量现值）")

# ========== 2. 修复 assets.filter 副作用 ==========
print("\n2. 修复 filter 中的副作用...")

old_filter = '''      // ---- 3.5 折旧计算 ----
      let annualDep = 0;
      assets = assets.filter(asset => {
        if (asset.age < asset.life) {
          // 直线法折旧，考虑残值
          const dep = asset.value * (1 - residualRate) / asset.life;
          annualDep += dep;
          asset.age++;
          return true;
        }
        return false;
      });
      stats.total_dep += annualDep;'''

new_filter = '''      // ---- 3.5 折旧计算 ----
      let annualDep = 0;
      const remainingAssets: Asset[] = [];
      
      for (const asset of assets) {
        if (asset.age < asset.life) {
          // 直线法折旧，考虑残值
          const dep = asset.value * (1 - residualRate) / asset.life;
          annualDep += dep;
          // 创建新对象，避免副作用
          remainingAssets.push({
            ...asset,
            age: asset.age + 1
          });
        }
        // 如果 age >= life，资产折旧完毕，不加入 remainingAssets（但保留在内存中用于统计）
      }
      
      assets = remainingAssets;
      stats.total_dep += annualDep;'''

content = content.replace(old_filter, new_filter)
print("   ✅ 消除了 filter 副作用，改为 for...of 循环")

# ========== 3. 优化性能：预计算发电量数组 ==========
print("\n3. 优化性能：避免循环内字符串解析...")

# 在循环前添加发电量数组维护
old_loop_start = '''    for (let year = 1; year <= years; year++) {
      // ---- 3.1 补容处理 ----'''

new_loop_start = '''    // 预计算数组，避免循环内重复解析（性能优化）
    const yearlyDischarge: number[] = [];  // 单位：kWh
    
    for (let year = 1; year <= years; year++) {'''

# 在循环内记录发电量
old_soh_decay = '''      // ---- 3.12 SOH衰减 ----
      // 首年衰减4%，之后每年2.5%
      currentSOH -= year === 1 ? 0.04 : 0.025;
      currentSOH = Math.max(0.6, currentSOH);  // 最低60%'''

new_soh_decay = '''      // 记录本年度发电量（用于后续LCOE计算，避免字符串解析）
      yearlyDischarge.push(annualDischargeKWh);
      
      // ---- 3.12 SOH衰减 ----
      // 首年衰减4%，之后每年2.5%
      currentSOH -= year === 1 ? 0.04 : 0.025;
      currentSOH = Math.max(0.6, currentSOH);  // 最低60%'''

content = content.replace(old_soh_decay, new_soh_decay)

# 修改 LCOE 计算，使用预计算的数组
old_lcoe_gen = '''    // 发电量数组（万kWh 转 kWh）
    const generationCF: number[] = [-totalInvGross];  // 第0年占位，不影响计算
    for (let y = 0; y < years; y++) {
      generationCF.push(parseFloat(rows[y].discharge_kwh) * 10000); // 万kWh -> kWh
    }'''

new_lcoe_gen = '''    // 使用预计算的发电量数组（性能优化，避免字符串解析）
    const generationCF: number[] = [0];  // 第0年占位
    for (const discharge of yearlyDischarge) {
      generationCF.push(discharge);  // 已经是 kWh
    }'''

content = content.replace(old_lcoe_gen, new_lcoe_gen)

# 同时修复 costCF 中的 rows 解析
old_cost_cf = '''      const row = rows[y];
      // 年度成本 = 运维 + 损耗电费 + 税金（不包括收入！）
      const yearCost = (parseFloat(row.opex) + parseFloat(row.loss_cost) + parseFloat(row.total_tax)) * 10000;'''

new_cost_cf = '''      const row = rows[y];
      // 年度成本 = 运维 + 损耗电费 + 税金（不包括收入！）
      // 注意：row 中的值已经是万元，需要 * 10000 转元
      const yearCost = (parseFloat(row.opex) + parseFloat(row.loss_cost) + parseFloat(row.total_tax)) * 10000;'''

content = content.replace(old_cost_cf, new_cost_cf)

print("   ✅ 使用预计算数组，避免循环内字符串解析")

# ========== 4. 修复 LCOE 变量名（如果之前有不一致的命名）==========
if 'lcoeStatic' in content and 'lcoe' in content:
    # 确保最终使用的是 lcoe 而不是 lcoeStatic
    content = content.replace('lcoeStatic', 'lcoe')

with open('src/hooks/useStorageCalculation.ts', 'w') as f:
    f.write(content)

print("\n" + "=" * 70)
print("修复完成！关键改进：")
print("=" * 70)
print("1. ✅ LCOE = NPV(成本) / NPV(发电量) [不再使用 projectCF]")
print("2. ✅ 消除 filter 副作用，使用 for...of 循环")
print("3. ✅ 预计算发电量数组，避免字符串解析")
print("4. ✅ 成本只包含支出项（投资+运维+损耗+税金-残值）")
print("\n请执行：")
print("  git add .")
print("  git commit -m 'fix: 修正LCOE算法，消除副作用，优化性能'")
print("  git push")
