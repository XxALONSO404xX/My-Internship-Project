import React, { useState, useEffect } from 'react';
import { 
  Box, Heading, Text, SimpleGrid, Button, VStack, useToast, Icon, Flex, useColorModeValue, HStack, Input, Stat, StatLabel, StatNumber, StatHelpText, StatArrow
} from '@chakra-ui/react';
import { FiActivity, FiWifi, FiServer, FiAlertCircle, FiRefreshCw, FiCalendar } from 'react-icons/fi';
import { motion } from 'framer-motion';
import CountUp from 'react-countup';
import { w3cwebsocket as W3CWebSocket } from 'websocket';
import { getDevices } from '../services/device-service';
import { getNetworkTrafficStats } from '../services/network-service';
import { getActivitySummary, getActivitiesInRange } from '../services/activity-service';
import { 
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid 
} from 'recharts';
import { Sparklines, SparklinesLine, SparklinesSpots } from 'react-sparklines';
import WelcomeAnimation from '../components/WelcomeAnimation';

// Reusable Dashboard Card Component
const DashboardCard = ({ children, ...props }) => {
  const cardBg = useColorModeValue('white', 'gray.700');
  const cardBorder = useColorModeValue('gray.200', 'gray.600');
  return (
    <Box
      bg={cardBg}
      borderWidth="1px"
      borderColor={cardBorder}
      borderRadius="xl"
      p={{ base: 4, md: 6 }}
      boxShadow="lg"
      transition="all 0.3s ease-in-out"
      _hover={{ transform: 'translateY(-5px)', boxShadow: 'xl' }}
      {...props}
    >
      {children}
    </Box>
  );
};

// Reusable Stat Card
const StatCard = ({ icon, color, title, value, detail, sparklineData }) => {
  const iconColor = useColorModeValue(`${color}.600`, `${color}.200`);
  const iconBg = useColorModeValue(`${color}.100`, `${color}.800`);
  const titleColor = useColorModeValue('gray.500', 'whiteAlpha.900');
  const valueColor = useColorModeValue('gray.800', 'white');
  const sparklineColor = useColorModeValue(`${color}.500`, `${color}.300`);

  return (
    <DashboardCard>
      <HStack spacing={4}>
        <Flex bg={iconBg} borderRadius="full" p={3} align="center" justify="center">
          <Icon as={icon} boxSize={6} color={iconColor} />
        </Flex>
        <VStack align="start" spacing={0} w="full">
          <Text fontSize="sm" color={titleColor}>{title}</Text>
          <Text fontSize="2xl" fontWeight="bold" color={valueColor}>
            <CountUp end={value} duration={1.5} separator="," />
          </Text>
          {detail && <Text fontSize="xs" color={titleColor}>{detail}</Text>}
        </VStack>
        {sparklineData && (
          <Box ml="auto" w="100px" h="40px">
            <Sparklines data={sparklineData} limit={20} width={100} height={40}>
              <SparklinesLine color={sparklineColor} style={{ strokeWidth: 2 }} />
              <SparklinesSpots style={{ fill: sparklineColor }} />
            </Sparklines>
          </Box>
        )}
      </HStack>
    </DashboardCard>
  );
};

const CustomTooltip = ({ active, payload, label, bg, color, borderColor }) => {
  if (active && payload && payload.length) {
    return (
      <Box
        bg={bg}
        p={3}
        borderRadius="lg"
        boxShadow="xl"
        border="1px solid"
        borderColor={borderColor}
      >
        <Text fontWeight="bold" color={color}>{label}</Text>
        <Text fontSize="sm" color={color}>{`Count: ${payload[0].value}`}</Text>
      </Box>
    );
  }

  return null;
};

export default function Dashboard() {
  const toast = useToast();
  const tooltipBg = useColorModeValue('white', 'gray.800');
  const tooltipColor = useColorModeValue('gray.800', 'white');
  const tooltipBorder = useColorModeValue('gray.200', 'gray.700');
  const [deviceStats, setDeviceStats] = useState({ online: 0, offline: 0 });
  const [networkStats, setNetworkStats] = useState({ incoming: 0, outgoing: 0 });
  const [activitySummary, setActivitySummary] = useState({ total: 0, actions: 0 });
  const [trend, setTrend] = useState([]);
  const [startDate, setStartDate] = useState('2025-04-12');
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [loading, setLoading] = useState(false);

  const [showWelcome, setShowWelcome] = useState(() => sessionStorage.getItem('welcomeShown') !== 'true');

  // Hoist hook calls out of JSX to preserve hook order
  const boxBg = useColorModeValue('gray.50', 'gray.800');
  const h2Color = useColorModeValue('gray.700', 'white');
  const gridStroke = useColorModeValue('gray.200', 'gray.700');
  const areaStroke = useColorModeValue('purple.500', 'purple.300');
  const headingGradient = useColorModeValue('linear(to-r, purple.600, blue.500)', 'linear(to-r, purple.300, blue.400)');
  const subtleText = useColorModeValue('gray.600', 'white');
  const chartColor1 = useColorModeValue('purple.500', 'purple.300');
  const chartColor2 = useColorModeValue('blue.500', 'blue.300');

  useEffect(() => {
    if (!showWelcome) {
      handleRefresh();
    }
  }, [showWelcome]);

  const fetchDeviceStats = async () => {
    try {
      const devices = await getDevices();
      const online = devices.filter(d => d.is_online).length;
      setDeviceStats({ online, offline: devices.length - online });
    } catch (err) { toast({ title: `Error fetching devices: ${err.message}`, status: 'error' }); }
  };

  const fetchActivitySummary = async () => {
    try {
      const data = await getActivitySummary(24);
      setActivitySummary({ total: data.total_activities, actions: data.counts.by_type.user_action || 0 });
    } catch (err) { toast({ title: `Error fetching activity: ${err.message}`, status: 'error' }); }
  };

  const fetchTrend = async (start = startDate, end = endDate) => {
    let s = new Date(start), e = new Date(end);
    if (s > e) [s, e] = [e, s];
    try {
      const events = await getActivitiesInRange(`${s.toISOString().split('T')[0]}T00:00:00Z`, `${e.toISOString().split('T')[0]}T23:59:59Z`);
      const counts = events.reduce((acc, event) => {
        const date = event.timestamp.split('T')[0];
        acc[date] = (acc[date] || 0) + 1;
        return acc;
      }, {});
      // Build full date range with zero defaults
      const dateList = [];
      for (let dt = new Date(s); dt <= e; dt.setDate(dt.getDate() + 1)) {
        dateList.push(dt.toISOString().split('T')[0]);
      }
      const formatted = dateList.map(date => ({ date, count: counts[date] || 0 }));
      setTrend(formatted);
    } catch (err) {
      toast({ title: `Failed to fetch activity trend: ${err.message}`, status: 'error' });
    }
  };

  const handleRefresh = () => {
    setLoading(true);
    Promise.all([fetchDeviceStats(), fetchActivitySummary(), fetchTrend()]).finally(() => setLoading(false));
  };

  const handleDateChange = () => {
    fetchTrend(startDate, endDate);
  };

  const handleWelcomeComplete = () => {
    sessionStorage.setItem('welcomeShown', 'true');
    setShowWelcome(false);
  };

  if (showWelcome) {
    return <WelcomeAnimation onComplete={handleWelcomeComplete} />;
  }

  // Generate 7 equispaced date ticks (including first and last)
  const tickCount = 7;
  const interval = trend.length > 1 ? Math.ceil((trend.length - 1) / (tickCount - 1)) : 1;
  const ticks = trend
    .filter((_, i) => i === 0 || i === trend.length - 1 || i % interval === 0)
    .map(d => d.date);

  return (
    <Box p={{ base: 4, md: 8 }} bg={boxBg} minH="100vh">
      <Flex justify="space-between" align="center" mb={8}>
        <VStack align="start">
          <Heading as="h1" size="xl" bgGradient={headingGradient} bgClip="text">Dashboard</Heading>
          <Text color={subtleText}>Real-time overview of your IoT network.</Text>
        </VStack>
        <Button leftIcon={<FiRefreshCw />} onClick={handleRefresh} isLoading={loading} variant="ghost" colorScheme="blue">Refresh</Button>
      </Flex>

      <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6} mb={8}>
        <StatCard icon={FiActivity} color="purple" title="Total Activities (24h)" value={activitySummary.total} detail={`User Actions: ${activitySummary.actions}`} />
        <StatCard icon={FiServer} color="blue" title="Devices Online" value={deviceStats.online} detail={`Offline: ${deviceStats.offline}`} />
        <StatCard icon={FiAlertCircle} color="orange" title="Security Alerts" value={0} detail="All systems secure" />
      </SimpleGrid>

      <DashboardCard>
        <Flex direction={{ base: 'column', md: 'row' }} justify="space-between" align="center" mb={6}>
          <Heading as="h2" size="lg" color={h2Color}>Activity Trend</Heading>
          <HStack spacing={4} mt={{ base: 4, md: 0 }}>
            <HStack>
              <Icon as={FiCalendar} color={subtleText} />
              <Input type="date" value={startDate} size="sm" max={endDate} onChange={e => setStartDate(e.target.value)} />
            </HStack>
            <HStack>
              <Icon as={FiCalendar} color={subtleText} />
              <Input type="date" value={endDate} size="sm" min={startDate} max={new Date().toISOString().split('T')[0]} onChange={e => setEndDate(e.target.value)} />
            </HStack>
            <Button size="sm" onClick={handleDateChange} colorScheme="blue">Update</Button>
          </HStack>
        </Flex>
        <Box height={{ base: '300px', md: '400px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={trend} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={chartColor1} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={chartColor2} stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
              <XAxis
                dataKey="date"
                ticks={ticks}
                stroke={subtleText}
                fontSize="sm"
                tickFormatter={str => str.slice(5).replace('-', '/')}
              />
              <YAxis stroke={subtleText} fontSize="sm" />
              <Tooltip cursor={{ fill: 'transparent' }} content={<CustomTooltip bg={tooltipBg} color={tooltipColor} borderColor={tooltipBorder} />} />
              <Area type="monotone" dataKey="count" stroke={areaStroke} fillOpacity={1} fill="url(#chartGradient)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </Box>
      </DashboardCard>
    </Box>
  );
}
