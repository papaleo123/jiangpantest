import { useState, useCallback, useMemo } from 'react';
import type { InputParams, CalculationResult, KpiResult, YearlyRow, Stats } from '@/types';

// ==================== 1. 配置常量 ====================

const FINANCIAL_CONSTANTS = {
  DEGRADATION: {
    FIRST_YEAR: 0.04,
    ANNUAL: 0.025,
    MIN_SOH: 0.60,
  },
  TAX_RATES: {
    ELEC: 0.13,   // 电力销售增值税
    SERVICE: 0.06 // 服务/补贴增值税
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
  
  // 1. 电费收入 (13% 税率)
  const elecRevGross = Precision.yuan(annualDischargeKWh * spread);
  const elecRevNet = Precision.yuan(elecRevGross / (1 + vatRate));
  
  // 2. 补贴收入 (6% 税率 - 服务)
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
  const subRevNet = Precision.yuan(subRevGross / (1 + FINANCIAL_CONSTANTS.TAX_RATES.SERVICE));
  
  // 3. 辅助服务 (6% 税率 - 服务)
  const auxRevGross = Precision.yuan(powerKW * auxPrice);
  const auxRevNet = Precision.yuan(auxRevGross / (1 + FINANCIAL_CONSTANTS.TAX_RATES.SERVICE));
  
  // 汇总
  const totalRevGross = Precision.yuan(elecRevGross + subRevGross + auxRevGross);
  const totalRevNet = Precision.yuan(elecRevNet + subRevNet + auxRevNet);
  
  // 销项税 = 各分项税额之和
  const outputVAT = Precision.yuan(
    (elecRevGross - elecRevNet) + 
    (subRevGross - subRevNet) + 
    (auxRevGross - auxRevNet)
  );
  
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
          vatRate: params.vatRate, // 这里的 vatRate 主要给电费收入用
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
    link.download = '储能财务分析表_V16_Fixed.csv';
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
