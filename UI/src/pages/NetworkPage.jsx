import React, { useState, useEffect } from 'react';
import { Box, Heading, SimpleGrid, Stat, StatLabel, StatNumber, StatHelpText, StatIcon, Text, Spinner, Flex, VStack, HStack, useColorModeValue, Table, Thead, Tbody, Tr, Th, Td } from '@chakra-ui/react';
import { FiAlertTriangle, FiAlertCircle, FiUsers } from 'react-icons/fi';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, PieChart, Pie, Cell, Legend, ResponsiveContainer, BarChart, Bar, AreaChart, Area } from 'recharts';
import { getNetworkSecuritySummary, getNetworkTopologyData, getNetworkTrafficStats } from '../services/network-service';

export default function NetworkPage() {
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [topology, setTopology] = useState(null);
  const [trafficStats, setTrafficStats] = useState(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [sum, topo, tStats] = await Promise.all([
          getNetworkSecuritySummary(),
          getNetworkTopologyData(),
          getNetworkTrafficStats('24h'),
        ]);
        setSummary(sum);
        setTopology(topo);
        setTrafficStats(tStats);
      } catch (err) {
        console.error('NetworkPage fetch error:', err);
        // Fallback defaults on error
        setSummary({});
        setTopology({});
        setTrafficStats({});
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const cardBg = useColorModeValue('white', 'gray.700');
  const lineColor = useColorModeValue('#8884d8', '#82ca9d');
  const gridColor = useColorModeValue('rgba(0,0,0,0.1)', 'rgba(255,255,255,0.1)');
  const pieColors = [
    useColorModeValue('#0088FE','#0056b3'),
    useColorModeValue('#00C49F','#007f6f'),
    useColorModeValue('#FFBB28','#b38f21'),
    useColorModeValue('#FF8042','#b35c21')
  ];

  if (loading) {
    return <Flex justify="center" p={8}><Spinner size="lg" /></Flex>;
  }

  const evt = summary?.events_summary ?? { total_last_24h: 0, high_severity: 0, medium_severity: 0, low_severity: 0 };
  const ts = summary?.traffic_summary ?? { anomalous_traffic_percent: 0 };
  const totalPackets = evt.total_last_24h;
  const anomalousRate = ts.anomalous_traffic_percent;
  const series = trafficStats?.traffic_series ?? [];
  const protocolDist = trafficStats?.protocol_distribution ?? {};
  const talkers = trafficStats?.top_talkers ?? [];
  const deviceCount = summary?.device_count ?? 0;
  const nodesArr = topology?.nodes ?? [];
  const edgesArr = topology?.edges ?? [];
  const lastUpdated = topology?.last_updated ?? '';

  return (
    <Box p={8}>
      <Heading mb={4}>Network Security Overview</Heading>
      <SimpleGrid columns={{ base:1, md:3 }} spacing={6} mb={6}>
        <Stat bg={cardBg} borderLeftWidth={4} borderLeftColor="red.500" p={4} shadow="md" borderRadius="lg">
          <StatIcon as={FiAlertTriangle} boxSize={6} color="red.500" mb={2} />
          <StatLabel>Intrusion Attempts</StatLabel>
          <StatNumber>{totalPackets}</StatNumber>
          <StatHelpText>Last 24h</StatHelpText>
        </Stat>
        <Stat bg={cardBg} borderLeftWidth={4} borderLeftColor="orange.500" p={4} shadow="md" borderRadius="lg">
          <StatIcon as={FiAlertCircle} boxSize={6} color="orange.500" mb={2} />
          <StatLabel>Traffic Anomalies</StatLabel>
          <StatNumber>{anomalousRate}%</StatNumber>
          <StatHelpText>Anomaly Rate</StatHelpText>
        </Stat>
        <Stat bg={cardBg} borderLeftWidth={4} borderLeftColor="green.500" p={4} shadow="md" borderRadius="lg">
          <StatIcon as={FiUsers} boxSize={6} color="green.500" mb={2} />
          <StatLabel>Connected Nodes</StatLabel>
          <StatNumber>{deviceCount}</StatNumber>
          <StatHelpText>Online</StatHelpText>
        </Stat>
      </SimpleGrid>

      <SimpleGrid columns={{ base:1, lg:2 }} spacing={6} mb={6}>
        <Box bg={cardBg} p={4} shadow="md" borderRadius="lg" height="300px">
          <Text mb={2}>Traffic Over Time</Text>
          <ResponsiveContainer width="100%" height="90%">
            <AreaChart data={series} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="trafficGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={lineColor} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={lineColor} stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="timestamp" tickFormatter={str => str.split('T')[1].slice(0,5)} />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="volume" stroke={lineColor} fill="url(#trafficGradient)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </Box>
        <Box bg={cardBg} p={4} shadow="md" borderRadius="lg" height="300px">
          <Text mb={2}>Protocol Distribution</Text>
          <ResponsiveContainer width="100%" height="90%">
            <PieChart>
              <Pie
                data={Object.entries(protocolDist).map(([name,value])=>({ name, value }))}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={2}
                startAngle={90}
                endAngle={-270}
                stroke="#fff"
                strokeWidth={2}
                isAnimationActive={true}
                animationBegin={300}
                animationDuration={800}
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                {Object.keys(protocolDist).map((key,i) => (
                  <Cell key={key} fill={pieColors[i % pieColors.length]} />
                ))}
              </Pie>
              <Legend verticalAlign="bottom" height={36} />
              <Tooltip formatter={(value,name) => [`${value}`, name]} />
            </PieChart>
          </ResponsiveContainer>
        </Box>
      </SimpleGrid>

      <Box bg={cardBg} p={4} shadow="md" borderRadius="lg" mb={6}>
        <Text mb={2}>Network Topology</Text>
        <Text>Nodes: {nodesArr.length}, Edges: {edgesArr.length}</Text>
        <Text fontSize="sm" color="gray.500">Last updated: {lastUpdated}</Text>
      </Box>

      <Box bg={cardBg} p={4} shadow="md" borderRadius="lg">
        <Text mb={2}>Top Talkers</Text>
        <Table size="sm">
          <Thead><Tr><Th>Device</Th><Th>Sent</Th><Th>Received</Th><Th>Bandwidth</Th></Tr></Thead>
          <Tbody>
            {talkers.map(t=>(
              <Tr key={t.device_id}><Td>{t.device_name}</Td><Td>{t.packets_sent}</Td><Td>{t.packets_received}</Td><Td>{t.bandwidth_usage}</Td></Tr>
            ))}
          </Tbody>
        </Table>
      </Box>
    </Box>
  );
}
