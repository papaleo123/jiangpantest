import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { CalculationResult } from '@/types';
import { CalculationTooltip, createCalculationDetail } from './CalculationTooltip';
import { Download, Table2, Zap, DollarSign, Receipt } from 'lucide-react';

interface DataTableProps {
  result: CalculationResult | null;
  inputs?: any;  // 输入参数，用于计算过程展示
  onExport: () => void;
}

// 物理量列
const physicalColumns = [
  { key: 'y', label: '年份', align: 'left' as const, className: 'font-semibold' },
  { key: 'soh', label: 'SOH' },
  { key: 'charge_kwh', label: '充电量(万kWh)', className: 'text-blue-600' },
  { key: 'discharge_kwh', label: '放电量(万kWh)', className: 'text-green-600' },
  { key: 'loss_kwh', label: '损耗电量(万kWh)', className: 'text-orange-500' },
];

// 收入列
const revenueColumns = [
  { key: 'y', label: '年份', align: 'left' as const, className: 'font-semibold' },
  { key: 'elec_rev', label: '电费套利', className: 'text-green-600' },
  { key: 'sub_rev', label: '补偿收入', className: 'text-orange-600' },
  { key: 'aux_rev', label: '或有收益', className: 'text-blue-600' },
  { key: 'total_rev', label: '总收入', className: 'font-bold' },
];

// 成本列
const costColumns = [
  { key: 'y', label: '年份', align: 'left' as const, className: 'font-semibold' },
  { key: 'opex', label: '运维成本' },
  { key: 'loss_cost', label: '损耗成本', className: 'text-orange-500' },
  { key: 'dep', label: '折旧', className: 'text-slate-500' },
  { key: 'interest', label: '利息', className: 'text-slate-500' },
];

// 税务列
const taxColumns = [
  { key: 'y', label: '年份', align: 'left' as const, className: 'font-semibold' },
  { key: 'vat_pay', label: '增值税' },
  { key: 'surcharge', label: '附加税' },
  { key: 'income_tax', label: '所得税' },
  { key: 'total_tax', label: '总税金', className: 'font-semibold' },
];

// 利润现金流列
const cashflowColumns = [
  { key: 'y', label: '年份', align: 'left' as const, className: 'font-semibold' },
  { key: 'ebitda', label: 'EBITDA', className: 'text-blue-600' },
  { key: 'net_profit', label: '净利润', className: 'font-semibold' },
  { key: 'cf', label: '股东现金流', highlight: true },
  { key: 'cum_cf', label: '累计现金流', className: 'text-purple-600 font-semibold' },
  { key: 'dscr', label: 'DSCR' },
];

interface TotalRow {
  [key: string]: string;
}

function DataTableContent({ 
  columns, 
  result, 
  inputs,
  getCellClassName 
}: { 
  columns: Array<{ key: string; label: string; align?: 'left'; className?: string; highlight?: boolean }>;
  result: CalculationResult | null;
  inputs?: any;
  getCellClassName: (col: { key: string; highlight?: boolean; className?: string; align?: 'left' }, value: string) => string;
}) {
  const [hoveredRow, setHoveredRow] = useState<number | null>(null);
  const [selectedCalc, setSelectedCalc] = useState<any>(null);
  const [isCalcOpen, setIsCalcOpen] = useState(false);

  const getTotalRow = (): TotalRow | null => {
    if (!result) return null;
    
    return {
      y: '合计',
      soh: '-',
      charge_kwh: (result.stats.total_charge_kwh / 10000).toFixed(0),
      discharge_kwh: (result.stats.total_discharge_kwh / 10000).toFixed(0),
      loss_kwh: (result.stats.total_loss_kwh / 10000).toFixed(0),
      elec_rev: (result.stats.total_elec_rev / 10000).toFixed(0),
      sub_rev: (result.stats.total_sub_rev / 10000).toFixed(0),
      aux_rev: (result.stats.total_aux_rev / 10000).toFixed(0),
      total_rev: (result.stats.total_rev / 10000).toFixed(0),
      opex: (result.stats.total_opex / 10000).toFixed(0),
      loss_cost: (result.stats.total_loss_cost / 10000).toFixed(0),
      dep: (result.stats.total_dep / 10000).toFixed(0),
      interest: (result.stats.total_interest / 10000).toFixed(0),
      vat_pay: (result.stats.total_vat / 10000).toFixed(0),
      surcharge: (result.stats.total_surcharge / 10000).toFixed(0),
      income_tax: (result.stats.total_income_tax / 10000).toFixed(0),
      total_tax: (result.stats.total_tax / 10000).toFixed(0),
      ebitda: '-',
      net_profit: (result.stats.total_net_profit / 10000).toFixed(0),
      cf: '-',
      cum_cf: '-',
      dscr: result.stats.min_dscr > 900 ? '-' : result.stats.min_dscr.toFixed(2),
    };
  };

  const totalRow = getTotalRow();

  return (
    <>
      <CalculationTooltip 
        detail={selectedCalc} 
        isOpen={isCalcOpen} 
        onClose={() => setIsCalcOpen(false)} 
      />
      <ScrollArea className="h-[350px] md:h-[400px] border rounded-lg">
      <Table>
        <TableHeader className="sticky top-0 bg-slate-50 z-10">
          <TableRow className="hover:bg-transparent">
            {columns.map((col) => (
              <TableHead 
                key={col.key}
                className={`${col.align === 'left' ? 'text-left' : 'text-right'} text-xs font-semibold text-slate-600 whitespace-nowrap px-2`}
              >
                {col.highlight ? (
                  <Badge variant="outline" className="bg-green-50 border-green-200 text-green-700 text-xs">
                    {col.label}
                  </Badge>
                ) : col.label}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {result?.rows.map((row, index) => (
            <TableRow 
              key={row.y}
              className={`transition-colors ${hoveredRow === index ? 'bg-blue-50' : ''}`}
              onMouseEnter={() => setHoveredRow(index)}
              onMouseLeave={() => setHoveredRow(null)}
            >
              {columns.map((col) => (
                <TableCell 
                  key={col.key}
                  className={`py-2 text-xs md:text-sm whitespace-nowrap px-2 cursor-pointer hover:bg-blue-100 transition-colors ${getCellClassName(col, String(row[col.key as keyof typeof row]))}`}
                  onClick={() => {
                    const calcColumns = ["elec_rev", "sub_rev", "loss_cost", "income_tax", "total_tax", "ebitda"];
                    if (calcColumns.includes(col.key) && inputs) {
                      const detail = createCalculationDetail(col.key, row, inputs);
                      if (detail) {
                        setSelectedCalc(detail);
                        setIsCalcOpen(true);
                      }
                    }
                  }}
                >
                  {String(row[col.key as keyof typeof row])}
                </TableCell>
              ))}
            </TableRow>
          ))}
          {totalRow && (
            <TableRow className="bg-gradient-to-r from-blue-50 to-blue-100 font-bold border-t-2 border-blue-300">
              {columns.map((col) => (
                <TableCell 
                  key={col.key}
                  className={`py-2 md:py-3 text-xs md:text-sm ${col.align === 'left' ? 'text-left' : 'text-right'} text-slate-800 px-2`}
                >
                  {totalRow[col.key] || '-'}
                </TableCell>
              ))}
            </TableRow>
          )}
        </TableBody>
      </Table>
    </ScrollArea>
  </>
  );
}

export function DataTable({ result, onExport }: DataTableProps) {
  const getCellClassName = (column: { key: string; highlight?: boolean; className?: string; align?: 'left' }, value: string) => {
    const classes: string[] = [];
    
    if (column.align === 'left') {
      classes.push('text-left');
    } else {
      classes.push('text-right');
    }
    
    if (column.className) {
      classes.push(column.className);
    }
    
    if (column.highlight) {
      const numValue = parseFloat(value);
      if (numValue > 0) {
        classes.push('text-green-600 font-semibold');
      } else if (numValue < 0) {
        classes.push('text-red-600 font-semibold');
      }
    }
    
    return classes.join(' ');
  };

  return (
    <Card className="flex-1">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Table2 className="w-4 h-4 text-slate-500" />
            年度财务明细表
          </div>
          <Button 
            onClick={onExport}
            size="sm"
            className="bg-green-500 hover:bg-green-600 text-white"
          >
            <Download className="w-4 h-4 mr-1" />
            <span className="hidden sm:inline">导出Excel</span>
            <span className="sm:hidden">导出</span>
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <Tabs defaultValue="physical" className="w-full">
          <TabsList className="w-full grid grid-cols-5 h-auto">
            <TabsTrigger value="physical" className="text-xs flex items-center gap-1">
              <Zap className="w-3 h-3" />
              <span className="hidden sm:inline">物理量</span>
            </TabsTrigger>
            <TabsTrigger value="revenue" className="text-xs flex items-center gap-1">
              <DollarSign className="w-3 h-3" />
              <span className="hidden sm:inline">收入</span>
            </TabsTrigger>
            <TabsTrigger value="cost" className="text-xs flex items-center gap-1">
              成本
            </TabsTrigger>
            <TabsTrigger value="tax" className="text-xs flex items-center gap-1">
              <Receipt className="w-3 h-3" />
              <span className="hidden sm:inline">税务</span>
            </TabsTrigger>
            <TabsTrigger value="cashflow" className="text-xs flex items-center gap-1">
              现金流
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="physical" className="mt-2">
            <DataTableContent columns={physicalColumns} result={result} inputs={inputs} getCellClassName={getCellClassName} />
          </TabsContent>
          
          <TabsContent value="revenue" className="mt-2">
            <DataTableContent columns={revenueColumns} result={result} inputs={inputs} getCellClassName={getCellClassName} />
          </TabsContent>
          
          <TabsContent value="cost" className="mt-2">
            <DataTableContent columns={costColumns} result={result} inputs={inputs} getCellClassName={getCellClassName} />
          </TabsContent>
          
          <TabsContent value="tax" className="mt-2">
            <DataTableContent columns={taxColumns} result={result} inputs={inputs} getCellClassName={getCellClassName} />
          </TabsContent>
          
          <TabsContent value="cashflow" className="mt-2">
            <DataTableContent columns={cashflowColumns} result={result} inputs={inputs} getCellClassName={getCellClassName} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
