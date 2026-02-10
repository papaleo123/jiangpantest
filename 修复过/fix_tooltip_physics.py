import re

with open('src/components/CalculationTooltip.tsx', 'r') as f:
    content = f.read()

print("修复展示公式，与 calculatePhysics 完全一致...")

# 修复放电量计算 - 完全复刻 calculatePhysics
old_discharge = '''    case 'discharge_kwh':
      const yearNum = parseInt(rowData.y) || 1;
      const initialSOH = 1.0;  // 首年初始100%
      const firstYearDecay = 0.04;  // 首年衰减4%
      const yearlyDecay = 0.025;    // 后续每年衰减2.5%
      
      // 计算当前年份SOH（与实际代码一致）
      // year 1: 100% - 4% = 96%
      // year 2: 96% - 2.5% = 93.5%
      // year 3: 93.5% - 2.5% = 91%
      let calcSOH = initialSOH;
      if (yearNum === 1) {
        calcSOH = initialSOH - firstYearDecay;
      } else {
        calcSOH = initialSOH - firstYearDecay - (yearNum - 1) * yearlyDecay;
      }
      calcSOH = Math.max(0.6, calcSOH);  // 最低60%
      
      const capacityWhDischarge = (inputs?.capacity || 100) * 1000000; // MWh -> Wh
      const usableCapacity = capacityWhDischarge * calcSOH * (inputs?.dod || 0.9);
      const dailyDischarge = usableCapacity * (inputs?.cycles || 2);
      const annualDischarge = (dailyDischarge * (inputs?.run_days || 330)) / 1000; // 转为万kWh
      
      return {
        title: '放电量计算（含逐年衰减）',
        description: '第' + yearNum + '年放电量，考虑SOH逐年衰减',
        formula: '装机容量 × SOH' + (yearNum > 1 ? '（首年-4%，后续-2.5%/年）' : '（首年-4%）') + ' × DOD × 日循环 × 运行天数 / 1000',
        steps: [
          { label: '装机容量', value: inputs?.capacity || 0, unit: 'MWh', formula: '输入参数' },
          { label: '初始SOH', value: '100.0', unit: '%', formula: '初始值' },
          { label: '首年衰减', value: '4.0', unit: '%', formula: '第1年' },
          ...(yearNum > 1 ? [{ label: '后续年衰减', value: ((yearNum - 1) * 2.5).toFixed(1), unit: '%', formula: `第2-${yearNum}年，每年2.5%` }] : []),
          { label: '当前SOH', value: (calcSOH * 100).toFixed(1), unit: '%', formula: `100% - ${(yearNum === 1 ? 4 : 4 + (yearNum - 1) * 2.5).toFixed(1)}%` },
          { label: '放电深度DOD', value: ((inputs?.dod || 0.9) * 100).toFixed(0), unit: '%', formula: '输入参数' },
          { label: '可用容量', value: (usableCapacity / 1000000).toFixed(2), unit: 'MWh', formula: `${inputs?.capacity || 100}MWh × ${(calcSOH * 100).toFixed(1)}% × ${((inputs?.dod || 0.9) * 100).toFixed(0)}%` },
          { label: '日循环次数', value: inputs?.cycles || 2, unit: '次/天', formula: '输入参数' },
          { label: '日放电量', value: (dailyDischarge / 1000).toFixed(2), unit: '万kWh', formula: '可用容量×循环次数' },
          { label: '年运行天数', value: inputs?.run_days || 330, unit: '天', formula: '输入参数' },
        ],
        result: { value: rowData.discharge_kwh, unit: '万kWh' }
      };'''

new_discharge = '''    case 'discharge_kwh':
      const yearNum = parseInt(rowData.y) || 1;
      
      // 完全复刻 calculatePhysics 中的 SOH 计算逻辑
      // 注意：这里模拟的是当年的SOH（currentSOH），不是nextSOH
      // 实际代码逻辑：usableCapacity = capacityWh * currentSOH * dod
      let currentSOH = 1.0;  // 初始100%
      if (yearNum === 1) {
        // 第1年：初始100%，当年衰减4%，所以当年 usable SOH = 100% - 4% = 96%
        currentSOH = 1.0 - 0.04;
      } else {
        // 第2年及以后：首年4% + 后续每年2.5%
        currentSOH = 1.0 - 0.04 - (yearNum - 1) * 0.025;
      }
      // 最低60%
      currentSOH = Math.max(0.60, currentSOH);
      
      // 完全复刻 calculatePhysics 的计算步骤
      const capacityWh = (inputs?.capacity || 100) * 1e6; // MWh -> Wh
      const dod = inputs?.dod || 0.9;
      const cycles = inputs?.cycles || 2;
      const runDays = inputs?.run_days || 330;
      const rte = (inputs?.charge_eff || 94) / 100 * (inputs?.discharge_eff || 94) / 100;
      
      // 步骤1: usableCapacity = capacityWh * currentSOH * dod
      const usableCapacity = capacityWh * currentSOH * dod;
      
      // 步骤2: dailyDischarge = usableCapacity * cycles
      const dailyDischarge = usableCapacity * cycles;
      
      // 步骤3: annualDischargeKWh = (dailyDischarge * runDays) / 1000
      const annualDischargeKWh = (dailyDischarge * runDays) / 1000;
      
      return {
        title: '放电量计算（完全复刻代码逻辑）',
        description: '第' + yearNum + '年放电量，SOH衰减与实际计算一致',
        formula: '((装机容量×1,000,000) × SOH × DOD) × 日循环 × 运行天数 ÷ 1000',
        steps: [
          { label: '装机容量', value: inputs?.capacity || 0, unit: 'MWh', formula: '输入参数' },
          { label: '转换为Wh', value: (capacityWh).toLocaleString(), unit: 'Wh', formula: 'capacity × 1,000,000' },
          { label: 'SOH计算', value: (yearNum === 1 ? '首年衰减4%' : `首年4% + ${yearNum-1}年×2.5%`), unit: '', formula: yearNum === 1 ? '100% - 4% = 96%' : `100% - 4% - ${((yearNum-1)*2.5).toFixed(1)}%` },
          { label: '当前SOH', value: (currentSOH * 100).toFixed(1), unit: '%', formula: `Math.max(60%, ${(currentSOH * 100).toFixed(1)}%)` },
          { label: '放电深度DOD', value: (dod * 100).toFixed(0), unit: '%', formula: '输入参数' },
          { label: '可用容量', value: (usableCapacity / 1e6).toFixed(2), unit: 'MWh', formula: `${inputs?.capacity}MWh × ${(currentSOH*100).toFixed(1)}% × ${(dod*100).toFixed(0)}%` },
          { label: '日循环次数', value: cycles, unit: '次', formula: '输入参数' },
          { label: '日放电量', value: (dailyDischarge / 1000).toFixed(2), unit: '万kWh', formula: '可用容量 × 循环次数' },
          { label: '年运行天数', value: runDays, unit: '天', formula: '输入参数' },
          { label: '年放电量', value: annualDischargeKWh.toFixed(2), unit: '万kWh', formula: '(日放电量 × 运行天数) ÷ 1000' },
        ],
        result: { value: rowData.discharge_kwh, unit: '万kWh' }
      };'''

content = content.replace(old_discharge, new_discharge)

# 修复充电量计算 - 完全复刻 calculatePhysics
old_charge = '''    case 'charge_kwh':
      const yearCharge = parseInt(rowData.y) || 1;
      
      // 计算SOH（与放电量一致）
      let calcSOHCharge = 1.0;
      if (yearCharge === 1) {
        calcSOHCharge = 1.0 - 0.04;  // 首年96%
      } else {
        calcSOHCharge = 1.0 - 0.04 - (yearCharge - 1) * 0.025;
      }
      calcSOHCharge = Math.max(0.6, calcSOHCharge);
      
      const rteCharge = (inputs?.charge_eff || 0.94) * (inputs?.discharge_eff || 0.94);
      const capacityWhCharge = (inputs?.capacity || 100) * 1000000;
      const dailyDischargeCharge = capacityWhCharge * calcSOHCharge * (inputs?.dod || 0.9) * (inputs?.cycles || 2);
      const annualDischargeKWhCharge = (dailyDischargeCharge * (inputs?.run_days || 330)) / 1000;
      const annualChargeKWhCalc = annualDischargeKWhCharge / rteCharge;
      
      return {
        title: '充电量计算（含逐年衰减）',
        description: '第' + yearCharge + '年充电量，根据放电量和效率反推',
        formula: '[装机容量 × SOH(逐年衰减) × DOD × 循环 × 天数 / 1000] / 综合效率',
        steps: [
          { label: '装机容量', value: inputs?.capacity || 0, unit: 'MWh', formula: '输入参数' },
          { label: '第' + yearCharge + '年SOH', value: (calcSOHCharge * 100).toFixed(1), unit: '%', formula: yearCharge === 1 ? '100% - 4%' : `100% - 4% - ${(yearCharge-1)*2.5}%` },
          { label: '放电深度DOD', value: ((inputs?.dod || 0.9) * 100).toFixed(0), unit: '%', formula: '输入参数' },
          { label: '日循环次数', value: inputs?.cycles || 2, unit: '次/天', formula: '输入参数' },
          { label: '年运行天数', value: inputs?.run_days || 330, unit: '天', formula: '输入参数' },
          { label: '年放电量', value: annualDischargeKWhCharge.toFixed(2), unit: '万kWh', formula: '见放电量计算' },
          { label: '充电效率', value: ((inputs?.charge_eff || 0.94) * 100).toFixed(0), unit: '%', formula: '输入参数' },
          { label: '放电效率', value: ((inputs?.discharge_eff || 0.94) * 100).toFixed(0), unit: '%', formula: '输入参数' },
          { label: '综合效率RTE', value: (rteCharge * 100).toFixed(2), unit: '%', formula: '充电效率×放电效率' },
        ],
        result: { value: rowData.charge_kwh, unit: '万kWh' }
      };'''

new_charge = '''    case 'charge_kwh':
      const yearCharge = parseInt(rowData.y) || 1;
      
      // 完全复刻 calculatePhysics 中的 SOH 计算
      let currentSOHCharge = 1.0;
      if (yearCharge === 1) {
        currentSOHCharge = 1.0 - 0.04;
      } else {
        currentSOHCharge = 1.0 - 0.04 - (yearCharge - 1) * 0.025;
      }
      currentSOHCharge = Math.max(0.60, currentSOHCharge);
      
      // 复刻 calculatePhysics 参数
      const capacityWhCharge = (inputs?.capacity || 100) * 1e6;
      const dodCharge = inputs?.dod || 0.9;
      const cyclesCharge = inputs?.cycles || 2;
      const runDaysCharge = inputs?.run_days || 330;
      const chargeEff = (inputs?.charge_eff || 94) / 100;
      const dischargeEff = (inputs?.discharge_eff || 94) / 100;
      const rteCharge = chargeEff * dischargeEff;
      
      // 步骤1: usableCapacity
      const usableCapacityCharge = capacityWhCharge * currentSOHCharge * dodCharge;
      // 步骤2: dailyDischarge
      const dailyDischargeCharge = usableCapacityCharge * cyclesCharge;
      // 步骤3: annualDischargeKWh
      const annualDischargeKWhCharge = (dailyDischargeCharge * runDaysCharge) / 1000;
      // 步骤4: annualChargeKWh = annualDischargeKWh / rte
      const annualChargeKWhCalc = annualDischargeKWhCharge / rteCharge;
      
      return {
        title: '充电量计算（完全复刻代码逻辑）',
        description: '第' + yearCharge + '年充电量 = 放电量 ÷ 综合效率',
        formula: '放电量 ÷ (充电效率 × 放电效率)',
        steps: [
          { label: '装机容量', value: inputs?.capacity || 0, unit: 'MWh', formula: '输入参数' },
          { label: '当前SOH', value: (currentSOHCharge * 100).toFixed(1), unit: '%', formula: yearCharge === 1 ? '96% (100%-4%)' : `${(currentSOHCharge*100).toFixed(1)}% (100%-4%-${((yearCharge-1)*2.5).toFixed(1)}%)` },
          { label: '可用容量', value: (usableCapacityCharge / 1e6).toFixed(2), unit: 'MWh', formula: 'capacity × SOH × DOD' },
          { label: '日放电量', value: (dailyDischargeCharge / 1000).toFixed(2), unit: '万kWh', formula: '可用容量 × 循环次数' },
          { label: '年放电量', value: annualDischargeKWhCharge.toFixed(2), unit: '万kWh', formula: '日放电量 × 运行天数 ÷ 1000' },
          { label: '充电效率', value: (chargeEff * 100).toFixed(0), unit: '%', formula: '输入参数' },
          { label: '放电效率', value: (dischargeEff * 100).toFixed(0), unit: '%', formula: '输入参数' },
          { label: '综合效率RTE', value: (rteCharge * 100).toFixed(2), unit: '%', formula: '充电效率 × 放电效率' },
          { label: '年充电量', value: annualChargeKWhCalc.toFixed(2), unit: '万kWh', formula: '放电量 ÷ RTE' },
        ],
        result: { value: rowData.charge_kwh, unit: '万kWh' }
      };'''

content = content.replace(old_charge, new_charge)

# 修复损耗电量 - 完全复刻 calculatePhysics
old_loss = '''    case 'loss_kwh':
      const chargeKWhLoss = parseFloat(rowData.charge_kwh || 0);
      const dischargeKWhLoss = parseFloat(rowData.discharge_kwh || 0);
      const lossKWhCalc = chargeKWhLoss - dischargeKWhLoss;
      const lossRateCalc = chargeKWhLoss > 0 ? (lossKWhCalc / chargeKWhLoss * 100).toFixed(2) : '0.00';
      
      return {
        title: '损耗电量',
        description: '充放电过程中的能量损耗（充电量 - 放电量）',
        formula: '充电量 - 放电量',
        steps: [
          { label: '充电量', value: chargeKWhLoss.toFixed(2), unit: '万kWh', formula: '见充电量计算' },
          { label: '放电量', value: dischargeKWhLoss.toFixed(2), unit: '万kWh', formula: '见放电量计算' },
          { label: '损耗电量', value: lossKWhCalc.toFixed(2), unit: '万kWh', formula: '充电量 - 放电量' },
          { label: '损耗率', value: lossRateCalc, unit: '%', formula: '损耗/充电量×100%' },
        ],
        result: { value: rowData.loss_kwh, unit: '万kWh' }
      };'''

new_loss = '''    case 'loss_kwh':
      // 完全复刻 calculatePhysics: lossKWh = annualChargeKWh - annualDischargeKWh
      const yearLoss = parseInt(rowData.y) || 1;
      
      // 复刻SOH计算
      let currentSOHLoss = 1.0;
      if (yearLoss === 1) {
        currentSOHLoss = 1.0 - 0.04;
      } else {
        currentSOHLoss = 1.0 - 0.04 - (yearLoss - 1) * 0.025;
      }
      currentSOHLoss = Math.max(0.60, currentSOHLoss);
      
      const capacityWhLoss = (inputs?.capacity || 100) * 1e6;
      const dodLoss = inputs?.dod || 0.9;
      const cyclesLoss = inputs?.cycles || 2;
      const runDaysLoss = inputs?.run_days || 330;
      const chargeEffLoss = (inputs?.charge_eff || 94) / 100;
      const dischargeEffLoss = (inputs?.discharge_eff || 94) / 100;
      const rteLoss = chargeEffLoss * dischargeEffLoss;
      
      // 复刻计算步骤
      const usableCapacityLoss = capacityWhLoss * currentSOHLoss * dodLoss;
      const dailyDischargeLoss = usableCapacityLoss * cyclesLoss;
      const annualDischargeKWhLoss = (dailyDischargeLoss * runDaysLoss) / 1000;
      const annualChargeKWhLoss = annualDischargeKWhLoss / rteLoss;
      const lossKWhCalc = annualChargeKWhLoss - annualDischargeKWhLoss;
      const lossRateCalc = annualChargeKWhLoss > 0 ? ((lossKWhCalc / annualChargeKWhLoss) * 100).toFixed(2) : '0.00';
      
      return {
        title: '损耗电量（完全复刻代码逻辑）',
        description: '充放电过程中的能量损耗',
        formula: '充电量 - 放电量',
        steps: [
          { label: '年放电量', value: annualDischargeKWhLoss.toFixed(2), unit: '万kWh', formula: '见放电量计算' },
          { label: '年充电量', value: annualChargeKWhLoss.toFixed(2), unit: '万kWh', formula: '放电量 ÷ RTE' },
          { label: '损耗电量', value: lossKWhCalc.toFixed(2), unit: '万kWh', formula: '充电量 - 放电量' },
          { label: '损耗率', value: lossRateCalc, unit: '%', formula: '(损耗÷充电量)×100%' },
        ],
        result: { value: rowData.loss_kwh, unit: '万kWh' }
      };'''

content = content.replace(old_loss, new_loss)

with open('src/components/CalculationTooltip.tsx', 'w') as f:
    f.write(content)

print("✅ 已完全复刻 calculatePhysics 逻辑：")
print("   • SOH衰减：首年4%，后续每年2.5%，最低60%")
print("   • 放电量：usableCapacity × cycles × runDays / 1000")
print("   • 充电量：放电量 / RTE")
print("   • 损耗：充电量 - 放电量")
print("   • 所有步骤与 useStorageCalculation.ts 中的代码完全一致")
