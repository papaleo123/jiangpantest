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
  // 注意：第1年计算时 SOH=1.0（年初状态），年末才衰减
  let currentSOH = 1.0;
  if (year === 1) {
    currentSOH = 1.0; // 第1年无衰减
  } else {
    currentSOH = 1.0 - 0.04 - (year - 2) * 0.025; // 第2年应用首年衰减，之后每年2.5%
  }
  currentSOH = Math.max(0.60, currentSOH); // 最低60%
  
  const capacityWh = (inputs?.capacity || 100) * 1e6;
  const dod = (inputs?.dod || 90) / 100;
  const cycles = inputs?.cycles || 2;
  const runDays = inputs?.run_days || 330;
  const chargeEff = (inputs?.charge_eff || 94) / 100;
  const dischargeEff = (inputs?.discharge_eff || 94) / 100;
  
  // 获取功率（kW）用于容量补贴计算
  const powerKW = (inputs?.capacity || 100) * 1000 / (inputs?.duration_hours || 2); // MWh -> kW (功率 = 容量/时长)
  const durationHours = inputs?.duration_hours || 2;
  const subMode = inputs?.sub_mode || 'energy';
  const subPrice = inputs?.sub_price || 0.35;
  const subDecline = inputs?.sub_decline || 0;
  const spread = inputs?.spread || 0.70;
  const auxPrice = inputs?.aux_price || 0;
  
  // 计算补贴退坡后的当前单价
  const declineFactor = Math.pow(1 - subDecline / 100, year - 1);
  const currentSubPrice = subPrice * declineFactor;
  
  switch (type) {
    case 'discharge_kwh': {
      // 完全复刻 calculatePhysics 中的计算
      const usableCapacityDC = capacityWh * currentSOH * dod; // 直流侧可用容量
      
      // 放电量（交流侧）= 直流可用容量 × 放电效率 × 日循环
      const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
      const annualDischargeKWh = (dailyDischargeAC * runDays) / 1000;
      
      return {
        title: '放电量计算',
        description: `第${year}年放电量，完全复刻代码逻辑`,
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
          { label: '年放电量', value: annualDischargeKWh.toFixed(2), unit: '万kWh', formula: '(日放电量 × runDays) ÷ 1000' },
        ],
        result: { value: rowData.discharge_kwh, unit: '万kWh' }
      };
    }
    
    case 'charge_kwh': {
      // 复刻计算：充电量独立计算，不再通过RTE反推
      const usableCapacityDC = capacityWh * currentSOH * dod; // 直流侧可用容量
      const dailyChargeAC = usableCapacityDC / chargeEff * cycles; // ÷ 充电效率
      const annualChargeKWh = (dailyChargeAC * runDays) / 1000;
      
      return {
        title: '充电量计算',
        description: `第${year}年充电量 = 直流可用容量 ÷ 充电效率 × 日循环 × 运行天数`,
        formula: '直流可用容量 ÷ 充电效率 × 日循环',
        steps: [
          { label: '直流可用容量', value: (usableCapacityDC / 1e6).toFixed(2), unit: 'MWh', formula: 'capacityWh × SOH × DOD' },
          { label: '充电效率', value: (chargeEff * 100).toFixed(0), unit: '%', formula: '输入参数' },
          { label: '日充电量(AC)', value: (dailyChargeAC / 1000).toFixed(2), unit: 'kWh', formula: 'usableCapacityDC ÷ chargeEff × cycles' },
          { label: '年运行天数', value: runDays, unit: '天', formula: '输入参数' },
          { label: '年充电量', value: annualChargeKWh.toFixed(2), unit: '万kWh', formula: '日充电量 × runDays ÷ 1000' },
        ],
        result: { value: rowData.charge_kwh, unit: '万kWh' }
      };
    }
    
    case 'loss_kwh': {
      // 复刻计算
      const usableCapacityDC = capacityWh * currentSOH * dod;
      
      // 放电量计算
      const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
      const annualDischargeKWh = (dailyDischargeAC * runDays) / 1000;
      
      // 充电量计算  
      const dailyChargeAC = usableCapacityDC / chargeEff * cycles;
      const annualChargeKWh = (dailyChargeAC * runDays) / 1000;
      
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
    
    case 'elec_rev': {
      // 需要先计算放电量
      const usableCapacityDC = capacityWh * currentSOH * dod;
      const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
      const annualDischargeKWh = (dailyDischargeAC * runDays) / 1000; // kWh
      const elecRevWan = (annualDischargeKWh * spread) / 10000; // 转换为万元
      
      return {
        title: '电费套利收入',
        description: `第${year}年电费套利收入 = 放电量 × 峰谷价差`,
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
      // 计算放电量（电量补贴用）或功率（容量补贴用）
      const usableCapacityDC = capacityWh * currentSOH * dod;
      const dailyDischargeAC = usableCapacityDC * dischargeEff * cycles;
      const annualDischargeKWh = (dailyDischargeAC * runDays) / 1000;
      
      let subRev = 0;
      let calcSteps = [];
      
      if (subMode === 'energy') {
        // 内蒙模式：按电量
        subRev = (annualDischargeKWh * currentSubPrice) / 10000; // 转换为万元
        calcSteps = [
          { label: '补贴模式', value: '按电量(内蒙模式)', unit: '', formula: '输入参数' },
          { label: '年放电量', value: (annualDischargeKWh / 10000).toFixed(2), unit: '万kWh', formula: '见放电量计算' },
          { label: '退坡后单价', value: currentSubPrice.toFixed(3), unit: '元/kWh', formula: `${subPrice} × (1-${subDecline}%)^{year-1}` },
          { label: '补偿收入', value: subRev.toFixed(2), unit: '万元', formula: '放电量(万kWh) × 单价 × 10000 ÷ 10000' },
        ];
      } else {
        // 甘肃模式：按功率
        const kFactor = Math.min(1, durationHours / 6.0);
        subRev = (powerKW * currentSubPrice * kFactor) / 10000; // 转换为万元
        const powerMW = (inputs?.capacity || 100) / (inputs?.duration_hours || 2); // MW
        calcSteps = [
          { label: '补贴模式', value: '按功率(甘肃模式)', unit: '', formula: '输入参数' },
          { label: '装机容量', value: (inputs?.capacity || 100).toFixed(0), unit: 'MWh', formula: '输入参数' },
          { label: '功率', value: (powerMW).toFixed(1), unit: 'MW', formula: '容量÷时长' },
          { label: 'K系数', value: kFactor.toFixed(2), unit: '', formula: `min(1, ${durationHours}/6)` },
          { label: '退坡后单价', value: currentSubPrice.toFixed(2), unit: '元/kW', formula: `${subPrice} × (1-${subDecline}%)^{year-1}` },
          { label: '补偿收入', value: subRev.toFixed(2), unit: '万元', formula: '功率(kW) × K系数 × 单价 ÷ 10000' },
        ];
      }
      
      return {
        title: '补偿收入',
        description: `第${year}年补偿收入（${subMode === 'energy' ? '内蒙-按电量' : '甘肃-按功率'}模式）`,
        formula: subMode === 'energy' ? '放电量 × 退坡后单价' : '功率 × K系数 × 退坡后单价',
        steps: calcSteps,
        result: { value: rowData.sub_rev, unit: '万元' }
      };
    }
    
    case 'aux_rev': {
      const auxRev = (powerKW * auxPrice) / 10000; // 转换为万元
      
      return {
        title: '辅助服务收入',
        description: `第${year}年辅助服务收入（调峰、调频等）`,
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
        description: `第${year}年总收入 = 电费套利 + 补偿 + 辅助服务`,
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
