import { Calculator, Info } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import type { InputParams, YearlyRow } from '@/types';
import { Badge } from '@/components/ui/badge';

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
  result: {
    value: string | number;
    unit: string;
  };
}

interface Props {
  detail: CalculationDetail | null;
  isOpen: boolean;
  onClose: () => void;
}

// 展示用的计算逻辑（完全复刻 useStorageCalculation.ts）
export function createCalculationDetail(
  type: string,
  rowData: YearlyRow,
  inputs: InputParams
): CalculationDetail | null {
  const year = typeof rowData.y === "string" ? parseInt(rowData.y) || 1 : (rowData.y || 1);
  
  // 复刻 SOH 计算逻辑（与 calculatePhysics 一致）
  let currentSOH = 1.0;
  if (year === 1) {
    currentSOH = 1.0 - 0.04; // 首年衰减4%
  } else {
    currentSOH = 1.0 - 0.04 - (year - 1) * 0.025; // 后续每年2.5%
  }
  currentSOH = Math.max(0.60, currentSOH); // 最低60%
  
  const capacityWh = (inputs?.capacity || 100) * 1e6;
  const dod = (inputs?.dod || 90) / 100;
  const cycles = inputs?.cycles || 2;
  const runDays = inputs?.run_days || 330;
  const chargeEff = (inputs?.charge_eff || 94) / 100;
  const dischargeEff = (inputs?.discharge_eff || 94) / 100;
  const rte = chargeEff * dischargeEff;
  
  switch (type) {
    case 'discharge_kwh': {
      // 完全复刻 calculatePhysics 中的计算
      const usableCapacity = capacityWh * currentSOH * dod;
      const dailyDischarge = usableCapacity * cycles;
      const annualDischargeKWh = (dailyDischarge * runDays) / 1000;
      
      return {
        title: '放电量计算',
        description: `第${year}年放电量，完全复刻代码逻辑`,
        formula: '((装机容量×1,000,000) × SOH × DOD) × 日循环 × 运行天数 ÷ 1000',
        steps: [
          { label: '装机容量', value: inputs?.capacity || 100, unit: 'MWh', formula: '输入参数' },
          { label: '转换为Wh', value: (capacityWh).toLocaleString(), unit: 'Wh', formula: 'capacity × 1,000,000' },
          { label: 'SOH计算', value: year === 1 ? '首年衰减4%' : `首年4% + ${year-1}年×2.5%`, unit: '', formula: '逐年衰减' },
          { label: '当前SOH', value: (currentSOH * 100).toFixed(1), unit: '%', formula: `Math.max(60%, ${(currentSOH * 100).toFixed(1)}%)` },
          { label: '放电深度DOD', value: (dod * 100).toFixed(0), unit: '%', formula: '输入参数' },
          { label: '可用容量', value: (usableCapacity / 1e6).toFixed(2), unit: 'MWh', formula: 'capacityWh × SOH × DOD' },
          { label: '日循环次数', value: cycles, unit: '次', formula: '输入参数' },
          { label: '日放电量', value: (dailyDischarge / 1000).toFixed(2), unit: '万kWh', formula: 'usableCapacity × cycles' },
          { label: '年运行天数', value: runDays, unit: '天', formula: '输入参数' },
          { label: '年放电量', value: annualDischargeKWh.toFixed(2), unit: '万kWh', formula: '(日放电量 × runDays) ÷ 1000' },
        ],
        result: { value: rowData.discharge_kwh, unit: '万kWh' }
      };
    }
    
    case 'charge_kwh': {
      // 复刻计算
      const usableCapacity = capacityWh * currentSOH * dod;
      const dailyDischarge = usableCapacity * cycles;
      const annualDischargeKWh = (dailyDischarge * runDays) / 1000;
      const annualChargeKWh = annualDischargeKWh / rte;
      
      return {
        title: '充电量计算',
        description: `第${year}年充电量 = 放电量 ÷ 综合效率`,
        formula: '放电量 ÷ (充电效率 × 放电效率)',
        steps: [
          { label: '年放电量', value: annualDischargeKWh.toFixed(2), unit: '万kWh', formula: '见放电量计算' },
          { label: '充电效率', value: (chargeEff * 100).toFixed(0), unit: '%', formula: '输入参数' },
          { label: '放电效率', value: (dischargeEff * 100).toFixed(0), unit: '%', formula: '输入参数' },
          { label: '综合效率RTE', value: (rte * 100).toFixed(2), unit: '%', formula: 'chargeEff × dischargeEff' },
          { label: '年充电量', value: annualChargeKWh.toFixed(2), unit: '万kWh', formula: '放电量 ÷ RTE' },
        ],
        result: { value: rowData.charge_kwh, unit: '万kWh' }
      };
    }
    
    case 'loss_kwh': {
      const usableCapacity = capacityWh * currentSOH * dod;
      const dailyDischarge = usableCapacity * cycles;
      const annualDischargeKWh = (dailyDischarge * runDays) / 1000;
      const annualChargeKWh = annualDischargeKWh / rte;
      const lossKWh = annualChargeKWh - annualDischargeKWh;
      
      return {
        title: '损耗电量',
        description: '充放电过程中的能量损耗',
        formula: '充电量 - 放电量',
        steps: [
          { label: '年充电量', value: annualChargeKWh.toFixed(2), unit: '万kWh', formula: '见充电量计算' },
          { label: '年放电量', value: annualDischargeKWh.toFixed(2), unit: '万kWh', formula: '见放电量计算' },
          { label: '损耗电量', value: lossKWh.toFixed(2), unit: '万kWh', formula: '充电量 - 放电量' },
        ],
        result: { value: rowData.loss_kwh, unit: '万kWh' }
      };
    }
    
    default:
      return null;
  }
}

export function CalculationTooltip({ detail, isOpen, onClose }: Props) {
  if (!detail) return null;
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Calculator className="w-5 h-5 text-blue-600" />
            {detail.title}
            <Badge variant="secondary">{detail.result.unit}</Badge>
          </DialogTitle>
        </DialogHeader>
        
        <p className="text-sm text-slate-600">{detail.description}</p>
        
        <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
          <div className="text-xs text-blue-600 font-medium mb-1">计算公式</div>
          <div className="text-sm font-mono text-blue-800 break-all">{detail.formula}</div>
        </div>
        
        <div className="mt-4 space-y-2">
          <div className="text-sm font-medium text-slate-700 flex items-center gap-2">
            <Info className="w-4 h-4" />
            计算过程（完全复刻代码逻辑）
          </div>
          
          {detail.steps.map((step, index) => (
            <div key={index} className="flex items-center justify-between p-2 bg-slate-50 rounded text-sm">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-slate-200 flex items-center justify-center text-xs font-medium">
                  {index + 1}
                </span>
                <span className="text-slate-700">{step.label}</span>
                {step.formula && <span className="text-xs text-slate-500 font-mono">= {step.formula}</span>}
              </div>
              <div className="text-right">
                <span className="font-mono font-medium">
                  {typeof step.value === 'number' ? step.value.toFixed(2) : step.value}
                </span>
                {step.unit && <span className="text-xs text-slate-500 ml-1">{step.unit}</span>}
              </div>
            </div>
          ))}
        </div>
        
        <div className="mt-4 pt-4 border-t flex justify-between items-center">
          <span className="text-sm font-medium text-slate-700">计算结果</span>
          <div className="text-right">
            <span className="text-2xl font-bold text-blue-600 font-mono">{detail.result.value}</span>
            <span className="text-sm text-slate-500 ml-1">{detail.result.unit}</span>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
