import re

with open('src/components/DataTable.tsx', 'r') as f:
    content = f.read()

# 添加导入
if 'CalculationTooltip' not in content:
    import_line = "import { CalculationTooltip, createCalculationDetail } from './CalculationTooltip';"
    lines = content.split('\\n')
    last_import = 0
    for i, line in enumerate(lines):
        if line.startswith('import '):
            last_import = i
    lines.insert(last_import + 1, import_line)
    content = '\\n'.join(lines)

# 修改 DataTableProps 添加 inputs
old_props = 'interface DataTableProps {\n  result: CalculationResult | null;\n  onExport: () => void;\n}'
new_props = 'interface DataTableProps {\n  result: CalculationResult | null;\n  inputs?: any;\n  onExport: () => void;\n}'
content = content.replace(old_props, new_props)

# 修改 DataTableContent 参数
old_params = 'function DataTableContent({ \n  columns, \n  result, \n  getCellClassName \n}'
new_params = 'function DataTableContent({ \n  columns, \n  result, \n  inputs,\n  getCellClassName \n}'
content = content.replace(old_params, new_params)

# 添加状态
old_state = 'const [hoveredRow, setHoveredRow] = useState<number | null>(null);'
new_state = '''const [hoveredRow, setHoveredRow] = useState<number | null>(null);
  const [selectedCalc, setSelectedCalc] = useState<any>(null);
  const [isCalcOpen, setIsCalcOpen] = useState(false);'''
content = content.replace(old_state, new_state)

# 修改单元格添加点击
old_cell = '<TableCell \n                  key={col.key}\n                  className={`py-2 text-xs md:text-sm whitespace-nowrap px-2 ${getCellClassName(col, String(row[col.key as keyof typeof row]))}`}\n                >'
new_cell = '''<TableCell 
                  key={col.key}
                  className={`py-2 text-xs md:text-sm whitespace-nowrap px-2 cursor-pointer hover:bg-blue-100 ${getCellClassName(col, String(row[col.key as keyof typeof row]))}`}
                  onClick={() => {
                    const detail = createCalculationDetail(col.key, row, inputs);
                    if (detail) {
                      setSelectedCalc(detail);
                      setIsCalcOpen(true);
                    }
                  }}'''
content = content.replace(old_cell, new_cell)

# 添加 Tooltip 组件
old_return = 'return (\n    <ScrollArea'
new_return = '''return (
    <>
      <CalculationTooltip detail={selectedCalc} isOpen={isCalcOpen} onClose={() => setIsCalcOpen(false)} />
      <ScrollArea'''
content = content.replace(old_return, new_return)

# 结束标签
old_end = '    </ScrollArea>\n  );\n}'
new_end = '    </ScrollArea>\n  </>\n  );\n}'
content = content.replace(old_end, new_end)

# 修改 DataTableContent 调用
content = content.replace(
    'result={result} getCellClassName={getCellClassName} />',
    'result={result} inputs={inputs} getCellClassName={getCellClassName} />'
)

with open('src/components/DataTable.tsx', 'w') as f:
    f.write(content)

print("✅ DataTable.tsx 修改完成")
