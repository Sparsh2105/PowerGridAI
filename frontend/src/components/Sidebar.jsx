import React from 'react';
import { 
  BarChart2, 
  MessageSquare, 
  Factory, 
  Database, 
  Shield, 
  Settings, 
  HelpCircle,
  Cpu,
  Zap,
  Activity,
  BarChart3,
  BrainCircuit
} from 'lucide-react';
import { motion } from 'framer-motion';

const Sidebar = ({ activeTab, setActiveTab, lastIntelAvailable }) => {
  const menuItems = [
    { id: 'dashboard', icon: BarChart2, label: 'National Overwatch' },
    { id: 'control', icon: MessageSquare, label: 'Neural Relay' },
    { id: 'autonomous', icon: BrainCircuit, label: 'Autonomous Hub' },
    { id: 'intel', icon: BarChart3, label: 'Strategic Intel', pulse: lastIntelAvailable },
    { id: 'plants', icon: Factory, label: 'Infrastructure Nodes' },
    { id: 'memory', icon: Database, label: 'Command Log' },
  ];

  return (
    <aside className="w-24 bg-surface border-r border-white/5 flex flex-col items-center py-10 gap-12 shrink-0 z-[1000] shadow-2xl relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-1 bg-blue-500/20"></div>
      
      <div className="flex flex-col items-center gap-2">
         <div 
           onClick={() => setActiveTab('dashboard')}
           className="w-14 h-14 rounded-2xl bg-blue-600/10 flex items-center justify-center border border-blue-500/20 group hover:bg-blue-600/30 transition-all cursor-pointer shadow-lg shadow-blue-900/10"
         >
            <Zap size={26} className="text-blue-500 group-hover:scale-110 transition-transform" />
         </div>
      </div>

      <nav className="flex flex-col gap-6 flex-grow">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={`relative p-5 rounded-2xl transition-all group ${
              activeTab === item.id 
                ? 'bg-blue-600/15 text-blue-500 border border-blue-500/10 shadow-[0_0_15px_rgba(59,130,246,0.1)]' 
                : 'text-slate-600 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <item.icon size={24} className={item.id === activeTab ? 'drop-shadow-[0_0_8px_currentColor]' : ''} />
            
            {item.pulse && activeTab !== item.id && (
               <div className="absolute top-3 right-3 w-2 h-2 bg-blue-500 rounded-full animate-ping"></div>
            )}

            {/* Tooltip */}
            <div className="absolute left-[calc(100%+16px)] top-1/2 -translate-y-1/2 bg-surface text-white text-[10px] font-tech uppercase tracking-widest px-4 py-2 rounded-xl opacity-0 pointer-events-none group-hover:opacity-100 transition-all transform group-hover:translate-x-1 z-50 shadow-2xl border border-white/5">
               {item.label}
            </div>

            {/* Selection Cursor */}
            {activeTab === item.id && (
              <motion.div 
                layoutId="sidebar-active"
                className="absolute left-0 top-3 bottom-3 w-1 bg-blue-500 rounded-full shadow-[0_0_10px_#3b82f6]"
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              />
            )}
          </button>
        ))}
      </nav>

      <div className="flex flex-col gap-6 mt-auto">
         {/* System utility footer icons removed per redundancy audit */}
      </div>
    </aside>
  );
};

export default Sidebar;
