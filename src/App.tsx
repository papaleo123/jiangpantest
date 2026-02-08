import { useEffect } from 'react';
import { Header } from '@/components/Header';
import { InputPanel } from '@/components/InputPanel';
import { KpiCards } from '@/components/KpiCards';
import { ChartsSection } from '@/components/ChartsSection';
import { DataTable } from '@/components/DataTable';
import { useStorageCalculation } from '@/hooks/useStorageCalculation';
import { Toaster } from '@/components/ui/sonner';
import { toast } from 'sonner';

function App() {
  const { inputs, result, kpi, powerMW, rte, updateInput, calculate, exportCSV } = useStorageCalculation();

  // 初始计算
  useEffect(() => {
    const timer = setTimeout(() => {
      calculate();
      toast.success('计算完成', {
        description: '财务模型 V13.0 已初始化',
      });
    }, 500);
    return () => clearTimeout(timer);
  }, []);

  const handleCalculate = () => {
    calculate();
    toast.success('计算完成', {
      description: '财务模型已更新',
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <Header />
      
      <main className="p-3 md:p-5">
        <div className="max-w-[1800px] mx-auto flex flex-col lg:flex-row gap-4 md:gap-5">
          {/* 左侧输入面板 */}
          <div className="w-full lg:w-[400px] lg:flex-shrink-0">
            <InputPanel
              inputs={inputs}
              powerMW={powerMW}
              rte={rte}
              onUpdate={updateInput}
              onCalculate={handleCalculate}
            />
          </div>

          {/* 右侧内容区 */}
          <div className="flex-1 min-w-0 flex flex-col gap-4">
            {/* KPI卡片 */}
            <KpiCards kpi={kpi} stats={result?.stats} />

            {/* 图表区域 */}
            <ChartsSection result={result} inputs={inputs} />

            {/* 数据表格 */}
            <DataTable result={result} inputs={inputs} onExport={exportCSV} />
          </div>
        </div>
      </main>

      <Toaster position="top-right" />
    </div>
  );
}

export default App;
