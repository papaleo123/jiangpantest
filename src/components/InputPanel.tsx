import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Settings2, Calculator, Zap, TrendingUp, DollarSign, Building2, Package, Info } from 'lucide-react';
import type { InputParams } from '@/types';

interface InputPanelProps {
  inputs: InputParams;
  powerMW: string;
  rte: string;
  onUpdate: <K extends keyof InputParams>(key: K, value: InputParams[K]) => void;
  onCalculate: () => void;
}

interface SectionTitleProps {
  icon: React.ReactNode;
  title: string;
  badge?: string;
}

function SectionTitle({ icon, title, badge }: SectionTitleProps) {
  return (
    <div className="flex items-center justify-between bg-slate-100 rounded-lg px-3 py-2 mb-3 border-l-4 border-blue-500">
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-sm font-semibold text-slate-700">{title}</span>
      </div>
      {badge && (
        <Badge className="bg-orange-400 text-white text-xs">{badge}</Badge>
      )}
    </div>
  );
}

interface InputGroupProps {
  label: string;
  children: React.ReactNode;
  hint?: string;
  tooltip?: string;
}

function InputGroup({ label, children, hint, tooltip }: InputGroupProps) {
  return (
    <div className="space-y-1 mb-3">
      <div className="flex items-center justify-between">
        <Label className="text-xs md:text-sm text-slate-600 flex items-center gap-1">
          {label}
          {tooltip && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="w-3 h-3 text-slate-400 cursor-help" />
                </TooltipTrigger>
                <TooltipContent className="max-w-[200px] text-xs">
                  <p>{tooltip}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </Label>
        <div className="w-[100px] md:w-[115px]">{children}</div>
      </div>
      {hint && <p className="text-xs text-orange-600 text-right">{hint}</p>}
    </div>
  );
}

export function InputPanel({ inputs, powerMW, rte, onUpdate, onCalculate }: InputPanelProps) {
  const getSubModeHint = () => {
    return inputs.sub_mode === 'energy' 
      ? '内蒙模式: 年放电量 × 单价'
      : '甘肃模式: 功率 × 单价 × (时长/6)';
  };

  const getSubPriceLabel = () => {
    return inputs.sub_mode === 'energy' 
      ? '补偿标准 (元/kWh)'
      : '补偿标准 (元/kW/年)';
  };

  const handleSubModeChange = (value: string) => {
    const newMode = value as 'energy' | 'capacity';
    onUpdate('sub_mode', newMode);
    if (newMode === 'energy' && inputs.sub_price > 10) {
      onUpdate('sub_price', 0.35);
    } else if (newMode === 'capacity' && inputs.sub_price < 10) {
      onUpdate('sub_price', 330);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-md p-4 md:p-5 border border-slate-100">
      <div className="flex items-center gap-2 mb-4 md:mb-5 pb-3 border-b-2 border-blue-500">
        <Settings2 className="w-5 h-5 text-blue-600" />
        <h2 className="text-base md:text-lg font-bold text-slate-800">投决参数面板</h2>
      </div>

      <InputGroup 
        label="项目总周期 (年)" 
        tooltip="储能项目的运营年限，通常为15-20年"
      >
        <Input
          type="number"
          value={inputs.years}
          onChange={(e) => onUpdate('years', Number(e.target.value))}
          className="text-right font-mono bg-blue-50 border-blue-300 text-sm"
        />
      </InputGroup>

      {/* 补偿/补贴模式 */}
      <SectionTitle 
        icon={<DollarSign className="w-4 h-4 text-slate-600" />}
        title="1. 补偿/补贴模式"
      />
      
      <InputGroup label="补偿模式">
        <Select value={inputs.sub_mode} onValueChange={handleSubModeChange}>
          <SelectTrigger className="text-right text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="energy">内蒙模式 (按电量)</SelectItem>
            <SelectItem value="capacity">甘肃模式 (按功率)</SelectItem>
          </SelectContent>
        </Select>
      </InputGroup>

      <InputGroup label={getSubPriceLabel()} hint={getSubModeHint()}>
        <Input
          type="number"
          step={0.01}
          value={inputs.sub_price}
          onChange={(e) => onUpdate('sub_price', Number(e.target.value))}
          className="text-right font-mono text-sm"
        />
      </InputGroup>

      <InputGroup label="补贴年限 (年)">
        <Input
          type="number"
          value={inputs.sub_years}
          onChange={(e) => onUpdate('sub_years', Number(e.target.value))}
          className="text-right font-mono text-sm"
        />
      </InputGroup>

      <InputGroup 
        label="年退坡比例 (%)" 
        tooltip="补贴每年递减的比例，如5%表示第二年补贴为去年的95%"
      >
        <Input
          type="number"
          value={inputs.sub_decline}
          onChange={(e) => onUpdate('sub_decline', Number(e.target.value))}
          className="text-right font-mono text-sm"
        />
      </InputGroup>

      {/* 或有收益 */}
      <SectionTitle 
        icon={<TrendingUp className="w-4 h-4 text-slate-600" />}
        title="2. 或有收益 (辅助服务)"
      />

      <InputGroup 
        label="预估收益 (元/kW/年)" 
        tooltip="调峰、调频等辅助服务的年化收益，如不参与填0"
      >
        <Input
          type="number"
          value={inputs.aux_price}
          onChange={(e) => onUpdate('aux_price', Number(e.target.value))}
          className="text-right font-mono text-sm"
          placeholder="0"
        />
      </InputGroup>

      {/* 基础参数 */}
      <SectionTitle 
        icon={<Zap className="w-4 h-4 text-slate-600" />}
        title="3. 基础参数"
        badge="核心"
      />

      <InputGroup 
        label="装机容量 (MWh)" 
        tooltip="储能系统的额定容量"
      >
        <Input
          type="number"
          value={inputs.capacity}
          onChange={(e) => onUpdate('capacity', Number(e.target.value))}
          className="text-right font-mono text-sm"
        />
      </InputGroup>

      <InputGroup 
        label="储能系统时长" 
        hint={`对应功率: ${powerMW} MW`}
        tooltip="储能时长决定功率大小，功率=容量/时长"
      >
        <Select 
          value={String(inputs.duration_hours)} 
          onValueChange={(v) => onUpdate('duration_hours', Number(v))}
        >
          <SelectTrigger className="text-right text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="2">2小时 (0.5C)</SelectItem>
            <SelectItem value="4">4小时 (0.25C)</SelectItem>
            <SelectItem value="6">6小时 (0.17C)</SelectItem>
          </SelectContent>
        </Select>
      </InputGroup>

      {/* 效率参数 - 分开显示 */}
      <div className="bg-orange-50 rounded-lg p-3 mb-3 border border-orange-200">
        <p className="text-xs text-orange-700 font-medium mb-2">效率参数 (影响充放电量计算)</p>
        
        <InputGroup 
          label="充电效率 (%)" 
          tooltip="AC端充电效率，通常92-96%"
        >
          <Input
            type="number"
            step={0.1}
            value={inputs.charge_eff}
            onChange={(e) => onUpdate('charge_eff', Number(e.target.value))}
            className="text-right font-mono bg-white text-sm"
          />
        </InputGroup>

        <InputGroup 
          label="放电效率 (%)" 
          tooltip="AC端放电效率，通常92-96%"
        >
          <Input
            type="number"
            step={0.1}
            value={inputs.discharge_eff}
            onChange={(e) => onUpdate('discharge_eff', Number(e.target.value))}
            className="text-right font-mono bg-white text-sm"
          />
        </InputGroup>

        <InputGroup 
          label="往返效率 RTE (%)" 
          tooltip="RTE = 充电效率 × 放电效率"
        >
          <Input
            type="number"
            value={rte}
            disabled
            className="text-right font-mono bg-slate-100 text-sm text-slate-500"
          />
        </InputGroup>

        <InputGroup 
          label="放电深度 DOD (%)" 
          tooltip="每次循环使用的容量比例，通常90%，影响电池寿命"
        >
          <Input
            type="number"
            step={1}
            value={inputs.dod}
            onChange={(e) => onUpdate('dod', Number(e.target.value))}
            className="text-right font-mono bg-white text-sm"
          />
        </InputGroup>
      </div>

      <InputGroup 
        label="充电电价 (元/kWh)" 
        hint="用于计算效率损耗成本"
        tooltip="低谷时段的购电电价"
      >
        <Input
          type="number"
          step={0.01}
          value={inputs.price_valley}
          onChange={(e) => onUpdate('price_valley', Number(e.target.value))}
          className="text-right font-mono text-sm"
        />
      </InputGroup>

      <InputGroup 
        label="峰谷价差 (元/kWh)" 
        tooltip="高峰电价 - 低谷电价，套利收入的基础"
      >
        <Input
          type="number"
          step={0.01}
          value={inputs.spread}
          onChange={(e) => onUpdate('spread', Number(e.target.value))}
          className="text-right font-mono text-sm"
        />
      </InputGroup>

      <InputGroup 
        label="系统造价 (元/Wh)" 
        tooltip="储能系统单位容量造价，含PCS、BMS、EMS等"
      >
        <Input
          type="number"
          step={0.05}
          value={inputs.capex}
          onChange={(e) => onUpdate('capex', Number(e.target.value))}
          className="text-right font-mono text-sm"
        />
      </InputGroup>

      <InputGroup 
        label="运维成本 (元/Wh/年)" 
        tooltip="年化运维成本，含人工、维护、保险等"
      >
        <Input
          type="number"
          step={0.005}
          value={inputs.opex}
          onChange={(e) => onUpdate('opex', Number(e.target.value))}
          className="text-right font-mono text-sm"
        />
      </InputGroup>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <InputGroup 
          label="日循环次数" 
          tooltip="每天充放电循环次数，通常1-2次"
        >
          <Input
            type="number"
            step={0.5}
            value={inputs.cycles}
            onChange={(e) => onUpdate('cycles', Number(e.target.value))}
            className="text-right font-mono text-sm"
          />
        </InputGroup>

        <InputGroup 
          label="年运行天数" 
          tooltip="每年实际运行天数，考虑检修等因素"
        >
          <Input
            type="number"
            value={inputs.run_days}
            onChange={(e) => onUpdate('run_days', Number(e.target.value))}
            className="text-right font-mono text-sm"
          />
        </InputGroup>
      </div>

      {/* 融资与税务 */}
      <SectionTitle 
        icon={<Building2 className="w-4 h-4 text-slate-600" />}
        title="4. 融资与税务"
      />

      <InputGroup 
        label="折旧年限 (年)" 
        tooltip="设备折旧年限，通常10-15年"
      >
        <Input
          type="number"
          value={inputs.dep_years}
          onChange={(e) => onUpdate('dep_years', Number(e.target.value))}
          className="text-right font-mono text-sm"
        />
      </InputGroup>

      <InputGroup 
        label="残值率 (%)" 
        tooltip="项目结束时设备的残值比例"
      >
        <Input
          type="number"
          step={1}
          value={inputs.residual_rate}
          onChange={(e) => onUpdate('residual_rate', Number(e.target.value))}
          className="text-right font-mono text-sm"
        />
      </InputGroup>

      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <Label className="text-xs md:text-sm text-slate-600">贷款比例 / 利率</Label>
          <div className="flex gap-2 w-[170px] md:w-[200px]">
            <Input
              type="number"
              value={inputs.debt_ratio}
              onChange={(e) => onUpdate('debt_ratio', Number(e.target.value))}
              className="text-right font-mono w-1/3 text-sm"
              placeholder="%"
            />
            <Input
              type="number"
              value={inputs.loan_rate}
              onChange={(e) => onUpdate('loan_rate', Number(e.target.value))}
              className="text-right font-mono w-1/3 text-sm"
              placeholder="%"
            />
          </div>
        </div>
      </div>

      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <Label className="text-xs md:text-sm text-slate-600">增值税 / 所得税 / 附加 / 附加</Label>
          <div className="flex gap-2 w-[170px] md:w-[200px]">
            <Input
              type="number"
              value={inputs.vat_rate}
              onChange={(e) => onUpdate('vat_rate', Number(e.target.value))}
              className="text-right font-mono w-1/3 text-sm"
              placeholder="%"
            />
            <Input
              type="number"
              value={inputs.tax_rate}
              onChange={(e) => onUpdate('tax_rate', Number(e.target.value))}
              className="text-right font-mono w-1/3 text-sm"
              placeholder="%"
            />
          </div>
        </div>
      </div>

      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <Label className="text-xs md:text-sm text-slate-600">优惠年限 / 优惠税率</Label>
          <div className="flex gap-2 w-[170px] md:w-[200px]">
            <Input
              type="number"
              value={inputs.tax_preferential_years}
              onChange={(e) => onUpdate('tax_preferential_years', Number(e.target.value))}
              className="text-right font-mono w-1/3 text-sm"
              placeholder="年"
            />
            <Input
              type="number"
              value={inputs.tax_preferential_rate}
              onChange={(e) => onUpdate('tax_preferential_rate', Number(e.target.value))}
              className="text-right font-mono w-1/3 text-sm"
              placeholder="%"
            />
          </div>
        </div>
        <p className="text-[10px] text-slate-400 text-right pr-1">0为无优惠 (例如: 3年/15%)</p>
      </div>

      {/* 补容策略 */}
      <SectionTitle 
        icon={<Package className="w-4 h-4 text-slate-600" />}
        title="5. 补容策略"
      />

      <div className="mb-5">
        <div className="flex items-center justify-between mb-1">
          <Label className="text-xs md:text-sm text-slate-600">补容年份 / 单价</Label>
          <div className="flex gap-2 w-[170px] md:w-[200px]">
            <Input
              type="number"
              value={inputs.aug_year}
              onChange={(e) => onUpdate('aug_year', Number(e.target.value))}
              className="text-right font-mono w-[40%] text-sm"
              placeholder="年"
            />
            <Input
              type="number"
              value={inputs.aug_price}
              onChange={(e) => onUpdate('aug_price', Number(e.target.value))}
              className="text-right font-mono w-[60%] text-sm"
              placeholder="元"
            />
          </div>
        </div>
      </div>

      <Button 
        onClick={onCalculate}
        className="w-full bg-gradient-to-r from-blue-500 to-blue-700 hover:from-blue-600 hover:to-blue-800 text-white font-semibold py-5 md:py-6 rounded-xl shadow-lg hover:shadow-xl transition-all hover:-translate-y-0.5"
      >
        <Calculator className="w-5 h-5 mr-2" />
        立即计算
      </Button>
    </div>
  );
}
