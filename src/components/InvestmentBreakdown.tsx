import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Trash2, Calculator } from 'lucide-react';

export interface InvestmentItem {
  id: string;
  name: string;
  amount: number;        // 万元
  taxRate: number;       // %
  category: 'equipment' | 'civil' | 'install' | 'other';
}

interface Props {
  items: InvestmentItem[];
  constructionPeriod: number;
  capacity: number;
  onChange: (items: InvestmentItem[], constructionPeriod: number) => void;
}

const DEFAULT_RATES: Record<string, number> = {
  equipment: 13,
  civil: 9,
  install: 9,
  other: 6,
};

const CATEGORY_NAMES: Record<string, string> = {
  equipment: '设备购置',
  civil: '建筑工程',
  install: '安装劳务',
  other: '其他费用',
};

export function InvestmentBreakdown({ 
  items, 
  constructionPeriod, 
  capacity, 
  onChange 
}: Props) {
  // 本地状态，提交时才更新父组件
  const [localItems, setLocalItems] = useState<InvestmentItem[]>(
    items.length > 0 ? items : [
      { id: '1', name: '储能系统设备', amount: 0, taxRate: 13, category: 'equipment' },
      { id: '2', name: '土建工程', amount: 0, taxRate: 9, category: 'civil' },
      { id: '3', name: '安装调试', amount: 0, taxRate: 9, category: 'install' },
    ]
  );
  const [localPeriod, setLocalPeriod] = useState(constructionPeriod);

  // 同步外部变化
  useEffect(() => {
    if (JSON.stringify(items) !== JSON.stringify(localItems)) {
      setLocalItems(items);
    }
  }, [items]);

  const generateId = () => Math.random().toString(36).substr(2, 9);

  const addItem = () => {
    const newItem: InvestmentItem = {
      id: generateId(),
      name: '',
      amount: 0,
      taxRate: 13,
      category: 'equipment',
    };
    const updated = [...localItems, newItem];
    setLocalItems(updated);
    onChange(updated, localPeriod);
  };

  const removeItem = (id: string) => {
    const updated = localItems.filter(item => item.id !== id);
    setLocalItems(updated);
    onChange(updated, localPeriod);
  };

  const updateItem = (id: string, field: keyof InvestmentItem, value: any) => {
    const updated = localItems.map(item => {
      if (item.id !== id) return item;
      
      if (field === 'category') {
        return {
          ...item,
          category: value,
          taxRate: DEFAULT_RATES[value],
        };
      }
      return { ...item, [field]: value };
    });
    setLocalItems(updated);
    onChange(updated, localPeriod);
  };

  const updatePeriod = (months: number) => {
    setLocalPeriod(months);
    onChange(localItems, months);
  };

  // 计算汇总
  const totals = localItems.reduce((acc, item) => {
    const net = item.amount / (1 + item.taxRate / 100);
    const vat = item.amount - net;
    return {
      gross: acc.gross + item.amount,
      net: acc.net + net,
      vat: acc.vat + vat,
    };
  }, { gross: 0, net: 0, vat: 0 });

  const unitCost = capacity > 0 ? (totals.gross * 10000) / (capacity * 1000000) : 0;

  return (
    <Card className="w-full mt-4 border-blue-200">
      <CardHeader className="bg-blue-50/50">
        <CardTitle className="text-lg flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calculator className="w-5 h-5 text-blue-600" />
            <span>投资构成明细</span>
          </div>
          <div className="text-sm font-normal text-slate-500">
            单位造价: <span className="font-bold text-blue-600">{unitCost.toFixed(2)}</span> 元/Wh
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 pt-4">
        {/* 建设期设置 */}
        <div className="grid grid-cols-2 gap-4 p-3 bg-slate-50 rounded-lg">
          <div>
            <Label className="text-sm font-medium">建设期（月）</Label>
            <Input
              type="number"
              min={1}
              max={36}
              value={localPeriod}
              onChange={(e) => updatePeriod(parseInt(e.target.value) || 12)}
              className="mt-1 h-9"
            />
            <p className="text-xs text-slate-500 mt-1">
              建设期内只产生成本，不产生收入
            </p>
          </div>
          <div className="text-right space-y-1">
            <div className="text-sm text-slate-600">总投资（含税）</div>
            <div className="text-2xl font-bold text-blue-600">
              {totals.gross.toFixed(2)}
              <span className="text-sm font-normal text-slate-500 ml-1">万元</span>
            </div>
            <div className="text-xs text-slate-500">
              不含税: {totals.net.toFixed(2)} 万元 | 
              进项税: <span className="text-green-600 font-medium">{totals.vat.toFixed(2)}</span> 万元
            </div>
          </div>
        </div>

        {/* 投资明细表 */}
        <div className="space-y-2">
          <div className="grid grid-cols-12 gap-2 text-xs font-medium text-slate-500 px-2">
            <div className="col-span-2">类别</div>
            <div className="col-span-4">项目名称</div>
            <div className="col-span-3">金额（万元）</div>
            <div className="col-span-2">税率</div>
            <div className="col-span-1"></div>
          </div>
          
          {localItems.map((item) => {
            const netAmount = item.amount / (1 + item.taxRate / 100);
            const itemVAT = item.amount - netAmount;
            
            return (
              <div key={item.id} className="grid grid-cols-12 gap-2 items-start bg-white border rounded-lg p-2 hover:border-blue-300 transition-colors">
                <div className="col-span-2">
                  <Select
                    value={item.category}
                    onValueChange={(v) => updateItem(item.id, 'category', v)}
                  >
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="equipment">设备</SelectItem>
                      <SelectItem value="civil">土建</SelectItem>
                      <SelectItem value="install">安装</SelectItem>
                      <SelectItem value="other">其他</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="col-span-4">
                  <Input
                    value={item.name}
                    onChange={(e) => updateItem(item.id, 'name', e.target.value)}
                    placeholder={CATEGORY_NAMES[item.category]}
                    className="h-8 text-sm"
                  />
                </div>

                <div className="col-span-3">
                  <Input
                    type="number"
                    value={item.amount || ''}
                    onChange={(e) => updateItem(item.id, 'amount', parseFloat(e.target.value) || 0)}
                    className="h-8 text-sm"
                  />
                </div>

                <div className="col-span-2">
                  <Select
                    value={item.taxRate.toString()}
                    onValueChange={(v) => updateItem(item.id, 'taxRate', parseInt(v))}
                  >
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="13">13%</SelectItem>
                      <SelectItem value="9">9%</SelectItem>
                      <SelectItem value="6">6%</SelectItem>
                      <SelectItem value="3">3%</SelectItem>
                      <SelectItem value="0">0%</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="col-span-1 flex justify-end">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeItem(item.id)}
                    className="h-8 w-8 p-0 text-slate-400 hover:text-red-500"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
                
                {/* 显示税额详情 */}
                <div className="col-span-12 text-xs text-slate-400 mt-1 pl-1">
                  进项税: {itemVAT.toFixed(2)} 万元 | 不含税: {netAmount.toFixed(2)} 万元
                </div>
              </div>
            );
          })}
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={addItem}
          className="w-full border-dashed"
        >
          <Plus className="w-4 h-4 mr-2" />
          添加投资项
        </Button>

        {/* 说明 */}
        <div className="text-xs text-slate-500 bg-amber-50 p-3 rounded border border-amber-200">
          <p className="font-medium text-amber-800 mb-1">💡 增值税抵扣说明：</p>
          <ul className="list-disc list-inside space-y-1 text-amber-700">
            <li>设备购置 13%、建筑工程 9%、现代服务 6%</li>
            <li>进项税可在运营期抵扣销项税，无期限限制</li>
            <li>建设期只产生成本，第 {Math.ceil(localPeriod/12)} 年开始运营</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
