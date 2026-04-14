import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid,
  AreaChart,
  Area,
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  BarChart,
  Bar,
  Cell
} from 'recharts';
import { 
  Play, 
  Square, 
  Activity, 
  Zap, 
  ShieldCheck, 
  TrendingUp, 
  Cpu, 
  BarChart3, 
  RefreshCcw,
  Target,
  BrainCircuit,
  Terminal,
  ChevronRight,
  Database,
  Waypoints,
  AlertTriangle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = 'http://127.0.0.1:8000';

const PLANT_NAMES = {
  "PLANT_001": "Delhi Coal",
  "PLANT_002": "Mumbai Gas",
  "PLANT_003": "Kolkata Nuclear",
  "PLANT_004": "Chennai Solar",
  "PLANT_005": "Bhopal Hydro",
  "PLANT_006": "Jaipur Wind"
};

const LINE_NAMES = {
  "LINE_001": "North Zone",
  "LINE_002": "West Zone",
  "LINE_003": "East Zone",
  "LINE_004": "South Zone",
  "LINE_005": "Central Zone",
  "LINE_006": "West Ext"
};

const AutonomousRL = ({ history, setHistory, currentStep, setCurrentStep }) => {
  const [isRunning, setIsRunning] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const scrollRef = useRef(null);

  const startRL = async () => {
    setLoading(true);
    setHistory([]);
    setCurrentStep(null);
    setProgress(0);
    try {
      await axios.post(`${API_BASE}/start?max_steps=20`);
      setIsRunning(true);
      const eventSource = new EventSource(`${API_BASE}/stream`);
      
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.done) {
          eventSource.close();
          setIsRunning(false);
          return;
        }
        if (data.error) {
          console.error(data.error);
          eventSource.close();
          setIsRunning(false);
          return;
        }

        setHistory(prev => [...prev, data]);
        setCurrentStep(data);
        setProgress((data.step / 20) * 100);
      };

      eventSource.onerror = (err) => {
        console.error("EventSource failed:", err);
        eventSource.close();
        setIsRunning(false);
      };
    } catch (err) {
      console.error("Failed to start RL:", err);
    } finally {
      setLoading(false);
    }
  };

  const stopRL = async () => {
    try {
      await axios.post(`${API_BASE}/stop`);
      setIsRunning(false);
    } catch (err) {
      console.error("Failed to stop RL:", err);
    }
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history]);

  const obsLabels = [
    "Avg Cap",
    "Avg Eff",
    "Health",
    "Integrity",
    "Total Cap",
    "Demand"
  ];

  const radarData = currentStep ? currentStep.obs.map((val, i) => ({
    subject: obsLabels[i],
    A: val * 100,
    fullMark: 100
  })) : [];

  const rewardData = history.length > 1 ? history.map((h, i) => ({
    step: h.step,
    reward: h.reward
  })) : [];

  const plantHealthData = (currentStep?.health_report?.plant_scores || []).map(p => ({
    name: PLANT_NAMES[p.plant_id] || p.plant_id.replace('PLANT_', ''),
    health: p.health_score,
    risk: p.risk_level
  }));

  const lineEffData = (currentStep?.transmission_report?.line_scores || []).map(l => ({
    name: LINE_NAMES[l.line_id] || l.line_id.replace('LINE_', ''),
    efficiency: l.efficiency_score
  }));

  return (
    <div className="h-full flex flex-col overflow-y-auto custom-scrollbar p-12">
      {/* Control Header */}
      <div className="glass-panel p-10 rounded-3xl flex items-center justify-between shrink-0 mb-12">
        <div className="flex items-center gap-8">
          <div className={`p-6 rounded-2xl ${isRunning ? 'bg-emerald-500/10 text-emerald-500 shadow-[0_0_30px_rgba(16,185,129,0.2)]' : 'bg-blue-600/10 text-blue-500 border border-current opacity-40 shadow-[0_0_15px_rgba(37,99,235,0.1)]'}`}>
            <BrainCircuit size={32} className={isRunning ? 'animate-pulse' : ''} />
          </div>
          <div className="flex flex-col gap-2">
            <h1 className="text-xl font-tech font-black text-white uppercase tracking-[0.4em]">Autonomous Neural Optimizer</h1>
            <p className="text-[11px] text-slate-500 font-tech font-bold uppercase tracking-widest flex items-center gap-3">
              <Activity size={12} className="text-blue-500" />
              State-Space: 6D Normalized // Action-Space: Discrete 3
            </p>
          </div>
        </div>

        <div className="flex items-center gap-8">
          {isRunning && (
             <div className="flex flex-col items-end gap-3 pr-8 border-r border-white/10">
                <span className="text-[10px] font-tech text-slate-500 uppercase tracking-widest">Neural Evolution Trend</span>
                <div className="w-48 h-1.5 bg-white/5 rounded-full overflow-hidden">
                   <motion.div 
                     initial={{ width: 0 }}
                     animate={{ width: `${progress}%` }}
                     className="bg-blue-600 h-full shadow-[0_0_15px_#2563eb]"
                   />
                </div>
             </div>
          )}
          
          {!isRunning ? (
            <button 
              onClick={startRL}
              disabled={loading}
              className="px-10 py-4 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl font-tech font-black text-xs uppercase tracking-widest transition-all active:scale-95 flex items-center gap-4 shadow-[0_0_40px_rgba(37,99,235,0.4)]"
            >
              {loading ? <RefreshCcw size={18} className="animate-spin" /> : <Play size={18} />} 
              Initialize Loop
            </button>
          ) : (
            <button 
              onClick={stopRL}
              className="px-10 py-4 bg-rose-600/10 hover:bg-rose-600 text-rose-500 hover:text-white border border-rose-500/20 rounded-2xl font-tech font-black text-xs uppercase tracking-widest transition-all active:scale-95 flex items-center gap-4 shadow-[0_0_20px_rgba(244,63,94,0.1)]"
            >
              <Square size={18} /> Terminate
            </button>
          )}
        </div>
      </div>

      {/* Main Stats Row */}
      <div className="grid grid-cols-12 gap-12 mb-12 shrink-0">
          {/* Radar Chart */}
          <div className="col-span-12 xl:col-span-4 glass-panel p-10 rounded-3xl h-[450px] flex flex-col gap-8">
             <div className="flex items-center justify-between border-b border-white/5 pb-6">
                <div className="flex items-center gap-4">
                   <Target size={18} className="text-blue-500" />
                   <h3 className="text-xs font-tech text-white uppercase tracking-widest">Vector State Map</h3>
                </div>
                <div className="text-[9px] font-tech text-slate-700 font-black tracking-tighter uppercase italic">V4.9-SEC</div>
             </div>
             <div className="flex-grow flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  {radarData.length > 0 ? (
                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                      <PolarGrid stroke="rgba(255,255,255,0.05)" />
                      <PolarAngleAxis dataKey="subject" tick={{ fill: '#475569', fontSize: 9, fontFamily: 'Orbitron' }} />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                      <Radar
                        name="Grid State"
                        dataKey="A"
                        stroke="#2563eb"
                        fill="#2563eb"
                        fillOpacity={0.3}
                        animationDuration={500}
                      />
                    </RadarChart>
                  ) : <div className="text-[10px] text-slate-800 font-tech">NODE_DETACHED</div>}
                </ResponsiveContainer>
             </div>
          </div>

          {/* Performance Curves */}
          <div className="col-span-12 xl:col-span-8 glass-panel p-10 rounded-3xl h-[450px] flex flex-col gap-8">
             <div className="flex items-center justify-between border-b border-white/5 pb-6">
                <div className="flex items-center gap-4">
                   <TrendingUp size={18} className="text-emerald-500" />
                   <h3 className="text-xs font-tech text-white uppercase tracking-widest">Reward Optimization Curve</h3>
                </div>
                {currentStep && (
                   <div className="flex items-baseline gap-3">
                      <span className="text-3xl font-tech font-black text-emerald-500 italic tracking-tighter">{currentStep.reward.toFixed(3)}</span>
                      <span className="text-[10px] text-slate-700 font-tech font-black uppercase tracking-widest">Step Rating</span>
                   </div>
                )}
             </div>
             <div className="flex-grow w-full pt-4">
                <ResponsiveContainer width="100%" height="100%">
                   {rewardData.length > 1 ? (
                     <AreaChart data={rewardData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorRewardFixed" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.02)" />
                        <XAxis dataKey="step" hide width={0} height={0} />
                        <YAxis hide domain={['auto', 'auto']} width={40} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#0a0d14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', fontFamily: 'Orbitron' }}
                          itemStyle={{ color: '#10b981' }}
                          labelStyle={{ fontSize: '10px', color: '#64748b', marginBottom: '8px' }}
                        />
                        <Area type="monotone" dataKey="reward" stroke="#10b981" fillOpacity={1} fill="url(#colorRewardFixed)" strokeWidth={4} animationDuration={500} />
                     </AreaChart>
                   ) : <div className="text-[10px] text-slate-800 font-tech">VECTOR_STABILIZING</div>}
                </ResponsiveContainer>
             </div>
          </div>
      </div>

      {/* Diagnostics Row */}
      <div className="grid grid-cols-12 gap-12 mb-12 shrink-0">
          {/* Action Hub */}
          <div className="col-span-12 lg:col-span-4 glass-panel p-10 rounded-3xl h-[400px] flex flex-col gap-8">
             <div className="flex items-center justify-between border-b border-white/5 pb-6">
                <div className="flex items-center gap-4 text-slate-500 uppercase">
                   <Cpu size={18} />
                   <h3 className="text-xs font-tech font-bold tracking-widest">Decision Hub</h3>
                </div>
             </div>
             <div className="flex-grow flex flex-col items-center justify-center gap-10 text-center relative">
                <div className={`w-36 h-36 rounded-full border-4 flex items-center justify-center shadow-[0_0_50px_rgba(0,0,0,0.3)] transition-all duration-1000 ${currentStep ? 'border-emerald-500/50 bg-emerald-500/10 shadow-emerald-500/20' : 'border-white/5 bg-white/[0.02]'}`}>
                   <Zap size={72} className={`transition-all duration-700 ${currentStep ? 'text-emerald-400 drop-shadow-[0_0_15px_#10b981] scale-110' : 'text-slate-800 scale-100'}`} />
                </div>
                <div className="flex flex-col gap-3">
                   <div className="text-4xl font-tech font-black text-white italic tracking-tighter uppercase">
                      {currentStep?.action_label || 'Standby'}
                   </div>
                   <div className="text-[14px] font-tech text-slate-400 font-bold uppercase tracking-[0.4em]">
                      Decision Index: {currentStep?.action ?? 'OFF'}
                   </div>
                </div>
             </div>
          </div>

          <div className="col-span-12 lg:col-span-8 grid grid-cols-2 gap-12">
             <div className="glass-panel p-10 rounded-3xl flex flex-col gap-8 h-[400px]">
                <div className="flex items-center gap-4 text-blue-500/60 uppercase">
                   <Database size={18} />
                   <h3 className="text-xs font-tech font-bold tracking-widest text-white">Node Status</h3>
                </div>
                <div className="flex-grow w-full">
                   <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={plantHealthData} layout="vertical" margin={{ left: 20 }}>
                         <XAxis type="number" hide domain={[0, 100]} width={0} height={0} />
                         <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#475569', fontSize: 10, fontFamily: 'Orbitron' }} width={120} height={0} />
                         <Tooltip cursor={{ fill: 'rgba(255,255,255,0.02)' }} contentStyle={{ backgroundColor: '#0a0d14', border: 'none', borderRadius: '12px', fontSize: '10px' }} />
                         <Bar dataKey="health" radius={[0, 4, 4, 0]} barSize={24}>
                            {plantHealthData.map((entry, index) => (
                               <Cell key={`cell-${index}`} fill={entry.health > 70 ? '#10b981' : entry.health > 40 ? '#f59e0b' : '#ef4444'} />
                            ))}
                         </Bar>
                      </BarChart>
                   </ResponsiveContainer>
                </div>
             </div>
             <div className="glass-panel p-10 rounded-3xl flex flex-col gap-8 h-[400px]">
                <div className="flex items-center gap-4 text-emerald-500/60 uppercase">
                   <Waypoints size={18} />
                   <h3 className="text-xs font-tech font-bold tracking-widest text-white">Grid Efficiency</h3>
                </div>
                <div className="flex-grow w-full">
                   <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={lineEffData} layout="vertical" margin={{ left: 20 }}>
                         <XAxis type="number" hide domain={[0, 100]} width={0} height={0} />
                         <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#475569', fontSize: 10, fontFamily: 'Orbitron' }} width={120} height={0} />
                         <Bar dataKey="efficiency" radius={[0, 4, 4, 0]} barSize={24} fill="#10b981" />
                      </BarChart>
                   </ResponsiveContainer>
                </div>
             </div>
          </div>
      </div>

      {/* Audit Log - Guaranteed to stay below */}
      <div className="glass-panel rounded-3xl flex flex-col overflow-hidden mb-24 shrink-0">
         <header className="px-12 py-10 border-b border-white/5 flex items-center justify-between bg-white/[0.01]">
            <div className="flex items-center gap-6">
               <div className="p-4 bg-blue-600/10 rounded-2xl">
                  <Terminal size={20} className="text-blue-500" />
               </div>
               <div className="flex flex-col gap-1">
                  <h3 className="text-sm font-tech text-white font-black uppercase tracking-[0.4em]">Neural Orchestration Audit</h3>
                  <span className="text-[10px] text-slate-600 uppercase tracking-widest font-bold">Deep Trace // Execution Log</span>
               </div>
            </div>
            <div className="flex items-center gap-10">
               <button 
                 onClick={() => setHistory([])}
                 className="text-[9px] font-tech text-slate-500 hover:text-rose-500 transition-colors uppercase tracking-[0.3em] font-black mr-4"
               >
                 Wipe Audit Trace
               </button>
               <div className="flex items-center gap-3">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_10px_#10b981]"></div>
                  <span className="text-[10px] font-tech text-slate-400 uppercase tracking-widest">Optimal Node</span>
               </div>
               <div className="flex items-center gap-3">
                  <div className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-[0_0_10px_#ef4444]"></div>
                  <span className="text-[10px] font-tech text-slate-400 uppercase tracking-widest">Security Alert</span>
               </div>
            </div>
         </header>
         
         <div ref={scrollRef} className="p-12 flex flex-col gap-8 min-h-[500px]">
            {history.length === 0 && (
               <div className="flex-grow flex flex-col items-center justify-center opacity-10 text-center py-40">
                  <BrainCircuit size={80} className="mb-10 text-slate-500" />
                  <p className="text-xs font-tech font-bold uppercase tracking-[0.8em] text-slate-600">Awaiting Neural Link Data Initiation...</p>
               </div>
            )}
            {history.map((h, i) => (
               <motion.div 
                 initial={{ opacity: 0, y: 30 }}
                 animate={{ opacity: 1, y: 0 }}
                 key={i} 
                 className="flex flex-col gap-8 p-10 bg-white/[0.02] border border-white/5 rounded-3xl hover:bg-white/[0.04] transition-all group relative overflow-hidden"
               >
                  <div className="absolute top-0 left-0 w-1.5 h-full bg-blue-500/20 group-hover:bg-blue-600 transition-colors"></div>
                  <div className="flex justify-between items-center">
                     <div className="flex items-center gap-6">
                        <span className="text-xs font-tech font-black text-blue-500 px-4 py-2 bg-blue-500/10 rounded-xl border border-blue-500/20 tracking-[0.3em] uppercase italic">STREAM_0{h.step}</span>
                        <div className="h-6 w-[2px] bg-white/5"></div>
                        <span className="text-slate-400 text-[11px] uppercase tracking-[0.3em] font-black italic">{h.action_label} State Transfer</span>
                     </div>
                     <div className="flex items-center gap-3 group-hover:scale-105 transition-transform">
                        <div className={`text-4xl font-tech font-black italic ${h.reward >= 1 ? 'text-emerald-500' : 'text-orange-500'}`}>{h.reward.toFixed(3)}</div>
                        <span className="text-[9px] text-slate-700 uppercase font-black tracking-widest">RT_SCORE</span>
                     </div>
                  </div>
                  
                  <div className="grid grid-cols-12 gap-12 pt-8 border-t border-white/5">
                     <div className="col-span-12 lg:col-span-8 flex flex-col gap-6">
                        <div className="flex items-center gap-4">
                           <ShieldCheck size={14} className="text-blue-500" />
                           <span className="text-[10px] text-slate-500 font-tech uppercase tracking-widest font-black">Strategic Execution Brief</span>
                        </div>
                        <p className="text-[16px] text-slate-200 italic font-medium leading-relaxed bg-black/40 p-8 rounded-2xl border border-white/5 font-serif shadow-inner">
                           {h.final_decisions || "Neural agent performing regional asset realignment based on real-time state vectors."}
                        </p>
                     </div>
                     <div className="col-span-12 lg:col-span-4 flex flex-col gap-8">
                        <div className="flex flex-col gap-4">
                           <span className="text-[10px] text-slate-600 font-tech uppercase tracking-widest font-black">Threat Matrix Analysis</span>
                           <div className="flex flex-col gap-3">
                              {h.health_report?.maintenance_actions?.length > 0 ? h.health_report.maintenance_actions.map((ma, idx) => (
                                 <div key={idx} className="flex items-center gap-6 px-6 py-4 bg-rose-500/15 border border-rose-500/30 rounded-2xl text-rose-500 text-[13px] font-black uppercase tracking-widest shadow-[0_0_20px_rgba(244,63,94,0.1)] group hover:bg-rose-500/20 transition-all">
                                    <AlertTriangle size={18} className="animate-pulse" /> 
                                    <div className="flex flex-col gap-1">
                                       <span>CRITICAL: {PLANT_NAMES[ma.plant_id] || ma.plant_id}_FAIL</span>
                                       <span className="text-[10px] text-rose-400 font-bold tracking-[0.2em]">{ma.required_action || 'URGENT_MAINTENANCE'}</span>
                                    </div>
                                 </div>
                              )) : (
                                 <div className="flex items-center gap-6 px-6 py-5 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl text-emerald-500 text-[13px] font-black uppercase tracking-widest italic shadow-xl opacity-60">
                                    <ShieldCheck size={20} /> VECTOR EQUILIBRIUM: SECURE
                                 </div>
                              )}
                           </div>
                        </div>
                     </div>
                  </div>
               </motion.div>
            ))}
         </div>
      </div>
    </div>
  );
};

export default AutonomousRL;
