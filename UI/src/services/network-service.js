import { apiRequest } from './api';

// Fetch simulated network traffic statistics
export async function getNetworkTrafficStats(time_period = '24h') {
  return apiRequest(`/api/v1/network-security/traffic-stats?time_period=${time_period}`, { method: 'GET' });
}

/**
 * Get overall network security summary (events, traffic, vulnerabilities, etc.)
 */
export async function getNetworkSecuritySummary() {
  return apiRequest('/api/v1/network-security/summary', { method: 'GET' });
}

/**
 * Get network topology data (nodes & edges)
 */
export async function getNetworkTopologyData() {
  try {
    return await apiRequest('/api/v1/network-security/network-topology', { method: 'GET' });
  } catch (err) {
    console.warn('[MockService] topology fetch failed, using mock data', err);
    // Generate mock nodes & edges
    const types = ['sensor', 'gateway', 'controller'];
    const nodes = Array.from({ length: 10 }).map((_, i) => ({
      id: `sim_${i+1}`,
      name: `Simulated Device ${i+1}`,
      type: types[Math.floor(Math.random()*types.length)],
      status: Math.random() < 0.8 ? 'online' : 'offline',
      ip_address: `192.168.${Math.floor(Math.random()*6)}.${Math.floor(Math.random()*254)+1}`
    }));
    nodes.push({ id: 'router_1', name: 'Main Router', type: 'router', status: 'online', ip_address: '192.168.0.1' });
    nodes.push({ id: 'internet', name: 'Internet', type: 'cloud', status: 'online', ip_address: 'external' });
    const gateways = nodes.filter(n => n.type==='gateway');
    const controllers = nodes.filter(n => n.type==='controller');
    const sensors = nodes.filter(n => n.type==='sensor');
    const edges = [];
    // Connect router to internet
    edges.push({ source: 'router_1', target: 'internet', type: 'wan', status: 'active', bandwidth: `${Math.floor(Math.random()*51)+50} Mbps`, protocol: 'TCP/IP' });
    // Gateways to router
    gateways.forEach(g => edges.push({ source: g.id, target: 'router_1', type: 'lan', status: g.status==='online'?'active':'inactive', bandwidth: `${Math.floor(Math.random()*91)+10} Mbps`, protocol: Math.random()<0.5?'Ethernet':'WiFi' }));
    // Controllers
    controllers.forEach(c => {
      const target = gateways.length && Math.random()<0.7 ? gateways[Math.floor(Math.random()*gateways.length)] : { id: 'router_1' };
      edges.push({ source: c.id, target: target.id, type: gateways.includes(target)?'local':'lan', status: c.status==='online'?'active':'inactive', bandwidth: `${Math.floor(Math.random()*10)+1} Mbps`, protocol: ['WiFi','Ethernet','Zigbee'][Math.floor(Math.random()*3)] });
    });
    // Sensors
    sensors.forEach(s => {
      const possible = controllers.length && Math.random()<0.6 ? controllers : gateways.length ? gateways : [{ id: 'router_1' }];
      const target = possible[Math.floor(Math.random()*possible.length)];
      const proto = possible===controllers ? ['Zigbee','Z-Wave','BLE'] : ['WiFi','Zigbee','Z-Wave'];
      edges.push({ source: s.id, target: target.id, type: 'sensor', status: s.status==='online'?'active':'inactive', bandwidth: `${Math.floor(Math.random()*901)+100} Kbps`, protocol: proto[Math.floor(Math.random()*proto.length)] });
    });
    // Other devices
    nodes.filter(n => !['router_1','internet'].includes(n.id) && !['gateway','controller','sensor'].includes(n.type)).forEach(d => {
      const target = Math.random()<0.3 && gateways.length ? gateways[Math.floor(Math.random()*gateways.length)] : { id: 'router_1' };
      edges.push({ source: d.id, target: target.id, type: 'device', status: d.status==='online'?'active':'inactive', bandwidth: `${Math.floor(Math.random()*50)+1} Mbps`, protocol: ['WiFi','Ethernet'][Math.floor(Math.random()*2)] });
    });
    return { nodes, edges, last_updated: new Date().toISOString() };
  }
}

/**
 * Fetch detailed security events
 */
export async function getSecurityEvents(time_period = '24h', limit = 100, severity) {
  const params = new URLSearchParams({ time_period, limit });
  if (severity) params.append('severity', severity);
  return apiRequest(`/api/v1/network-security/security-events?${params.toString()}`, { method: 'GET' });
}
