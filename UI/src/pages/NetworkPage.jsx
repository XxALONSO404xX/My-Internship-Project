import React, { useState, useEffect, useRef } from 'react';
import { Box, Heading, SimpleGrid, Stat, StatLabel, StatNumber, StatHelpText, Text, Spinner, Flex, VStack, HStack, Icon, useColorModeValue, Table, Thead, Tbody, Tr, Th, Td, Select, CircularProgress, CircularProgressLabel, IconButton, Skeleton, Stack } from '@chakra-ui/react';
import { FiShield, FiWifiOff, FiUsers, FiTrendingUp, FiArrowUp, FiArrowDown } from 'react-icons/fi';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, PieChart, Pie, Cell, Legend, ResponsiveContainer, BarChart, Bar, AreaChart, Area } from 'recharts';
import { getNetworkSecuritySummary, getNetworkTopologyData, getNetworkTrafficStats } from '../services/network-service';

export default function NetworkPage() {
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [topology, setTopology] = useState(null);
  const [trafficStats, setTrafficStats] = useState(null);
  const [timeRange, setTimeRange] = useState('24h'); // 1h,24h,7d
  const [talkerSortAsc, setTalkerSortAsc] = useState(false);

  useEffect(() => {
    const start = Date.now();
    async function fetchData() {
      try {
        const [sum, topo, tStats] = await Promise.all([
          getNetworkSecuritySummary(),
          getNetworkTopologyData(),
          getNetworkTrafficStats(timeRange),
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
        const elapsed = Date.now() - start;
        const remain = 10000 - elapsed; // 10s minimum
        if (remain > 0) {
          setTimeout(() => setLoading(false), remain);
        } else {
          setLoading(false);
        }
      }
    }
    fetchData();
  }, [timeRange]);

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
    return (
      <Box p={8}>
        <Stack spacing={6}>
          <Skeleton height="40px" borderRadius="md" />
          <SimpleGrid columns={{base:1, md:3}} spacing={6}>
            {Array.from({length:3}).map((_,i)=>(<Skeleton key={i} height="120px" borderRadius="lg" />))}
          </SimpleGrid>
          <SimpleGrid columns={{base:1, lg:2}} spacing={6}>
            <Skeleton height="320px" borderRadius="lg" />
            <Skeleton height="320px" borderRadius="lg" />
          </SimpleGrid>
          <Skeleton height="140px" borderRadius="lg" />
          <Skeleton height="220px" borderRadius="lg" />
        </Stack>
      </Box>
    );
  }

  const evt = summary?.events_summary ?? { total_last_24h: 0, high_severity: 0, medium_severity: 0, low_severity: 0 };
  const ts = summary?.traffic_summary ?? { anomalous_traffic_percent: 0 };
  const totalPackets = evt.total_last_24h;
  const anomalousRate = ts.anomalous_traffic_percent;
  const series = trafficStats?.traffic_series ?? [];
  const protocolDist = trafficStats?.protocol_distribution ?? {};
  const talkers = trafficStats?.top_talkers ?? [];
  const sortedTalkers = [...talkers].sort((a,b)=>{
    const valA = a.bandwidth_usage || 0;
    const valB = b.bandwidth_usage || 0;
    return talkerSortAsc ? valA - valB : valB - valA;
  });
  const deviceCount = summary?.device_count ?? 0;
  const nodesArr = topology?.nodes ?? [];
  const edgesArr = topology?.edges ?? [];
  const gateways = nodesArr.filter(n=>n.type==='gateway').length;
  const sensors = nodesArr.filter(n=>n.type==='sensor').length;
  const lastUpdated = topology?.last_updated ?? '';

  return (
    <Box p={8}>
      <HStack mb={4} justify="space-between" flexWrap="wrap" gap={4}>
        <Heading bgGradient="linear(to-r, teal.400, blue.500)" bgClip="text">Network Security Overview</Heading>
        <Select size="sm" value={timeRange} onChange={(e)=>setTimeRange(e.target.value)} maxW="120px" bg={useColorModeValue('white','gray.700')}>
          <option value="1h">Last 1h</option>
          <option value="24h">Last 24h</option>
          <option value="7d">Last 7d</option>
        </Select>
      </HStack>
      <SimpleGrid columns={{ base:1, md:3 }} spacing={6} mb={6}>
        <Stat bg={cardBg} borderLeftWidth={4} borderLeftColor="purple.500" p={4} shadow="md" borderRadius="lg">
          <Icon as={FiShield} boxSize={6} color="purple.500" mb={2} />
          <StatLabel>Security Events</StatLabel>
          <HStack spacing={1} justify="center">
            <StatNumber>{totalPackets}</StatNumber>
          </HStack>
          <StatHelpText fontSize="xs" color="gray.500" title={`High: ${evt.high_severity}, Medium: ${evt.medium_severity}, Low: ${evt.low_severity}`}>Last 24h</StatHelpText>
        </Stat>
        <Stat bg={cardBg} p={4} shadow="md" borderRadius="lg" textAlign="center">
          <Text fontWeight="medium" mb={2}>Anomaly Rate</Text>
          <CircularProgress value={anomalousRate} size="90px" color="orange.400" thickness="8px">
            <CircularProgressLabel>{anomalousRate}%</CircularProgressLabel>
          </CircularProgress>
          <StatHelpText mt={1}>of traffic flagged</StatHelpText>
        </Stat>
        <Stat bg={cardBg} borderLeftWidth={4} borderLeftColor="green.500" p={4} shadow="md" borderRadius="lg">
          <Icon as={FiUsers} boxSize={6} color="green.500" mb={2} />
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

      <Box bgGradient="linear(to-r, teal.500, blue.500)" p={1} borderRadius="xl" mb={6}>
        <Box bg={cardBg} p={4} borderRadius="xl">
          <Text mb={2} fontWeight="medium">Network Topology Snapshot</Text>
          <SimpleGrid columns={{base:2, md:4}} spacing={4} textAlign="center">
            <Stat>
              <StatLabel>Nodes</StatLabel>
              <StatNumber>{nodesArr.length}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>Edges</StatLabel>
              <StatNumber>{edgesArr.length}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>Gateways</StatLabel>
              <StatNumber>{gateways}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>Sensors</StatLabel>
              <StatNumber>{sensors}</StatNumber>
            </Stat>
          </SimpleGrid>
          <Text fontSize="xs" mt={2} color="gray.500">Updated: {lastUpdated}</Text>
        </Box>
      </Box>

      <Box bg={cardBg} p={4} shadow="md" borderRadius="lg">
        <HStack mb={2} justify="space-between">
          <Text>Top Talkers</Text>
          <IconButton icon={talkerSortAsc? <FiArrowDown/>:<FiArrowUp/>} size="xs" aria-label="toggle sort" onClick={()=>setTalkerSortAsc(p=>!p)} />
        </HStack>
        <Table size="sm">
          <Thead><Tr><Th>Device</Th><Th>Sent</Th><Th>Received</Th><Th>Bandwidth</Th></Tr></Thead>
          <Tbody>
            {sortedTalkers.map(t=>(
              <Tr key={t.device_id} _hover={{ bg: useColorModeValue('gray.50','gray.700') }}>
                <Td>{t.device_name}</Td>
                <Td>{t.packets_sent}</Td>
                <Td>{t.packets_received}</Td>
                <Td fontWeight="bold">{t.bandwidth_usage}</Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>
    </Box>
  );
}
