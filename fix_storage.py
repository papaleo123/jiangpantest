import os
import shutil
import re

# ================= 配置路径 =================
# 请确保路径正确
HOOK_PATH = "/Users/papaleo/Desktop/app/src/hooks/useStorageCalculation.ts"
UTILS_PATH = "/Users/papaleo/Desktop/app/src/utils/calculationDetails.ts"

# ================= 1. 修复后的 Hook 完整代码 =================
FIXED_HOOK_CONTENT = r"""import { useState, useCallback, useMemo } from 'react';
import type { InputParams, CalculationResult, KpiResult, YearlyRow, Stats } from '@/types';

// ==================== 1. 配置常量 ====================

const FINANCIAL_CONSTANTS = {
  DEGRADATION: {
    FIRST_YEAR: 0.04,
    ANNUAL: 0.025,
    MIN_SOH: 0.60,
  },
  SURCHARGE_RATE: 0.12,
  MAX_LOAN_TERM: 10,
  RESIDUAL_RATE: 0.05,
  DISCOUNT_RATE: 0.08,
  PRECISION: {
    AMOUNT: 2,
    PERCENTAGE: 1,
    RATIO: 4,
  },
} as const;

// ==================== 2. 工具函数 ====================

const Precision = {
  round: (n: number, digits: number = FINANCIAL_CONSTANTS.PRECISION.AMOUNT): number => {
    const factor = Math.pow(10, digits);
    return Math.round(n * factor) / factor;
  },
  yuan: (n: number) => Precision.round(n, 2),
  calc: (n: number) => Precision.round(n, 4),
};

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
  if (errors.length > 0) throw new Error(`参数校验失败:\n${errors.join('\n')}`);
};

// ==================== 3. 纯计算模块 ====================

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
  chargeEff: number,
  dischargeEff: number,
  year: number
): PhysicsResult => {
  const degradation = year === 1 
    ? FINANCIAL_CONSTANTS.DEGRADATION.FIRST_YEAR 
    : FINANCIAL_CONSTANTS.DEGRADATION.ANNUAL;
  
  const yearEndSOH = Math.max(FINANCIAL_CONSTANTS.DEGRADATION.MIN_SOH, currentSOH - degradation);
  const avgSOH = (currentSOH + yearEndSOH) / 2; 
  
  const usableCapacityDC = capacityWh * avgSOH * dod; 
  
  const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
  const annualDischargeKWh = Precision.calc((dailyDischargeAC * runDays) / 1000);
  
  const dailyChargeAC = usableCapacityDC / chargeEff * cycles;
  const annualChargeKWh = Precision.calc((dailyChargeAC * runDays) / 1000);
  const lossKWh = Precision.calc(annualChargeKWh - annualDischargeKWh);
  
  return {
    annualChargeKWh,
    annualDischargeKWh,
    lossKWh,
    nextSOH: yearEndSOH,
  };
};

interface RevenueResult {
  elecRevGross: number;
  subRevGross: number;
  auxRevGross: number;
  totalRevGross: number;
  totalRevNet: number;
  outputVAT: number;
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
  const { annualDischargeKWh, spread, auxPrice, powerKW, durationHours, subMode, subPrice, subYears, subDecline, vatRate } = params;
  
  const elecRevGross = Precision.yuan(annualDischargeKWh * spread);
  
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
  
  const auxRevGross = Precision.yuan(powerKW * auxPrice);
  const totalRevGross = Precision.yuan(elecRevGross + subRevGross + auxRevGross);
  const totalRevNet = Precision.yuan(totalRevGross / (1 + vatRate));
  const outputVAT = Precision.yuan(totalRevGross - totalRevNet);
  
  return { elecRevGross, subRevGross, auxRevGross, totalRevGross, totalRevNet, outputVAT };
};

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
  const opexGross = Precision.yuan(capacityWh * opexRate);
  const opexNet = Precision.yuan(opexGross / (1 + vatRate));
  const opexVAT = Precision.yuan(opexGross - opexNet);
  
  const lossCostGross = Precision.yuan(lossKWh * priceValley);
  const lossCostNet = Precision.yuan(lossCostGross / (1 + vatRate));
  const lossVAT = Precision.yuan(lossCostGross - lossCostNet);
  
  return { opexGross, opexNet, opexVAT, lossCostGross, lossCostNet, lossVAT };
};

interface Asset {
  value: number;
  life: number;
  age: number;
  residualRate: number;
}

const calculateDepreciation = (assets: Asset[]): { annualDep: number; updatedAssets: Asset[] } => {
  let annualDep = 0;
  const updatedAssets: Asset[] = [];
  
  for (const asset of assets) {
    if (asset.age < asset.life) {
      const dep = Precision.yuan(asset.value * (1 - asset.residualRate) / asset.life);
      annualDep += dep;
    }
    updatedAssets.push({
      ...asset,
      age: asset.age + 1,
    });
  }
  
  return { annualDep: Precision.yuan(annualDep), updatedAssets };
};

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
  
  return { interest, principal, debtService: payment, remainingDebt: newRemainingDebt };
};

interface TaxResult {
  vatPayable: number;
  remainingVATCredit: number;
  surcharge: number;
  taxableIncome: number;
  incomeTax: number;
  netProfit: number;
  ebit: number;
  ebitda: number;
}

const calculateTaxes = (
  revenueNet: number,
  costs: { opexNet: number; lossCostNet: number },
  depreciation: number,
  interest: number,
  outputVAT: number,
  inputVAT: number,
  existingVATCredit: number,
  taxRate: number, 
  surchargeRate: number
): TaxResult & { newVATCredit: number } => {
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
  
  const surcharge = Precision.yuan(vatPayable * surchargeRate);
  
  // EBIT = 收入 - 运维 - 损耗 - 折旧
  const ebit = Precision.yuan(revenueNet - costs.opexNet - costs.lossCostNet - depreciation);
  const ebitda = Precision.yuan(ebit + depreciation);
  
  // 应纳税所得额 = EBIT - 利息 - 附加税
  const taxableIncome = Math.max(0, Precision.yuan(ebit - interest - surcharge));
  const incomeTax = Precision.yuan(taxableIncome * taxRate);
  
  // 净利润
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

// ==================== 5. 主 Hook ====================

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
    surcharge_rate: 12,
    tax_preferential_years: 0, 
    tax_preferential_rate: 15,
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
    setError(null);
  }, []);

  const sensitivityData = useMemo(() => {
    if (!inputs) return [];
    return []; 
  }, [inputs]);

  const calculate = useCallback(() => {
    try {
      const safeInputs = {
        ...inputs,
        tax_preferential_years: Number(inputs.tax_preferential_years || 0),
        tax_preferential_rate: Number(inputs.tax_preferential_rate || 15),
        tax_rate: Number(inputs.tax_rate || 25),
      };
      
      validateInputs(safeInputs);
      
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

      const debt = Precision.yuan(totalInvGross * params.debtRatio);
      const equity = Precision.yuan(totalInvGross * (1 - params.debtRatio));
      const annualPMT = calculatePMT(debt, params.loanRate, params.loanTerm);

      let assets: Asset[] = [{
        value: totalInvNet,
        life: inputs.dep_years,
        age: 0,
        residualRate: params.residualRate,
      }];

      let currentSOH = 1.0;
      let remainingVAT = inputVAT;
      let remainingDebt = debt;
      
      const equityCF: number[] = [-equity];
      const projectCF: number[] = [-totalInvNet];
      const costCF: number[] = [-totalInvNet];
      const generationCF: number[] = [0];
      
      const rows: YearlyRow[] = [];
      let cumEquityCF = -equity;
      let minDSCR = 999;
      
      const stats: Stats = {
        total_charge_kwh: 0, total_discharge_kwh: 0, total_loss_kwh: 0,
        total_elec_rev: 0, total_sub_rev: 0, total_aux_rev: 0, total_rev: 0,
        total_opex: 0, total_loss_cost: 0, total_dep: 0, total_interest: 0,
        total_vat: 0, total_surcharge: 0, total_income_tax: 0, total_tax: 0,
        total_net_profit: 0, total_principal: 0, min_dscr: 999,
        total_inv_gross: totalInvGross, total_inv_net: totalInvNet, equity, debt,
      };

      for (let year = 1; year <= params.years; year++) {
        let augCost = 0;     
        let augNet = 0;     
        
        if (year === inputs.aug_year && inputs.aug_year > 0) {
          augCost = params.Wh * inputs.aug_price;
          const augVAT = augCost - augCost / (1 + params.vatRate);
          augNet = augCost / (1 + params.vatRate);
          
          remainingVAT += augVAT;
          assets.push({
            value: augNet,
            life: inputs.aug_dep_years,
            age: 0,
            residualRate: params.residualRate,
          });
          currentSOH = 0.95; 
        }

        const physics = calculatePhysics(
          params.Wh, currentSOH, params.dod, params.cycles, 
          params.runDays, params.chargeEff, params.dischargeEff, year
        );

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

        const costs = calculateOperatingCosts(
          params.Wh, inputs.opex, physics.lossKWh, 
          inputs.price_valley, params.vatRate
        );

        const { annualDep, updatedAssets } = calculateDepreciation(assets);
        assets = updatedAssets;

        const loan = calculateLoanService(remainingDebt, annualPMT, params.loanRate, year, params.loanTerm);
        remainingDebt = loan.remainingDebt;

        const surchargeRateInput = (inputs.surcharge_rate ?? 12) / 100;
        const prefYears = Number(inputs.tax_preferential_years || 0);
        const prefRate = Number(inputs.tax_preferential_rate || 15) / 100;
        const currentTaxRate = (prefYears > 0 && year <= prefYears) ? prefRate : params.taxRate;

        const taxes = calculateTaxes(
          revenue.totalRevNet,
          { opexNet: costs.opexNet, lossCostNet: costs.lossCostNet },
          annualDep, loan.interest, revenue.outputVAT,
          costs.opexVAT + costs.lossVAT, remainingVAT,
          currentTaxRate, surchargeRateInput
        );
        remainingVAT = taxes.newVATCredit;

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

        const dscr = loan.debtService > 0 ? (taxes.netProfit + annualDep + loan.interest) / loan.debtService : 999;
        if (year <= params.loanTerm && dscr < minDSCR) minDSCR = dscr;

        let cf = taxes.netProfit + annualDep - loan.principal;
        if (year === inputs.aug_year && inputs.aug_year > 0) {
          cf -= augCost; 
        }
        
        const nopat = (taxes.ebit - taxes.surcharge) * (1 - currentTaxRate);
        let projectCFYear = nopat + annualDep;
        if (year === inputs.aug_year && inputs.aug_year > 0) {
           projectCFYear -= augNet;
        }
        
        let residualValue = 0;
        if (year === params.years) {
          residualValue = assets.reduce((sum, asset) => sum + asset.value * asset.residualRate, 0);
          cf += residualValue;
          projectCFYear += residualValue;
        }

        cumEquityCF += cf;
        equityCF.push(Precision.yuan(cf));
        projectCF.push(Precision.yuan(projectCFYear));
        
        let yearCostLCOE = costs.opexNet + costs.lossCostNet;
        if (year === inputs.aug_year && inputs.aug_year > 0) yearCostLCOE += augNet;
        if (year === params.years) yearCostLCOE -= residualValue;
        
        costCF.push(Precision.yuan(yearCostLCOE));
        generationCF.push(physics.annualDischargeKWh);

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

        currentSOH = physics.nextSOH;
      }

      stats.min_dscr = minDSCR === 999 ? 0 : minDSCR;

      const irr = calculateIRR(equityCF);
      const projIRR = calculateIRR(projectCF);
      const npv = calculateNPV(FINANCIAL_CONSTANTS.DISCOUNT_RATE, projectCF);
      const payback = calculatePayback(equityCF);
      const projectPayback = calculatePayback(projectCF);

      const npvCost = calculateNPV(FINANCIAL_CONSTANTS.DISCOUNT_RATE, costCF);
      const npvGen = calculateNPV(FINANCIAL_CONSTANTS.DISCOUNT_RATE, generationCF);
      const lcoe = npvGen > 0 ? Precision.yuan(npvCost / npvGen) : 0;
      
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
        project_payback: projectPayback,
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
    let txt = headers.join(',') + '\\n';
    result.rows.forEach(r => {
      txt += `${r.y},${r.soh},${r.charge_kwh},${r.discharge_kwh},${r.loss_kwh},` +
             `${r.elec_rev},${r.sub_rev},${r.aux_rev},${r.total_rev},` +
             `${r.opex},${r.loss_cost},${r.dep},${r.interest},` +
             `${r.vat_pay},${r.surcharge},${r.income_tax},${r.total_tax},` +
             `${r.ebit},${r.ebitda},${r.net_profit},${r.principal},${r.cf},${r.cum_cf},${r.dscr}\\n`;
    });
    const blob = new Blob([txt], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = '储能财务分析表_V15_Fixed.csv';
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
    sensitivityData,
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
"""

# ================= 2. 修复后的 Utils 完整代码 (TS Error Fixed) =================
FIXED_UTILS_CONTENT = r"""import type { InputParams, YearlyRow } from "@/types";

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

  const taxRate = (inputs?.tax_rate || 25) / 100;
  const taxPreferentialYears = inputs?.tax_preferential_years || 0;
  const taxPreferentialRate = (inputs?.tax_preferential_rate || 15) / 100;
  
  // SOH 计算逻辑
  let yearStartSOH: number;
  if (year === 1) {
    yearStartSOH = 1.0;
  } else if (year === (inputs?.aug_year || 0) && inputs?.aug_year > 0) {
    yearStartSOH = 0.95; 
  } else if (inputs?.aug_year > 0 && year > inputs?.aug_year) {
    yearStartSOH = 0.95 - (year - inputs?.aug_year - 1) * 0.025; 
  } else {
    yearStartSOH = 1.0 - 0.04 - (year - 2) * 0.025; 
  }
  yearStartSOH = Math.max(0.60, yearStartSOH);
  
  const degradation = year === 1 ? 0.04 : 0.025;
  const yearEndSOH = Math.max(0.60, yearStartSOH - degradation);
  const currentSOH = (yearStartSOH + yearEndSOH) / 2; // 平均SOH
  
  const capacityWh = (inputs?.capacity || 100) * 1e6;
  const dod = (inputs?.dod || 90) / 100;
  const cycles = inputs?.cycles || 2;
  const runDays = inputs?.run_days || 330;
  const chargeEff = (inputs?.charge_eff || 94) / 100;
  const dischargeEff = (inputs?.discharge_eff || 94) / 100;
  
  const powerKW = (inputs?.capacity || 100) * 1000 / (inputs?.duration_hours || 2); 
  const durationHours = inputs?.duration_hours || 2;
  const subMode = inputs?.sub_mode || 'energy';
  const subPrice = inputs?.sub_price || 0.35;
  const subDecline = inputs?.sub_decline || 0;
  const spread = inputs?.spread || 0.70;
  const auxPrice = inputs?.aux_price || 0;
  
  const declineFactor = Math.pow(1 - subDecline / 100, year - 1);
  const currentSubPrice = subPrice * declineFactor;
  
  const vatRate = (inputs?.vat_rate || 13) / 100;
  const priceValley = inputs?.price_valley || 0.30;
  
  switch (type) {
    case 'discharge_kwh': {
      const usableCapacityDC = capacityWh * currentSOH * dod; 
      const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
      const annualDischargeKWh = (dailyDischargeAC * runDays) / 1000;
      
      return {
        title: '放电量计算',
        description: `第${year}年放电量`,
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
          { label: '年放电量', value: (annualDischargeKWh / 10000).toFixed(2), unit: '万kWh', formula: '(日放电量 × runDays) ÷ 1000' },
        ],
        result: { value: rowData.discharge_kwh, unit: '万kWh' }
      };
    }
    
    case 'charge_kwh': {
      const usableCapacityDC = capacityWh * currentSOH * dod; 
      const dailyChargeAC = usableCapacityDC / chargeEff * cycles; 
      const annualChargeKWh = (dailyChargeAC * runDays) / 1000;
      
      return {
        title: '充电量计算',
        description: `第${year}年充电量`,
        formula: '直流可用容量 ÷ 充电效率 × 日循环',
        steps: [
          { label: '直流可用容量', value: (usableCapacityDC / 1e6).toFixed(2), unit: 'MWh', formula: 'capacityWh × SOH × DOD' },
          { label: '充电效率', value: (chargeEff * 100).toFixed(0), unit: '%', formula: '输入参数' },
          { label: '日充电量(AC)', value: (dailyChargeAC / 1000).toFixed(2), unit: 'kWh', formula: 'usableCapacityDC ÷ chargeEff × cycles' },
          { label: '年运行天数', value: runDays, unit: '天', formula: '输入参数' },
          { label: '年充电量', value: (annualChargeKWh / 10000).toFixed(2), unit: '万kWh', formula: '日充电量 × runDays ÷ 1000' },
        ],
        result: { value: rowData.charge_kwh, unit: '万kWh' }
      };
    }
    
    case 'loss_kwh': {
      const usableCapacityDC = capacityWh * currentSOH * dod;
      const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
      const annualDischargeKWh = (dailyDischargeAC * runDays) / 1000;
      const dailyChargeAC = usableCapacityDC / chargeEff * cycles;
      const annualChargeKWh = (dailyChargeAC * runDays) / 1000;
      const lossKWh = annualChargeKWh - annualDischargeKWh;
      
      return {
        title: '损耗电量',
        description: '充放电过程中的能量损耗',
        formula: '充电量 - 放电量',
        steps: [
          { label: '年充电量', value: (annualChargeKWh / 10000).toFixed(2), unit: '万kWh', formula: '见充电量计算' },
          { label: '年放电量', value: (annualDischargeKWh / 10000).toFixed(2), unit: '万kWh', formula: '见放电量计算' },
          { label: '损耗电量', value: (lossKWh / 10000).toFixed(2), unit: '万kWh', formula: '充电量 - 放电量' },
        ],
        result: { value: rowData.loss_kwh, unit: '万kWh' }
      };
    }
    
    case 'elec_rev': {
      const usableCapacityDC = capacityWh * currentSOH * dod;
      const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
      const annualDischargeKWh = (dailyDischargeAC * runDays) / 1000; 
      const elecRevWan = (annualDischargeKWh * spread) / 10000; 
      
      return {
        title: '电费套利收入',
        description: `第${year}年电费套利收入`,
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
      const usableCapacityDC = capacityWh * currentSOH * dod;
      const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
      const annualDischargeKWh = (dailyDischargeAC * runDays) / 1000;
      
      let subRev = 0;
      let calcSteps = [];
      
      if (subMode === 'energy') {
        subRev = (annualDischargeKWh * currentSubPrice) / 10000; 
        calcSteps = [
          { label: '补贴模式', value: '按电量(内蒙模式)', unit: '', formula: '输入参数' },
          { label: '年放电量', value: (annualDischargeKWh / 10000).toFixed(2), unit: '万kWh', formula: '见放电量计算' },
          { label: '退坡后单价', value: currentSubPrice.toFixed(3), unit: '元/kWh', formula: `${subPrice} × (1-${subDecline}%)^{year-1}` },
          { label: '补偿收入', value: subRev.toFixed(2), unit: '万元', formula: '放电量(万kWh) × 单价 × 10000 ÷ 10000' },
        ];
      } else {
        const kFactor = Math.min(1, durationHours / 6.0);
        const actualPowerKW = ((inputs?.capacity || 100) * 1000) / (inputs?.duration_hours || 2);
        subRev = (actualPowerKW * currentSubPrice * kFactor) / 10000; 
        const powerMW = actualPowerKW / 1000; 
        
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
        description: `第${year}年补偿收入`,
        formula: subMode === 'energy' ? '放电量 × 退坡后单价' : '功率 × K系数 × 退坡后单价',
        steps: calcSteps,
        result: { value: rowData.sub_rev, unit: '万元' }
      };
    }
    
    case 'aux_rev': {
      const auxRev = (powerKW * auxPrice) / 10000; 
      
      return {
        title: '辅助服务收入',
        description: `第${year}年辅助服务收入`,
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
        description: `第${year}年总收入`,
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
      const opexGross = (capacityWh * opexRate) / 10000; 
      
      return {
        title: '运维成本',
        description: `第${year}年运维成本`,
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
      const usableCapacityDC = capacityWh * currentSOH * dod;
      const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
      const annualDischargeKWh = (dailyDischargeAC * runDays) / 1000;
      const dailyChargeAC = usableCapacityDC / chargeEff * cycles;
      const annualChargeKWh = (dailyChargeAC * runDays) / 1000;
      const lossKWh = annualChargeKWh - annualDischargeKWh;
      const priceValley = inputs?.price_valley || 0.30;
      const lossCostGross = (lossKWh * priceValley) / 10000; 
      
      return {
        title: '效率损耗成本',
        description: `第${year}年损耗成本`,
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
      
      const baseCapex = inputs?.capex || 1.20;
      const baseInvGross = baseCapex * capacityWh; 
      const baseInvNet = baseInvGross / (1 + vatRate); 
      const baseAnnualDep = (baseInvNet * (1 - residualRate)) / depYears / 10000; 
      
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
      
      if (year === augYear && augYear > 0) {
        const augPrice = inputs?.aug_price || 0.6;
        const augInvGross = capacityWh * augPrice; 
        const augInvNet = augInvGross / (1 + vatRate); 
        const augAnnualDep = (augInvNet * (1 - residualRate)) / augDepYears / 10000; 
        
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
        const augPrice = inputs?.aug_price || 0.6;
        const augInvGross = capacityWh * augPrice;
        const augInvNet = augInvGross / (1 + vatRate);
        const augAnnualDep = (augInvNet * (1 - residualRate)) / augDepYears / 10000;
        
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
      const totalInvGross = (inputs?.capex || 1.20) * capacityWh; 
      const debt = totalInvGross * debtRatio / 10000; 
      const interest = debt * loanRate;
      
      return {
        title: '利息支出',
        description: `第${year}年利息支出`,
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
      
      const elecRevGross = annualDischargeKWh * spread; 
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
      
      const outputVAT = totalRevGross - (totalRevGross / (1 + vatRate));
      
      const opexGross = capacityWh * (inputs?.opex || 0.02);
      const lossCostGross = lossKWh * priceValley;
      const opexNet = opexGross / (1 + vatRate);
      const lossCostNet = lossCostGross / (1 + vatRate);
      const inputVAT = (opexGross - opexNet) + (lossCostGross - lossCostNet);
      
      const theoreticalVat = outputVAT - inputVAT;
      const actualVat = parseFloat(rowData.vat_pay || '0') * 10000;
      const vatCreditUsed = Math.max(0, theoreticalVat - actualVat);
      let vatPayable = theoreticalVat;
      if (vatPayable < 0) vatPayable = 0;
      
      return {
        title: '增值税',
        description: `第${year}年应交增值税`,
        formula: '销项税 - 进项税',
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
      const vatPay = parseFloat(rowData.vat_pay || '0') * 10000; 
      const surchargeRate = (inputs?.surcharge_rate ?? 12) / 100; // Fixed: ?? 12
      const surcharge = vatPay * surchargeRate;
      
      return {
        title: '附加税',
        description: `第${year}年附加税`,
        formula: `增值税 × ${surchargeRate * 100}%`,
        steps: [
          { label: '应交增值税', value: (vatPay / 10000).toFixed(2), unit: '万元', formula: '见增值税计算' },
          { label: '附加税率', value: (surchargeRate * 100).toFixed(0), unit: '%', formula: '城建+教育+地方' },
          { label: '附加税额', value: (surcharge / 10000).toFixed(2), unit: '万元', formula: '增值税 × 税率' },
        ],
        result: { value: rowData.surcharge, unit: '万元' }
      };
    }
    
    case 'income_tax': {
      const isPreferential = taxPreferentialYears > 0 && year <= taxPreferentialYears;
      const currentTaxRate = isPreferential ? taxPreferentialRate : taxRate;

      const vatRate = (inputs?.vat_rate || 13) / 100;
      
      const totalRevGross = parseFloat(rowData.total_rev || '0') * 10000;
      const totalRevNet = totalRevGross / (1 + vatRate);

      const opexGross = parseFloat(rowData.opex || '0') * 10000;
      const opexNet = opexGross / (1 + vatRate);
      
      const lossGross = parseFloat(rowData.loss_cost || '0') * 10000;
      const lossNet = lossGross / (1 + vatRate);

      const dep = parseFloat(rowData.dep || '0') * 10000;
      const interest = parseFloat(rowData.interest || '0') * 10000; 
      const surcharge = parseFloat(rowData.surcharge || '0') * 10000;

      const taxableIncome = Math.max(0, totalRevNet - opexNet - lossNet - dep - interest - surcharge);
      
      const incomeTax = taxableIncome * currentTaxRate;
      
      return {
        title: '所得税 (基于表格数据验证)',
        description: `第${year}年所得税`,
        formula: '(总收入/1.13 - 总成本/1.13 - 折旧 - 利息 - 附加税) × 税率',
        steps: [
          { label: '总收入(不含税)', value: (totalRevNet / 10000).toFixed(2), unit: '万元', formula: `表格总收入 ${rowData.total_rev} ÷ (1+${vatRate*100}%)` },
          { label: '减：运维成本(不含税)', value: (opexNet / 10000).toFixed(2), unit: '万元', formula: `表格运维 ${rowData.opex} ÷ (1+${vatRate*100}%)` },
          { label: '减：损耗成本(不含税)', value: (lossNet / 10000).toFixed(2), unit: '万元', formula: `表格损耗 ${rowData.loss_cost} ÷ (1+${vatRate*100}%)` },
          { label: '减：折旧费用', value: (dep / 10000).toFixed(2), unit: '万元', formula: '表格数值' },
          { label: '减：利息支出', value: (interest / 10000).toFixed(2), unit: '万元', formula: '表格数值(逐年递减)' },
          { label: '减：附加税', value: (surcharge / 10000).toFixed(2), unit: '万元', formula: '表格数值' },
          { label: '应纳税所得额', value: (taxableIncome / 10000).toFixed(2), unit: '万元', formula: '收入 - 各项扣除' },
          { label: '税率', value: (currentTaxRate * 100).toFixed(1), unit: '%', formula: isPreferential ? `优惠期` : '标准' },
          { label: '计算所得税', value: (incomeTax / 10000).toFixed(2), unit: '万元', formula: '应纳税额 × 税率' },
          { label: '表格显示值', value: rowData.income_tax, unit: '万元', formula: '实际显示' },
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
        description: `第${year}年总税金`,
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
      const annualDep = (totalInvNet * (1 - residualRate)) / depYears / 10000; 
      
      const ebit = (totalRevNet - opexNet - lossCostNet) / 10000 - annualDep;
      const ebitda = ebit + annualDep;
      
      return {
        title: '息税折旧前利润 EBITDA',
        description: `第${year}年EBITDA`,
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
        description: `第${year}年净利润`,
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
        description: `第${year}年股东现金流`,
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
        description: `第${year}年累计现金流`,
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
        description: `第${year}年偿债覆盖率`,
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
"""

def backup_file(filepath):
    """创建备份文件"""
    if os.path.exists(filepath):
        backup_path = filepath + ".bak"
        shutil.copy2(filepath, backup_path)
        print(f"✅ 备份成功: {backup_path}")
    else:
        print(f"❌ 文件未找到，无法备份: {filepath}")

def fix_hook_file():
    """完全重写 useStorageCalculation.ts"""
    print(f"正在修复 Hook 文件: {HOOK_PATH}...")
    backup_file(HOOK_PATH)
    
    try:
        with open(HOOK_PATH, 'w', encoding='utf-8') as f:
            f.write(FIXED_HOOK_CONTENT)
        print("✅ Hook 文件已重写。")
    except Exception as e:
        print(f"❌ 写入 Hook 文件失败: {e}")

def fix_utils_file():
    """完全重写 calculationDetails.ts"""
    print(f"正在修复 Utils 文件: {UTILS_PATH}...")
    backup_file(UTILS_PATH)
    
    try:
        with open(UTILS_PATH, 'w', encoding='utf-8') as f:
            f.write(FIXED_UTILS_CONTENT)
        print("✅ Utils 文件已重写 (TS错误已修复)。")
    except Exception as e:
        print(f"❌ 写入 Utils 文件失败: {e}")

if __name__ == "__main__":
    print("=== 开始执行自动修复脚本 (V2) ===")
    
    if not os.path.exists(HOOK_PATH):
        print(f"❌ 错误: 找不到路径 {HOOK_PATH}")
    else:
        fix_hook_file()
        
    if not os.path.exists(UTILS_PATH):
        print(f"⚠️ 警告: 找不到路径 {UTILS_PATH}")
    else:
        fix_utils_file()
        
    print("=== 脚本执行完毕 ===")
    print("请重新运行您的项目验证结果。")