import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, ComposedChart, Area, Bar, LineChart, Line } from 'recharts';
import type { CalculationResult, InputParams } from '@/types';
import { TrendingUp, PieChart as PieChartIcon, Activity, Battery } from 'lucide-react';

interface ChartsSectionProps {
  result: CalculationResult | null;
  inputs: InputParams;
}

interface ChartDataPoint {
  year: number;
  cf: number;
  cum_cf: number;
}

interface CostDataPoint {
  name: string;
  value: number;
  color: string;
}

interface SensitivityPoint {
  rate: string;
  npv: number;
  irr: number;
}

const COLORS = {
  capex: '#3b82f6',
  opex: '#22c55e',
  loss: '#f97316',
  interest: '#ef4444',
  tax: '#8b5cf6',
};

// IRR计算
function calculateIRR(cf: number[]): number {
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

// NPV计算
function calculateNPV(rate: number, cf: number[]): number {
  return cf.reduce((npv, cashflow, t) => npv + cashflow / Math.pow(1 + rate, t), 0);
}

// 生成敏感性分析数据
function generateSensitivityData(inputs: InputParams): SensitivityPoint[] {
  const rates = [-20, -15, -10, -5, 0, 5, 10, 15, 20];
  const data: SensitivityPoint[] = [];
  
  const baseSpread = inputs.spread;
  const chargeEff = inputs.charge_eff / 100;
  const dischargeEff = inputs.discharge_eff / 100;
  const rte = chargeEff * dischargeEff;
  const dod = inputs.dod / 100;
  
  for (const rate of rates) {
    const adjustedSpread = baseSpread * (1 + rate / 100);
    
    const MWh = inputs.capacity;
    const Wh = MWh * 1e6;
    const cycles = inputs.cycles;
    const runDays = inputs.run_days;
    
    const equityCF: number[] = [];
    let currentSOH = 1.0;
    
    for (let y = 1; y <= inputs.years; y++) {
      const usableCapacity = Wh * currentSOH * dod;
      const dailyDischarge = usableCapacity * cycles;
      const annualDischargeKWh = (dailyDischarge * runDays) / 1000;
      const annualChargeKWh = annualDischargeKWh / rte;
      const lossKWh = annualChargeKWh - annualDischargeKWh;
      
      const elecRev = annualDischargeKWh * adjustedSpread;
      const opex = Wh * inputs.opex;
      const lossCost = lossKWh * inputs.price_valley;
      
      const net = elecRev - opex - lossCost;
      equityCF.push(net * (1 - inputs.tax_rate / 100));
      currentSOH -= y === 1 ? 0.04 : 0.025;
    }
    
    const totalInv = Wh * inputs.capex;
    const cf = [-totalInv * (1 - inputs.debt_ratio / 100), ...equityCF];
    
    const irr = calculateIRR(cf) * 100;
    const npv = calculateNPV(0.08, cf) / 10000;
    
    data.push({ rate: `${rate > 0 ? '+' : ''}${rate}%`, npv, irr });
  }
  
  return data;
}

export function ChartsSection({ result, inputs }: ChartsSectionProps) {
  // J曲线数据
  const mainChartData = useMemo<ChartDataPoint[]>(() => {
    if (!result) return [];
    return result.rows.map((row) => ({
      year: row.y,
      cf: parseFloat(row.cf),
      cum_cf: parseFloat(row.cum_cf),
    }));
  }, [result]);

  // 成本结构数据
  const pieChartData = useMemo<CostDataPoint[]>(() => {
    if (!result) return [];
    return [
      { name: '初始投资', value: result.stats.total_inv_gross, color: COLORS.capex },
      { name: '运维成本', value: result.stats.total_opex, color: COLORS.opex },
      { name: '效率损耗', value: result.stats.total_loss_cost, color: COLORS.loss },
      { name: '利息支出', value: result.stats.total_interest, color: COLORS.interest },
      { name: '税金', value: result.stats.total_tax, color: COLORS.tax },
    ];
  }, [result]);

  // 敏感性分析数据
  const sensitivityData = useMemo(() => generateSensitivityData(inputs), [inputs]);

  // 盈亏平衡点
  const breakevenIndex = useMemo(() => {
    if (!result) return -1;
    for (let i = 0; i < result.rows.length; i++) {
      if (parseFloat(result.rows[i].cum_cf) > 0) return i;
    }
    return -1;
  }, [result]);

  const totalCost = pieChartData.reduce((sum, item) => sum + item.value, 0);
  const formatWan = (value: number) => (value / 10000).toFixed(0) + '万';

  // Tooltip组件
  const MainTooltip = ({ active, payload, label }: { active?: boolean; payload?: any[]; label?: number }) => {
    if (active && payload?.length) {
      return (
        <div className="bg-slate-800 text-white p-3 rounded-lg shadow-lg text-sm">
          <p className="font-semibold mb-2">第 {label} 年</p>
          {payload.map((entry, i) => (
            <p key={i} className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full" style={{ backgroundColor: entry.color }} />
              <span>{entry.name}: {entry.value.toFixed(2)} 万元</span>
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const PieTooltip = ({ active, payload }: { active?: boolean; payload?: any[] }) => {
    if (active && payload?.length) {
      const data = payload[0].payload;
      const pct = totalCost > 0 ? ((data.value / totalCost) * 100).toFixed(1) : '0';
      return (
        <div className="bg-slate-800 text-white p-3 rounded-lg shadow-lg text-sm">
          <p className="font-semibold">{data.name}</p>
          <p>{formatWan(data.value)} ({pct}%)</p>
        </div>
      );
    }
    return null;
  };

  const SensitivityTooltip = ({ active, payload, label }: { active?: boolean; payload?: any[]; label?: string }) => {
    if (active && payload?.length) {
      return (
        <div className="bg-slate-800 text-white p-3 rounded-lg shadow-lg text-sm">
          <p className="font-semibold mb-2">电价变化: {label}</p>
          {payload.map((entry, i) => (
            <p key={i} className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full" style={{ backgroundColor: entry.color }} />
              <span>{entry.name}: {entry.value.toFixed(2)}{entry.name === 'IRR' ? '%' : ' 万'}</span>
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-4">
      {/* J曲线图表 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-slate-500" />
              资金流向与累计净现金流 (J曲线)
            </div>
            <Badge variant="secondary">单位: 万元</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="h-[250px] sm:h-[300px] md:h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={mainChartData} margin={{ top: 20, right: 20, left: 0, bottom: 50 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="year" tick={{ fontSize: 10 }} axisLine={{ stroke: '#cbd5e1' }} />
              <YAxis yAxisId="left" tick={{ fontSize: 10 }} axisLine={{ stroke: '#cbd5e1' }} label={{ value: '当年(万)', angle: -90, position: 'insideLeft', fontSize: 10 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} axisLine={{ stroke: '#cbd5e1' }} label={{ value: '累计(万)', angle: 90, position: 'insideRight', fontSize: 10 }} />
              <Tooltip content={<MainTooltip />} />
              <Legend verticalAlign="bottom" height={40} wrapperStyle={{ fontSize: 11, paddingTop: '10px' }} />
              <Bar yAxisId="left" dataKey="cf" name="当年净现金流" radius={[4, 4, 0, 0]}>
                {mainChartData.map((entry, idx) => (
                  <Cell key={`cell-${idx}`} fill={entry.cf > 0 ? '#22c55e' : '#ef4444'} />
                ))}
              </Bar>
              <Area yAxisId="right" type="monotone" dataKey="cum_cf" name="累计净现金流" stroke="#8b5cf6" strokeWidth={3} fill="rgba(139, 92, 246, 0.1)"
                dot={(props: any) => {
                  const { cx, cy, index } = props;
                  if (index === breakevenIndex && cx !== undefined && cy !== undefined) {
                    return <svg x={cx - 6} y={cy - 6} width={12} height={12}><circle cx={6} cy={6} r={6} fill="#22c55e" stroke="white" strokeWidth={2} /></svg>;
                  }
                  return <></>;
                }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* 下方三个图表 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* 成本结构饼图 */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <PieChartIcon className="w-4 h-4 text-slate-500" />
              全周期成本结构
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[160px] md:h-[180px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieChartData} cx="50%" cy="50%" innerRadius={35} outerRadius={55} paddingAngle={2} dataKey="value"
                    label={({ percent }) => `${(percent * 100).toFixed(0)}%`} labelLine={false}>
                    {pieChartData.map((entry, idx) => <Cell key={`cell-${idx}`} fill={entry.color} />)}
                  </Pie>
                  <Tooltip content={<PieTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 bg-slate-50 rounded-lg p-2 space-y-1">
              {pieChartData.map((item) => (
                <div key={item.name} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                    <span className="text-slate-600">{item.name}</span>
                  </div>
                  <span className="font-semibold text-slate-800">{formatWan(item.value)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 敏感性分析 */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Activity className="w-4 h-4 text-slate-500" />
              敏感性分析
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[200px] md:h-[220px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={sensitivityData} margin={{ top: 10, right: 20, left: 0, bottom: 35 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="rate" tick={{ fontSize: 9 }} axisLine={{ stroke: '#cbd5e1' }} interval={0} angle={-30} textAnchor="end" height={40} />
                  <YAxis yAxisId="left" tick={{ fontSize: 9 }} axisLine={{ stroke: '#cbd5e1' }} label={{ value: 'NPV(万)', angle: -90, position: 'insideLeft', fontSize: 9 }} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 9 }} axisLine={{ stroke: '#cbd5e1' }} label={{ value: 'IRR(%)', angle: 90, position: 'insideRight', fontSize: 9 }} />
                  <Tooltip content={<SensitivityTooltip />} />
                  <Legend verticalAlign="bottom" height={30} wrapperStyle={{ fontSize: 10, paddingTop: '5px' }} />
                  <Line yAxisId="left" type="monotone" dataKey="npv" name="NPV" stroke="#3b82f6" strokeWidth={2} dot={{ fill: '#3b82f6', r: 3 }} />
                  <Line yAxisId="right" type="monotone" dataKey="irr" name="IRR" stroke="#22c55e" strokeWidth={2} dot={{ fill: '#22c55e', r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="text-[10px] text-slate-500 mt-1 text-center">峰谷价差 ±20% 变化</p>
          </CardContent>
        </Card>

        {/* 电量统计 */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Battery className="w-4 h-4 text-slate-500" />
              全周期电量统计
            </CardTitle>
          </CardHeader>
          <CardContent>
            {result ? (
              <div className="space-y-3">
                <div className="bg-blue-50 rounded-lg p-3">
                  <p className="text-xs text-blue-600 mb-1">总充电量</p>
                  <p className="text-xl font-bold text-blue-700">
                    {(result.stats.total_charge_kwh / 10000).toFixed(0)} 
                    <span className="text-sm font-normal ml-1">万kWh</span>
                  </p>
                </div>
                <div className="bg-green-50 rounded-lg p-3">
                  <p className="text-xs text-green-600 mb-1">总放电量</p>
                  <p className="text-xl font-bold text-green-700">
                    {(result.stats.total_discharge_kwh / 10000).toFixed(0)}
                    <span className="text-sm font-normal ml-1">万kWh</span>
                  </p>
                </div>
                <div className="bg-orange-50 rounded-lg p-3">
                  <p className="text-xs text-orange-600 mb-1">效率损耗电量</p>
                  <p className="text-xl font-bold text-orange-700">
                    {(result.stats.total_loss_kwh / 10000).toFixed(0)}
                    <span className="text-sm font-normal ml-1">万kWh</span>
                  </p>
                  <p className="text-xs text-orange-500 mt-1">
                    损耗率: {((result.stats.total_loss_kwh / result.stats.total_charge_kwh) * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400 text-sm">
                等待计算...
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
