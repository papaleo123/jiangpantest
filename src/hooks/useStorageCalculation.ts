import { useState, useCallback, useMemo } from 'react';
import type { InputParams, CalculationResult, KpiResult, YearlyRow, Stats } from '@/types';

/**
 * 工商业储能财务模型 - V13.0 专业版
 * 
 * 核心假设：
 * 1. 充电效率 × 放电效率 = 往返效率(RTE)
 * 2. 放电量 = 装机容量 × SOH × DOD × 日循环 × 年运行天数
 * 3. 充电量 = 放电量 / (充电效率 × 放电效率) = 放电量 / RTE
 * 4. 效率损耗电量 = 充电量 - 放电量
 * 5. 效率损耗成本 = 损耗电量 × 充电电价
 * 
 * 税务处理：
 * 1. 增值税：销项税 - 进项税（运维、损耗电费可抵扣）
 * 2. 附加税：增值税 × 12%
 * 3. 所得税：(收入 - 成本 - 折旧 - 利息 - 附加税) × 税率
 * 4. 折旧：直线法，残值率5%
 */

// ==================== 财务计算工具函数 ====================

/**
 * IRR计算 - 牛顿迭代法
 */
function calculateIRR(cf: number[]): number {
  if (cf.length === 0) return 0;
  
  let guess = 0.1;
  for (let i = 0; i < 100; i++) {
    let npv = 0, derivative = 0;
    for (let t = 0; t < cf.length; t++) {
      const discountFactor = Math.pow(1 + guess, t);
      npv += cf[t] / discountFactor;
      derivative -= t * cf[t] / Math.pow(1 + guess, t + 1);
    }
    if (Math.abs(npv) < 0.01) return guess;
    if (Math.abs(derivative) < 0.0001) break;
    guess -= npv / derivative;
  }
  return guess;
}

/**
 * NPV计算
 */
function calculateNPV(rate: number, cf: number[]): number {
  return cf.reduce((npv, cashflow, t) => npv + cashflow / Math.pow(1 + rate, t), 0);
}

/**
 * 静态回收期计算
 */
function calculatePayback(equity_cf: number[]): number {
  let cum = 0;
  for (let i = 0; i < equity_cf.length; i++) {
    const pre = cum;
    cum += equity_cf[i];
    if (cum > 0) {
      return Math.max(0, (i - 1) + Math.abs(pre) / equity_cf[i]);
    }
  }
  return 99;
}

/**
 * 等额本息还款计算
 */
function calculatePMT(principal: number, rate: number, periods: number): number {
  if (rate === 0) return principal / periods;
  return principal * rate * Math.pow(1 + rate, periods) / (Math.pow(1 + rate, periods) - 1);
}

// ==================== 主Hook ====================

export function useStorageCalculation() {
  // 默认参数 - 基于行业典型值
  const [inputs, setInputs] = useState<InputParams>({
    years: 20,
    sub_mode: 'energy',
    sub_price: 0.35,
    sub_years: 10,
    sub_decline: 0,
    aux_price: 0,
    capacity: 100,           // 100 MWh
    duration_hours: 2,       // 2小时系统
    charge_eff: 94,          // 充电效率 94%
    discharge_eff: 94,       // 放电效率 94%
    dod: 90,                 // 放电深度 90% (明确标注，用户可修改)
    price_valley: 0.30,      // 充电电价 0.30元/kWh
    capex: 1.20,             // 系统造价 1.20元/Wh
    spread: 0.70,            // 峰谷价差 0.70元/kWh
    opex: 0.02,              // 运维成本 0.02元/Wh/年
    cycles: 2.0,             // 日循环次数
    run_days: 330,           // 年运行天数
    dep_years: 15,           // 折旧年限
    debt_ratio: 70,          // 贷款比例 70%
    loan_rate: 3.5,          // 贷款利率 3.5%
    vat_rate: 13,            // 增值税率 13%
    tax_rate: 25,            // 所得税率 25%
    aug_year: 0,             // 补容年份 (0表示不补容)
    aug_price: 0.6,          // 补容单价
    aug_dep_years: 15,        // 补容折旧年限
    residual_rate: 5,        // 残值率 5%
  });

  const [result, setResult] = useState<CalculationResult | null>(null);
  const [kpi, setKpi] = useState<KpiResult | null>(null);

  const updateInput = useCallback(<K extends keyof InputParams>(
    key: K,
    value: InputParams[K]
  ) => {
    setInputs(prev => ({ ...prev, [key]: value }));
  }, []);

  /**
   * 核心计算函数
   */
  const calculate = useCallback(() => {
    // ========== 1. 基础参数转换 ==========
    const MWh = inputs.capacity;
    const hours = inputs.duration_hours;
    const MW = MWh / hours;           // 功率 MW
    const Wh = MWh * 1e6;             // 容量 Wh
    const kW = MW * 1000;             // 功率 kW
    
    const chargeEff = inputs.charge_eff / 100;      // 充电效率小数
    const dischargeEff = inputs.discharge_eff / 100; // 放电效率小数
    const rte = chargeEff * dischargeEff;            // 往返效率
    const dod = inputs.dod / 100;                    // 放电深度
    
    const years = inputs.years;
    const cycles = inputs.cycles;
    const runDays = inputs.run_days;
    
    // 投资参数
    const totalInvGross = Wh * inputs.capex;                    // 总投资(含税)
    const vatRate = inputs.vat_rate / 100;
    const totalInvNet = totalInvGross / (1 + vatRate);          // 总投资(不含税)
    const inputVAT = totalInvGross - totalInvNet;               // 设备进项税
    
    // 融资参数
    const debtRatio = inputs.debt_ratio / 100;
    const loanRate = inputs.loan_rate / 100;
    const loanTerm = Math.min(10, years);  // 贷款期限不超过10年或项目期
    
    const debt = totalInvGross * debtRatio;
    const equity = totalInvGross * (1 - debtRatio);
    const annualPMT = calculatePMT(debt, loanRate, loanTerm);
    
    // 税务参数
    const taxRate = inputs.tax_rate / 100;
    const residualRate = inputs.residual_rate / 100;
    
    // ========== 2. 初始化资产折旧 ==========
    // 支持多个资产（初始投资 + 补容投资）
    interface Asset {
      value: number;      // 资产原值(不含税)
      life: number;       // 折旧年限
      age: number;        // 已使用年数
    }
    
    let assets: Asset[] = [{
      value: totalInvNet,
      life: inputs.dep_years,
      age: 0
    }];
    
    // ========== 3. 年度循环计算 ==========
    let currentSOH = 1.0;           // 当前电池健康度
    let remainingVAT = inputVAT;    // 剩余可抵扣进项税
    let remainingDebt = debt;       // 剩余贷款本金
    
    const equityCF: number[] = [-equity];  // 股东现金流（初始为负的投资）
    const projectCF: number[] = [-totalInvGross];
    const rows: YearlyRow[] = [];
    
    // 统计累计值
    let cumEquityCF = -equity;
    let minDSCR = 999;
    
    const stats: Stats = {
      total_charge_kwh: 0,
      total_discharge_kwh: 0,
      total_loss_kwh: 0,
      total_elec_rev: 0,
      total_sub_rev: 0,
      total_aux_rev: 0,
      total_rev: 0,
      total_opex: 0,
      total_loss_cost: 0,
      total_dep: 0,
      total_interest: 0,
      total_vat: 0,
      total_surcharge: 0,
      total_income_tax: 0,
      total_tax: 0,
      total_net_profit: 0,
      total_principal: 0,
      min_dscr: 999,
      total_inv_gross: totalInvGross,
      total_inv_net: totalInvNet,
      equity,
      debt,
    };

    for (let year = 1; year <= years; year++) {
      // ---- 3.1 补容处理 ----
      let augCost = 0;
      if (year === inputs.aug_year && inputs.aug_year > 0) {
        augCost = Wh * inputs.aug_price;
        const augVAT = augCost - augCost / (1 + vatRate);
        remainingVAT += augVAT;
        assets.push({
          value: augCost / (1 + vatRate),
          life: inputs.aug_dep_years,
          age: 0
        });
        currentSOH = 0.95;  // 补容后SOH重置
      }
      
      // ---- 3.2 物理量计算 ----
      // 可用容量 = 装机容量 × SOH × DOD
      const usableCapacity = Wh * currentSOH * dod;
      
      // 日放电量 = 可用容量 × 日循环次数
      const dailyDischarge = usableCapacity * cycles;
      
      // 年放电量 (kWh)
      const annualDischargeKWh = (dailyDischarge * runDays) / 1000;
      
      // 年充电量 = 放电量 / RTE
      const annualChargeKWh = annualDischargeKWh / rte;
      
      // 效率损耗电量
      const lossKWh = annualChargeKWh - annualDischargeKWh;
      
      stats.total_discharge_kwh += annualDischargeKWh;
      stats.total_charge_kwh += annualChargeKWh;
      stats.total_loss_kwh += lossKWh;
      
      // ---- 3.3 收入计算 ----
      // 电费套利收入 = 放电量 × 峰谷价差
      const elecRevGross = annualDischargeKWh * inputs.spread;
      
      // 补偿收入
      let subRevGross = 0;
      if (year <= inputs.sub_years) {
        const declineFactor = Math.pow(1 - inputs.sub_decline / 100, year - 1);
        const currentRate = inputs.sub_price * declineFactor;
        
        if (inputs.sub_mode === 'energy') {
          // 内蒙模式：按放电量
          subRevGross = annualDischargeKWh * currentRate;
        } else {
          // 甘肃模式：按功率，时长系数
          const kFactor = Math.min(1, hours / 6.0);
          subRevGross = kW * currentRate * kFactor;
        }
      }
      
      // 或有收益（辅助服务）
      const auxRevGross = kW * inputs.aux_price;
      
      const totalRevGross = elecRevGross + subRevGross + auxRevGross;
      const totalRevNet = totalRevGross / (1 + vatRate);  // 不含税收入
      const outputVAT = totalRevGross - totalRevNet;       // 销项税
      
      stats.total_elec_rev += elecRevGross;
      stats.total_sub_rev += subRevGross;
      stats.total_aux_rev += auxRevGross;
      stats.total_rev += totalRevGross;
      
      // ---- 3.4 成本计算 ----
      // 运维成本
      const opexGross = Wh * inputs.opex;
      const opexVAT = opexGross - opexGross / (1 + vatRate);
      const opexNet = opexGross / (1 + vatRate);
      
      // 效率损耗成本（购电成本）
      const lossCostGross = lossKWh * inputs.price_valley;
      const lossVAT = lossCostGross - lossCostGross / (1 + vatRate);
      const lossCostNet = lossCostGross / (1 + vatRate);
      
      stats.total_opex += opexGross;
      stats.total_loss_cost += lossCostGross;
      
      // ---- 3.5 折旧计算 ----
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
      stats.total_dep += annualDep;
      
      // ---- 3.6 贷款还款 ----
      let interest = 0;
      let principal = 0;
      let debtService = 0;  // 当期还款额
      
      if (year <= loanTerm && remainingDebt > 1) {
        interest = remainingDebt * loanRate;
        const payment = Math.min(annualPMT, remainingDebt + interest);
        principal = payment - interest;
        remainingDebt -= principal;
        debtService = payment;
      }
      stats.total_interest += interest;
      stats.total_principal += principal;
      
      // ---- 3.7 增值税计算 ----
      // 可抵扣进项税 = 运维进项税 + 损耗电费进项税
      const deductibleVAT = opexVAT + lossVAT;
      
      // 应交增值税 = 销项税 - 可抵扣进项税 - 留抵税额
      let vatPayable = outputVAT - deductibleVAT;
      
      // 使用留抵税额抵扣
      if (remainingVAT > 0) {
        if (remainingVAT >= vatPayable) {
          remainingVAT -= vatPayable;
          vatPayable = 0;
        } else {
          vatPayable -= remainingVAT;
          remainingVAT = 0;
        }
      } else if (vatPayable < 0) {
        // 产生新的留抵
        remainingVAT += Math.abs(vatPayable);
        vatPayable = 0;
      }
      
      // 附加税 = 增值税 × 12% (城建7% + 教育3% + 地方2%)
      const surcharge = vatPayable * 0.12;
      
      stats.total_vat += vatPayable;
      stats.total_surcharge += surcharge;
      
      // ---- 3.8 所得税计算 ----
      // 息税前利润 EBIT = 收入 - 运维 - 损耗 - 折旧
      const ebit = totalRevNet - opexNet - lossCostNet - annualDep;
      
      // 息税折旧前利润 EBITDA
      const ebitda = ebit + annualDep;
      
      // 应纳税所得额 = EBIT - 利息 - 附加税
      const taxableIncome = Math.max(0, ebit - interest - surcharge);
      
      // 所得税
      const incomeTax = taxableIncome * taxRate;
      
      // 净利润
      const netProfit = ebit - interest - surcharge - incomeTax;
      
      stats.total_income_tax += incomeTax;
      stats.total_tax += vatPayable + surcharge + incomeTax;
      stats.total_net_profit += netProfit;
      
      // ---- 3.9 现金流计算 ----
      // 股东净现金流 = 净利润 + 折旧 - 本金偿还 - 补容投资
      let cf = netProfit + annualDep - principal;
      if (year === inputs.aug_year && inputs.aug_year > 0) {
        cf -= augCost;
      }
      
      // 最后一年回收残值
      if (year === years) {
        const residualValue = totalInvNet * residualRate;
        cf += residualValue;
      }
      
      equityCF.push(cf);
      cumEquityCF += cf;
      
      // 项目现金流（全投资角度）
      const projectCFYear = ebitda * (1 - taxRate) + annualDep * taxRate - augCost;
      projectCF.push(projectCFYear);
      
      // ---- 3.10 偿债覆盖率 DSCR ----
      // DSCR = (净利润 + 折旧 + 利息) / 当期还款额
      const dscr = debtService > 0 ? (netProfit + annualDep + interest) / debtService : 999;
      if (year <= loanTerm && dscr < minDSCR) {
        minDSCR = dscr;
      }
      
      // ---- 3.11 记录年度数据 ----
      rows.push({
        y: year,
        soh: (currentSOH * 100).toFixed(1) + '%',
        
        charge_kwh: (annualChargeKWh / 10000).toFixed(2),
        discharge_kwh: (annualDischargeKWh / 10000).toFixed(2),
        loss_kwh: (lossKWh / 10000).toFixed(2),
        
        elec_rev: (elecRevGross / 10000).toFixed(2),
        sub_rev: (subRevGross / 10000).toFixed(2),
        aux_rev: (auxRevGross / 10000).toFixed(2),
        total_rev: (totalRevGross / 10000).toFixed(2),
        
        opex: (opexGross / 10000).toFixed(2),
        loss_cost: (lossCostGross / 10000).toFixed(2),
        dep: (annualDep / 10000).toFixed(2),
        interest: (interest / 10000).toFixed(2),
        
        vat_pay: (vatPayable / 10000).toFixed(2),
        surcharge: (surcharge / 10000).toFixed(2),
        income_tax: (incomeTax / 10000).toFixed(2),
        total_tax: ((vatPayable + surcharge + incomeTax) / 10000).toFixed(2),
        
        ebit: (ebit / 10000).toFixed(2),
        ebitda: (ebitda / 10000).toFixed(2),
        net_profit: (netProfit / 10000).toFixed(2),
        principal: (principal / 10000).toFixed(2),
        cf: (cf / 10000).toFixed(2),
        cum_cf: (cumEquityCF / 10000).toFixed(2),
        dscr: dscr === 999 ? '-' : dscr.toFixed(2),
      });
      
      // ---- 3.12 SOH衰减 ----
      // 首年衰减4%，之后每年2.5%
      currentSOH -= year === 1 ? 0.04 : 0.025;
      currentSOH = Math.max(0.6, currentSOH);  // 最低60%
    }
    
    stats.min_dscr = minDSCR === 999 ? 0 : minDSCR;
    
    const calcResult: CalculationResult = {
      equity_cf: equityCF,
      project_cf: projectCF,
      rows,
      stats,
    };
    
    // ========== 4. KPI计算 ==========
    const irr = calculateIRR(equityCF);
    const projIRR = calculateIRR(projectCF);
    const npv = calculateNPV(0.08, projectCF);
    const payback = calculatePayback(equityCF);
    
    // LCOE计算 = 全生命周期成本 / 总放电量
    const lifecycleCost = stats.total_inv_gross + stats.total_opex + stats.total_loss_cost + 
                         stats.total_interest + stats.total_tax;
    const lcoe = lifecycleCost / stats.total_discharge_kwh;
    
    // ROI = 总净利润 / 总投资
    const roi = (stats.total_net_profit / totalInvGross) * 100;
    
    const kpiResult: KpiResult = {
      equity_irr: irr * 100,
      project_irr: projIRR * 100,
      npv: npv / 10000,
      roi,
      payback,
      min_dscr: stats.min_dscr,
      lcoe,
      total_profit: stats.total_net_profit / 10000,
    };
    
    setResult(calcResult);
    setKpi(kpiResult);
  }, [inputs]);

  /**
   * 导出CSV
   */
  const exportCSV = useCallback(() => {
    if (!result) return;
    
    const headers = [
      '年份', 'SOH', '充电量(万kWh)', '放电量(万kWh)', '损耗电量(万kWh)',
      '电费收入', '补偿收入', '或有收益', '总收入',
      '运维成本', '损耗成本', '折旧', '利息',
      '增值税', '附加税', '所得税', '总税金',
      'EBIT', 'EBITDA', '净利润', '本金偿还', '股东现金流', '累计现金流', 'DSCR'
    ];
    
    let txt = headers.join(',') + '\n';
    result.rows.forEach(r => {
      txt += `${r.y},${r.soh},${r.charge_kwh},${r.discharge_kwh},${r.loss_kwh},` +
             `${r.elec_rev},${r.sub_rev},${r.aux_rev},${r.total_rev},` +
             `${r.opex},${r.loss_cost},${r.dep},${r.interest},` +
             `${r.vat_pay},${r.surcharge},${r.income_tax},${r.total_tax},` +
             `${r.ebit},${r.ebitda},${r.net_profit},${r.principal},${r.cf},${r.cum_cf},${r.dscr}\n`;
    });
    
    const link = document.createElement('a');
    link.href = 'data:text/csv;charset=utf-8,\uFEFF' + encodeURI(txt);
    link.download = '储能财务分析表_V13.csv';
    link.click();
  }, [result]);

  /**
   * 计算属性
   */
  const powerMW = useMemo(() => {
    return (inputs.capacity / inputs.duration_hours).toFixed(1);
  }, [inputs.capacity, inputs.duration_hours]);
  
  // 往返效率
  const rte = useMemo(() => {
    return ((inputs.charge_eff / 100) * (inputs.discharge_eff / 100) * 100).toFixed(1);
  }, [inputs.charge_eff, inputs.discharge_eff]);

  return {
    inputs,
    result,
    kpi,
    powerMW,
    rte,
    updateInput,
    calculate,
    exportCSV,
  };
}
