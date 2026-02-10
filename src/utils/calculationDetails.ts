import type { InputParams, YearlyRow } from "@/types";

interface CalculationStep {
  label: string;
  value: string | number;
  unit?: string;
  formula?: string;
}
interface CalculationDetail {
  title: string;
  description: string;
  formula: string;
  steps: CalculationStep[];
  result: { value: string | number; unit: string; };
}

export function createCalculationDetail(
  type: string,
  rowData: YearlyRow,
  inputs: InputParams
): CalculationDetail | null {
  const year = typeof rowData.y === "string" ? parseInt(rowData.y) || 1 : (rowData.y || 1);

  // [修复] 提升变量定义到函数顶层，供所有 case 使用
  const taxRate = (inputs?.tax_rate || 25) / 100;
  const taxPreferentialYears = inputs?.tax_preferential_years || 0;
  const taxPreferentialRate = (inputs?.tax_preferential_rate || 15) / 100;
  
  // 复刻 SOH 计算逻辑（与 calculatePhysics 一致）
  // 注意：第1年计算时 SOH=1.0（年初状态），年末才衰减
  let currentSOH = 1.0;
  if (year === 1) {
    currentSOH = 1.0; // 第1年无衰减
  } else {
    currentSOH = 1.0 - 0.04 - (year - 2) * 0.025; // 第2年应用首年衰减，之后每年2.5%
  }
  currentSOH = Math.max(0.60, currentSOH); // 最低60%
  
  const capacityWh = (inputs?.capacity || 100) * 1e6;
  const dod = (inputs?.dod || 90) / 100;
  const cycles = inputs?.cycles || 2;
  const runDays = inputs?.run_days || 330;
  const chargeEff = (inputs?.charge_eff || 94) / 100;
  const dischargeEff = (inputs?.discharge_eff || 94) / 100;
  
  // 获取功率（kW）用于容量补贴计算
  const powerKW = (inputs?.capacity || 100) * 1000 / (inputs?.duration_hours || 2); // MWh -> kW (功率 = 容量/时长)
  const durationHours = inputs?.duration_hours || 2;
  const subMode = inputs?.sub_mode || 'energy';
  const subPrice = inputs?.sub_price || 0.35;
  const subDecline = inputs?.sub_decline || 0;
  const spread = inputs?.spread || 0.70;
  const auxPrice = inputs?.aux_price || 0;
  
  // 计算补贴退坡后的当前单价
  const declineFactor = Math.pow(1 - subDecline / 100, year - 1);
  const currentSubPrice = subPrice * declineFactor;
  
  const vatRate = (inputs?.vat_rate || 13) / 100;
  const priceValley = inputs?.price_valley || 0.30;
  
  switch (type) {
    case 'discharge_kwh': {
      // 完全复刻 calculatePhysics 中的计算
      const usableCapacityDC = capacityWh * currentSOH * dod; // 直流侧可用容量
      
      // 放电量（交流侧）= 直流可用容量 × 放电效率 × 日循环
      const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
      const annualDischargeKWh = (dailyDischargeAC * runDays) / 1000;
      
      return {
        title: '放电量计算',
        description: `第${year}年放电量，完全复刻代码逻辑`,
        formula: '((装机容量×1,000,000) × SOH × DOD) × 日循环 × 运行天数 ÷ 1000',
        steps: [
          { label: '装机容量', value: inputs?.capacity || 100, unit: 'MWh', formula: '输入参数' },
          { label: '转换为Wh', value: (capacityWh).toLocaleString(), unit: 'Wh', formula: 'capacity × 1,000,000' },
          { label: 'SOH计算', value: year === 1 ? '第1年无衰减' : `首年4% + ${year-2}年×2.5%`, unit: '', formula: '年末衰减' },
          { label: '当前SOH', value: (currentSOH * 100).toFixed(1), unit: '%', formula: '计算年度初始SOH' },
          { label: '放电深度DOD', value: (dod * 100).toFixed(0), unit: '%', formula: '输入参数' },
          { label: '可用容量', value: (usableCapacityDC / 1e6).toFixed(2), unit: 'MWh', formula: 'capacityWh × SOH × DOD' },
          { label: '日循环次数', value: cycles, unit: '次', formula: '输入参数' },
          { label: '日放电量', value: (dailyDischargeAC / 1000).toFixed(2), unit: '万kWh', formula: 'usableCapacity × cycles' },
          { label: '年运行天数', value: runDays, unit: '天', formula: '输入参数' },
          { label: '年放电量', value: annualDischargeKWh.toFixed(2), unit: '万kWh', formula: '(日放电量 × runDays) ÷ 1000' },
        ],
        result: { value: rowData.discharge_kwh, unit: '万kWh' }
      };
    }
    
    case 'charge_kwh': {
      // 复刻计算：充电量独立计算，不再通过RTE反推
      const usableCapacityDC = capacityWh * currentSOH * dod; // 直流侧可用容量
      const dailyChargeAC = usableCapacityDC / chargeEff * cycles; // ÷ 充电效率
      const annualChargeKWh = (dailyChargeAC * runDays) / 1000;
      
      return {
        title: '充电量计算',
        description: `第${year}年充电量 = 直流可用容量 ÷ 充电效率 × 日循环 × 运行天数`,
        formula: '直流可用容量 ÷ 充电效率 × 日循环',
        steps: [
          { label: '直流可用容量', value: (usableCapacityDC / 1e6).toFixed(2), unit: 'MWh', formula: 'capacityWh × SOH × DOD' },
          { label: '充电效率', value: (chargeEff * 100).toFixed(0), unit: '%', formula: '输入参数' },
          { label: '日充电量(AC)', value: (dailyChargeAC / 1000).toFixed(2), unit: 'kWh', formula: 'usableCapacityDC ÷ chargeEff × cycles' },
          { label: '年运行天数', value: runDays, unit: '天', formula: '输入参数' },
          { label: '年充电量', value: annualChargeKWh.toFixed(2), unit: '万kWh', formula: '日充电量 × runDays ÷ 1000' },
        ],
        result: { value: rowData.charge_kwh, unit: '万kWh' }
      };
    }
    
    case 'loss_kwh': {
      // 复刻计算
      const usableCapacityDC = capacityWh * currentSOH * dod;
      
      // 放电量计算
      const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
      const annualDischargeKWh = (dailyDischargeAC * runDays) / 1000;
      
      // 充电量计算  
      const dailyChargeAC = usableCapacityDC / chargeEff * cycles;
      const annualChargeKWh = (dailyChargeAC * runDays) / 1000;
      
      const lossKWh = annualChargeKWh - annualDischargeKWh;
      
      return {
        title: '损耗电量',
        description: '充放电过程中的能量损耗',
        formula: '充电量 - 放电量',
        steps: [
          { label: '年充电量', value: annualChargeKWh.toFixed(2), unit: '万kWh', formula: '见充电量计算' },
          { label: '年放电量', value: annualDischargeKWh.toFixed(2), unit: '万kWh', formula: '见放电量计算' },
          { label: '损耗电量', value: lossKWh.toFixed(2), unit: '万kWh', formula: '充电量 - 放电量' },
        ],
        result: { value: rowData.loss_kwh, unit: '万kWh' }
      };
    }
    
    case 'elec_rev': {
      // 需要先计算放电量
      const usableCapacityDC = capacityWh * currentSOH * dod;
      const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
      const annualDischargeKWh = (dailyDischargeAC * runDays) / 1000; // kWh
      const elecRevWan = (annualDischargeKWh * spread) / 10000; // 转换为万元
      
      return {
        title: '电费套利收入',
        description: `第${year}年电费套利收入 = 放电量 × 峰谷价差`,
        formula: '放电量(万kWh) × 价差(元/kWh)',
        steps: [
          { label: '年放电量', value: (annualDischargeKWh / 10000).toFixed(2), unit: '万kWh', formula: '见放电量计算' },
          { label: '峰谷价差', value: spread.toFixed(2), unit: '元/kWh', formula: '输入参数' },
          { label: '电费套利收入', value: elecRevWan.toFixed(2), unit: '万元', formula: '放电量(万kWh) × 价差 × 10000 ÷ 10000' },
        ],
        result: { value: rowData.elec_rev, unit: '万元' }
      };
    }
    
    case 'sub_rev': {
      // 计算放电量（电量补贴用）或功率（容量补贴用）
      const usableCapacityDC = capacityWh * currentSOH * dod;
      const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
      const annualDischargeKWh = (dailyDischargeAC * runDays) / 1000;
      
      let subRev = 0;
      let calcSteps = [];
      
      if (subMode === 'energy') {
        // 内蒙模式：按电量
        subRev = (annualDischargeKWh * currentSubPrice) / 10000; // 转换为万元
        calcSteps = [
          { label: '补贴模式', value: '按电量(内蒙模式)', unit: '', formula: '输入参数' },
          { label: '年放电量', value: (annualDischargeKWh / 10000).toFixed(2), unit: '万kWh', formula: '见放电量计算' },
          { label: '退坡后单价', value: currentSubPrice.toFixed(3), unit: '元/kWh', formula: `${subPrice} × (1-${subDecline}%)^{year-1}` },
          { label: '补偿收入', value: subRev.toFixed(2), unit: '万元', formula: '放电量(万kWh) × 单价 × 10000 ÷ 10000' },
        ];
      } else {
        // 甘肃模式：按功率
        const kFactor = Math.min(1, durationHours / 6.0);
        // 关键：确保功率单位是 kW（与 useStorageCalculation.ts 一致）
        const actualPowerKW = ((inputs?.capacity || 100) * 1000) / (inputs?.duration_hours || 2);
        subRev = (actualPowerKW * currentSubPrice * kFactor) / 10000; // 转换为万元
        const powerMW = actualPowerKW / 1000; // 转换为MW用于显示
        
        calcSteps = [
          { label: '补贴模式', value: '按功率(甘肃模式)', unit: '', formula: '输入参数' },
          { label: '装机容量', value: (inputs?.capacity || 100).toFixed(0), unit: 'MWh', formula: '输入参数' },
          { label: '功率', value: powerMW.toFixed(1), unit: 'MW', formula: '容量÷时长' },
          { label: '功率(kW)', value: actualPowerKW.toFixed(0), unit: 'kW', formula: '用于计算' },
          { label: 'K系数', value: kFactor.toFixed(2), unit: '', formula: `min(1, ${durationHours}/6)` },
          { label: '退坡后单价', value: currentSubPrice.toFixed(2), unit: '元/kW', formula: `${subPrice} × (1-${subDecline/100})^${year-1}` },
          { label: '补偿收入', value: subRev.toFixed(2), unit: '万元', formula: `${actualPowerKW.toFixed(0)}kW × ${kFactor.toFixed(2)} × ${currentSubPrice.toFixed(2)} ÷ 10000` },
        ];
      }
      
      return {
        title: '补偿收入',
        description: `第${year}年补偿收入（${subMode === 'energy' ? '内蒙-按电量' : '甘肃-按功率'}模式）`,
        formula: subMode === 'energy' ? '放电量 × 退坡后单价' : '功率 × K系数 × 退坡后单价',
        steps: calcSteps,
        result: { value: rowData.sub_rev, unit: '万元' }
      };
    }
    
    case 'aux_rev': {
      const auxRev = (powerKW * auxPrice) / 10000; // 转换为万元
      
      return {
        title: '辅助服务收入',
        description: `第${year}年辅助服务收入（调峰、调频等）`,
        formula: '功率 × 单位收益',
        steps: [
          { label: '功率', value: (powerKW / 1000).toFixed(1), unit: 'MW', formula: '容量÷时长' },
          { label: '单位收益', value: auxPrice.toFixed(2), unit: '元/kW/年', formula: '输入参数' },
          { label: '辅助服务收入', value: auxRev.toFixed(2), unit: '万元', formula: '功率(kW) × 单位收益 ÷ 10000' },
        ],
        result: { value: rowData.aux_rev, unit: '万元' }
      };
    }
    
    case 'total_rev': {
      return {
        title: '总收入',
        description: `第${year}年总收入 = 电费套利 + 补偿 + 辅助服务`,
        formula: '电费套利 + 补偿收入 + 辅助服务收入',
        steps: [
          { label: '电费套利', value: rowData.elec_rev, unit: '万元', formula: '' },
          { label: '补偿收入', value: rowData.sub_rev, unit: '万元', formula: '' },
          { label: '辅助服务', value: rowData.aux_rev, unit: '万元', formula: '' },
          { label: '总收入', value: rowData.total_rev, unit: '万元', formula: '三者之和' },
        ],
        result: { value: rowData.total_rev, unit: '万元' }
      };
    }

    case 'opex': {
      const opexRate = inputs?.opex || 0.02;
      const opexGross = (capacityWh * opexRate) / 10000; // 转换为万元
      
      return {
        title: '运维成本',
        description: `第${year}年运维成本 = 装机容量 × 运维费率`,
        formula: '装机容量(Wh) × 费率(元/Wh/年) ÷ 10000',
        steps: [
          { label: '装机容量', value: (capacityWh / 1e6).toFixed(0), unit: 'MWh', formula: '输入参数' },
          { label: '转换为Wh', value: capacityWh.toLocaleString(), unit: 'Wh', formula: 'capacity × 1,000,000' },
          { label: '运维费率', value: opexRate.toFixed(3), unit: '元/Wh/年', formula: '输入参数' },
          { label: '运维成本(含税)', value: opexGross.toFixed(2), unit: '万元', formula: 'capacityWh × opexRate ÷ 10000' },
        ],
        result: { value: rowData.opex, unit: '万元' }
      };
    }
    
    case 'loss_cost': {
      // 需要先计算损耗电量
      const usableCapacityDC = capacityWh * currentSOH * dod;
      const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
      const annualDischargeKWh = (dailyDischargeAC * runDays) / 1000;
      const dailyChargeAC = usableCapacityDC / chargeEff * cycles;
      const annualChargeKWh = (dailyChargeAC * runDays) / 1000;
      const lossKWh = annualChargeKWh - annualDischargeKWh;
      const priceValley = inputs?.price_valley || 0.30;
      const lossCostGross = (lossKWh * priceValley) / 10000; // 转换为万元
      
      return {
        title: '效率损耗成本',
        description: `第${year}年损耗成本 = 损耗电量 × 充电电价`,
        formula: '损耗电量(万kWh) × 电价(元/kWh)',
        steps: [
          { label: '年充电量', value: (annualChargeKWh / 10000).toFixed(2), unit: '万kWh', formula: '见充电量计算' },
          { label: '年放电量', value: (annualDischargeKWh / 10000).toFixed(2), unit: '万kWh', formula: '见放电量计算' },
          { label: '损耗电量', value: (lossKWh / 10000).toFixed(2), unit: '万kWh', formula: '充电量 - 放电量' },
          { label: '充电电价', value: priceValley.toFixed(2), unit: '元/kWh', formula: '输入参数(低谷电价)' },
          { label: '损耗成本(含税)', value: lossCostGross.toFixed(2), unit: '万元', formula: '损耗电量 × 电价' },
        ],
        result: { value: rowData.loss_cost, unit: '万元' }
      };
    }
    
    case 'dep': {
      const depYears = inputs?.dep_years || 15;
      const augYear = inputs?.aug_year || 0;
      const augDepYears = inputs?.aug_dep_years || 15;
      const residualRate = (inputs?.residual_rate || 5) / 100;
      const vatRate = (inputs?.vat_rate || 13) / 100;
      
      // 基础投资（不含税）
      const baseCapex = inputs?.capex || 1.20;
      const baseInvGross = baseCapex * capacityWh; // 元
      const baseInvNet = baseInvGross / (1 + vatRate); // 不含税
      const baseAnnualDep = (baseInvNet * (1 - residualRate)) / depYears / 10000; // 万元
      
      let steps = [
        { label: '基础系统造价', value: baseCapex.toFixed(2), unit: '元/Wh', formula: '输入参数' },
        { label: '装机容量', value: (capacityWh / 1e6).toFixed(0), unit: 'MWh', formula: '输入参数' },
        { label: '基础投资(含税)', value: (baseInvGross / 10000).toFixed(0), unit: '万元', formula: 'capex × capacity' },
        { label: '基础投资(不含税)', value: (baseInvNet / 10000).toFixed(0), unit: '万元', formula: '含税 ÷ (1+增值税率)' },
        { label: '残值率', value: (residualRate * 100).toFixed(0), unit: '%', formula: '输入参数' },
        { label: '基础折旧年限', value: depYears, unit: '年', formula: '输入参数' },
        { label: '基础年折旧', value: baseAnnualDep.toFixed(2), unit: '万元', formula: '投资(不含税) × (1-残值率) ÷ 年限' },
      ];
      
      let totalDep = baseAnnualDep;
      let description = `第${year}年基础资产折旧（不含税投资按${depYears}年直线折旧）`;
      
      // 如果是补容年，增加补容资产折旧
      if (year === augYear && augYear > 0) {
        const augPrice = inputs?.aug_price || 0.6;
        const augInvGross = capacityWh * augPrice; // 补容投资（含税）
        const augInvNet = augInvGross / (1 + vatRate); // 不含税
        const augAnnualDep = (augInvNet * (1 - residualRate)) / augDepYears / 10000; // 万元
        
        totalDep += augAnnualDep;
        description = `第${year}年折旧（含补容资产，基础+补容）`;
        
        steps = steps.concat([
          { label: '--- 补容资产 ---', value: '', unit: '', formula: '' },
          { label: '补容年份', value: augYear, unit: '年', formula: '输入参数' },
          { label: '补容单价', value: augPrice.toFixed(2), unit: '元/Wh', formula: '输入参数' },
          { label: '补容投资(含税)', value: (augInvGross / 10000).toFixed(0), unit: '万元', formula: 'aug_price × capacity' },
          { label: '补容投资(不含税)', value: (augInvNet / 10000).toFixed(0), unit: '万元', formula: '含税 ÷ (1+增值税率)' },
          { label: '补容折旧年限', value: augDepYears, unit: '年', formula: '输入参数' },
          { label: '补容年折旧', value: augAnnualDep.toFixed(2), unit: '万元', formula: '补容投资 × (1-残值率) ÷ 年限' },
          { label: '合计年折旧', value: totalDep.toFixed(2), unit: '万元', formula: '基础折旧 + 补容折旧' },
        ]);
      } else if (augYear > 0 && year > augYear) {
        // 补容后的年份，提示包含补容折旧
        const augPrice = inputs?.aug_price || 0.6;
        const augInvGross = capacityWh * augPrice;
        const augInvNet = augInvGross / (1 + vatRate);
        const augAnnualDep = (augInvNet * (1 - residualRate)) / augDepYears / 10000;
        
        // 简化计算：假设补容资产也在折旧
        totalDep = baseAnnualDep + augAnnualDep;
        description = `第${year}年折旧（基础+补容资产，补容第${year - augYear}年）`;
        
        steps.push({ label: '补容资产折旧', value: augAnnualDep.toFixed(2), unit: '万元', formula: `补容后第${year - augYear}年折旧` });
        steps.push({ label: '合计年折旧(估)', value: totalDep.toFixed(2), unit: '万元', formula: '基础+补容（简化计算）' });
      }
      
      return {
        title: '折旧费用',
        description: description,
        formula: year === augYear ? '基础折旧 + 补容折旧' : '投资原值 × (1-残值率) ÷ 年限',
        steps: steps,
        result: { value: rowData.dep, unit: '万元' }
      };
    }
    
    case 'interest': {
      const debtRatio = (inputs?.debt_ratio || 70) / 100;
      const loanRate = (inputs?.loan_rate || 3.5) / 100;
      const totalInvGross = (inputs?.capex || 1.20) * capacityWh; // 总投资（元）
      const debt = totalInvGross * debtRatio / 10000; // 贷款额（万元）
      
      // 简化计算：假设等额本息，首年利息≈贷款余额×利率
      // 实际应该用剩余本金计算，这里做展示用简化
      const interest = debt * loanRate;
      
      return {
        title: '利息支出',
        description: `第${year}年利息支出（贷款比例${(debtRatio*100).toFixed(0)}%，利率${(loanRate*100).toFixed(1)}%）`,
        formula: '剩余本金 × 年利率',
        steps: [
          { label: '总投资(含税)', value: (totalInvGross / 10000).toFixed(0), unit: '万元', formula: 'capex × capacity' },
          { label: '贷款比例', value: (debtRatio * 100).toFixed(0), unit: '%', formula: '输入参数' },
          { label: '贷款金额', value: debt.toFixed(0), unit: '万元', formula: '投资 × 贷款比例' },
          { label: '贷款利率', value: (loanRate * 100).toFixed(2), unit: '%', formula: '输入参数' },
          { label: '利息支出(约)', value: interest.toFixed(2), unit: '万元', formula: '贷款余额 × 利率' },
        ],
        result: { value: rowData.interest, unit: '万元' }
      };
    }

    case 'vat_pay': {
      // 复现 useStorageCalculation.ts 中的增值税计算逻辑
      const usableCapacityDC = capacityWh * currentSOH * dod;
      const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
      const annualDischargeKWh = (dailyDischargeAC * runDays) / 1000;
      const dailyChargeAC = usableCapacityDC / chargeEff * cycles;
      const annualChargeKWh = (dailyChargeAC * runDays) / 1000;
      const lossKWh = annualChargeKWh - annualDischargeKWh;
      
      const spread = inputs?.spread || 0.70;
      const priceValley = inputs?.price_valley || 0.30;
      const vatRate = (inputs?.vat_rate || 13) / 100;
      const subPrice = inputs?.sub_price || 0.35;
      const subYears = inputs?.sub_years || 10;
      const subDecline = inputs?.sub_decline || 0;
      const auxPrice = inputs?.aux_price || 0;
      const durationHours = inputs?.duration_hours || 2;
      const powerKW = (inputs?.capacity || 100) * 1000 / durationHours;
      const subMode = inputs?.sub_mode || 'energy';
      
      // 计算收入（含税）
      const elecRevGross = annualDischargeKWh * spread; // 电费套利
      let subRevGross = 0;
      if (year <= subYears) {
        const declineFactor = Math.pow(1 - subDecline / 100, year - 1);
        const currentRate = subPrice * declineFactor;
        if (subMode === 'energy') {
          subRevGross = annualDischargeKWh * currentRate;
        } else {
          const kFactor = Math.min(1, durationHours / 6.0);
          subRevGross = powerKW * currentRate * kFactor;
        }
      }
      const auxRevGross = powerKW * auxPrice;
      const totalRevGross = elecRevGross + subRevGross + auxRevGross;
      
      // 销项税
      const outputVAT = totalRevGross - (totalRevGross / (1 + vatRate));
      
      // 进项税（运维成本 + 损耗电费）
      const opexGross = capacityWh * (inputs?.opex || 0.02);
      const lossCostGross = lossKWh * priceValley;
      const opexNet = opexGross / (1 + vatRate);
      const lossCostNet = lossCostGross / (1 + vatRate);
      const inputVAT = (opexGross - opexNet) + (lossCostGross - lossCostNet);
      
      // 增值税计算（简化，不考虑历史留抵）
      const theoreticalVat = outputVAT - inputVAT;
      const actualVat = parseFloat(rowData.vat_pay || '0') * 10000;
      const vatCreditUsed = Math.max(0, theoreticalVat - actualVat);
      let vatPayable = theoreticalVat;
      if (vatPayable < 0) vatPayable = 0;
      
      return {
        title: '增值税',
        description: `第${year}年应交增值税 = 销项税 - 进项税`,
        formula: '销项税(收入不含税部分 × 税率) - 进项税(成本中已缴增值税)',
        steps: [
          { label: '总收入(含税)', value: (totalRevGross / 10000).toFixed(2), unit: '万元', formula: '电费+补偿+辅助服务' },
          { label: '总收入(不含税)', value: ((totalRevGross / (1 + vatRate)) / 10000).toFixed(2), unit: '万元', formula: '含税 ÷ (1+税率)' },
          { label: '销项税额', value: (outputVAT / 10000).toFixed(2), unit: '万元', formula: '含税 - 不含税' },
          { label: '运维成本(含税)', value: (opexGross / 10000).toFixed(2), unit: '万元', formula: 'capacityWh × opex' },
          { label: '损耗电费(含税)', value: (lossCostGross / 10000).toFixed(2), unit: '万元', formula: 'lossKWh × priceValley' },
          { label: '进项税额', value: (inputVAT / 10000).toFixed(2), unit: '万元', formula: '成本(含税) - 成本(不含税)' },
          { label: '理论应交增值税', value: (theoreticalVat / 10000).toFixed(2), unit: '万元', formula: '销项税额 - 进项税额' },
          ...(vatCreditUsed > 0.01 ? [{ label: '减：留抵税额抵扣', value: (vatCreditUsed / 10000).toFixed(2), unit: '万元', formula: '历史累积进项税留抵' }] : []),
          { label: '实际应交增值税', value: (actualVat / 10000).toFixed(2), unit: '万元', formula: vatCreditUsed > 0.01 ? '理论应交 - 留抵抵扣' : '销项 - 进项' },
        ],
        result: { value: rowData.vat_pay, unit: '万元' }
      };
    }
    
    case 'surcharge': {
      // 附加税 = 增值税 × 12%
      const vatPay = parseFloat(rowData.vat_pay || '0') * 10000; // 转回元计算
      const surchargeRate = 0.12; // 城建7% + 教育3% + 地方2%
      const surcharge = vatPay * surchargeRate;
      
      return {
        title: '附加税',
        description: `第${year}年附加税 = 增值税 × 附加税率(${surchargeRate * 100}%)`,
        formula: '增值税 × 12%（城建7% + 教育3% + 地方2%）',
        steps: [
          { label: '应交增值税', value: (vatPay / 10000).toFixed(2), unit: '万元', formula: '见增值税计算' },
          { label: '附加税率', value: '12', unit: '%', formula: '7%(城建) + 3%(教育) + 2%(地方)' },
          { label: '附加税额', value: (surcharge / 10000).toFixed(2), unit: '万元', formula: '增值税 × 12%' },
        ],
        result: { value: rowData.surcharge, unit: '万元' }
      };
    }
    
    case 'income_tax': {
      const isPreferential = taxPreferentialYears > 0 && year <= taxPreferentialYears;
      const currentTaxRate = isPreferential ? taxPreferentialRate : taxRate;
      // 所得税计算需要多个前置数据
      const usableCapacityDC = capacityWh * currentSOH * dod;
      const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
      const annualDischargeKWh = (dailyDischargeAC * runDays) / 1000;
      
      const spread = inputs?.spread || 0.70;
      const elecRevGross = annualDischargeKWh * spread;
      const vatRate = (inputs?.vat_rate || 13) / 100;
      const totalRevNet = elecRevGross / (1 + vatRate); // 简化，仅用套利收入
      
      // 成本（不含税）
      const opexNet = (capacityWh * (inputs?.opex || 0.02)) / (1 + vatRate);
      
      // 折旧（简化计算）
      const depYears = inputs?.dep_years || 15;
      const residualRate = (inputs?.residual_rate || 5) / 100;
      const totalInvNet = ((inputs?.capex || 1.20) * capacityWh) / (1 + vatRate);
      const annualDep = (totalInvNet * (1 - residualRate)) / depYears;
      
      // 利息（简化）
      const debtRatio = (inputs?.debt_ratio || 70) / 100;
      const loanRate = (inputs?.loan_rate || 3.5) / 100;
      const totalInvGross = (inputs?.capex || 1.20) * capacityWh;
      const debt = totalInvGross * debtRatio;
      const interest = debt * loanRate; // 简化首年利息
      
      // 附加税（引用）
      const surcharge = parseFloat(rowData.surcharge || '0') * 10000;
      
      // 应纳税所得额
      const taxableIncome = Math.max(0, totalRevNet - opexNet - annualDep - interest - surcharge);
      // 移除局部定义，使用上方定义的动态逻辑
  
  
      const incomeTax = taxableIncome * currentTaxRate;
      
      return {
        title: '所得税',
        description: `第${year}年所得税 = 应纳税所得额 × ${isPreferential ? '优惠' : '标准'}税率(${(currentTaxRate * 100).toFixed(1)}%)`,
        formula: '(收入 - 成本 - 折旧 - 利息 - 附加税) × 税率',
        steps: [
          { label: '营业收入(不含税)', value: (totalRevNet / 10000).toFixed(2), unit: '万元', formula: '收入 ÷ (1+增值税率)' },
          { label: '减：运维成本', value: (opexNet / 10000).toFixed(2), unit: '万元', formula: '成本(不含税)' },
          { label: '减：折旧费用', value: (annualDep / 10000).toFixed(2), unit: '万元', formula: '投资 × (1-残值率) ÷ 年限' },
          { label: '减：利息支出', value: (interest / 10000).toFixed(2), unit: '万元', formula: '贷款余额 × 利率' },
          { label: '减：附加税', value: (surcharge / 10000).toFixed(2), unit: '万元', formula: '见附加税计算' },
          { label: '应纳税所得额', value: (taxableIncome / 10000).toFixed(2), unit: '万元', formula: '收入 - 各项扣除' },
          { label: '所得税率', value: (currentTaxRate * 100).toFixed(1), unit: '%', formula: isPreferential ? `优惠期(前${taxPreferentialYears}年)` : '标准税率' },
          { label: '应交所得税', value: (incomeTax / 10000).toFixed(2), unit: '万元', formula: '应纳税所得额 × 税率' },
        ],
        result: { value: rowData.income_tax, unit: '万元' }
      };
    }
    
    case 'total_tax': {
      const vat = parseFloat(rowData.vat_pay || '0');
      const surcharge = parseFloat(rowData.surcharge || '0');
      const income = parseFloat(rowData.income_tax || '0');
      const total = vat + surcharge + income;
      
      return {
        title: '总税金',
        description: `第${year}年总税金 = 增值税 + 附加税 + 所得税`,
        formula: '三类税金之和',
        steps: [
          { label: '增值税', value: vat.toFixed(2), unit: '万元', formula: '销项 - 进项' },
          { label: '附加税', value: surcharge.toFixed(2), unit: '万元', formula: '增值税 × 12%' },
          { label: '所得税', value: income.toFixed(2), unit: '万元', formula: '(利润 - 扣除项) × 税率' },
          { label: '总税金', value: total.toFixed(2), unit: '万元', formula: '三者之和' },
        ],
        result: { value: rowData.total_tax, unit: '万元' }
      };
    }

    case 'ebitda': {
      // 计算 EBITDA = 息税前利润 + 折旧
      const usableCapacityDC = capacityWh * currentSOH * dod;
      const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
      const annualDischargeKWh = (dailyDischargeAC * runDays) / 1000;
      const elecRevGross = annualDischargeKWh * spread;
      
      const declineFactor = Math.pow(1 - subDecline / 100, year - 1);
      const currentSubRate = subPrice * declineFactor;
      let subRevGross = 0;
      if (subMode === 'energy') {
        subRevGross = annualDischargeKWh * currentSubRate;
      } else {
        const kFactor = Math.min(1, durationHours / 6.0);
        const actualPowerKW = ((inputs?.capacity || 100) * 1000) / durationHours;
        subRevGross = actualPowerKW * currentSubRate * kFactor;
      }
      const auxRevGross = powerKW * auxPrice;
      const totalRevGross = elecRevGross + subRevGross + auxRevGross;
      const totalRevNet = totalRevGross / (1 + vatRate);
      
      const opexNet = (capacityWh * (inputs?.opex || 0.02)) / (1 + vatRate);
      const dailyChargeAC = usableCapacityDC / chargeEff * cycles;
      const annualChargeKWh = (dailyChargeAC * runDays) / 1000;
      const lossKWh = annualChargeKWh - annualDischargeKWh;
      const lossCostNet = (lossKWh * priceValley) / (1 + vatRate);
      
      const depYears = inputs?.dep_years || 15;
      const residualRate = (inputs?.residual_rate || 5) / 100;
      const totalInvNet = ((inputs?.capex || 1.20) * capacityWh) / (1 + vatRate);
      const annualDep = (totalInvNet * (1 - residualRate)) / depYears / 10000; // 万元
      
      const ebit = (totalRevNet - opexNet - lossCostNet) / 10000 - annualDep;
      const ebitda = ebit + annualDep;
      
      return {
        title: '息税折旧前利润 EBITDA',
        description: `第${year}年EBITDA = 息税前利润 + 折旧`,
        formula: '营业收入 - 运维成本 - 损耗成本',
        steps: [
          { label: '营业收入(不含税)', value: (totalRevNet / 10000).toFixed(2), unit: '万元', formula: '总收入 ÷ (1+增值税率)' },
          { label: '减：运维成本(不含税)', value: (opexNet / 10000).toFixed(2), unit: '万元', formula: 'capacityWh × opex ÷ (1+税率)' },
          { label: '减：损耗成本(不含税)', value: (lossCostNet / 10000).toFixed(2), unit: '万元', formula: 'lossKWh × priceValley ÷ (1+税率)' },
          { label: '息税前利润 EBIT', value: (ebit + annualDep).toFixed(2), unit: '万元', formula: '收入 - 成本' },
          { label: '加：折旧费用', value: annualDep.toFixed(2), unit: '万元', formula: '投资 × (1-残值率) ÷ 年限' },
          { label: 'EBITDA', value: ebitda.toFixed(2), unit: '万元', formula: 'EBIT + 折旧' },
        ],
        result: { value: rowData.ebitda, unit: '万元' }
      };
    }
    
    case 'net_profit': {
      return {
        title: '净利润',
        description: `第${year}年净利润 = 总收入 - 总成本 - 税金`,
        formula: '营业收入 - 营业成本 - 税金及附加 - 所得税',
        steps: [
          { label: '营业收入', value: rowData.total_rev, unit: '万元', formula: '见收入计算' },
          { label: '减：总成本', value: (parseFloat(rowData.opex || '0') + parseFloat(rowData.loss_cost || '0') + parseFloat(rowData.dep || '0') + parseFloat(rowData.interest || '0')).toFixed(2), unit: '万元', formula: '运维+损耗+折旧+利息' },
          { label: '减：总税金', value: rowData.total_tax, unit: '万元', formula: '见税务计算' },
          { label: '净利润', value: rowData.net_profit, unit: '万元', formula: '收入 - 成本 - 税金' },
        ],
        result: { value: rowData.net_profit, unit: '万元' }
      };
    }
    
    case 'cf': {
      return {
        title: '股东现金流',
        description: `第${year}年股东现金流 = 净利润 + 折旧 - 本金偿还`,
        formula: '净利润 + 折旧 - 本金偿还 ± 补容投资',
        steps: [
          { label: '净利润', value: rowData.net_profit, unit: '万元', formula: '见净利润计算' },
          { label: '加：折旧费用', value: rowData.dep, unit: '万元', formula: '非现金支出，加回' },
          { label: '减：本金偿还', value: rowData.principal, unit: '万元', formula: '贷款本金偿还' },
          { label: '股东现金流', value: rowData.cf, unit: '万元', formula: year === (inputs?.aug_year || 0) ? '净利润+折旧-本金-补容投资' : '净利润+折旧-本金' },
        ],
        result: { value: rowData.cf, unit: '万元' }
      };
    }
    
    case 'cum_cf': {
      const prevCum = parseFloat(rowData.cum_cf || '0') - parseFloat(rowData.cf || '0');
      return {
        title: '累计现金流',
        description: `第${year}年累计现金流 = 上年累计 + 当年现金流`,
        formula: '累计至上年末 + 当年股东现金流',
        steps: [
          { label: '上年末累计', value: prevCum.toFixed(2), unit: '万元', formula: year === 1 ? '初始投资' : '前一年累计' },
          { label: '当年现金流', value: rowData.cf, unit: '万元', formula: '见股东现金流' },
          { label: '累计现金流', value: rowData.cum_cf, unit: '万元', formula: '上年累计 + 当年' },
        ],
        result: { value: rowData.cum_cf, unit: '万元' }
      };
    }
    
    case 'dscr': {
      const debtRatio = (inputs?.debt_ratio || 70) / 100;
      const hasLoan = debtRatio > 0 && year <= 10;
      
      if (!hasLoan || rowData.dscr === '-') {
        return {
          title: '偿债覆盖率 DSCR',
          description: `第${year}年无贷款或已还清`,
          formula: '(净利润 + 折旧 + 利息) ÷ 当期还本付息',
          steps: [
            { label: '状态', value: debtRatio === 0 ? '无贷款' : '贷款已还清', unit: '', formula: '' },
            { label: 'DSCR', value: '-', unit: '', formula: '不适用' },
          ],
          result: { value: '-', unit: '' }
        };
      }
      
      const netProfit = parseFloat(rowData.net_profit || '0') * 10000;
      const dep = parseFloat(rowData.dep || '0') * 10000;
      const interest = parseFloat(rowData.interest || '0') * 10000;
      const debtService = parseFloat(rowData.principal || '0') * 10000 + interest;
      const dscr = debtService > 0 ? (netProfit + dep + interest) / debtService : 999;
      
      return {
        title: '偿债覆盖率 DSCR',
        description: `第${year}年偿债覆盖率 = (净利润+折旧+利息) ÷ 当期还本付息`,
        formula: '可用于偿债现金流 ÷ 当期债务',
        steps: [
          { label: '净利润', value: (netProfit / 10000).toFixed(2), unit: '万元', formula: '' },
          { label: '加：折旧', value: (dep / 10000).toFixed(2), unit: '万元', formula: '非现金支出，加回' },
          { label: '加：利息', value: (interest / 10000).toFixed(2), unit: '万元', formula: '利息支出' },
          { label: '可用于偿债现金流', value: ((netProfit + dep + interest) / 10000).toFixed(2), unit: '万元', formula: '净利润+折旧+利息' },
          { label: '当期还本付息', value: (debtService / 10000).toFixed(2), unit: '万元', formula: '本金+利息' },
          { label: 'DSCR', value: dscr.toFixed(2), unit: '', formula: '可偿债现金流 ÷ 还本付息' },
        ],
        result: { value: rowData.dscr, unit: '' }
      };
    }

    default:
      return null;
  }
}
