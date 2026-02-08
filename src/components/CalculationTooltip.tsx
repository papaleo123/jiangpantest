import { Calculator, Info } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
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

interface CalculationTooltipProps {
  detail: CalculationDetail | null;
  isOpen: boolean;
  onClose: () => void;
}

export function CalculationTooltip({ detail, isOpen, onClose }: CalculationTooltipProps) {
  if (!detail) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <Calculator className="w-5 h-5 text-blue-600" />
            {detail.title}
            <Badge variant="secondary" className="ml-2">
              {detail.result.unit}
            </Badge>
          </DialogTitle>
        </DialogHeader>

        <p className="text-sm text-slate-600 mt-2">{detail.description}</p>

        <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
          <div className="text-xs text-blue-600 font-medium mb-1">计算公式</div>
          <div className="text-sm font-mono text-blue-800 break-all">
            {detail.formula}
          </div>
        </div>

        <div className="mt-4 space-y-2">
          <div className="text-sm font-medium text-slate-700 flex items-center gap-2">
            <Info className="w-4 h-4" />
            计算过程
          </div>
          
          <div className="space-y-2">
            {detail.steps.map((step, index) => (
              <div key={index} className="flex items-center justify-between p-2 bg-slate-50 rounded text-sm">
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-slate-200 flex items-center justify-center text-xs font-medium text-slate-600">
                    {index + 1}
                  </span>
                  <span className="text-slate-700">{step.label}</span>
                  {step.formula && (
                    <span className="text-xs text-slate-500 font-mono">
                      = {step.formula}
                    </span>
                  )}
                </div>
                <div className="text-right">
                  <span className="font-mono font-medium text-slate-900">
                    {typeof step.value === 'number' ? step.value.toFixed(2) : step.value}
                  </span>
                  {step.unit && (
                    <span className="text-xs text-slate-500 ml-1">{step.unit}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-4 pt-4 border-t">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-700">计算结果</span>
            <div className="text-right">
              <span className="text-2xl font-bold text-blue-600 font-mono">
                {detail.result.value}
              </span>
              <span className="text-sm text-slate-500 ml-1">{detail.result.unit}</span>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// 创建计算详情的函数
export function createCalculationDetail(
  type: string,
  rowData: any,
  inputs: any
): CalculationDetail | null {
  switch (type) {
    case 'elec_rev':
      return {
        title: '峰谷价差收益',
        description: '通过低谷充电、高峰放电赚取的电价差收益',
        formula: '放电电量 × (峰时电价 - 谷时电价)',
        steps: [
          { label: '放电电量', value: rowData.discharge_kwh, unit: '万kWh' },
          { label: '峰时电价', value: (inputs?.price_valley || 0) + (inputs?.spread || 0), unit: '元/kWh', formula: '谷时电价 + 价差' },
          { label: '谷时电价', value: inputs?.price_valley || 0, unit: '元/kWh' },
          { label: '单位收益', value: inputs?.spread || 0, unit: '元/kWh' },
        ],
        result: { value: rowData.elec_rev, unit: '万元' }
      };
    
    case 'sub_rev':
      return {
        title: '补贴收益',
        description: '政策补贴收入',
        formula: inputs?.sub_mode === 'energy' ? '放电量 × 补贴单价' : '容量 × 补贴单价',
        steps: [
          { label: '补贴模式', value: inputs?.sub_mode === 'energy' ? '按电量' : '按容量', unit: '' },
          { label: '补贴单价', value: inputs?.sub_price || 0, unit: inputs?.sub_mode === 'energy' ? '元/kWh' : '元/kW' },
          { label: '补贴年限', value: inputs?.sub_years || 0, unit: '年' },
        ],
        result: { value: rowData.sub_rev, unit: '万元' }
      };
    
    case 'loss_cost':
      return {
        title: '充电成本',
        description: '低谷时段充电的电费成本',
        formula: '充电电量 × 谷时电价',
        steps: [
          { label: '充电电量', value: rowData.charge_kwh, unit: '万kWh' },
          { label: '谷时电价', value: inputs?.price_valley || 0, unit: '元/kWh' },
        ],
        result: { value: rowData.loss_cost, unit: '万元' }
      };
    
    case 'income_tax':
      const taxableIncome = (parseFloat(rowData.total_rev || 0) - parseFloat(rowData.opex || 0) - parseFloat(rowData.loss_cost || 0) - parseFloat(rowData.dep || 0) - parseFloat(rowData.interest || 0) - parseFloat(rowData.surcharge || 0));
      return {
        title: '所得税',
        description: '企业应缴纳的所得税',
        formula: '应纳税所得额 × 税率',
        steps: [
          { label: '营业收入', value: rowData.total_rev, unit: '万元' },
          { label: '运营成本', value: rowData.opex, unit: '万元' },
          { label: '充电成本', value: rowData.loss_cost, unit: '万元' },
          { label: '折旧', value: rowData.dep, unit: '万元' },
          { label: '利息', value: rowData.interest, unit: '万元' },
          { label: '附加税', value: rowData.surcharge, unit: '万元' },
          { label: '应纳税所得额', value: Math.max(0, taxableIncome).toFixed(2), unit: '万元' },
          { label: '税率', value: inputs?.tax_rate || 25, unit: '%' },
        ],
        result: { value: rowData.income_tax, unit: '万元' }
      };
    
    case 'total_tax':
      return {
        title: '总税金',
        description: '增值税、附加税、所得税合计',
        formula: '增值税 + 附加税 + 所得税',
        steps: [
          { label: '增值税', value: rowData.vat_pay, unit: '万元' },
          { label: '附加税', value: rowData.surcharge, unit: '万元' },
          { label: '所得税', value: rowData.income_tax, unit: '万元' },
        ],
        result: { value: rowData.total_tax, unit: '万元' }
      };
    
    case 'ebitda':
      return {
        title: 'EBITDA',
        description: '息税折旧前利润',
        formula: '营业收入 - 运营成本 - 充电成本 - 附加税',
        steps: [
          { label: '营业收入', value: rowData.total_rev, unit: '万元' },
          { label: '运营成本', value: rowData.opex, unit: '万元' },
          { label: '充电成本', value: rowData.loss_cost, unit: '万元' },
          { label: '附加税', value: rowData.surcharge, unit: '万元' },
        ],
        result: { value: rowData.ebitda, unit: '万元' }
      };
    

    case 'charge_kwh':
      return {
        title: '充电量计算',
        description: '年度总充电量，考虑日循环次数和运行天数',
        formula: '容量 × 日循环次数 × 运行天数 × SOH',
        steps: [
          { label: '装机容量', value: inputs?.capacity || 0, unit: 'MWh' },
          { label: '日循环次数', value: inputs?.cycles || 1, unit: '次/天' },
          { label: '年运行天数', value: inputs?.run_days || 330, unit: '天' },
          { label: '当前SOH', value: rowData.soh, unit: '' },
          { label: '充电效率', value: inputs?.charge_eff || 0.9, unit: '' },
        ],
        result: { value: rowData.charge_kwh, unit: '万kWh' }
      };
    
    case 'discharge_kwh':
      return {
        title: '放电量计算',
        description: '年度总放电量，考虑放电深度和效率',
        formula: '充电量 × DOD × 放电效率',
        steps: [
          { label: '充电量', value: rowData.charge_kwh, unit: '万kWh' },
          { label: '放电深度DOD', value: inputs?.dod || 0.9, unit: '' },
          { label: '放电效率', value: inputs?.discharge_eff || 0.92, unit: '' },
        ],
        result: { value: rowData.discharge_kwh, unit: '万kWh' }
      };
    
    case 'loss_kwh':
      return {
        title: '损耗电量',
        description: '充放电过程中的能量损耗',
        formula: '充电量 - 放电量',
        steps: [
          { label: '充电量', value: rowData.charge_kwh, unit: '万kWh' },
          { label: '放电量', value: rowData.discharge_kwh, unit: '万kWh' },
          { label: '损耗率', value: ((parseFloat(rowData.charge_kwh) - parseFloat(rowData.discharge_kwh)) / parseFloat(rowData.charge_kwh) * 100).toFixed(2), unit: '%' },
        ],
        result: { value: rowData.loss_kwh, unit: '万kWh' }
      };
    
    case 'soh':
      return {
        title: '电池健康度 SOH',
        description: '电池容量保持率，随使用年限衰减',
        formula: '初始SOH - 首年衰减 - 后续年衰减',
        steps: [
          { label: '年份', value: rowData.y, unit: '年' },
          { label: '首年衰减', value: '4%', unit: '' },
          { label: '后续年衰减', value: '2.5%', unit: '' },
          { label: '计算公式', value: rowData.y === '1' ? '100% - 4%' : '上一年SOH - 2.5%', unit: '' },
        ],
        result: { value: rowData.soh, unit: '' }
      };
    
    case 'aux_rev':
      return {
        title: '辅助服务收益',
        description: '调频调峰等辅助服务收入',
        formula: '装机容量 × 辅助服务单价 × 调节性能',
        steps: [
          { label: '装机容量', value: inputs?.capacity || 0, unit: 'MWh' },
          { label: '辅助服务单价', value: inputs?.aux_price || 0, unit: '元/kW' },
          { label: '年调节次数', value: '按实际调用', unit: '次' },
        ],
        result: { value: rowData.aux_rev, unit: '万元' }
      };
    
    case 'opex':
      return {
        title: '运维成本',
        description: '年度运营维护费用',
        formula: '装机容量 × 单位运维成本',
        steps: [
          { label: '装机容量', value: inputs?.capacity || 0, unit: 'MWh' },
          { label: '单位运维成本', value: inputs?.opex || 0, unit: '元/Wh/年' },
          { label: '总容量', value: (inputs?.capacity || 0) * 1000000, unit: 'Wh' },
        ],
        result: { value: rowData.opex, unit: '万元' }
      };
    
    case 'dep':
      return {
        title: '折旧费用',
        description: '设备折旧费用（直线法）',
        formula: '(投资原值 - 残值) / 折旧年限',
        steps: [
          { label: '投资原值', value: ((inputs?.capex || 0) * (inputs?.capacity || 0)).toFixed(2), unit: '万元' },
          { label: '残值率', value: inputs?.residual_rate || 5, unit: '%' },
          { label: '折旧年限', value: inputs?.dep_years || 10, unit: '年' },
          { label: '年折旧额', value: (((inputs?.capex || 0) * (inputs?.capacity || 0) * (1 - (inputs?.residual_rate || 5)/100)) / (inputs?.dep_years || 10)).toFixed(2), unit: '万元/年' },
        ],
        result: { value: rowData.dep, unit: '万元' }
      };
    
    case 'interest':
      return {
        title: '利息支出',
        description: '贷款利息（等额本金还款法）',
        formula: '剩余本金 × 贷款利率',
        steps: [
          { label: '贷款比例', value: inputs?.debt_ratio || 70, unit: '%' },
          { label: '贷款金额', value: ((inputs?.capex || 0) * (inputs?.capacity || 0) * (inputs?.debt_ratio || 70) / 100).toFixed(2), unit: '万元' },
          { label: '贷款利率', value: inputs?.loan_rate || 4.5, unit: '%' },
          { label: '还款年限', value: inputs?.years || 10, unit: '年' },
          { label: '剩余本金', value: '逐年递减', unit: '万元' },
        ],
        result: { value: rowData.interest, unit: '万元' }
      };
    
    case 'vat_pay':
      return {
        title: '增值税',
        description: '应交增值税（销项 - 进项）',
        formula: '销项税 - 可抵扣进项税 - 留抵税额',
        steps: [
          { label: '销项税', value: (parseFloat(rowData.total_rev || 0) * 0.13).toFixed(2), unit: '万元', formula: '收入 × 13%' },
          { label: '可抵扣进项', value: (parseFloat(rowData.opex || 0) * 0.13).toFixed(2), unit: '万元', formula: '运维 × 13%' },
          { label: '留抵税额', value: '设备投资进项税，逐年抵扣', unit: '万元' },
        ],
        result: { value: rowData.vat_pay, unit: '万元' }
      };
    
    case 'surcharge':
      return {
        title: '附加税',
        description: '城建税 + 教育费附加 + 地方教育附加',
        formula: '应交增值税 × 12%',
        steps: [
          { label: '应交增值税', value: rowData.vat_pay, unit: '万元' },
          { label: '城建税(7%)', value: (parseFloat(rowData.vat_pay || 0) * 0.07).toFixed(2), unit: '万元' },
          { label: '教育附加(3%)', value: (parseFloat(rowData.vat_pay || 0) * 0.03).toFixed(2), unit: '万元' },
          { label: '地方教育(2%)', value: (parseFloat(rowData.vat_pay || 0) * 0.02).toFixed(2), unit: '万元' },
        ],
        result: { value: rowData.surcharge, unit: '万元' }
      };
    
    case 'net_profit':
      return {
        title: '净利润',
        description: '税后净利润',
        formula: '营业收入 - 总成本 - 总税金',
        steps: [
          { label: '营业收入', value: rowData.total_rev, unit: '万元' },
          { label: '运营成本', value: rowData.opex, unit: '万元' },
          { label: '充电成本', value: rowData.loss_cost, unit: '万元' },
          { label: '折旧', value: rowData.dep, unit: '万元' },
          { label: '利息', value: rowData.interest, unit: '万元' },
          { label: '总税金', value: rowData.total_tax, unit: '万元' },
        ],
        result: { value: rowData.net_profit, unit: '万元' }
      };
    
    case 'cf':
      return {
        title: '股东现金流',
        description: '股东可分配的现金流',
        formula: '净利润 + 折旧 - 本金偿还',
        steps: [
          { label: '净利润', value: rowData.net_profit, unit: '万元' },
          { label: '折旧加回', value: rowData.dep, unit: '万元' },
          { label: '本金偿还', value: rowData.principal, unit: '万元' },
        ],
        result: { value: rowData.cf, unit: '万元' }
      };
    
    case 'cum_cf':
      return {
        title: '累计现金流',
        description: '历年现金流累计值',
        formula: '∑历年股东现金流',
        steps: [
          { label: '上年累计', value: '前一年 cum_cf', unit: '万元' },
          { label: '本年现金流', value: rowData.cf, unit: '万元' },
        ],
        result: { value: rowData.cum_cf, unit: '万元' }
      };
    
    case 'dscr':
      return {
        title: '偿债覆盖率 DSCR',
        description: '偿还债务能力指标',
        formula: '(净利润 + 折旧 + 利息) / 当期还款额',
        steps: [
          { label: '净利润', value: rowData.net_profit, unit: '万元' },
          { label: '折旧', value: rowData.dep, unit: '万元' },
          { label: '利息', value: rowData.interest, unit: '万元' },
          { label: '可用于偿债资金', value: (parseFloat(rowData.net_profit || 0) + parseFloat(rowData.dep || 0) + parseFloat(rowData.interest || 0)).toFixed(2), unit: '万元' },
          { label: '当期还款额', value: rowData.principal, unit: '万元' },
        ],
        result: { value: rowData.dscr, unit: '' }
      };
    default:
      return null;
  }
}
