import { Zap } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

export function Header() {
  return (
    <header className="bg-gradient-to-r from-slate-800 to-slate-700 sticky top-0 z-50 shadow-lg">
      <div className="flex items-center justify-between px-3 md:px-6 py-2 md:py-3">
        <div className="flex items-center gap-2 md:gap-4">
          <img 
            src="/logo.png" 
            alt="江槃科技" 
            className="h-8 md:h-10 brightness-0 invert"
          />
          <div>
            <h1 className="text-white text-sm md:text-lg font-semibold flex items-center gap-1 md:gap-2">
              <Zap className="w-4 h-4 md:w-5 md:h-5 text-yellow-400" />
              <span className="truncate">江槃独立储能投决系统</span>
            </h1>
            <p className="text-slate-400 text-[10px] md:text-xs hidden sm:block">
              Industrial & Commercial ESS Investment Decision System
            </p>
          </div>
        </div>
        <Badge 
          variant="secondary" 
          className="bg-white/10 text-white border-0 text-xs"
        >
          
        </Badge>
      </div>
    </header>
  );
}
