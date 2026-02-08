import { Calculator, Info } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { createCalculationDetail } from '@/utils/calculationDetails';

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

export { createCalculationDetail };
export type { CalculationDetail };
