import { apiRequest } from './api';

// ------------------
// Helper utilities
// ------------------

// Seed changes once per day (UTC) for deterministic-but-fresh mocks
const DAY_SEED = Math.floor(Date.now() / (1000 * 60 * 60 * 24));

export function createSeededRandom(offset = 0) {
  let val = ((DAY_SEED + offset) ^ 0x1badf00d) & 0xffffffff;
  return () => {
    // Linear-congruential generator (LCG)
    val = (val * 1664525 + 1013904223) & 0xffffffff;
    return (val >>> 0) / 0xffffffff;
  };
}

function readCachedJSON(key) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
}

function writeCachedJSON(key, data) {
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch (_) {/* quota errors ignored */}
}

// Fetch simulated network traffic statistics
const TRAFFIC_CACHE_PREFIX = 'iot_platform_traffic_cache_v1_';

export async function getNetworkTrafficStats(time_period = '24h') {
  try {
    return await apiRequest(`/api/v1/network-security/traffic-stats?time_period=${time_period}`, { method: 'GET' });
  } catch (err) {
    console.warn('[NetworkService] traffic-stats fetch failed, using mock', err?.message || err);
  }

  // Try cache
  const key = `${TRAFFIC_CACHE_PREFIX}${time_period}`;
  const cached = readCachedJSON(key);
  if (cached) return cached;

  // Generate deterministic mock series based on seed + time_range
  const rand = createSeededRandom(time_period==='1h'?1:time_period==='24h'?2:3);

  const now = Date.now();
  const series = [];
  const addPoint = (ts) => series.push({ timestamp: new Date(ts).toISOString(), volume: Math.floor(rand()*900)+100 });
  if (time_period === '1h') {
    for (let i=12; i>=0; i--) addPoint(now - i*5*60*1000);
  } else if (time_period === '24h') {
    for (let i=24; i>=0; i--) addPoint(now - i*60*60*1000);
  } else { // 7d
    for (let i=7; i>=0; i--) addPoint(now - i*24*60*60*1000);
  }

  // Protocol distribution
  const protos = ['HTTP','MQTT','DNS','CoAP','Other'];
  const protocol_distribution = {};
  let remaining = 100;
  protos.forEach((p, idx) => {
    if (idx === protos.length-1) protocol_distribution[p] = remaining;
    else {
      const val = Math.floor(rand()*remaining*0.6);
      protocol_distribution[p] = val;
      remaining -= val;
    }
  });

  // Top talkers
  const top_talkers = Array.from({ length: 5 }).map((_, i) => {
    const bw = Math.floor(rand()*90)+10; // MB
    return {
      device_id: `dev_${i+1}`,
      device_name: `Device ${i+1}`,
      packets_sent: Math.floor(rand()*10000)+1000,
      packets_received: Math.floor(rand()*10000)+1000,
      bandwidth_usage: `${bw} MB`
    };
  });

  const result = { traffic_series: series, protocol_distribution, top_talkers };
  writeCachedJSON(key, result);
  return result;
}

/**
 * Get overall network security summary (events, traffic, vulnerabilities, etc.)
 */
const SUMMARY_CACHE_KEY = 'iot_platform_net_summary_v1';
export async function getNetworkSecuritySummary() {
  try {
    return await apiRequest('/api/v1/network-security/summary', { method: 'GET' });
  } catch (err) {
    console.warn('[NetworkService] summary fetch failed, using mock', err?.message || err);
  }

  const cachedSum = readCachedJSON(SUMMARY_CACHE_KEY);
  if (cachedSum) return cachedSum;

  const seed = Math.floor(Date.now() / (1000*60*60*24));
  const rand = createSeededRandom(5);

  const total = Math.floor(rand()*200)+50;
  const high = Math.floor(total*rand()*0.4);
  const medium = Math.floor((total-high)*rand()*0.6);
  const low = total - high - medium;

  const summary = {
    events_summary: {
      total_last_24h: total,
      high_severity: high,
      medium_severity: medium,
      low_severity: low,
    },
    traffic_summary: {
      anomalous_traffic_percent: Math.floor(rand()*15)+1
    },
    device_count: Math.floor(rand()*30)+10
  };
  writeCachedJSON(SUMMARY_CACHE_KEY, summary);
  return summary;
}

/**
 * Get network topology data (nodes & edges)
 */
// Cache key for storing mock topology in localStorage
const TOPOLOGY_CACHE_KEY = 'iot_platform_topology_cache_v1';
let topologyCache = null; // in-memory for same session

export async function getNetworkTopologyData() {
  // 1. Try backend API first
  try {
    const apiTopo = await apiRequest('/api/v1/network-security/network-topology', { method: 'GET' });
    return apiTopo;
  } catch (err) {
    console.warn('[NetworkService] topology fetch failed, falling back to mock data', err?.message || err);
  }

  // 2. Return in-memory cached topology if already generated during this session
  if (topologyCache) return topologyCache;

  // 3. Attempt to load previously generated mock from localStorage so page reloads remain consistent
  const cachedTopo = readCachedJSON(TOPOLOGY_CACHE_KEY);
  if (cachedTopo) {
    topologyCache = cachedTopo;
    return topologyCache;
  }

  // 4. Generate deterministic mock data using a seeded random based on the current day
  const rand = createSeededRandom(9);

  const types = ['sensor', 'gateway', 'controller'];
  const nodes = Array.from({ length: 10 }).map((_, i) => ({
    id: `sim_${i+1}`,
    name: `Simulated Device ${i+1}`,
    type: types[Math.floor(rand()*types.length)],
    status: rand() < 0.8 ? 'online' : 'offline',
    ip_address: `192.168.${Math.floor(rand()*6)}.${Math.floor(rand()*254)+1}`
  }));
  nodes.push({ id: 'router_1', name: 'Main Router', type: 'router', status: 'online', ip_address: '192.168.0.1' });
  nodes.push({ id: 'internet', name: 'Internet', type: 'cloud', status: 'online', ip_address: 'external' });

  const gateways = nodes.filter(n => n.type==='gateway');
  const controllers = nodes.filter(n => n.type==='controller');
  const sensors = nodes.filter(n => n.type==='sensor');
  const edges = [];

  const randBandwidth = (min, max, unit='Mbps') => `${Math.floor(rand()*(max-min+1))+min} ${unit}`;

  // Connect router to internet
  edges.push({ source: 'router_1', target: 'internet', type: 'wan', status: 'active', bandwidth: randBandwidth(50,100), protocol: 'TCP/IP' });
  // Gateways to router
  gateways.forEach(g => edges.push({ source: g.id, target: 'router_1', type: 'lan', status: g.status==='online'?'active':'inactive', bandwidth: randBandwidth(10,100), protocol: rand()<0.5?'Ethernet':'WiFi' }));
  // Controllers
  controllers.forEach(c => {
    const target = gateways.length && rand()<0.7 ? gateways[Math.floor(rand()*gateways.length)] : { id: 'router_1' };
    edges.push({ source: c.id, target: target.id, type: gateways.includes(target)?'local':'lan', status: c.status==='online'?'active':'inactive', bandwidth: randBandwidth(1,10), protocol: ['WiFi','Ethernet','Zigbee'][Math.floor(rand()*3)] });
  });
  // Sensors
  sensors.forEach(s => {
    const possible = controllers.length && rand()<0.6 ? controllers : gateways.length ? gateways : [{ id: 'router_1' }];
    const target = possible[Math.floor(rand()*possible.length)];
    const protoArr = possible===controllers ? ['Zigbee','Z-Wave','BLE'] : ['WiFi','Zigbee','Z-Wave'];
    edges.push({ source: s.id, target: target.id, type: 'sensor', status: s.status==='online'?'active':'inactive', bandwidth: randBandwidth(100,1000,'Kbps'), protocol: protoArr[Math.floor(rand()*protoArr.length)] });
  });

  topologyCache = { nodes, edges, last_updated: new Date().toISOString(), mock: true };

  // store
  writeCachedJSON(TOPOLOGY_CACHE_KEY, topologyCache);
  
  return topologyCache;
}

/**
 * Fetch detailed security events
 */
export async function getSecurityEvents(time_period = '24h', limit = 100, severity) {
  const params = new URLSearchParams({ time_period, limit });
  if (severity) params.append('severity', severity);
  return apiRequest(`/api/v1/network-security/security-events?${params.toString()}`, { method: 'GET' });
}
