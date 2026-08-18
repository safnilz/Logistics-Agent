import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Bot, Send, Mic, Map as MapIcon, 
  LayoutDashboard, Truck, Settings, Bell, Check, X,
  Users, Plus, Clock, Trash2, MapPin, Activity, ShieldCheck, PlayCircle,
  Flame, Scale, Percent, Route
} from 'lucide-react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import L from 'leaflet';

// Fix for default marker icons
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom Icons for Jobs
const redIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]
});
const greenIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]
});

// Custom SVG solid badge for live trucks
const truckIcon = L.divIcon({
  className: 'truck-marker-wrapper',
  html: `<div style="background: var(--accent-cyan); color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3); border: 2px solid white;">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="3" width="15" height="13"></rect><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon><circle cx="5.5" cy="18.5" r="2.5"></circle><circle cx="18.5" cy="18.5" r="2.5"></circle></svg>
  </div>`,
  iconSize: [32, 32],
  iconAnchor: [16, 16]
});

const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000/api';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  action?: {
    type: string;
    job_id?: string;
    vehicle_id?: string;
    client_name?: string;
    job_type?: string;
    expected_weight_kg?: number;
    latitude?: number;
    longitude?: number;
    allocated_time?: string;
    expected_bins?: number;
    bin_size?: string;
    reason: string;
    status?: 'pending' | 'confirmed' | 'rejected';
  };
};

type MarkerData = {
  id: string;
  deviceId: string;
  deviceName: string;
  latitude: number;
  longitude: number;
  speed: number;
  course?: number;
  ignition: boolean;
  motion: boolean;
  total_distance_km: number;
  engine_hours: number;
  daily_distance_km: number;
  daily_engine_hours: number;
  state: string;
  address: string;
};

type ClientData = {
  id: string;
  name: string;
  default_job_type: string;
  location: string;
  latitude?: number;
  longitude?: number;
  allocated_time?: string;
  expected_bins?: number;
  bin_size?: string;
};

type JobData = {
  id: string;
  type: string;
  client: string;
  location: string;
  latitude?: number;
  longitude?: number;
  allocated_time?: string;
  expected_bins?: number;
  bin_size?: string;
  expected_weight_kg: number;
  assigned_vehicle: string | null;
  status: string;
  eta_minutes?: number;
};

type AlertData = {
  id: string;
  message: string;
  vehicle_id: string;
  type: string;
  timestamp: string;
};

const DEFAULT_MARKERS: MarkerData[] = [
  {
    id: '29918965635',
    deviceId: '75828',
    deviceName: 'Isuzu 48390',
    latitude: 25.0780616,
    longitude: 55.2366916,
    speed: 0.0,
    course: 180,
    ignition: true,
    motion: false,
    total_distance_km: 26971.03,
    engine_hours: 496.19,
    daily_distance_km: 221.03,
    daily_engine_hours: 4.19,
    state: 'parking',
    address: 'Al Barsha South, Dubai Hills, Dubai'
  },
  {
    id: '29919119032',
    deviceId: '72746',
    deviceName: 'Fuso 54127',
    latitude: 24.8608799,
    longitude: 55.1575616,
    speed: 38.5,
    course: 214,
    ignition: true,
    motion: true,
    total_distance_km: 71924.56,
    engine_hours: 195489.29,
    daily_distance_km: 174.56,
    daily_engine_hours: 9.29,
    state: 'moving',
    address: 'Dubai South, Dubai'
  }
];

const DEFAULT_SCHEDULE = {
  vehicles: [
    { id: 'V1', name: 'Isuzu 48390 (3-Ton)', max_weight_kg: 5000.0, max_volume_m3: 20.0 },
    { id: 'V2', name: 'Fuso 54127 (7-Ton)', max_weight_kg: 3000.0, max_volume_m3: 12.0 }
  ],
  jobs: [
    { id: 'JOB-001', type: 'Recova', client: 'Client A', location: 'Downtown', latitude: 25.2048, longitude: 55.2708, allocated_time: '09:00 - 12:00', expected_bins: 2, bin_size: '240L', expected_weight_kg: 500.0, assigned_vehicle: 'V1', status: 'pending', eta_minutes: 18 },
    { id: 'JOB-002', type: 'Recova', client: 'Client B', location: 'Business Bay', latitude: 25.1856, longitude: 55.2666, allocated_time: '13:00 - 15:00', expected_bins: 5, bin_size: '1100L', expected_weight_kg: 1200.0, assigned_vehicle: 'V1', status: 'pending', eta_minutes: 32 },
    { id: 'JOB-003', type: 'ReClaim', client: 'Client C', location: 'JLT', latitude: 25.0773, longitude: 55.1403, allocated_time: '10:00 - 16:00', expected_bins: 1, bin_size: 'CBM', expected_weight_kg: 800.0, assigned_vehicle: 'V2', status: 'pending', eta_minutes: 12 }
  ]
};

function App() {
  const [schedule, setSchedule] = useState<{vehicles: any[], jobs: JobData[]}>(DEFAULT_SCHEDULE);
  const [clients, setClients] = useState<ClientData[]>([]);
  const [showClientModal, setShowClientModal] = useState(false);
  const [currentView, setCurrentView] = useState<'dashboard' | 'schedule' | 'map'>('dashboard');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg-1',
      role: 'assistant',
      content: "Good morning! I am the Ehfaaz Logistics AI Agent. How can I assist you in optimizing the fleet today?"
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [liveMarkers, setLiveMarkers] = useState<MarkerData[]>(DEFAULT_MARKERS);
  const [displayMarkers, setDisplayMarkers] = useState<MarkerData[]>(DEFAULT_MARKERS);
  const targetMarkersRef = useRef<MarkerData[]>(DEFAULT_MARKERS);
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [playbackMode, setPlaybackMode] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchSchedule = async () => {
    try {
      const res = await axios.get(`${API_BASE}/schedule`);
      if (res.data && res.data.vehicles && res.data.vehicles.length > 0) {
        setSchedule(res.data);
      }
    } catch (err) {
      console.warn("Backend schedule not connected, using offline defaults.");
    }
  };

  const fetchClients = async () => {
    try {
      const res = await axios.get(`${API_BASE}/clients`);
      if (res.data) setClients(res.data);
    } catch (err) {
      console.warn("Backend clients not connected.");
    }
  };

  const fetchLiveTracking = async () => {
    try {
      const res = await axios.get(`${API_BASE}/tracker/live`);
      if (res.data && res.data.length > 0) {
        setLiveMarkers(res.data);
        targetMarkersRef.current = res.data;
        setDisplayMarkers(prev => prev.length === 0 ? res.data : prev);
      }
    } catch (err) {
      console.warn("Backend tracker not connected, displaying cached live telemetry.");
    }
  };

  const fetchAlerts = async () => {
    try {
      const res = await axios.get(`${API_BASE}/alerts`);
      if (res.data) setAlerts(res.data);
    } catch (err) {
      console.warn("Backend alerts not connected.");
    }
  };

  useEffect(() => {
    fetchSchedule();
    fetchClients();
    fetchLiveTracking();
    fetchAlerts();
    const interval = setInterval(() => {
      fetchLiveTracking();
      fetchSchedule();
      fetchAlerts();
    }, 10000); // 10 second interval for smoother tracking
    return () => clearInterval(interval);
  }, []);

  // Smooth Interpolation Loop (LERP) & Simulation for Map Markers
  useEffect(() => {
    let animationFrameId: number;
    const animate = () => {
      setDisplayMarkers(prev => prev.map(marker => {
        const target = targetMarkersRef.current.find(t => t.id === marker.id);
        if (!target) return marker;
        
        const latDiff = target.latitude - marker.latitude;
        const lngDiff = target.longitude - marker.longitude;
        
        // CORRECTION PHASE: If distance is noticeable, LERP towards target
        if (Math.abs(latDiff) > 0.000005 || Math.abs(lngDiff) > 0.000005) {
            // If it's a huge jump, snap to target
            if (Math.abs(latDiff) > 0.05 || Math.abs(lngDiff) > 0.05) {
              return { ...target };
            }
            
            // Smoothly close 5% of the distance every frame (~60fps)
            return {
              ...marker,
              latitude: marker.latitude + (latDiff * 0.05),
              longitude: marker.longitude + (lngDiff * 0.05),
              speed: target.speed,
              motion: target.motion,
              course: target.course
            };
        } 
        // SIMULATION PHASE: If we are roughly at target, simulate forward movement if moving
        else if (marker.speed > 0 && marker.course !== undefined) {
            // Convert speed (km/h) to roughly degrees per frame at 60fps
            const kmPerFrame = (marker.speed / 3600) / 60;
            const degPerFrame = kmPerFrame * 0.009; // 1km is roughly 0.009 degrees
            
            // Traccar course is 0=North, 90=East
            const rad = (90 - marker.course) * (Math.PI / 180); // convert course to standard math angle
            const dLat = Math.sin(rad) * degPerFrame;
            const dLng = Math.cos(rad) * degPerFrame;
            
            return {
              ...marker,
              latitude: marker.latitude + dLat,
              longitude: marker.longitude + dLng,
              speed: target.speed,
              motion: target.motion,
              course: target.course
            };
        }
        
        return {
            ...marker,
            speed: target.speed,
            motion: target.motion,
            course: target.course
        };
      }));
      animationFrameId = requestAnimationFrame(animate);
    };
    animationFrameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!inputText.trim()) return;

    const newMsg: Message = { id: Date.now().toString(), role: 'user', content: inputText };
    setMessages(prev => [...prev, newMsg]);
    setInputText('');

    try {
      const res = await axios.post(`${API_BASE}/chat`, { message: newMsg.content });
      
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: res.data.reply,
        action: res.data.suggested_action ? { ...res.data.suggested_action, status: 'pending' } : undefined
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAction = async (msgId: string, confirm: boolean) => {
    const msg = messages.find(m => m.id === msgId);
    if (!msg || !msg.action) return;

    if (confirm) {
      try {
        await axios.post(`${API_BASE}/execute-action`, msg.action);
        setMessages(prev => prev.map(m => m.id === msgId ? { ...m, action: { ...m.action!, status: 'confirmed' } } : m));
        const successMessage = msg.action.type === 'move_stop' 
          ? `Action confirmed. Moved ${msg.action.job_id} to ${msg.action.vehicle_id}.`
          : `Action confirmed. Created a new ${msg.action.job_type} collection for ${msg.action.client_name}.`;
        setMessages(prev => [...prev, { id: Date.now().toString(), role: 'assistant', content: successMessage }]);
        fetchSchedule(); 
      } catch (err) {
        console.error(err);
      }
    } else {
      setMessages(prev => prev.map(m => m.id === msgId ? { ...m, action: { ...m.action!, status: 'rejected' } } : m));
    }
  };

  const toggleVoice = () => {
    setIsListening(!isListening);
    if (!isListening) {
      setInputText("How is the truck performing today?");
      setTimeout(() => setIsListening(false), 1500);
    }
  };

  const centerPosition: [number, number] = [25.15, 55.20]; // Dubai roughly centered

  // Dashboard KPI Computations
  const totalFleetJobs = schedule.jobs.length;
  const completedJobs = schedule.jobs.filter(j => j.status === 'completed').length;
  const totalEngineHours = liveMarkers.reduce((acc, m) => acc + (m.daily_engine_hours || 0), 0).toFixed(1);

  // New Daily KPIs
  const totalPayload = schedule.jobs.filter(j => j.status === 'completed').reduce((sum, j) => sum + j.expected_weight_kg, 0);
  const totalDailyDistance = liveMarkers.reduce((acc, m) => acc + (m.daily_distance_km || 0), 0).toFixed(1);
  const estimatedFuel = (parseFloat(totalDailyDistance) * 0.25).toFixed(1); // 25L/100km
  const utilizationRate = liveMarkers.length > 0 ? ((liveMarkers.filter(m => m.motion).length / liveMarkers.length) * 100).toFixed(0) : 0;

  // Fleet Health Score
  const jobProgress = totalFleetJobs > 0 ? (completedJobs / totalFleetJobs) * 100 : 0;
  const healthScore = Math.min(100, Math.round((parseFloat(utilizationRate.toString()) * 0.4) + (jobProgress * 0.6)));

  // Proactive AI Insight
  let aiInsight = "All vehicles are operating within optimal parameters.";
  const idleTrucks = liveMarkers.filter(m => m.ignition && !m.motion && m.speed < 1);
  const movingTrucks = liveMarkers.filter(m => m.motion);
  
  if (idleTrucks.length > 0) {
      aiInsight = `Insight: ${idleTrucks[0].deviceName} is currently idling unnecessarily. Suggest turning off engine to conserve fuel.`;
  } else if (parseFloat(utilizationRate.toString()) < 50 && totalFleetJobs > 0) {
      aiInsight = `Insight: Low fleet utilization (${utilizationRate}%). Suggest consolidating remaining pending stops to a single vehicle.`;
  } else if (movingTrucks.length > 0) {
      aiInsight = `Insight: Active tracking engaged. ${movingTrucks.length} vehicle(s) en route to next destination.`;
  }

  // Vehicle Mapping helper for table
  const getVehicleMapping = (deviceName: string) => {
    if (deviceName.toLowerCase().includes('isuzu')) return 'V1';
    if (deviceName.toLowerCase().includes('fuso')) return 'V2';
    return null;
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <div className="glass-panel sidebar" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <div style={{ color: 'var(--accent-cyan)', fontWeight: 'bold', fontSize: '1.2rem', marginBottom: '30px', textAlign: 'center' }}>Ehfaaz</div>
        
        <div className={`sidebar-icon ${currentView === 'dashboard' ? 'active' : ''}`} onClick={() => setCurrentView('dashboard')} title="Dashboard">
          <LayoutDashboard size={24} />
        </div>
        
        <div className={`sidebar-icon ${currentView === 'schedule' ? 'active' : ''}`} onClick={() => setCurrentView('schedule')} title="Schedule">
          <Truck size={24} />
        </div>
        
        <div className={`sidebar-icon ${currentView === 'map' ? 'active' : ''}`} onClick={() => setCurrentView('map')} title="Live Map">
          <MapIcon size={24} />
        </div>
        
        <div className="sidebar-icon" onClick={() => setShowClientModal(true)} title="Client Registry" style={{ cursor: 'pointer' }}>
          <Users size={24} />
        </div>
        
        <div className="sidebar-icon" style={{ marginTop: 'auto', cursor: 'pointer', position: 'relative' }} title="Notifications" onClick={() => setShowNotifications(true)}>
          <Bell size={24} />
          {alerts.length > 0 && <div style={{ position: 'absolute', top: -5, right: -5, background: 'var(--danger)', color: 'white', borderRadius: '50%', width: 18, height: 18, fontSize: '0.7rem', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>{alerts.length}</div>}
        </div>
        <div className="sidebar-icon" title="Settings">
          <Settings size={24} />
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, display: 'flex', gap: '20px', paddingRight: '20px', overflow: 'hidden' }}>
        
        {/* VIEW: DASHBOARD */}
        {currentView === 'dashboard' && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto', paddingRight: '10px' }}>
            <h1 style={{ margin: '0 0 10px 0', fontSize: '2rem' }}>Fleet Overview Dashboard</h1>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' }}>
              <div className="glass-panel" style={{ padding: '20px', textAlign: 'center' }}>
                <Activity size={32} color={healthScore > 80 ? 'var(--success)' : (healthScore > 50 ? 'var(--warning)' : 'var(--danger)')} style={{ marginBottom: 10 }} />
                <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{healthScore}<span style={{fontSize:'1.2rem'}}>%</span></div>
                <div style={{ color: 'var(--text-secondary)' }}>Fleet Health Score</div>
                <div style={{ fontSize: '0.75rem', marginTop: 8, color: healthScore > 80 ? 'var(--success)' : 'var(--warning)' }}>
                  {healthScore > 80 ? '▲ Optimal Efficiency' : '▼ Needs Attention'}
                </div>
              </div>
              <div className="glass-panel" style={{ padding: '20px', textAlign: 'center' }}>
                <Clock size={32} color="#f39c12" style={{ marginBottom: 10 }} />
                <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{totalEngineHours}</div>
                <div style={{ color: 'var(--text-secondary)' }}>Total Engine Hours</div>
                <div style={{ fontSize: '0.75rem', marginTop: 8, color: 'var(--text-secondary)' }}>
                  Active Runtime Today
                </div>
              </div>
              <div className="glass-panel" style={{ padding: '20px', textAlign: 'center' }}>
                <ShieldCheck size={32} color="#2ecc71" style={{ marginBottom: 10 }} />
                <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{completedJobs} / {totalFleetJobs}</div>
                <div style={{ color: 'var(--text-secondary)' }}>Jobs Completed</div>
                <div style={{ fontSize: '0.75rem', marginTop: 8, color: completedJobs === totalFleetJobs ? 'var(--success)' : 'var(--accent-cyan)' }}>
                  {completedJobs === totalFleetJobs && totalFleetJobs > 0 ? '✓ Schedule Complete' : '▶ In Progress'}
                </div>
              </div>
              <div className="glass-panel" style={{ padding: '20px', textAlign: 'center' }}>
                <Truck size={32} color="#9b59b6" style={{ marginBottom: 10 }} />
                <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{liveMarkers.filter(m => m.motion).length} / {liveMarkers.length}</div>
                <div style={{ color: 'var(--text-secondary)' }}>Trucks Moving</div>
                <div style={{ fontSize: '0.75rem', marginTop: 8, color: 'var(--text-secondary)' }}>
                  Live Active Count
                </div>
              </div>
            </div>

            {/* Premium Daily KPIs */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' }}>
              <div className="glass-panel" style={{ padding: '20px', textAlign: 'center', background: 'linear-gradient(135deg, rgba(69,162,158,0.1) 0%, transparent 100%)' }}>
                <Scale size={32} color="var(--accent-cyan)" style={{ marginBottom: 10 }} />
                <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{totalPayload} <span style={{fontSize:'1rem'}}>kg</span></div>
                <div style={{ color: 'var(--text-secondary)' }}>Payload Collected Today</div>
                <div style={{ fontSize: '0.75rem', marginTop: 8, color: 'var(--success)' }}>
                  ▲ Verified Intake
                </div>
              </div>
              <div className="glass-panel" style={{ padding: '20px', textAlign: 'center', background: 'linear-gradient(135deg, rgba(230,57,70,0.1) 0%, transparent 100%)' }}>
                <Route size={32} color="var(--danger)" style={{ marginBottom: 10 }} />
                <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{totalDailyDistance} <span style={{fontSize:'1rem'}}>km</span></div>
                <div style={{ color: 'var(--text-secondary)' }}>Total Daily Distance</div>
                <div style={{ fontSize: '0.75rem', marginTop: 8, color: 'var(--text-secondary)' }}>
                  Expected Range
                </div>
              </div>
              <div className="glass-panel" style={{ padding: '20px', textAlign: 'center', background: 'linear-gradient(135deg, rgba(243,156,18,0.1) 0%, transparent 100%)' }}>
                <Flame size={32} color="#f39c12" style={{ marginBottom: 10 }} />
                <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{estimatedFuel} <span style={{fontSize:'1rem'}}>L</span></div>
                <div style={{ color: 'var(--text-secondary)' }}>Est. Fuel Consumption</div>
                <div style={{ fontSize: '0.75rem', marginTop: 8, color: parseFloat(estimatedFuel) < 50 ? 'var(--success)' : 'var(--warning)' }}>
                  {parseFloat(estimatedFuel) < 50 ? '▲ Under Budget' : '▼ Monitor Usage'}
                </div>
              </div>
              <div className="glass-panel" style={{ padding: '20px', textAlign: 'center', background: 'linear-gradient(135deg, rgba(46,204,113,0.1) 0%, transparent 100%)' }}>
                <Percent size={32} color="#2ecc71" style={{ marginBottom: 10 }} />
                <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{utilizationRate}%</div>
                <div style={{ color: 'var(--text-secondary)' }}>Live Fleet Utilization</div>
                <div style={{ fontSize: '0.75rem', marginTop: 8, color: parseFloat(utilizationRate.toString()) > 50 ? 'var(--success)' : 'var(--warning)' }}>
                  {parseFloat(utilizationRate.toString()) > 50 ? '▲ Healthy Activity' : '▼ Under-Utilized'}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '20px', flex: 1 }}>
              {/* Telemetry Breakdown */}
              <div className="glass-panel" style={{ flex: 2, display: 'flex', flexDirection: 'column' }}>
                <h3 style={{ marginTop: 0 }}>Live Telemetry & Utilization</h3>
                <div style={{ flex: 1, overflowY: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                        <th style={{ padding: '12px' }}>Vehicle</th>
                        <th style={{ padding: '12px' }}>Speed & Status</th>
                        <th style={{ padding: '12px' }}>Payload Capacity</th>
                        <th style={{ padding: '12px' }}>Active ETA</th>
                        <th style={{ padding: '12px' }}>Engine</th>
                      </tr>
                    </thead>
                    <tbody>
                      {liveMarkers.map(marker => {
                        const vId = getVehicleMapping(marker.deviceName);
                        const vData = schedule.vehicles.find(v => v.id === vId);
                        const vJobs = schedule.jobs.filter(j => j.assigned_vehicle === vId && j.status !== 'completed');
                        const currentLoad = vJobs.reduce((sum, j) => sum + j.expected_weight_kg, 0);
                        const nextJob = vJobs.length > 0 ? vJobs[0] : null;
                        
                        return (
                          <tr key={marker.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                            <td style={{ padding: '12px', fontWeight: 'bold' }}>{marker.deviceName}</td>
                            <td style={{ padding: '12px' }}>
                              <span style={{ color: marker.speed > 0 ? 'var(--accent-cyan)' : 'var(--text-secondary)', marginRight: 8 }}>{marker.speed} km/h</span>
                              {marker.motion ? <span style={{ color: '#2ecc71', fontSize: '0.8rem' }}>(Moving)</span> : <span style={{ color: 'var(--warning)', fontSize: '0.8rem' }}>(Idle)</span>}
                            </td>
                            <td style={{ padding: '12px' }}>
                              {vData ? (
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                  <div style={{ width: 60, height: 6, background: 'rgba(255,255,255,0.1)', borderRadius: 3, overflow: 'hidden' }}>
                                    <div style={{ height: '100%', width: `${Math.min((currentLoad / vData.max_weight_kg)*100, 100)}%`, background: 'var(--accent-cyan)' }} />
                                  </div>
                                  <span style={{ fontSize: '0.85rem' }}>{currentLoad}/{vData.max_weight_kg}</span>
                                </div>
                              ) : <span style={{ color: 'var(--text-secondary)' }}>N/A</span>}
                            </td>
                            <td style={{ padding: '12px', fontSize: '0.85rem' }}>
                              {nextJob && nextJob.eta_minutes !== undefined ? <span style={{ color: 'var(--accent-cyan)', fontWeight: 'bold' }}>{nextJob.eta_minutes} mins</span> : <span style={{ color: 'var(--text-secondary)' }}>No Active Stops</span>}
                            </td>
                            <td style={{ padding: '12px' }}>{marker.daily_engine_hours} hr</td>
                          </tr>
                        );
                      })}
                      {liveMarkers.length === 0 && <tr><td colSpan={5} style={{ padding: '12px', textAlign: 'center', fontStyle: 'italic', color: 'var(--text-secondary)' }}>No telemetry available</td></tr>}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Mini AI Agent */}
              <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0 }}>
                
                {/* AI Proactive Insight Banner */}
                <div style={{ background: 'linear-gradient(90deg, rgba(69, 162, 158, 0.2), transparent)', padding: '12px 20px', borderBottom: '1px solid var(--surface-border)', display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ background: 'rgba(69, 162, 158, 0.2)', padding: 6, borderRadius: '50%', display: 'flex' }}>
                    <Bot size={16} color="var(--accent-cyan)" />
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 500 }}>
                    {aiInsight}
                  </div>
                </div>

                <div className="chat-header">
                  <Bot className="chat-header-icon" /> Ehfaaz AI Analyst
                </div>
                <div className="chat-messages" style={{ flex: 1 }}>
                  {messages.map(msg => (
                    <div key={msg.id} className={`message ${msg.role}`}>
                      <div>{msg.content}</div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
                <form className="chat-input-container" onSubmit={handleSendMessage} style={{ borderRadius: '0 0 16px 16px' }}>
                  <input type="text" className="chat-input" placeholder="Ask for insights..." value={inputText} onChange={(e) => setInputText(e.target.value)} />
                  <button type="submit" className="send-btn"><Send size={18} /></button>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* VIEW: SCHEDULE & MAP SIDE-BY-SIDE (Classic View) */}
        {currentView === 'schedule' && (
          <>
            {/* Chat */}
            <div className="glass-panel chat-container" style={{ width: '400px', flex: 'none' }}>
              <div className="chat-header">
                <Bot className="chat-header-icon" /> Ehfaaz Logistics AI
              </div>
              <div className="chat-messages">
                {messages.map(msg => (
                  <div key={msg.id} className={`message ${msg.role}`}>
                    <div>{msg.content}</div>
                    {msg.action && (
                      <div className="action-card">
                        <div style={{ fontSize: '0.85rem', color: 'var(--accent-cyan)' }}>
                          {msg.action.type === 'move_stop' ? 'Proposed Route Change:' : 'Proposed Job Creation:'}
                        </div>
                        <div style={{ margin: '8px 0', fontSize: '0.9rem' }}>{msg.action.reason}</div>
                        {msg.action.status === 'pending' ? (
                          <div className="action-buttons">
                            <button className="btn btn-confirm" onClick={() => handleAction(msg.id, true)}>Confirm</button>
                            <button className="btn btn-reject" onClick={() => handleAction(msg.id, false)}>Reject</button>
                          </div>
                        ) : (
                          <div style={{ marginTop: 8, fontSize: '0.8rem', color: msg.action.status === 'confirmed' ? 'var(--success)' : 'var(--danger)' }}>
                            {msg.action.status ? msg.action.status.toUpperCase() : ''}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
              <form className="chat-input-container" onSubmit={handleSendMessage}>
                <button type="button" className="mic-btn" onClick={toggleVoice} style={{ color: isListening ? 'var(--danger)' : '' }}><Mic size={20} /></button>
                <input type="text" className="chat-input" placeholder="Schedule or analyze..." value={inputText} onChange={(e) => setInputText(e.target.value)} />
                <button type="submit" className="send-btn"><Send size={20} /></button>
              </form>
            </div>

            {/* Schedule */}
            <div className="glass-panel schedule-container" style={{ width: '350px', flex: 'none' }}>
              <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>Daily Trip Schedule</div>
              </div>
              <div style={{ overflowY: 'auto', paddingRight: '4px' }}>
                {schedule.vehicles.map(vehicle => {
                  const jobs = schedule.jobs.filter(j => j.assigned_vehicle === vehicle.id);
                  const currentWeight = jobs.reduce((sum, j) => sum + j.expected_weight_kg, 0);
                  const progress = (currentWeight / vehicle.max_weight_kg) * 100;
                  return (
                    <div key={vehicle.id} className="vehicle-card">
                      <div className="vehicle-header">
                        <div>
                          <span className="vehicle-name">{vehicle.name}</span>
                          <span style={{ fontSize: '0.8rem', marginLeft: 8, color: 'var(--text-secondary)' }}>({vehicle.id})</span>
                        </div>
                        <div style={{ fontSize: '0.85rem' }}>{currentWeight} / {vehicle.max_weight_kg} kg</div>
                      </div>
                      <div className="progress-bar-bg">
                        <div className="progress-bar-fill" style={{ width: `${Math.min(progress, 100)}%`, background: progress > 90 ? 'var(--danger)' : '' }}></div>
                      </div>
                      <div style={{ marginTop: 16 }}>
                        {jobs.length === 0 ? <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>No stops assigned.</div> : jobs.map((job, idx) => (
                          <div key={job.id} className="job-item">
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                              <div>
                                <span style={{ marginRight: 8, color: 'var(--text-secondary)' }}>{idx + 1}.</span>
                                {job.client} <span style={{ marginLeft: 8, fontSize: '0.75rem' }} className={job.type === 'Recova' ? 'job-type-recova' : 'job-type-reclaim'}>[{job.type}]</span>
                              </div>
                              <div>{job.expected_weight_kg} kg</div>
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4, marginLeft: 20 }}>
                              {job.eta_minutes !== undefined && job.eta_minutes !== null && job.status !== 'completed' && (
                                <span style={{ background: 'rgba(69, 162, 158, 0.2)', padding: '2px 6px', borderRadius: '4px', color: 'var(--accent-cyan)', fontWeight: 'bold', marginRight: 8 }}>
                                  ⏱️ ETA: {job.eta_minutes} mins
                                </span>
                              )}
                              {job.expected_bins && job.bin_size && <span><Trash2 size={10} style={{display:'inline'}}/> {job.expected_bins}x {job.bin_size} &nbsp;&nbsp;</span>}
                              {job.allocated_time && <span><Clock size={10} style={{display:'inline'}}/> {job.allocated_time} &nbsp;&nbsp;</span>}
                              {job.location && <span><MapPin size={10} style={{display:'inline'}}/> {job.location}</span>}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
                <div style={{ marginTop: 20 }}>
                  <div style={{ fontSize: '0.9rem', color: 'var(--warning)', marginBottom: 8, fontWeight: 600 }}>Unassigned Jobs</div>
                  {schedule.jobs.filter(j => !j.assigned_vehicle).map(job => (
                    <div key={job.id} className="job-item" style={{ borderLeft: '3px solid var(--warning)', paddingLeft: 8 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <div>{job.client} <span className={job.type === 'Recova' ? 'job-type-recova' : 'job-type-reclaim'}>[{job.type}]</span></div>
                        <div>{job.expected_weight_kg} kg</div>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                        {job.expected_bins && job.bin_size && <span><Trash2 size={10} style={{display:'inline'}}/> {job.expected_bins}x {job.bin_size} &nbsp;&nbsp;</span>}
                        {job.allocated_time && <span><Clock size={10} style={{display:'inline'}}/> {job.allocated_time}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Map */}
            <div className="glass-panel map-container" style={{ flex: 1, padding: 0, overflow: 'hidden' }}>
              <div className="section-header" style={{ position: 'absolute', top: 0, left: 0, right: 0, zIndex: 1000, padding: '20px', background: 'linear-gradient(to bottom, rgba(11,12,16,0.9), transparent)', pointerEvents: 'none' }}>
                Live Map <MapIcon size={20} color="var(--accent-cyan)" />
              </div>
              <MapContainer center={centerPosition} zoom={10} style={{ height: '100%', width: '100%', zIndex: 1 }} zoomControl={true}>
                <TileLayer attribution='&copy; <a href="https://carto.com/">CartoDB</a>' url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png" />
                {displayMarkers.map(m => (
                  <Marker key={m.id} position={[m.latitude, m.longitude]} icon={truckIcon}>
                    <Popup><div style={{ color: '#333' }}><strong>{m.deviceName}</strong><br/>Speed: {m.speed} km/h<br/>Status: {m.motion ? 'Moving' : 'Idle'}</div></Popup>
                  </Marker>
                ))}
                {schedule.jobs.map(j => {
                  if (!j.latitude || !j.longitude) return null;
                  return (
                    <Marker key={j.id} position={[j.latitude, j.longitude]} icon={j.assigned_vehicle ? greenIcon : redIcon}>
                      <Popup><div style={{ color: '#333' }}><strong>{j.client}</strong> [{j.type}]<br/>Weight: {j.expected_weight_kg} kg</div></Popup>
                    </Marker>
                  )
                })}
              </MapContainer>
            </div>
          </>
        )}

        {/* VIEW: FULL SCREEN MAP */}
        {currentView === 'map' && (
          <div className="glass-panel map-container" style={{ flex: 1, padding: 0, overflow: 'hidden', position: 'relative' }}>
            <div className="section-header" style={{ position: 'absolute', top: 0, left: 0, right: 0, zIndex: 1000, padding: '20px', background: 'linear-gradient(to bottom, rgba(11,12,16,0.9), transparent)', pointerEvents: 'none', display: 'flex', justifyContent: 'space-between' }}>
              <div>Fleet Global View <MapIcon size={20} color="var(--accent-cyan)" style={{ display: 'inline', marginLeft: 8 }} /></div>
              <div style={{ pointerEvents: 'auto' }}>
                <button className="btn btn-confirm" onClick={() => setPlaybackMode(!playbackMode)} style={{ background: playbackMode ? 'var(--danger)' : 'var(--accent-cyan)', color: playbackMode ? 'white' : 'black', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <PlayCircle size={16} /> {playbackMode ? 'Stop Playback' : 'Historical Playback'}
                </button>
              </div>
            </div>
            
            <MapContainer center={centerPosition} zoom={10} style={{ height: '100%', width: '100%', zIndex: 1 }} zoomControl={true}>
              <TileLayer attribution='&copy; <a href="https://carto.com/">CartoDB</a>' url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png" />
              {liveMarkers.map(m => (
                <Marker key={m.id} position={[m.latitude, m.longitude]} icon={truckIcon}>
                  <Popup><div style={{ color: '#333' }}><strong>{m.deviceName}</strong><br/>Speed: {m.speed} km/h<br/>Status: {m.motion ? 'Moving' : 'Idle'}</div></Popup>
                </Marker>
              ))}
              {schedule.jobs.map(j => {
                if (!j.latitude || !j.longitude) return null;
                return (
                  <Marker key={j.id} position={[j.latitude, j.longitude]} icon={j.assigned_vehicle ? greenIcon : redIcon}>
                    <Popup><div style={{ color: '#333' }}><strong>{j.client}</strong> [{j.type}]<br/>Weight: {j.expected_weight_kg} kg<br/>{j.status.toUpperCase()}</div></Popup>
                  </Marker>
                )
              })}

              {/* Mock Playback Route (Trailing behind each truck) */}
              {playbackMode && displayMarkers.map(m => {
                // Generate a fake winding path behind the marker
                const path: [number, number][] = [];
                for(let i=10; i>=0; i--) {
                  path.push([m.latitude - (i * 0.01) + (Math.sin(i)*0.005), m.longitude - (i * 0.015) + (Math.cos(i)*0.005)]);
                }
                return <Polyline key={`path-${m.id}`} positions={path} color="var(--accent-cyan)" weight={4} opacity={0.6} dashArray="5, 10" />;
              })}
            </MapContainer>

            {playbackMode && (
              <div style={{ position: 'absolute', bottom: 30, left: '50%', transform: 'translateX(-50%)', zIndex: 1000, background: 'rgba(0,0,0,0.8)', padding: '16px 24px', borderRadius: 30, display: 'flex', gap: 16, alignItems: 'center', border: '1px solid var(--accent-cyan)' }}>
                <span style={{ fontSize: '0.85rem' }}>08:00</span>
                <input type="range" min="0" max="100" defaultValue="100" style={{ width: 300, cursor: 'pointer' }} />
                <span style={{ fontSize: '0.85rem' }}>Now</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Notifications Modal */}
      {showNotifications && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.85)', zIndex: 2000, display: 'flex', alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(5px)' }}>
          <div className="glass-panel" style={{ width: 450, maxHeight: '85vh', display: 'flex', flexDirection: 'column', padding: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '24px 24px 16px 24px', borderBottom: '1px solid var(--surface-border)', background: 'linear-gradient(to right, rgba(230, 57, 70, 0.2), transparent)' }}>
              <h2 style={{ margin: 0, color: 'white', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Bell size={24} color="var(--danger)" /> System Alerts
              </h2>
              <X style={{ cursor: 'pointer', color: 'var(--text-secondary)' }} onClick={() => setShowNotifications(false)} />
            </div>
            
            <div style={{ padding: '24px', overflowY: 'auto' }}>
              {alerts.length === 0 ? (
                <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic', textAlign: 'center' }}>No active alerts.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {alerts.map(a => (
                    <div key={a.id} style={{ background: 'rgba(230, 57, 70, 0.1)', border: '1px solid rgba(230, 57, 70, 0.3)', padding: '16px', borderRadius: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                        <span style={{ fontWeight: 'bold', color: 'white', fontSize: '0.9rem' }}>{a.type === 'idle' ? '⚠️ Idle Warning' : '📍 Auto-Complete'}</span>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{a.timestamp}</span>
                      </div>
                      <div style={{ fontSize: '0.95rem' }}>{a.message}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Client Registry Modal */}
      {showClientModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.85)', zIndex: 2000, display: 'flex', alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(5px)' }}>
          <div className="glass-panel" style={{ width: 550, maxHeight: '85vh', display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: 0 }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '24px 24px 16px 24px', borderBottom: '1px solid var(--surface-border)', background: 'linear-gradient(to right, rgba(69, 162, 158, 0.1), transparent)' }}>
              <div>
                <h2 style={{ margin: 0, color: 'white', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Users size={24} color="var(--accent-cyan)" />
                  Ehfaaz Client Registry
                </h2>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  Manage clients for AI auto-population.
                </div>
              </div>
              <X style={{ cursor: 'pointer', color: 'var(--text-secondary)' }} onClick={() => setShowClientModal(false)} />
            </div>
            
            <div style={{ padding: '24px', overflowY: 'auto', overflowX: 'hidden' }}>
              {/* Existing Clients List */}
              <div style={{ display: 'grid', gap: '12px', marginBottom: '32px' }}>
                {clients.map(c => (
                  <div key={c.id} style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.05)', padding: '16px', borderRadius: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', transition: 'all 0.2s' }}>
                    <div>
                      <div style={{ fontWeight: '600', color: 'white', fontSize: '1.05rem', marginBottom: '4px' }}>{c.name}</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', gap: '12px' }}>
                        <span><MapPin size={12} style={{display:'inline', marginBottom:'-2px'}}/> {c.location}</span>
                        <span className={c.default_job_type === 'Recova' ? 'job-type-recova' : 'job-type-reclaim'}>{c.default_job_type}</span>
                        <span><Clock size={12} style={{display:'inline', marginBottom:'-2px'}}/> {c.allocated_time}</span>
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '0.85rem', color: 'white' }}>{c.expected_bins}x {c.bin_size}</div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Capacity</div>
                    </div>
                  </div>
                ))}
                {clients.length === 0 && <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>No clients registered yet.</div>}
              </div>

              {/* Add New Client Form */}
              <form onSubmit={async (e) => {
                e.preventDefault();
                const formData = new FormData(e.currentTarget);
                try {
                  await axios.post(`${API_BASE}/clients`, {
                    name: formData.get('name'),
                    default_job_type: formData.get('type'),
                    location: formData.get('location'),
                    latitude: parseFloat(formData.get('latitude') as string) || null,
                    longitude: parseFloat(formData.get('longitude') as string) || null,
                    allocated_time: formData.get('allocated_time'),
                    expected_bins: parseInt(formData.get('expected_bins') as string) || null,
                    bin_size: formData.get('bin_size')
                  });
                  fetchClients();
                  (e.target as HTMLFormElement).reset();
                } catch (err) {
                  console.error(err);
                }
              }} style={{ background: 'rgba(255,255,255,0.02)', padding: '20px', borderRadius: '12px', border: '1px solid var(--surface-border)' }}>
                <h4 style={{ margin: '0 0 16px 0', color: 'white', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Plus size={18} color="var(--accent-cyan)" />
                  Register New Client
                </h4>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <input name="name" className="chat-input" placeholder="Client Name (e.g. Al Maya Supermarket)" required style={{ width: '100%', borderRadius: '8px', padding: '12px' }} />
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '12px' }}>
                    <input name="location" className="chat-input" placeholder="Area Name" required style={{ width: '100%', borderRadius: '8px', padding: '12px' }} />
                    <select name="type" className="chat-input" style={{ width: '100%', borderRadius: '8px', padding: '12px', appearance: 'none', background: 'rgba(0,0,0,0.5)', color: 'white', cursor: 'pointer' }}>
                      <option value="Recova">Recova</option>
                      <option value="ReClaim">ReClaim</option>
                    </select>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <input name="latitude" type="number" step="any" className="chat-input" placeholder="Latitude (e.g. 25.2)" style={{ width: '100%', borderRadius: '8px', padding: '12px' }} />
                    <input name="longitude" type="number" step="any" className="chat-input" placeholder="Longitude (e.g. 55.2)" style={{ width: '100%', borderRadius: '8px', padding: '12px' }} />
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 2fr', gap: '12px' }}>
                    <input name="expected_bins" type="number" className="chat-input" placeholder="Bins (e.g. 4)" style={{ width: '100%', borderRadius: '8px', padding: '12px' }} />
                    <input name="bin_size" className="chat-input" placeholder="Size (e.g. 240L)" style={{ width: '100%', borderRadius: '8px', padding: '12px' }} />
                    <input name="allocated_time" className="chat-input" placeholder="Time (e.g. 09:00-12:00)" style={{ width: '100%', borderRadius: '8px', padding: '12px' }} />
                  </div>

                  <button type="submit" className="btn btn-confirm" style={{ width: '100%', padding: '14px', marginTop: '8px', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', fontSize: '1rem' }}>
                    <Check size={18} />
                    Save Detailed Client
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
