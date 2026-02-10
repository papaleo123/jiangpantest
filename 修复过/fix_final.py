import os

# 这是修复后的完整 KpiCards.tsx 代码
# 1. 移除了 />\n <span 中的 \n
# 2. 增加了 safeFormat 函数，彻底根治 NaN
# 3. 增强了 AnimatedNumber 的稳定性
FIXED_CONTENT = r"""import { TrendingUp, Wallet, Clock, Battery, Zap, Scale } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { KpiResult } from '@/types';
import { useEffect, useState, useRef } from 'react';

interface KpiCardsProps {
  kpi: KpiResult | null;
}

interface KpiCardProps {
  title: string;
  value: string;
  unit: string;
  subLabel: string;
  subValue: string;
  subUnit?: string;
  gradient: string;
  icon: React.ReactNode;
  delay: number;
}

function AnimatedNumber({ value, decimals = 2 }: { value: string; decimals?: number }) {
  const [displayValue, setDisplayValue] = useState('0');
  const prevValueRef = useRef(value);
  
  useEffect(() => {
    // 修复 NaN: 如果输入值无效，直接显示 --
    if (value === '--' || value === 'NaN' || !value) {
      setDisplayValue('--');
      return;
    }
    
    const numValue = parseFloat(value);
    if (isNaN(numValue)) {
      setDisplayValue('--');
      return;
    }

    const prevValue = parseFloat(prevValueRef.current);
    const startValue = isNaN(prevValue) || prevValueRef.current === '--' ? 0 : prevValue;
    
    const duration = 600;
    const startTime = performance.now();
    
    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      const current = startValue + (numValue - startValue) * easeProgress;
      
      // 动画过程防御 NaN
      if (!isNaN(current)) {
          setDisplayValue(current.toFixed(decimals));
      }
      
      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };
    
    requestAnimationFrame(animate);
    prevValueRef.current = value;
  }, [value, decimals]);
  
  return <span>{displayValue}</span>;
}

function KpiCard({ title, value, unit, subLabel, subValue, subUnit, gradient, icon, delay }: KpiCardProps) {
  const [isVisible, setIsVisible] = useState(false);
  
  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);

  return (
    <Card 
      className={`relative overflow-hidden transition-all duration-500 hover:-translate-y-1 hover:shadow-xl ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
      }`}
    >
      <div className={`absolute top-0 left-0 right-0 h-1 ${gradient}`} />
      <CardHeader className="pb-2 px-3 md:px-6">
        <CardTitle className="text-xs md:text-sm font-medium text-slate-500 flex items-center gap-1 md:gap-2">
          {icon}
          <span className="truncate">{title}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="px-3 md:px-6">
        <div className="text-xl md:text-3xl font-bold text-slate-800">
          {/* 这里的 \n 已经被彻底移除 */}
          <AnimatedNumber value={value} decimals={value?.toString().includes(".") ? (value.toString().split(".")[1]?.length || 2) : 0} />
          <span className="text-xs md:text-sm font-normal text-slate-400 ml-1">{unit}</span>
        </div>
        <div className="mt-2 md:mt-3 pt-2 md:pt-3 border-t border-slate-100 flex items-center gap-1 md:gap-2 text-xs md:text-sm flex-wrap">
          <span className="text-slate-500">{subLabel}</span>
          <span className="font-semibold text-slate-700">{subValue}</span>
          {subUnit && <span className="text-slate-400">{subUnit}</span>}
        </div>
      </CardContent>
    </Card>
  );
}

export function KpiCards({ kpi }: KpiCardsProps) {
  const getDscrBadge = (dscr: number) => {
    if (dscr < 1.2) {
      return <Badge className="bg-yellow-100 text-yellow-800 text-xs">{dscr.toFixed(2)}</Badge>;
    }
    return <Badge className="bg-green-100 text-green-800 text-xs">{dscr.toFixed(2)}</Badge>;
  };

  // 辅助函数：安全格式化，如果是 NaN 则返回 --
  const safeFormat = (val: number | undefined, decimals: number = 0) => {
      if (val === undefined || val === null || isNaN(val)) return '--';
      return val.toFixed(decimals);
  };

  return (
    <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-2 md:gap-4">
      <KpiCard
        title="税后资本金 IRR"
        value={safeFormat(kpi?.equity_irr, 2)}
        unit="%"
        subLabel="全投资 IRR:"
        subValue={safeFormat(kpi?.project_irr, 2) + '%'}
        gradient="bg-gradient-to-r from-green-400 to-green-600"
        icon={<TrendingUp className="w-3 h-3 md:w-4 md:h-4 text-green-500" />}
        delay={0}
      />
      
      <KpiCard
        title="项目净现值 NPV"
        value={safeFormat(kpi?.npv, 0)}
        unit="万"
        subLabel="ROI:"
        subValue={safeFormat(kpi?.roi, 1) + '%'}
        gradient="bg-gradient-to-r from-purple-400 to-purple-600"
        icon={<Wallet className="w-3 h-3 md:w-4 md:h-4 text-purple-500" />}
        delay={100}
      />
      
      <KpiCard
        title="静态回收期"
        value={safeFormat(kpi?.payback, 1)}
        unit="年"
        subLabel="最低DSCR:"
        subValue={kpi ? '' : '--'}
        subUnit={kpi ? getDscrBadge(kpi.min_dscr).props.children : undefined}
        gradient="bg-gradient-to-r from-orange-400 to-orange-600"
        icon={<Clock className="w-3 h-3 md:w-4 md:h-4 text-orange-500" />}
        delay={200}
      />
      
      <KpiCard
        title="度电成本 LCOE"
        value={safeFormat(kpi?.lcoe, 3)}
        unit="元/kWh"
        subLabel="总利润:"
        subValue={safeFormat(kpi?.total_profit, 0)}
        subUnit="万"
        gradient="bg-gradient-to-r from-blue-400 to-blue-600"
        icon={<Battery className="w-3 h-3 md:w-4 md:h-4 text-blue-500" />}
        delay={300}
      />

      <KpiCard
        title="总放电量"
        value={safeFormat((kpi as any)?.total_discharge, 0)}
        unit="万kWh"
        subLabel="全生命周期"
        subValue=""
        gradient="bg-gradient-to-r from-cyan-400 to-cyan-600"
        icon={<Zap className="w-3 h-3 md:w-4 md:h-4 text-cyan-500" />}
        delay={400}
      />

      <KpiCard
        title="总投资"
        value={safeFormat((kpi as any)?.total_inv, 0)}
        unit="万"
        subLabel="含税总投资"
        subValue=""
        gradient="bg-gradient-to-r from-rose-400 to-rose-600"
        icon={<Scale className="w-3 h-3 md:w-4 md:h-4 text-rose-500" />}
        delay={500}
      />
    </div>
  );
}
"""

def main():
    target_file = 'src/components/KpiCards.tsx'
    
    # 检查文件是否存在
    if not os.path.exists(target_file):
        print(f"❌ 错误: 找不到文件 {target_file}")
        print("请确保你在项目根目录下运行此脚本")
        return

    # 全量写入
    print(f"🔄 正在重写 {target_file} ...")
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(FIXED_CONTENT)
    
    print("✅ 修复完成！")
    print("   1. 所有的 '\\n' 都已清除")
    print("   2. 所有的 NaN 现在会显示为 '--'")
    print("🚀 现在请执行: git add . && git commit -m 'fix: final fix for NaN and newline' && git push")

if __name__ == "__main__":
    main()