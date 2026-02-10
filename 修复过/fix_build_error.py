import os
import re

# ==========================================
# 1. 全量重写 KpiCards.tsx (最稳妥的方式)
# ==========================================
KPI_CARDS_CONTENT = r"""import { TrendingUp, Wallet, Clock, Battery, Zap, Scale } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { KpiResult } from '@/types';
import { useEffect, useState, useRef } from 'react';

interface KpiCardsProps {
  kpi: KpiResult | null;
  stats?: any; // 新增 stats 接口定义
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

// 确保这里参数里有 stats
export function KpiCards({ kpi, stats }: KpiCardsProps) {
  const getDscrBadge = (dscr: number) => {
    if (dscr < 1.2) {
      return <Badge className="bg-yellow-100 text-yellow-800 text-xs">{dscr.toFixed(2)}</Badge>;
    }
    return <Badge className="bg-green-100 text-green-800 text-xs">{dscr.toFixed(2)}</Badge>;
  };

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
        value={safeFormat((stats?.total_discharge_kwh || 0) / 10000, 0)}
        unit="万kWh"
        subLabel="全生命周期"
        subValue=""
        gradient="bg-gradient-to-r from-cyan-400 to-cyan-600"
        icon={<Zap className="w-3 h-3 md:w-4 md:h-4 text-cyan-500" />}
        delay={400}
      />

      <KpiCard
        title="总投资"
        value={safeFormat((stats?.total_inv_gross || 0) / 10000, 0)}
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

def fix_kpi_cards_file():
    path = 'src/components/KpiCards.tsx'
    if not os.path.exists(path):
        print(f"❌ 找不到文件: {path}")
        return
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(KPI_CARDS_CONTENT)
    print("✅ [KpiCards.tsx] 已全量重写，确保参数定义正确。")

# ==========================================
# 2. 修复 App.tsx 中的参数传递错误
# ==========================================
def fix_app_usage():
    # 尝试在常见的入口文件中寻找错误代码
    possible_files = ['src/App.tsx', 'src/Main.tsx', 'src/pages/Dashboard.tsx']
    target_file = None
    
    for p in possible_files:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                content = f.read()
                # 寻找错误的调用： stats={kpi.stats} 或者 stats={xxx}
                # 错误特征：上个脚本可能把 result.kpi 拆分错，导致生成 stats={kpi.stats}
                if 'KpiCards' in content:
                    target_file = p
                    break
    
    if not target_file:
        print("⚠️ 未能在常见位置找到 App.tsx 或相关文件，跳过 App 修复。")
        return

    print(f"🔎 正在检查文件: {target_file}")
    with open(target_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    fixed = False
    
    for line in lines:
        if '<KpiCards' in line and 'stats={' in line:
            # 这一行就是之前脚本改坏的地方
            # 我们直接暴力修复：把 stats={...} 替换成 stats={result?.stats}
            # 这里的 assumption 是：你的主数据变量名叫 'result' (这在 DataTable 和其他组件里是通用的)
            
            # 使用正则替换：不管之前填的是什么奇怪的变量，统统改成 result?.stats
            new_line = re.sub(r'stats=\{[^}]+\}', 'stats={result?.stats}', line)
            
            # 顺便修复 kpi={...} 可能出现的 nullable 报错
            # 如果是 kpi={result.kpi} 改成 kpi={result?.kpi} 防止 null 报错
            new_line = new_line.replace('kpi={result.kpi}', 'kpi={result?.kpi}')
            
            new_lines.append(new_line)
            fixed = True
            print(f"✅ 修复了代码行: {line.strip()} -> {new_line.strip()}")
        else:
            new_lines.append(line)

    if fixed:
        with open(target_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
    else:
        print("ℹ️ 未发现错误的 stats={...} 调用，可能是文件路径不对或已经修复。")

def main():
    print("🚀 开始修复构建错误...")
    fix_kpi_cards_file()
    fix_app_usage()
    print("\n✨ 修复完成！建议重新执行 npm run build (或直接推送 git) 测试。")

if __name__ == "__main__":
    main()
