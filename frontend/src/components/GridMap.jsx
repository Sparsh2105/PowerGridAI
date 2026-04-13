import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import axios from 'axios';
import { Zap, MapPin, Activity } from 'lucide-react';

const GridMap = () => {
  const [plants, setPlants] = useState([]);
  const position = [22, 78];

  useEffect(() => {
    axios.get('http://127.0.0.1:8000/plants')
      .then(res => setPlants(res.data))
      .catch(err => console.error("[Map Connectivity Error]", err));
  }, []);

  const getIcon = (type) => {
    const color = type === 'coal' ? '#ef4444' : 
                  type === 'nuclear' ? '#a855f7' : 
                  '#10b981';
    
    return L.divIcon({
      className: 'custom-icon-wrapper',
      html: `<div class="marker-flicker" style="background-color: ${color}; width: 10px; height: 10px; border-radius: 50%; border: 2px solid white;"></div>`,
      iconSize: [20, 20],
      iconAnchor: [10, 10]
    });
  };

  return (
    <div className="w-full h-full bg-[#0b0e14] relative">
      <MapContainer 
        center={position} 
        zoom={4.8} 
        zoomControl={false}
        className="w-full h-full"
        scrollWheelZoom={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; CARTO'
        />
        {plants.map((plant, idx) => (
          <Marker 
            key={`${plant.name}-${idx}`} 
            position={[plant.lat, plant.lon]}
            icon={getIcon(plant.type)}
          >
            <Popup>
              <div className="p-4 flex flex-col gap-3 min-w-[180px]">
                 <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-500/10 rounded">
                       <Zap size={14} className="text-blue-500" />
                    </div>
                    <div>
                       <div className="text-[11px] font-bold text-white uppercase tracking-tight">{plant.name}</div>
                       <div className="text-[9px] text-slate-500 font-bold uppercase tracking-widest">{plant.type} Generation</div>
                    </div>
                 </div>
                 <div className="flex flex-col gap-2 pt-2 border-t border-white/10">
                    <div className="flex justify-between text-[10px]">
                       <span className="text-slate-500">Max Capacity</span>
                       <span className="text-blue font-bold">{plant.max_mw} MW</span>
                    </div>
                    <div className="flex justify-between text-[10px]">
                       <span className="text-slate-500">Active Status</span>
                       <span className="text-emerald-500 font-bold uppercase">Optimized</span>
                    </div>
                 </div>
                 <div className="pt-2 text-[9px] text-slate-600 font-mono uppercase tracking-tighter">
                   Region // {plant.state}
                 </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
};

export default GridMap;
