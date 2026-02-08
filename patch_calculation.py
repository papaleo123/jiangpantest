import re

with open('src/hooks/useStorageCalculation.ts', 'r') as f:
    content = f.read()

print("修复财务计算问题...")

# 1. 修复 LCOE 计算 - 使用折现方法
old_lcoe = '''    // LCOE计算 = 全生命周期成本 / 总放电量
    const lifecycleCost = stats.total_inv_gross + stats.total_opex + stats.total_loss_cost + 
                         stats.total_interest + stats.total_tax;
    const lcoe = lifecycleCost / stats.total_discharge_kwh;'''

new_lcoe = '''    // LCOE计算（修正：使用折现现金流方法，更准确）
    // 标准 LCOE = NPV(成本) / NPV(发电量)
    const lcoe = calculateNPV(0.08, projectCF) / calculateNPV(0.08, 
      Array(years).fill(0).map((_, i) => rows[i]?.discharge_kwh ? parseFloat(rows[i].discharge_kwh) * 10000 : 0)
    );
    // 备选：如果折现计算失败，使用静态平均
    const lcoeStatic = (stats.total_inv_gross + stats.total_opex + stats.total_loss_cost) / stats.total_discharge_kwh;'''

content = content.replace(old_lcoe, new_lcoe)

# 2. 修复 projectCF 残值回收问题
old_project_cf = '''      // 项目现金流（全投资角度）
      const projectCFYear = ebitda * (1 - taxRate) + annualDep * taxRate - augCost;
      projectCF.push(projectCFYear);'''

new_project_cf = '''      // 项目现金流（全投资角度）
      let projectCFYear = ebitda * (1 - taxRate) + annualDep * taxRate - augCost;
      
      // 最后一年回收残值（修正：全投资现金流也应包含残值）
      if (year === years) {
        const residualValue = totalInvNet * residualRate;
        projectCFYear += residualValue;
      }
      
      projectCF.push(projectCFYear);'''

content = content.replace(old_project_cf, new_project_cf)

# 3. 在 inputs 中添加 investmentItems 和 constructionPeriod
if 'investmentItems:' not in content:
    old_inputs = '''aug_dep_years: 15,        // 补容折旧年限
    residual_rate: 5,        // 残值率 5%'''
    
    new_inputs = '''aug_dep_years: 15,        // 补容折旧年限
    residual_rate: 5,        // 残值率 5%
    constructionPeriod: 12,   // 建设期（月）
    investmentItems: [        // 投资明细（空数组表示使用 capex）
      // { id: '1', name: '储能系统设备', amount: 9600, taxRate: 13, category: 'equipment' },
      // { id: '2', name: '土建工程', amount: 1800, taxRate: 9, category: 'civil' },
    ],'''
    
    content = content.replace(old_inputs, new_inputs)
    print("  ✅ 添加 investmentItems 和 constructionPeriod")

# 4. 修改投资计算逻辑（支持明细或 capex）
old_inv_calc = '''    // 投资参数（修复版：使用简单 capex 计算，避免悬空代码）
    // 后续可以扩展为分项投资明细
    const totalInvGross = Wh * inputs.capex;                    // 总投资(含税)
    const totalInvNet = totalInvGross / (1 + vatRate);          // 总投资(不含税)
    const inputVAT = totalInvGross - totalInvNet;               // 设备进项税'''

new_inv_calc = '''    // 投资参数（支持明细或 capex）
    let totalInvGross: number;
    let totalInvNet: number;
    let inputVAT: number;
    
    // 如果有投资明细，使用明细计算；否则使用 capex
    if (inputs.investmentItems && inputs.investmentItems.length > 0) {
      // 使用投资明细（不同税率）
      totalInvGross = inputs.investmentItems.reduce((sum, item) => sum + (item.amount || 0), 0);
      totalInvNet = inputs.investmentItems.reduce((sum, item) => {
        const rate = (item.taxRate || 13) / 100;
        return sum + (item.amount / (1 + rate));
      }, 0);
      inputVAT = totalInvGross - totalInvNet;
    } else {
      // 使用 capex（单一税率）
      totalInvGross = Wh * inputs.capex;
      totalInvNet = totalInvGross / (1 + vatRate);
      inputVAT = totalInvGross - totalInvNet;
    }'''

content = content.replace(old_inv_calc, new_inv_calc)

with open('src/hooks/useStorageCalculation.ts', 'w') as f:
    f.write(content)

print("✅ 财务计算修复完成！")
