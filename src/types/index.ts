// 投资明细项
export interface InvestmentItem {
  id?: string;
  name: string;
  amount: number;        // 万元
  taxRate: number;       // %
  category: 'equipment' | 'civil' | 'install' | 'other';
}

// 输入参数类型
export interface InputParams {
  years: number;
  sub_mode: 'energy' | 'capacity';
  sub_price: number;
  sub_years: number;
  sub_decline: number;
  aux_price: number;
  capacity: number;
  duration_hours: number;
  charge_eff: number;      // 充电效率 (%)
  discharge_eff: number;   // 放电效率 (%)
  dod: number;             // 放电深度 (%)
  price_valley: number;
  capex: number;
  spread: number;
  opex: number;
  cycles: number;
  run_days: number;        // 年运行天数
  dep_years: number;
  debt_ratio: number;
  loan_rate: number;
  vat_rate: number;
  tax_rate: number;
  aug_year: number;
  aug_price: number;
  aug_dep_years: number;
  residual_rate: number;
  
  // 新增：投资明细和建设期
  constructionPeriod?: number;
  investmentItems?: InvestmentItem[];   // 残值率 (%)
}

// 年度详细数据行
export interface YearlyRow {
  y: number;
  soh: string;           // 电池健康度
  
  // 物理量
  charge_kwh: string;    // 年充电量 (万kWh)
  discharge_kwh: string; // 年放电量 (万kWh)
  loss_kwh: string;      // 效率损耗电量 (万kWh)
  
  // 收入
  elec_rev: string;      // 电费套利收入 (万元)
  sub_rev: string;       // 补偿收入 (万元)
  aux_rev: string;       // 或有收益 (万元)
  total_rev: string;     // 总收入 (万元)
  
  // 成本
  opex: string;          // 运维成本 (万元)
  loss_cost: string;     // 效率损耗成本 (万元)
  dep: string;           // 折旧 (万元)
  interest: string;      // 利息 (万元)
  
  // 税务
  vat_pay: string;       // 增值税 (万元)
  surcharge: string;     // 附加税 (万元)
  income_tax: string;    // 所得税 (万元)
  total_tax: string;     // 总税金 (万元)
  
  // 利润与现金流
  ebit: string;          // 息税前利润 (万元)
  ebitda: string;        // 息税折旧前利润 (万元)
  net_profit: string;    // 净利润 (万元)
  principal: string;     // 本金偿还 (万元)
  cf: string;            // 股东净现金流 (万元)
  cum_cf: string;        // 累计现金流 (万元)
  dscr: string;          // 偿债覆盖率
}

// 统计信息
export interface Stats {
  total_charge_kwh: number;      // 总充电量
  total_discharge_kwh: number;   // 总放电量
  total_loss_kwh: number;        // 总损耗电量
  
  total_elec_rev: number;        // 总电费收入
  total_sub_rev: number;         // 总补偿收入
  total_aux_rev: number;         // 总或有收益
  total_rev: number;             // 总收入
  
  total_opex: number;            // 总运维成本
  total_loss_cost: number;       // 总损耗成本
  total_dep: number;             // 总折旧
  total_interest: number;        // 总利息
  
  total_vat: number;             // 总增值税
  total_surcharge: number;       // 总附加税
  total_income_tax: number;      // 总所得税
  total_tax: number;             // 总税金
  
  total_net_profit: number;      // 总净利润
  total_principal: number;       // 总本金偿还
  min_dscr: number;              // 最低偿债覆盖率
  
  // 投资信息
  total_inv_gross: number;       // 总投资(含税)
  total_inv_net: number;         // 总投资(不含税)
  equity: number;                // 资本金
  debt: number;                  // 贷款额
}

// 计算结果
export interface CalculationResult {
  equity_cf: number[];           // 股东现金流序列
  project_cf: number[];          // 项目现金流序列
  rows: YearlyRow[];             // 年度明细
  stats: Stats;                  // 统计信息
}

// KPI结果
export interface KpiResult {
  equity_irr: number;            // 资本金IRR (%)
  project_irr: number;           // 项目IRR (%)
  npv: number;                   // NPV @8% (万元)
  roi: number;                   // 投资回报率 (%)
  payback: number;               // 静态回收期 (年)
  min_dscr: number;              // 最低偿债覆盖率
  lcoe: number;                  // 度电成本 (元/kWh)
  total_profit: number;          // 总净利润 (万元)
}

// 成本结构项
export interface CostItem {
  label: string;
  value: number;
  color: string;
}

// 敏感性分析点
export interface SensitivityPoint {
  rate: string;
  npv: number;
  irr: number;
}
