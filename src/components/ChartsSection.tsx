
import { ResponsiveContainer, ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import type { CalculationResult } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { BarChart3 } from 'lucide-react';

interface ChartsSectionProps {
  data: CalculationResult | null;
}

export function ChartsSection({ data }: ChartsSectionProps) {
  if (!data) return null;

  // 准备图表数据
  const chartData = data.rows.map(row => ({
    year: row.y,
    revenue: parseFloat(row.total_rev),
    cost: parseFloat(row.opex) + parseFloat(row.loss_cost) + parseFloat(row.total_tax) + parseFloat(row.interest),
    profit: parseFloat(row.net_profit),
    cf: parseFloat(row.cf)
  }));

  return (
    <div className="grid grid-cols-1 gap-6 mb-6">
      {/* 恢复：年度经营分析卡片 */}
      <Card className="bg-white shadow-sm border-slate-100">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-600" />
            <CardTitle className="text-base text-slate-700">年度经营分析 (收入 vs 成本 vs 利润)</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-[350px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis 
                  dataKey="year" 
                  tick={{ fontSize: 12, fill: '#64748b' }} 
                  axisLine={{ stroke: '#e2e8f0' }}
                />
                <YAxis 
                  yAxisId="left"
                  tick={{ fontSize: 12, fill: '#64748b' }} 
                  axisLine={false}
                  label={{ value: '金额 (万元)', angle: -90, position: 'insideLeft', style: { fill: '#94a3b8', fontSize: 12 } }}
                />
                <Tooltip 
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  labelStyle={{ color: '#64748b', marginBottom: '0.5rem' }}
                />
                <Legend wrapperStyle={{ paddingTop: '20px' }} />
                
                {/* 柱状图：收入 */}
                <Bar yAxisId="left" dataKey="revenue" name="总收入" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={20} />
                
                {/* 柱状图：总成本支出 (运维+损耗+税+利息) */}
                <Bar yAxisId="left" dataKey="cost" name="总支出" fill="#94a3b8" radius={[4, 4, 0, 0]} barSize={20} />
                
                {/* 折线图：净利润 */}
                <Line yAxisId="left" type="monotone" dataKey="profit" name="净利润" stroke="#10b981" strokeWidth={3} dot={{ r: 4, fill: '#10b981' }} />
                
                {/* 折线图：股东现金流 */}
                <Line yAxisId="left" type="monotone" dataKey="cf" name="股东现金流" stroke="#f59e0b" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 3, fill: '#f59e0b' }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
