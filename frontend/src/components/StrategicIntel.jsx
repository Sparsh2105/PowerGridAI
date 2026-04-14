import React from 'react';
import { motion } from 'framer-motion';
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  Cell, 
  ScatterChart,
  Scatter,
  ZAxis
} from 'recharts';
import { Zap, Activity, ShieldAlert, MapPin, Gauge, Droplets, Sun, Wind, Flame, Radio, ArrowRight, List, Cpu, Target, BarChart3, ChevronRight } from 'lucide-react';

const StrategicIntel = ({ data }) => {
  if (!data) return (
    <div className="h-full flex flex-col items-center justify-center text-slate-600 font-tech">
       <ShieldAlert size={60} className="mb-6 opacity-20" />
       <p className="tracking-[0.5em] uppercase text-xl font-black text-blue-500/40">Awaiting Tactical Payload</p>
    </div>
  );

  const supplyData = Object.entries(data.supply_breakdown?.by_type || {}).map(([name, stats]) => ({
    name: name.toUpperCase(),
    value: stats.current_mw,
    max: stats.max_mw,
    color: name === 'hydro' ? '#3b82f6' : name === 'solar' ? '#fbbf24' : name === 'wind' ? '#06b6d4' : name === 'nuclear' ? '#a855f7' : '#ef4444'
  }));

  const plantScatter = data.plants?.map((p, i) => {
    const baseCost = p.cost && p.cost !== 4.5 ? p.cost : (3.5 + (p.type === 'coal' ? 4.2 : p.type === 'nuclear' ? 1.5 : 0.8));
    return {
      name: p.name || p.plant_name || `NODE_${i}`,
      output: p.current_mw || 100,
      distance: p.distance_km || (150 + (i * 80)),
      cost: baseCost,
      type: p.type
    };
  }) || [];

  return (
    <div className="flex flex-col h-full gap-8 overflow-y-auto custom-scrollbar pb-20 p-8">
      {/* Prime Strategic HUD */}
      <div className="grid grid-cols-12 gap-8">
         <div className="col-span-12 xl:col-span-8 flex flex-col gap-8">
            <div className="glass-panel p-10 rounded-2xl relative overflow-hidden">
               <div className="absolute top-0 left-0 w-2 h-full bg-blue-500 shadow-[0_0_20px_#3b82f6]"></div>
               <div className="flex justify-between items-start relative z-10">
                  <div className="flex flex-col gap-2">
                     <span className="text-sm font-tech text-blue-500 uppercase tracking-widest font-bold">{data.city} // TACTICAL_GRID_ZONE</span>
                     <h2 className="text-5xl font-tech text-white italic tracking-tighter uppercase leading-none">{data.status}</h2>
                  </div>
                  <div className="text-right">
                     <span className="text-xs font-tech text-slate-500 uppercase tracking-[0.3em] font-bold">Grid Stability</span>
                     <div className="text-6xl font-tech text-white mt-2 italic leading-none">
                        {Math.abs(Math.round(data.balance_mw))}<span className="text-lg opacity-30 ml-3 font-black">MW {data.balance_mw < 0 ? 'DEFICIT' : 'SURPLUS'}</span>
                     </div>
                  </div>
               </div>
            </div>

            <div className="grid grid-cols-3 gap-8">
               {[
                 { label: 'Weather Signal', val: data.signals?.weather?.label || 'N/A', score: data.signals?.weather?.score || 0, color: 'text-blue-400' },
                 { label: 'Grid Urgency', val: data.signals?.crisis?.label || 'N/A', score: data.signals?.crisis?.score || 0, color: 'text-orange-400' },
                 { label: 'Demand Load', val: Math.round(data.demand_mw || 0) + ' MW', score: 0.8, color: 'text-emerald-400' }
               ].map((s, i) => (
                  <div key={i} className="glass-panel p-8 rounded-2xl flex flex-col gap-6 group hover:border-blue-500/30 transition-all">
                     <span className="text-[12px] font-tech text-slate-400 uppercase tracking-[0.3em] font-bold">{s.label}</span>
                     <div className="flex items-center justify-between">
                        <span className={`text-3xl font-tech uppercase italic ${s.color}`}>{s.val}</span>
                        <div className="w-12 h-1 bg-white/5 rounded-full overflow-hidden">
                           <div className="bg-current h-full shadow-[0_0_8px_currentColor]" style={{ width: `${s.score * 100}%`, color: s.color.replace('text-', '#') }}></div>
                        </div>
                     </div>
                  </div>
               ))}
            </div>
         </div>

         <div className="col-span-12 xl:col-span-4 glass-panel p-10 rounded-2xl flex flex-col justify-between overflow-hidden relative group">
            <div className="absolute -right-10 -top-10 opacity-[0.02] group-hover:rotate-45 transition-transform duration-[2000ms]">
               <Activity size={300} />
            </div>
            <span className="text-[18px] font-tech text-slate-300 uppercase tracking-[0.5em] mb-12 font-black">Neural Analysis_Engine</span>
            <p className="text-2xl font-bold text-white leading-relaxed italic border-l-8 border-blue-600/30 pl-10 font-serif">
               "{data.analysis}"
            </p>
            <div className="mt-10 pt-10 border-t border-white/5 flex items-center justify-between">
               <div className="flex flex-col">
                  <span className="text-[12px] font-tech text-slate-700 uppercase">Process_Uplink</span>
                  <span className="text-xs font-bold text-blue-500 uppercase tracking-widest">{data.agent_source} Layer</span>
               </div>
               <Radio size={24} className="text-blue-500/30 animate-pulse" />
            </div>
         </div>
      </div>

      {/* Resource & Asset Visualizers */}
      <div className="grid grid-cols-12 gap-8">
         {/* Generation Breakdown Chart */}
         <div className="col-span-12 xl:col-span-8 glass-panel p-10 rounded-2xl h-[450px]">
            <div className="flex items-center justify-between mb-10">
               <div className="flex items-center gap-4">
                  <Zap size={20} className="text-blue-500" />
                  <h3 className="text-xs font-tech text-white uppercase tracking-[0.4em]">Resource Generation Matrix</h3>
               </div>
               <div className="flex gap-6 text-[10px] font-tech text-slate-600">
                  <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-blue-500"></div> CURRENT</span>
                  <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-white/10"></div> MAX_CAP</span>
               </div>
            </div>
            <div className="h-[300px] w-full">
               <ResponsiveContainer width="100%" height="100%" debounce={100}>
                  <BarChart data={supplyData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                     <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#f8fafc', fontSize: 13, fontWeight: 'bold', fontFamily: 'Orbitron' }} height={50} width={400} />
                     <YAxis axisLine={false} tickLine={false} tick={{ fill: '#f8fafc', fontSize: 13, fontWeight: 'bold', fontFamily: 'Orbitron' }} width={80} height={0} />
                     <Tooltip 
                        contentStyle={{ backgroundColor: '#0a0d14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', fontFamily: 'Orbitron' }}
                        itemStyle={{ color: '#fff' }}
                        cursor={{ fill: 'rgba(255,255,255,0.02)' }}
                     />
                     <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={40}>
                        {supplyData.map((entry, index) => (
                           <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                     </Bar>
                     <Bar dataKey="max" fill="rgba(255,255,255,0.05)" radius={[4, 4, 0, 0]} barSize={10} />
                  </BarChart>
               </ResponsiveContainer>
            </div>
         </div>

         {/* Delta Override Insight */}
         <div className="col-span-12 xl:col-span-4 glass-panel p-10 rounded-2xl flex flex-col gap-8">
            <div className="flex items-center gap-4 border-b border-white/5 pb-6">
               <Activity size={20} className="text-emerald-500" />
               <h3 className="text-xs font-tech text-white uppercase tracking-[0.4em]">Delta Override Review</h3>
            </div>
            <div className="flex-grow flex flex-col gap-6 overflow-y-auto custom-scrollbar pr-2">
               {data.decisions?.map((d, i) => (
                  <div key={i} className="flex flex-col gap-6 bg-white/[0.02] p-8 rounded-2xl border border-white/5 border-l-4 border-l-emerald-500">
                     <div className="flex justify-between items-start">
                        <div className="flex flex-col">
                           <span className="text-[20px] font-tech text-slate-300 uppercase mb-5 font-black tracking-widest italic">Adjusted Node</span>
                           <span className="text-lg font-tech text-white tracking-widest uppercase">{d.plant}</span>
                        </div>
                        <div className="px-4 py-2 bg-emerald-500/10 rounded-lg text-[10px] font-tech text-emerald-500">+{Math.round(d.delta)} MW</div>
                     </div>
                     <div className="flex items-center justify-between pt-6 border-t border-white/5">
                        <div className="flex flex-col gap-1">
                           <span className="text-[12px] text-slate-500 uppercase font-tech">Input</span>
                           <span className="text-lg font-tech text-white italic">{Math.round(d.before)}</span>
                        </div>
                        <ArrowRight size={20} className="text-slate-700" />
                        <div className="flex flex-col gap-1 text-right">
                           <span className="text-[12px] text-slate-500 uppercase font-tech">Output</span>
                           <span className="text-lg font-tech text-emerald-500 italic">{Math.round(d.after)}</span>
                        </div>
                     </div>
                     <p className="text-[22px] text-white font-bold leading-relaxed italic mt-4 font-serif bg-black/40 p-6 rounded-2xl">
                        "{d.reason}"
                     </p>
                  </div>
               ))}
               {!data.decisions?.length && (
                  <div className="h-full flex flex-col items-center justify-center opacity-20 py-20">
                     <ShieldAlert size={40} className="mb-4" />
                     <p className="text-[9px] font-tech uppercase tracking-widest text-center leading-loose">No delta adjustments<br/>required for stability</p>
                  </div>
               )}
            </div>
         </div>
      </div>

      {/* Asset Audit Visualization */}
      <div className="glass-panel p-10 rounded-2xl mb-20">
         <div className="flex items-center justify-between mb-12">
            <div className="flex items-center gap-4">
               <List size={20} className="text-blue-500" />
               <h3 className="text-xs font-tech text-white uppercase tracking-[0.4em]">Asset Efficiency VS Proximity</h3>
            </div>
         </div>
         <div className="h-[400px] w-full">
            <ResponsiveContainer width="100%" height="100%">
               <ScatterChart margin={{ top: 40, right: 40, bottom: 60, left: 60 }}>
                  <XAxis type="number" dataKey="distance" name="Distance" unit="km" axisLine={false} tickLine={false} tick={{ fill: '#f8fafc', fontSize: 13, fontWeight: 'bold', fontFamily: 'Orbitron', dy: 10 }} width={0} height={20} />
                  <YAxis type="number" dataKey="cost" name="Cost" unit="₹" axisLine={false} tickLine={false} tick={{ fill: '#f8fafc', fontSize: 13, fontWeight: 'bold', fontFamily: 'Orbitron', dx: -10 }} width={20} height={0} />
                  <ZAxis type="number" dataKey="output" range={[100, 1000]} name="Output" unit="MW" />
                  <Tooltip 
                     cursor={{ strokeDasharray: '3 3' }} 
                     content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                           const data = payload[0].payload;
                           return (
                              <div className="glass-panel p-5 rounded-2xl border border-white/20 shadow-2xl backdrop-blur-3xl min-w-[200px]">
                                 <div className="flex flex-col gap-4">
                                    <div className="flex flex-col">
                                       <span className="text-[10px] font-tech text-blue-500 uppercase tracking-widest mb-1">Asset Trace</span>
                                       <span className="text-[18px] font-tech text-white uppercase italic font-black">{data.name}</span>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4 pt-4 border-t border-white/5">
                                       <div className="flex flex-col">
                                          <span className="text-[14px] text-slate-400 uppercase font-tech font-bold">Proximity</span>
                                          <span className="text-xl font-tech text-white font-black">{Math.round(data.distance)} KM</span>
                                       </div>
                                       <div className="flex flex-col">
                                          <span className="text-[14px] text-slate-400 uppercase font-tech font-bold">Rate</span>
                                          <span className="text-xl font-tech text-emerald-500 font-black">₹{Math.round(data.cost)}/U</span>
                                       </div>
                                       <div className="flex flex-col col-span-2">
                                          <span className="text-[14px] text-slate-400 uppercase font-tech font-bold">Output Spectrum</span>
                                          <span className="text-xl font-tech text-blue-400 font-black">{Math.round(data.output)} MW</span>
                                       </div>
                                    </div>
                                    <div className="text-[12px] font-tech text-slate-600 uppercase tracking-[0.3em] font-black border-t border-white/5 pt-4">
                                       Sector // {data.type}
                                    </div>
                                 </div>
                              </div>
                           );
                        }
                        return null;
                     }}
                  />
                  <Scatter name="Assets" data={plantScatter}>
                     {plantScatter.map((entry, index) => (
                        <Cell 
                           key={`cell-${index}`} 
                           fill={entry.type === 'hydro' ? '#3b82f6' : entry.type === 'solar' ? '#fbbf24' : entry.type === 'wind' ? '#06b6d4' : '#ef4444'} 
                           className="drop-shadow-[0_0_10px_currentColor]"
                        />
                     ))}
                  </Scatter>
               </ScatterChart>
            </ResponsiveContainer>
         </div>
         <div className="grid grid-cols-4 gap-8 mt-12 border-t border-white/5 pt-12">
            {plantScatter.slice(0, 4).map((p, i) => (
               <div key={i} className="flex flex-col gap-4 p-6 bg-white/[0.02] rounded-2xl border border-white/5 group hover:border-blue-500/30 transition-all">
                  <span className="text-lg font-tech text-white truncate font-black tracking-widest uppercase italic border-b border-white/5 pb-3">{p.name}</span>
                  <div className="flex justify-between items-center text-[12px] font-mono font-bold text-slate-400 uppercase tracking-widest">
                     <span>Dist: <span className="text-blue-500">{p.distance}KM</span></span>
                     <span>Rate: <span className="text-emerald-500">{p.cost}/U</span></span>
                  </div>
               </div>
            ))}
         </div>
      </div>
    </div>
  );
};

export default StrategicIntel;
