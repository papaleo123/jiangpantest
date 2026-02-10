
import { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import { Maximize2 } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

interface SensitivityChartProps {
  data: any[];
}

export function SensitivityChart({ data }: SensitivityChartProps) {
  const [isOpen, setIsOpen] = useState(false);

  // 图表配置 - 统一定义颜色和名称
  const lines = [
    { key: 'spread', name: '峰谷价差', color: '#8884d8' },
    { key: 'capex', name: '建设成本', color: '#ff4d4f' }, 
    { key: 'cycles', name: '循环次数', color: '#52c41a' }, 
    { key: 'loan_rate', name: '融资利率', color: '#faad14' }, 
  ];

  // 渲染图表内容的函数 (复用)
  const renderChart = (height: number | string, isModal = false) => (
    <div style={{ width: '100%', height: height }} className="relative group">
      {!isModal && (
        <Button 
          variant="ghost" 
          size="icon" 
          className="absolute right-0 top-0 z-10 opacity-0 group-hover:opacity-100 transition-opacity bg-white/80 hover:bg-white"
          onClick={() => setIsOpen(true)}
        >
          <Maximize2 className="w-4 h-4 text-slate-500" />
        </Button>
      )}
      
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
          <XAxis 
            dataKey="name" 
            stroke="#9ca3af" 
            tick={{ fontSize: 12 }}
            label={{ value: '变动幅度 (%)', position: 'insideBottom', offset: -5, fontSize: 10, fill: '#9ca3af' }}
          />
          <YAxis 
            stroke="#9ca3af" 
            tick={{ fontSize: 12 }} 
            unit="%"
            width={50}
            label={{ value: 'IRR (%)', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle', fill: '#9ca3af', fontSize: 12 } }}
          />
          <Tooltip 
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            formatter={(value: number, name: string) => [`${value.toFixed(2)}%`, name]}
            labelStyle={{ color: '#6b7280', marginBottom: '0.5rem' }}
          />
          <Legend wrapperStyle={{ paddingTop: '10px' }} />
          <ReferenceLine x="0%" stroke="#d1d5db" strokeDasharray="3 3" />
          
          {lines.map(line => (
            <Line
              key={line.key}
              type="monotone"
              dataKey={line.key}
              name={line.name}
              stroke={line.color}
              strokeWidth={isModal ? 3 : 2}
              dot={{ r: isModal ? 4 : 3 }}
              activeDot={{ r: isModal ? 6 : 5 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );

  return (
    <>
      <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-100">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-700">敏感性分析 (IRR)</h3>
            <p className="text-xs text-slate-400">各核心要素波动±20%对股东IRR的影响</p>
          </div>
          <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setIsOpen(true)}>
            <Maximize2 className="w-3 h-3 mr-1" />
            放大
          </Button>
        </div>
        
        {renderChart(240)}
      </div>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-4xl w-[90vw] h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>多维敏感性分析详情</DialogTitle>
          </DialogHeader>
          <div className="flex-1 min-h-0 w-full pt-4">
             {renderChart('100%', true)}
          </div>
          <div className="text-sm text-slate-500 mt-4 bg-slate-50 p-3 rounded-lg">
            <strong>分析结论：</strong>
            <ul className="list-disc list-inside mt-1 space-y-1">
              <li>斜率越陡峭，说明该因素对收益率的影响越敏感（越关键）。</li>
              <li>通常情况下，<span className="text-[#8884d8] font-medium">峰谷价差</span> 是最敏感因素，其次是 <span className="text-[#ff4d4f] font-medium">建设成本</span>。</li>
              <li>如果 <span className="text-[#faad14] font-medium">融资利率</span> 曲线平缓，说明高杠杆带来的风险相对可控。</li>
            </ul>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
