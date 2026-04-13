import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Sidebar from './components/Sidebar';
import CommandCenter from './components/CommandCenter';
import PlantGrid from './components/PlantGrid';
import MemoryLog from './components/MemoryLog';
import GridMap from './components/GridMap';
import StrategicIntel from './components/StrategicIntel';
import { Shield, Zap, Wind, Thermometer, Database, Globe, Activity, LayoutGrid, Target, Clock, MessageSquare, List, ChevronRight, BarChart3, Radio } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const App = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [health, setHealth] = useState({ status: 'loading', service: 'GridMind AI' });
  const [lastIntel, setLastIntel] = useState(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await axios.get('http://127.0.0.1:8000/health');
        setHealth(res.data);
      } catch (err) {
        setHealth({ status: 'offline', service: 'GridMind AI' });
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleNav = (e) => setActiveTab(e.detail);
    window.addEventListener('nav-tab', handleNav);
    return () => window.removeEventListener('nav-tab', handleNav);
  }, []);

  const onIntelReceived = (data) => {
    setLastIntel(data);
    // Auto-pulse or notify user? Let's just store it for now.
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <div className="flex flex-col h-full gap-8 overflow-hidden relative z-10">
            {/* Real-time KPI Belt */}
            <div className="grid grid-cols-4 gap-6">
              {[
                { label: 'System Load', value: '1.24', unit: 'TW', sub: '+2.4% vs prev', icon: Zap, color: 'text-blue-500' },
                { label: 'Renewable Mix', value: '38.5', unit: '%', sub: 'Target 40%', icon: Wind, color: 'text-emerald-500' },
                { label: 'Thermal Profile', value: '312.4', unit: 'K', sub: 'Nominal Range', icon: Thermometer, color: 'text-orange-500' },
                { label: 'Gateway Status', value: health.status === 'ok' ? 'Online' : 'Offline', unit: '', sub: `${health.service || 'Link'}`, icon: Database, color: health.status === 'ok' ? 'text-emerald-500' : 'text-rose-500' }
              ].map((m, i) => (
                <div key={i} className="glass-panel p-8 rounded-2xl flex items-center justify-between group hover:border-blue-500/30 transition-all">
                  <div className="flex flex-col gap-2">
                    <span className="text-[10px] font-tech font-bold text-slate-500 uppercase tracking-widest">{m.label}</span>
                    <div className="flex items-baseline gap-1">
                      <span className="text-3xl font-tech font-black tracking-tighter text-white italic">{m.value}</span>
                      <span className="text-xs font-bold text-slate-600 font-tech">{m.unit}</span>
                    </div>
                    <span className="text-[10px] text-slate-600 font-medium">{m.sub}</span>
                  </div>
                  <div className="p-4 bg-white/5 rounded-xl">
                    <m.icon size={22} className={m.color} />
                  </div>
                </div>
              ))}
            </div>

            {/* Primary Command and Map Area */}
            <div className="flex-grow grid grid-cols-12 gap-8 overflow-hidden min-h-0">
              {/* Map Container - Full Control */}
              <div className="col-span-12 xl:col-span-9 glass-panel rounded-2xl overflow-hidden relative border border-white/5 shadow-2xl">
                <GridMap />

                {/* Native Floating HUD */}
                <div className="absolute top-6 left-6 z-[1000] bg-core/80 backdrop-blur-md border border-white/10 p-6 rounded-xl shadow-2xl flex flex-col gap-5 min-w-[240px]">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse shadow-[0_0_10px_#3b82f6]"></div>
                    <span className="text-[10px] font-tech font-black text-white uppercase tracking-widest">Operational Context</span>
                  </div>
                  <div className="h-[1px] bg-white/5 w-full"></div>
                  <div className="flex flex-col gap-3">
                    <div className="flex justify-between items-center text-[10px]">
                      <span className="text-slate-500 font-tech uppercase">Active Region</span>
                      <span className="text-slate-200 font-bold tracking-widest">NATIONAL_MAINLAND</span>
                    </div>
                    <div className="flex justify-between items-center text-[10px]">
                      <span className="text-slate-500 font-tech uppercase">Integrity</span>
                      <span className="text-emerald-500 font-bold tracking-widest">SYNC_0.98</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Auxiliary Side Stats */}
              <div className="col-span-12 xl:col-span-3 flex flex-col gap-6 overflow-y-auto custom-scrollbar">
                <div className="glass-panel p-8 rounded-2xl flex flex-col gap-8">
                  <h3 className="text-[10px] font-tech font-bold text-slate-500 uppercase tracking-[0.4em] border-b border-white/5 pb-6 italic">Incidents</h3>
                  <div className="flex flex-col gap-6">
                    {[
                      { id: "A-04", msg: "Voltage drop in West Bengal segment", time: "2m ago", type: "warn" },
                      { id: "S-12", msg: "Optimal balance achieved in Mumbai", time: "14m ago", type: "success" },
                      { id: "N-01", msg: "Neural Link resync completed", time: "1h ago", type: "info" }
                    ].map((n, i) => (
                      <div key={i} className="flex gap-4 group cursor-pointer">
                        <div className={`mt-1 h-3 w-3 rounded-full shrink-0 ${n.type === 'warn' ? 'bg-orange-500' : n.type === 'success' ? 'bg-emerald-500' : 'bg-blue-500'} opacity-30 group-hover:opacity-100 transition-opacity`}></div>
                        <div className="flex flex-col">
                          <span className="text-[12px] text-slate-300 font-medium leading-relaxed italic">{n.msg}</span>
                          <span className="text-[9px] font-tech text-slate-600 mt-2 uppercase font-bold tracking-[0.2em]">{n.id} // T_{n.time}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="glass-panel p-8 rounded-2xl flex-grow flex flex-col items-center justify-center relative group min-h-[300px] overflow-hidden">
                  <div className="absolute top-6 left-8 text-[10px] font-tech text-slate-700 uppercase tracking-[0.5em]">Infrastructure Hub</div>
                  <div className="mb-10 opacity-30 group-hover:opacity-100 transition-transform duration-700 group-hover:scale-110">
                    <Activity size={50} className="text-blue-500" />
                  </div>
                  <div className="relative z-10 text-center flex flex-col gap-4">
                    <div className="h-[1px] w-12 bg-blue-500/40 mx-auto"></div>
                    <p className="text-[10px] font-tech text-slate-600 uppercase tracking-[0.3em]">DELTA_9_CENTRAL<br /><span className="text-blue-500/30 text-[8px]">ACTIVE_ENCRYPTION_LINK</span></p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
      case 'control':
        return <CommandCenter onIntel={onIntelReceived} />;
      case 'intel':
        return <StrategicIntel data={lastIntel} />;
      case 'plants':
        return <PlantGrid />;
      case 'memory':
        return <MemoryLog />;
      default:
        return null;
    }
  };

  return (
    <div className="flex h-screen w-screen bg-core text-slate-200 overflow-hidden grid-bg font-sans">
      <div className="scanline"></div>
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} lastIntelAvailable={!!lastIntel} />

      <main className="flex-grow flex flex-col relative z-20 min-w-0">
        {/* Global Nav Bar */}
        <header className="h-20 flex items-center justify-between px-12 border-b border-white/5 bg-surface/40 backdrop-blur-xl shrink-0">
          <div className="flex items-center gap-10">
            <div className="flex items-center gap-4 cursor-pointer group" onClick={() => setActiveTab('dashboard')}>
              <div className="p-2 bg-blue-600/10 rounded-lg group-hover:bg-blue-600 transition-colors">
                <Shield size={22} className="text-blue-500 group-hover:text-white transition-colors" />
              </div>
              <span className="text-lg font-tech font-black tracking-[-0.05em] uppercase italic">GridMind <span className="text-blue-500">v4.0</span></span>
            </div>
            <div className="h-6 w-[1px] bg-white/5"></div>
            <nav className="flex items-center gap-3">
              <span className="text-[9px] font-tech text-slate-500 uppercase tracking-[0.6em]">System Console</span>
              <ChevronRight size={12} className="text-slate-800" />
              <span className="text-[9px] font-tech font-black text-blue-500 uppercase tracking-[0.4em] italic">{activeTab}</span>
            </nav>
          </div>

          <div className="flex items-center gap-10">
            <div className="flex items-center gap-4 bg-white/[0.03] border border-white/5 px-6 py-2 rounded-xl">
              <Clock size={16} className="text-blue-500" />
              <span className="text-[12px] font-tech text-slate-400 tabular-nums italic">{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
            </div>

            <div className="flex items-center gap-5">
              <div className="text-right flex flex-col items-end">
                <span className="text-[9px] font-tech text-slate-600 uppercase tracking-widest italic opacity-50">Authorized Commander</span>
                <span className="text-[10px] font-tech font-bold text-white uppercase tracking-[0.2em] italic">AUTH_SEC_ALPHA</span>
              </div>
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-700 to-blue-900 flex items-center justify-center text-sm font-tech font-black shadow-2xl shadow-blue-900/40 border border-white/10 italic">
                AR
              </div>
            </div>
          </div>
        </header>

        <div className="flex-grow overflow-hidden relative p-12">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="h-full w-full"
            >
              {renderContent()}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
};

export default App;
