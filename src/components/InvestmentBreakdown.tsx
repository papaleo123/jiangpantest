import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Trash2 } from 'lucide-react';

interface InvestmentItem {
  name: string;
  amount: number;
  taxRate: number;
  category: 'equipment' | 'civil' | 'install' | 'other';
}

interface InvestmentBreakdownProps {
  items: InvestmentItem[];
  constructionPeriod: number;
  capacity: number;
  onItemsChange: (items: InvestmentItem[]) => void;
  onConstructionPeriodChange: (months: number) => void;
}

const DEFAULT_TAX_RATES = {
  equipment: 13,
  civil: 9,
  install: 9,
  other: 6,
};

export function InvestmentBreakdown({
  items,
  constructionPeriod,
  capacity,
  onItemsChange,
  onConstructionPeriodChange,
}: InvestmentBreakdownProps) {
  const [editingItems, setEditingItems] = useState<InvestmentItem[]>(
    items.length > 0 ? items : [
      { name: '储能系统设备', amount: 0, taxRate: 13, category: 'equipment' },
      { name: '土建工程', amount: 0, taxRate: 9, category: 'civil' },
      { name: '安装调试', amount: 0, taxRate: 9, category: 'install' },
    ]
  );

  const addItem = () => {
    const newItem: InvestmentItem = {
      name: '',
      amount: 0,
      taxRate: 13,
      category: 'equipment',
    };
    const updated = [...editingItems, newItem];
    setEditingItems(updated);
    onItemsChange(updated);
  };

  const removeItem = (index: number) => {
    const updated = editingItems.filter((_, i) => i !== index);
    setEditingItems(updated);
    onItemsChange(updated);
  };

  const updateItem = (index: number, field: keyof InvestmentItem, value: any) => {
    const updated = editingItems.map((item, i) => {
      if (i !== index) return item;
      
      if (field === 'category') {
        return {
          ...item,
          [field]: value,
          taxRate: DEFAULT_TAX_RATES[value as keyof typeof DEFAULT_TAX_RATES],
        };
      }
      
      return { ...item, [field]: value };
    });
    setEditingItems(updated);
    onItemsChange(updated);
  };

  const totalInvestment = editingItems.reduce((sum, item) => sum + item.amount, 0);
  
  const totalInputVAT = editingItems.reduce((sum, item) => {
    const taxExcluded = item.amount / (1 + item.taxRate / 100);
    return sum + (item.amount - taxExcluded);
  }, 0);

  const unitCost = capacity > 0 ? (totalInvestment * 10000) / (capacity * 1000000) : 0;

  return (
    <Card className="w-full mt-4">
      <CardHeader>
        <CardTitle className="text-lg flex items-center justify-between">
          <span>投资构成明细</span>
          <div className="text-sm font-normal text-slate-500">
            单位造价: {unitCost.toFixed(2)} 元/Wh
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 建设期设置 */}
        <div className="grid grid-cols-2 gap-4 pb-4 border-b">
          <div>
            <Label>建设期（月）</Label>
            <Input
              type="number"
              min={1}
              max={36}
              value={constructionPeriod}
              onChange={(e) => onConstructionPeriodChange(parseInt(e.target.value) || 12)}
              className="mt-1"
            />
            <p className="text-xs text-slate-500 mt-1">
              建设期内只产生成本，不产生收入
            </p>
          </div>
          <div className="text-right">
            <div className="text-sm text-slate-600">总投资（含税）</div>
            <div className="text-2xl font-bold text-blue-600">
              {totalInvestment.toFixed(2)} 万元
            </div>
            <div className="text-xs text-slate-500">
              进项税合计: {totalInputVAT.toFixed(2)} 万元
            </div>
          </div>
        </div>

        {/* 投资明细列表 */}
        <div className="space-y-3">
          {editingItems.map((item, index) => (
            <div key={index} className="grid grid-cols-12 gap-2 items-end bg-slate-50 p-3 rounded-lg">
              <div className="col-span-2">
                <Label className="text-xs">类别</Label>
                <Select
                  value={item.category}
                  onValueChange={(v) => updateItem(index, 'category', v)}
                >
                  <SelectTrigger className="h-8">
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
                <Label className="text-xs">项目名称</Label>
                <Input
                  value={item.name}
                  onChange={(e) => updateItem(index, 'name', e.target.value)}
                  placeholder="如：储能系统设备"
                  className="h-8"
                />
              </div>

              <div className="col-span-3">
                <Label className="text-xs">金额（万元）</Label>
                <Input
                  type="number"
                  value={item.amount}
                  onChange={(e) => updateItem(index, 'amount', parseFloat(e.target.value) || 0)}
                  className="h-8"
                />
              </div>

              <div className="col-span-2">
                <Label className="text-xs">税率</Label>
                <Select
                  value={item.taxRate.toString()}
                  onValueChange={(v) => updateItem(index, 'taxRate', parseInt(v))}
                >
                  <SelectTrigger className="h-8">
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

              <div className="col-span-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeItem(index)}
                  className="h-8 text-red-500 hover:text-red-700"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>

              <div className="col-span-12 text-xs text-slate-500 mt-1">
                进项税: {((item.amount - item.amount / (1 + item.taxRate / 100))).toFixed(2)} 万元
              </div>
            </div>
          ))}
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={addItem}
          className="w-full"
        >
          <Plus className="w-4 h-4 mr-2" />
          添加投资项
        </Button>

        <div className="text-xs text-slate-500 bg-blue-50 p-3 rounded">
          <p>💡 不同成本类型适用不同增值税率：</p>
          <ul className="list-disc list-inside mt-1 space-y-1">
            <li>设备购置：13%</li>
            <li>建筑工程：9%</li>
            <li>安装劳务：9% 或 3%</li>
            <li>设计咨询：6%</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
