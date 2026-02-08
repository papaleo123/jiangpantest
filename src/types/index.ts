// 投资明细项（统一定义）
export interface InvestmentItem {
  id?: string;              // 可选，为了向后兼容
  name: string;
  amount: number;
  taxRate: number;
  category: 'equipment' | 'civil' | 'install' | 'other';
}

// 如果 InputParams 在其他地方定义，请确保包含：
// investmentItems?: InvestmentItem[];
// constructionPeriod?: number;
