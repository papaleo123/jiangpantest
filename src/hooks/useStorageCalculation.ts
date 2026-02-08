import { useState, useCallback, useMemo } from 'react';
import type { InputParams, CalculationResult, KpiResult, YearlyRow, Stats } from '@/types';

// ==================== 1. 配置常量（避免魔法数字）====================

const FINANCIAL_CONSTANTS = {
  // 衰减率
  DEGRADATION: {
    FIRST_YEAR: 0.04,
    ANNUAL: 0.025,
    MIN_SOH: 0.60,
  },
  // 附加税率（城建7% + 教育3% + 地方2%）
  SURCHARGE_RATE: 0.12,
  // 贷款期限上限
  MAX_LOAN_TERM: 10,
  // 残值率
  RESIDUAL_RATE: 0.05,
  // 折现率（用于NPV/LCOE）
  DISCOUNT_RATE: 0.08,
  // 精度配置
  PRECISION: {
    AMOUNT: 2,    // 金额保留2位
    PERCENTAGE: 1, // 百分比保留1位
    RATIO: 4,     // 系数保留4位
  },
} as const;

// ==================== 2. 工具函数 ====================

/**
 * 精度处理工具 - 避免浮点数误差
 */
const Precision = {
  round: (n: number, digits: number = FINANCIAL_CONSTANTS.PRECISION.AMOUNT): number => {
    const factor = Math.pow(10, digits);
    return Math.round(n * factor) / factor;
  },
  
  // 金额分转为元（避免0.1+0.2≠0.3）
  yuan: (n: number) => Precision.round(n, 2),
  
  // 财务计算专用（4位精度中间计算）
  calc: (n: number) => Precision.round(n, 4),
};

/**
 * 输入校验
 */
const validateInputs = (inputs: InputParams): void => {
  const errors: string[] = [];
  
  if (inputs.capacity <= 0) errors.push('装机容量必须大于0');
  if (inputs.duration_hours <= 0) errors.push('时长必须大于0');
  if (inputs.cycles <= 0) errors.push('日循环次数必须大于0');
  if (inputs.run_days <= 0 || inputs.run_days > 366) errors.push('年运行天数必须在1-366之间');
  if (inputs.debt_ratio < 0 || inputs.debt_ratio > 100) errors.push('贷款比例必须在0-100之间');
  if (inputs.dod <= 0 || inputs.dod > 100) errors.push('放电深度必须在0-100之间');
  if (inputs.charge_eff <= 0 || inputs.discharge_eff <= 0) errors.push('效率必须大于0');
  if (inputs.sub_decline < 0 || inputs.sub_decline > 100) errors.push('补贴退坡率不能大于100%');
  
  if (errors.length > 0) {
    throw new Error(`参数校验失败:\n${errors.join('\n')}`);
  }
};

// ==================== 3. 纯计算模块（可独立单元测试）====================

/**
 * 物理计算模块 - 计算电量、SOH衰减
 */
interface PhysicsResult {
  annualChargeKWh: number;
  annualDischargeKWh: number;
  lossKWh: number;
  nextSOH: number;
}

const calculatePhysics = (
  capacityWh: number,
  currentSOH: number,
  dod: number,
  cycles: number,
  runDays: number,
  rte: number,
  year: number
): PhysicsResult => {
  const usableCapacity = capacityWh * currentSOH * dod;
  const dailyDischarge = usableCapacity * cycles;
  const annualDischargeKWh = Precision.calc((dailyDischarge * runDays) / 1000);
  const annualChargeKWh = Precision.calc(annualDischargeKWh / rte);
  const lossKWh = Precision.calc(annualChargeKWh - annualDischargeKWh);
  
  // SOH衰减
  const degradation = year === 1 
    ? FINANCIAL_CONSTANTS.DEGRADATION.FIRST_YEAR 
    : FINANCIAL_CONSTANTS.DEGRADATION.ANNUAL;
  const nextSOH = Math.max(FINANCIAL_CONSTANTS.DEGRADATION.MIN_SOH, currentSOH - degradation);
  
  return {
    annualChargeKWh,
    annualDischargeKWh,
    lossKWh,
    nextSOH,
  };
};

/**
 * 收入计算模块
 */
interface RevenueResult {
  elecRevGross: number;    // 电费套利收入（含税）
  subRevGross: number;     // 补贴收入（含税）
  auxRevGross: number;     // 辅助服务收入（含税）
  totalRevGross: number;   // 总收入（含税）
  totalRevNet: number;     // 总收入（不含税）
  outputVAT: number;       // 销项税
}

const calculateRevenue = (
  params: {
    annualDischargeKWh: number;
    spread: number;
    auxPrice: number;
    powerKW: number;
    durationHours: number;
    subMode: 'energy' | 'capacity';
    subPrice: number;
    subYears: number;
    subDecline: number;
    vatRate: number;
  },
  year: number
): RevenueResult => {
  const { 
    annualDischargeKWh, spread, auxPrice, powerKW, durationHours,
    subMode, subPrice, subYears, subDecline, vatRate 
  } = params;
  
  // 电费套利
  const elecRevGross = Precision.yuan(annualDischargeKWh * spread);
  
  // 补贴收入
  let subRevGross = 0;
  if (year <= subYears) {
    const declineFactor = Math.pow(1 - subDecline / 100, year - 1);
    const currentRate = subPrice * declineFactor;
    
    if (subMode === 'energy') {
      subRevGross = Precision.yuan(annualDischargeKWh * currentRate);
    } else {
      const kFactor = Math.min(1, durationHours / 6.0);
      subRevGross = Precision.yuan(powerKW * currentRate * kFactor);
    }
  }
  
  // 辅助服务
  const auxRevGross = Precision.yuan(powerKW * auxPrice);
  
  const totalRevGross = Precision.yuan(elecRevGross + subRevGross + auxRevGross);
  const totalRevNet = Precision.yuan(totalRevGross / (1 + vatRate));
  const outputVAT = Precision.yuan(totalRevGross - totalRevNet);
  
  return {
    elecRevGross,
    subRevGross,
    auxRevGross,
    totalRevGross,
    totalRevNet,
    outputVAT,
  };
};

/**
 * 运营成本计算
 */
interface CostResult {
  opexGross: number;
  opexNet: number;
  opexVAT: number;
  lossCostGross: number;
  lossCostNet: number;
  lossVAT: number;
}

const calculateOperatingCosts = (
  capacityWh: number,
  opexRate: number,
  lossKWh: number,
  priceValley: number,
  vatRate: number
): CostResult => {
  // 运维成本
  const opexGross = Precision.yuan(capacityWh * opexRate);
  const opexNet = Precision.yuan(opexGross / (1 + vatRate));
  const opexVAT = Precision.yuan(opexGross - opexNet);
  
  // 损耗电费
  const lossCostGross = Precision.yuan(lossKWh * priceValley);
  const lossCostNet = Precision.yuan(lossCostGross / (1 + vatRate));
  const lossVAT = Precision.yuan(lossCostGross - lossCostNet);
  
  return {
    opexGross,
    opexNet,
    opexVAT,
    lossCostGross,
    lossCostNet,
    lossVAT,
  };
};

/**
 * 折旧计算 - 支持多资产
 */
interface Asset {
  value: number;      // 资产原值(不含税)
  life: number;       // 折旧年限
  age: number;        // 已使用年数
  residualRate: number;
}

const calculateDepreciation = (assets: Asset[]): { annualDep: number; updatedAssets: Asset[] } => {
  let annualDep = 0;
  const updatedAssets: Asset[] = [];
  
  for (const asset of assets) {
    if (asset.age < asset.life) {
      const dep = Precision.yuan(asset.value * (1 - asset.residualRate) / asset.life);
      annualDep += dep;
      updatedAssets.push({
        ...asset,
        age: asset.age + 1,
      });
    }
    // 已折旧完毕的资产不再加入列表
  }
  
  return { annualDep: Precision.yuan(annualDep), updatedAssets };
};

/**
 * 贷款还款计算 - 等额本息
 */
interface LoanResult {
  interest: number;
  principal: number;
  debtService: number;
  remainingDebt: number;
}

const calculateLoanService = (
  remainingDebt: number,
  annualPMT: number,
  loanRate: number,
  year: number,
  loanTerm: number
): LoanResult => {
  if (year > loanTerm || remainingDebt <= 1) {
    return { interest: 0, principal: 0, debtService: 0, remainingDebt };
  }
  
  const interest = Precision.yuan(remainingDebt * loanRate);
  const payment = Math.min(annualPMT, remainingDebt + interest);
  const principal = Precision.yuan(payment - interest);
  const newRemainingDebt = Precision.yuan(remainingDebt - principal);
  
  return {
    interest,
    principal,
    debtService: payment,
    remainingDebt: newRemainingDebt,
  };
};

/**
 * 税务计算模块
 */
interface TaxResult {
  vatPayable: number;      // 应交增值税
  remainingVATCredit: number; // 剩余留抵税额
  surcharge: number;       // 附加税
  taxableIncome: number;   // 应纳税所得额
  incomeTax: number;       // 所得税
  netProfit: number;       // 净利润
  ebit: number;            // 息税前利润
  ebitda: number;          // 息税折旧前利润
}

const calculateTaxes = (
  revenueNet: number,
  costs: { opexNet: number; lossCostNet: number },
  depreciation: number,
  interest: number,
  outputVAT: number,
  inputVAT: number,
  existingVATCredit: number,
  taxRate: number
): TaxResult & { newVATCredit: number } => {
  // 1. 增值税计算
  const deductibleVAT = inputVAT;
  let vatPayable = Precision.yuan(outputVAT - deductibleVAT);
  let remainingVAT = existingVATCredit;
  
  if (remainingVAT > 0) {
    if (remainingVAT >= vatPayable) {
      remainingVAT = Precision.yuan(remainingVAT - vatPayable);
      vatPayable = 0;
    } else {
      vatPayable = Precision.yuan(vatPayable - remainingVAT);
      remainingVAT = 0;
    }
  } else if (vatPayable < 0) {
    remainingVAT = Precision.yuan(Math.abs(vatPayable));
    vatPayable = 0;
  }
  
  // 2. 附加税
  const surcharge = Precision.yuan(vatPayable * FINANCIAL_CONSTANTS.SURCHARGE_RATE);
  
  // 3. 所得税计算
  const ebit = Precision.yuan(revenueNet - costs.opexNet - costs.lossCostNet - depreciation);
  const ebitda = Precision.yuan(ebit + depreciation);
  const taxableIncome = Math.max(0, Precision.yuan(ebit - interest - surcharge));
  const incomeTax = Precision.yuan(taxableIncome * taxRate);
  const netProfit = Precision.yuan(ebit - interest - surcharge - incomeTax);
  
  return {
    vatPayable,
    remainingVATCredit: remainingVAT,
    newVATCredit: remainingVAT,
    surcharge,
    taxableIncome,
    incomeTax,
    netProfit,
    ebit,
    ebitda,
  };
};

// ==================== 4. 核心财务算法（保持原有）====================

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

function calculateNPV(rate: number, cf: number[]): number {
  return cf.reduce((npv, cashflow, t) => npv + cashflow / Math.pow(1 + rate, t), 0);
}

function calculatePayback(equityCF: number[]): number {
  let cum = 0;
  for (let i = 0; i < equityCF.length; i++) {
    const pre = cum;
    cum += equityCF[i];
    if (cum > 0) {
      return Math.max(0, (i - 1) + Math.abs(pre) / equityCF[i]);
    }
  }
  return 99;
}

function calculatePMT(principal: number, rate: number, periods: number): number {
  if (rate === 0) return principal / periods;
  return principal * rate * Math.pow(1 + rate, periods) / (Math.pow(1 + rate, periods) - 1);
}

// ==================== 5. 重构后的主Hook ====================

export function useStorageCalculation() {
  const [inputs, setInputs] = useState<InputParams>({
    years: 20,
    sub_mode: 'energy',
    sub_price: 0.35,
    sub_years: 10,
    sub_decline: 0,
    aux_price: 0,
    capacity: 100,
    duration_hours: 2,
    charge_eff: 94,
    discharge_eff: 94,
    dod: 90,
    price_valley: 0.30,
    capex: 1.20,
    spread: 0.70,
    opex: 0.02,
    cycles: 2.0,
    run_days: 330,
    dep_years: 15,
    debt_ratio: 70,
    loan_rate: 3.5,
    vat_rate: 13,
    tax_rate: 25,
    aug_year: 0,
    aug_price: 0.6,
    aug_dep_years: 15,
    residual_rate: 5,
    constructionPeriod: 12,
    investmentItems: [],
  });

  const [result, setResult] = useState<CalculationResult | null>(null);
  const [kpi, setKpi] = useState<KpiResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const updateInput = useCallback(<K extends keyof InputParams>(
    key: K,
    value: InputParams[K]
  ) => {
    setInputs(prev => ({ ...prev, [key]: value }));
    setError(null); // 清除错误
  }, []);

  const calculate = useCallback(() => {
    try {
      // 5.1 输入校验
      validateInputs(inputs);
      
      // 5.2 基础参数转换
      const params = {
        MWh: inputs.capacity,
        hours: inputs.duration_hours,
        MW: inputs.capacity / inputs.duration_hours,
        Wh: inputs.capacity * 1e6,
        kW: (inputs.capacity / inputs.duration_hours) * 1000,
        chargeEff: inputs.charge_eff / 100,
        dischargeEff: inputs.discharge_eff / 100,
        rte: (inputs.charge_eff / 100) * (inputs.discharge_eff / 100),
        dod: inputs.dod / 100,
        years: inputs.years,
        cycles: inputs.cycles,
        runDays: inputs.run_days,
        vatRate: inputs.vat_rate / 100,
        taxRate: inputs.tax_rate / 100,
        residualRate: inputs.residual_rate / 100,
        debtRatio: inputs.debt_ratio / 100,
        loanRate: inputs.loan_rate / 100,
        loanTerm: Math.min(FINANCIAL_CONSTANTS.MAX_LOAN_TERM, inputs.years),
      };

      // 5.3 投资计算（支持明细或 Capex）
      let totalInvGross: number;
      let totalInvNet: number;
      let inputVAT: number;

      if (inputs.investmentItems && inputs.investmentItems.length > 0) {
        totalInvGross = inputs.investmentItems.reduce((sum, item) => sum + (item.amount || 0), 0);
        totalInvNet = inputs.investmentItems.reduce((sum, item) => {
          const rate = (item.taxRate || 13) / 100;
          return sum + (item.amount / (1 + rate));
        }, 0);
        inputVAT = totalInvGross - totalInvNet;
      } else {
        totalInvGross = params.Wh * inputs.capex;
        totalInvNet = totalInvGross / (1 + params.vatRate);
        inputVAT = totalInvGross - totalInvNet;
      }

      // 融资计算
      const debt = Precision.yuan(totalInvGross * params.debtRatio);
      const equity = Precision.yuan(totalInvGross * (1 - params.debtRatio));
      const annualPMT = calculatePMT(debt, params.loanRate, params.loanTerm);

      // 5.4 初始化资产
      let assets: Asset[] = [{
        value: totalInvNet,
        life: inputs.dep_years,
        age: 0,
        residualRate: params.residualRate,
      }];

      // 5.5 年度循环计算
      let currentSOH = 1.0;
      let remainingVAT = inputVAT;
      let remainingDebt = debt;
      
      const equityCF: number[] = [-equity];
      const projectCF: number[] = [-totalInvNet];
      const costCF: number[] = [-totalInvNet]; // 用于LCOE：不含税初始投资
      const generationCF: number[] = [0];      // 用于LCOE：发电量
      
      const rows: YearlyRow[] = [];
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

      for (let year = 1; year <= params.years; year++) {
        // 补容处理
        let augCost = 0;
        // let augDep = 0; // 预留，暂未使用
        if (year === inputs.aug_year && inputs.aug_year > 0) {
          augCost = params.Wh * inputs.aug_price;
          const augVAT = augCost - augCost / (1 + params.vatRate);
          const augNet = augCost / (1 + params.vatRate);
          
          remainingVAT += augVAT;
          assets.push({
            value: augNet,
            life: inputs.aug_dep_years,
            age: 0,
            residualRate: params.residualRate,
          });
          currentSOH = 0.95;
          
          // 补容当年增加投资支出（用于LCOE）
          costCF[0] = Precision.yuan(costCF[0] + augNet);
        }

        // 物理计算
        const physics = calculatePhysics(
          params.Wh, currentSOH, params.dod, params.cycles, 
          params.runDays, params.rte, year
        );

        // 收入计算
        const revenue = calculateRevenue({
          annualDischargeKWh: physics.annualDischargeKWh,
          spread: inputs.spread,
          auxPrice: inputs.aux_price,
          powerKW: params.kW,
          durationHours: params.hours,
          subMode: inputs.sub_mode,
          subPrice: inputs.sub_price,
          subYears: inputs.sub_years,
          subDecline: inputs.sub_decline,
          vatRate: params.vatRate,
        }, year);

        // 成本计算
        const costs = calculateOperatingCosts(
          params.Wh, inputs.opex, physics.lossKWh, 
          inputs.price_valley, params.vatRate
        );

        // 折旧计算
        const { annualDep, updatedAssets } = calculateDepreciation(assets);
        assets = updatedAssets;
        if (year === inputs.aug_year && inputs.aug_year > 0) {
          augDep = annualDep; // 补容当年折旧已包含新资产
        }

        // 贷款计算
        const loan = calculateLoanService(remainingDebt, annualPMT, params.loanRate, year, params.loanTerm);
        remainingDebt = loan.remainingDebt;

        // 税务计算
        const taxes = calculateTaxes(
          revenue.totalRevNet,
          { opexNet: costs.opexNet, lossCostNet: costs.lossCostNet },
          annualDep,
          loan.interest,
          revenue.outputVAT,
          costs.opexVAT + costs.lossVAT,
          remainingVAT,
          params.taxRate
        );
        remainingVAT = taxes.newVATCredit;

        // 更新统计
        stats.total_charge_kwh += physics.annualChargeKWh;
        stats.total_discharge_kwh += physics.annualDischargeKWh;
        stats.total_loss_kwh += physics.lossKWh;
        stats.total_elec_rev += revenue.elecRevGross;
        stats.total_sub_rev += revenue.subRevGross;
        stats.total_aux_rev += revenue.auxRevGross;
        stats.total_rev += revenue.totalRevGross;
        stats.total_opex += costs.opexGross;
        stats.total_loss_cost += costs.lossCostGross;
        stats.total_dep += annualDep;
        stats.total_interest += loan.interest;
        stats.total_vat += taxes.vatPayable;
        stats.total_surcharge += taxes.surcharge;
        stats.total_income_tax += taxes.incomeTax;
        stats.total_tax += taxes.vatPayable + taxes.surcharge + taxes.incomeTax;
        stats.total_net_profit += taxes.netProfit;
        stats.total_principal += loan.principal;

        // DSCR计算
        const dscr = loan.debtService > 0 
          ? (taxes.netProfit + annualDep + loan.interest) / loan.debtService 
          : 999;
        if (year <= params.loanTerm && dscr < minDSCR) {
          minDSCR = dscr;
        }

        // 现金流计算
        // 股东现金流 = 净利润 + 折旧 - 本金 - 补容投资
        let cf = taxes.netProfit + annualDep - loan.principal;
        if (year === inputs.aug_year && inputs.aug_year > 0) {
          cf -= augCost;
        }
        
        // 项目现金流（全投资视角，不含融资）
        // 修正：使用 EBIT(1-t) + 折旧 - 补容，而非 EBITDA(1-t)
        const projectCFYear = taxes.ebit * (1 - params.taxRate) + annualDep - augCost;
        
        // 最后一年回收残值
        let residualValue = 0;
        if (year === params.years) {
          // 计算剩余资产残值（考虑补容）
          residualValue = assets.reduce((sum, asset) => {
            return sum + asset.value * asset.residualRate;
          }, 0);
          cf += residualValue;
        }

        cumEquityCF += cf;
        
        equityCF.push(Precision.yuan(cf));
        projectCF.push(Precision.yuan(projectCFYear + (year === params.years ? residualValue : 0)));
        
        // LCOE计算准备
        // 成本现金流：运维(不含税) + 损耗(不含税) + 税金 - 补容(不含税)
        const yearCostNet = costs.opexNet + costs.lossCostNet + taxes.vatPayable + taxes.surcharge + taxes.incomeTax;
        costCF.push(Precision.yuan(yearCostNet - (year === params.years ? residualValue : 0)));
        generationCF.push(physics.annualDischargeKWh);

        // 记录行数据
        rows.push({
          y: year,
          soh: `${(currentSOH * 100).toFixed(1)}%`,
          charge_kwh: (physics.annualChargeKWh / 10000).toFixed(2),
          discharge_kwh: (physics.annualDischargeKWh / 10000).toFixed(2),
          loss_kwh: (physics.lossKWh / 10000).toFixed(2),
          elec_rev: (revenue.elecRevGross / 10000).toFixed(2),
          sub_rev: (revenue.subRevGross / 10000).toFixed(2),
          aux_rev: (revenue.auxRevGross / 10000).toFixed(2),
          total_rev: (revenue.totalRevGross / 10000).toFixed(2),
          opex: (costs.opexGross / 10000).toFixed(2),
          loss_cost: (costs.lossCostGross / 10000).toFixed(2),
          dep: (annualDep / 10000).toFixed(2),
          interest: (loan.interest / 10000).toFixed(2),
          vat_pay: (taxes.vatPayable / 10000).toFixed(2),
          surcharge: (taxes.surcharge / 10000).toFixed(2),
          income_tax: (taxes.incomeTax / 10000).toFixed(2),
          total_tax: ((taxes.vatPayable + taxes.surcharge + taxes.incomeTax) / 10000).toFixed(2),
          ebit: (taxes.ebit / 10000).toFixed(2),
          ebitda: (taxes.ebitda / 10000).toFixed(2),
          net_profit: (taxes.netProfit / 10000).toFixed(2),
          principal: (loan.principal / 10000).toFixed(2),
          cf: (cf / 10000).toFixed(2),
          cum_cf: (cumEquityCF / 10000).toFixed(2),
          dscr: dscr === 999 ? '-' : dscr.toFixed(2),
        });

        // 更新SOH用于下一年
        currentSOH = physics.nextSOH;
      }

      stats.min_dscr = minDSCR === 999 ? 0 : minDSCR;

      // 5.6 KPI计算
      const irr = calculateIRR(equityCF);
      const projIRR = calculateIRR(projectCF);
      const npv = calculateNPV(FINANCIAL_CONSTANTS.DISCOUNT_RATE, projectCF);
      const payback = calculatePayback(equityCF);

      // 修正后的LCOE计算（成本现值/发电量现值）
      const npvCost = calculateNPV(FINANCIAL_CONSTANTS.DISCOUNT_RATE, costCF);
      const npvGen = calculateNPV(FINANCIAL_CONSTANTS.DISCOUNT_RATE, generationCF);
      const lcoe = npvGen > 0 ? Precision.yuan(npvCost / npvGen) : 0;
      
      // ROI计算
      const roi = (stats.total_net_profit / totalInvGross) * 100;

      const calcResult: CalculationResult = {
        equity_cf: equityCF,
        project_cf: projectCF,
        rows,
        stats,
      };

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
      setError(null);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : '计算发生错误');
      setResult(null);
      setKpi(null);
    }
  }, [inputs]);

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
    
    const blob = new Blob([txt], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = '储能财务分析表_V14_重构版.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [result]);

  const powerMW = useMemo(() => {
    return (inputs.capacity / inputs.duration_hours).toFixed(1);
  }, [inputs.capacity, inputs.duration_hours]);
  
  const rte = useMemo(() => {
    return ((inputs.charge_eff / 100) * (inputs.discharge_eff / 100) * 100).toFixed(1);
  }, [inputs.charge_eff, inputs.discharge_eff]);

  return {
    inputs,
    result,
    kpi,
    error,
    powerMW,
    rte,
    updateInput,
    calculate,
    exportCSV,
  };
}

