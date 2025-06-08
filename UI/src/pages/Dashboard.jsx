import React, { useState, useEffect } from 'react';
import { 
  Box, Heading, Stat, StatLabel, StatNumber, Text, SimpleGrid, Stack,
  Button, VStack, useToast, Icon, Flex, useColorModeValue, HStack, Badge, Input, Progress,
  StatGroup, StatArrow, StatHelpText
} from '@chakra-ui/react';
import { FiSearch, FiActivity, FiWifi, FiServer, FiAlertCircle, FiRefreshCw, FiTrendingUp } from 'react-icons/fi';
import { motion } from 'framer-motion';
import CountUp from 'react-countup';
import { w3cwebsocket as W3CWebSocket } from 'websocket';
import { 
  getDevices 
} from '../services/device-service';
import { 
  getNetworkTrafficStats 
} from '../services/network-service';
import { 
  getActivitySummary, 
  getActivitiesInRange 
} from '../services/activity-service';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid 
} from 'recharts';
import { Sparklines, SparklinesLine } from 'react-sparklines';
import { useNavigate } from 'react-router-dom';
import WelcomeAnimation from '../components/WelcomeAnimation';

// Motion-enhanced Stat component
const MotionStat = motion(Stat);
// Motion-enhanced Icon for scanning animation
const MotionIcon = motion(Icon);

// Scan animation parameters
const SCAN_INTERVAL = 20; // ms
const SCAN_STEP_MIN = 3;
const SCAN_STEP_MAX = 7;

export default function Dashboard() {
  const toast = useToast();
  const navigate = useNavigate();
  const [deviceStats, setDeviceStats] = useState({ online: 0, offline: 0, devices: [] });
  const [networkStats, setNetworkStats] = useState(null);
  const [activitySummary, setActivitySummary] = useState({ total: 0, actions: 0 });
  const [trend, setTrend] = useState([]);
  const [startDate, setStartDate] = useState('2025-04-07');
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [initialScanDone, setInitialScanDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [socket, setSocket] = useState(null);
  const [liveTraffic, setLiveTraffic] = useState({ 
    incoming: 0, 
    outgoing: 0, 
    total: 0,
    connections: 0
  });
  const [isConnected, setIsConnected] = useState(false);
  const [trafficHistory, setTrafficHistory] = useState({
    incoming: [],
    outgoing: [],
    total: []
  });
  const [isScanning, setIsScanning] = useState(false);
  const [showWelcome, setShowWelcome] = useState(() => sessionStorage.getItem('welcomeShown') !== 'true');

  // After welcome completes (or on direct navigation), load dashboard data
  useEffect(() => {
    if (!showWelcome) {
      fetchDeviceStats();
      fetchNetworkStats();
      fetchActivitySummary();
      fetchTrend();
    }
  }, [showWelcome]);

  // Track expanded device cards
  const [expandedIds, setExpandedIds] = useState(new Set());
  const toggleExpand = (id) => {
    setExpandedIds(prev => {
      const s = new Set(prev);
      s.has(id) ? s.delete(id) : s.add(id);
      return s;
    });
  };

  // Theme-aware palette using authTheme tokens
  const cardBg = useColorModeValue('white', 'gray.800');
  const cardBorder = useColorModeValue('primary.100', 'primary.700');
  const headingGradient = useColorModeValue(
    'linear(to-r, primary.500, secondary.500)',
    'linear(to-r, primary.300, secondary.400)'
  );
  const iconPrimary = useColorModeValue('primary.600', 'primary.400');
  const iconSecondary = useColorModeValue('secondary.600', 'secondary.400');
  const subtleText = useColorModeValue('gray.600', 'gray.400');

  // Load welcome animation, then fetch data
  const handleWelcomeComplete = () => {
    sessionStorage.setItem('welcomeShown', 'true');
    setShowWelcome(false);
    // Initial data load after welcome animation
    fetchDeviceStats();
    fetchNetworkStats();
    fetchActivitySummary();
    fetchTrend();
  };

  // Mock data for development
  const mockTrafficData = {
    incoming: 1024 * 5,
    outgoing: 1024 * 2,
    total: 1024 * 7,
    connections: 5
  };

  // Generate mock traffic history
  const generateMockHistory = () => {
    const historyLength = 20;
    return {
      incoming: Array(historyLength).fill(0).map((_, i) => 
        Math.floor(Math.random() * 1000) + 500
      ),
      outgoing: Array(historyLength).fill(0).map((_, i) => 
        Math.floor(Math.random() * 500) + 100
      ),
      total: Array(historyLength).fill(0).map((_, i) => 
        Math.floor(Math.random() * 1500) + 600
      )
    };
  };

  useEffect(() => {
    // Set initial mock data
    setLiveTraffic(mockTrafficData);
    setTrafficHistory(generateMockHistory());
    
    // Only connect to WebSocket in production or when explicitly enabled
    if (process.env.NODE_ENV === 'production' || localStorage.getItem('enableWebSocket') === 'true') {
      const ws = new W3CWebSocket('ws://localhost:8000/ws/traffic');
      
      ws.onopen = () => {
        console.log('WebSocket Connected');
        setIsConnected(true);
        setSocket(ws);
      };

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          setLiveTraffic(prev => {
            const newState = {
              incoming: prev.incoming + (data.incoming || 0),
              outgoing: prev.outgoing + (data.outgoing || 0),
              total: prev.total + (data.total || 0),
              connections: data.connections || prev.connections
            };
            setTrafficHistory(prevHistory => ({
              incoming: [...prevHistory.incoming.slice(-19), newState.incoming],
              outgoing: [...prevHistory.outgoing.slice(-19), newState.outgoing],
              total: [...prevHistory.total.slice(-19), newState.total]
            }));
            return newState;
          });
        } catch (err) {
          console.error('Error processing WebSocket message:', err);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket Disconnected');
        setIsConnected(false);
        setSocket(null);
      };

      ws.onerror = (error) => {
        console.error('WebSocket Error:', error);
      };

      setSocket(ws);
      return () => ws.close();
    } else {
      console.log('Running with mock data. To enable WebSocket, set localStorage.enableWebSocket = true');
    }
  }, []);

  const cardAnimation = {
    hover: { y: -5, boxShadow: '0 10px 25px rgba(0, 0, 0, 0.1)' },
    tap: { y: 0 }
  };

  // Generate realistic sensor metadata for each device
  const generateMetadata = () => ({
    temperature: (Math.random() * 20 + 20).toFixed(1) + ' °C',
    humidity: (Math.random() * 50 + 30).toFixed(1) + ' %',
    battery: Math.floor(Math.random() * 100) + ' %',
  });

  const fetchDeviceStats = async () => {
    try {
      const devices = await getDevices();
      // Enrich devices with generated metadata
      const enriched = devices.map(d => ({ ...d, metadata: generateMetadata() }));
      const online = enriched.filter(d => d.is_online).length;
      setDeviceStats({ online, offline: enriched.length - online, devices: enriched });
    } catch (err) { toast({ title: err.message, status: 'error' }); }
  };

  const fetchNetworkStats = async () => {
    try {
      const data = await getNetworkTrafficStats('24h');
      setNetworkStats(data);
    } catch (err) { toast({ title: err.message, status: 'error' }); }
  };

  const fetchActivitySummary = async () => {
    try {
      const data = await getActivitySummary(24);
      setActivitySummary({ total: data.total_activities, actions: data.counts.by_type.user_action || 0 });
    } catch (err) { toast({ title: err.message, status: 'error' }); }
  };

  const fetchTrend = async (start = startDate, end = endDate) => {
    // Ensure start<=end by swapping if needed
    let s = new Date(start), e = new Date(end);
    if (s > e) [s, e] = [e, s];
    try {
      const events = await getActivitiesInRange(`${s.toISOString().split('T')[0]}T00:00:00Z`, `${e.toISOString().split('T')[0]}T23:59:59Z`);
      // Count events by date
      const counts = {};
      events.forEach(evt => {
        const dateKey = evt.timestamp.split('T')[0];
        counts[dateKey] = (counts[dateKey] || 0) + 1;
      });
      // Build full date range with zeros
      const trendData = [];
      for (let d = new Date(s); d <= e; d.setDate(d.getDate() + 1)) {
        const key = d.toISOString().split('T')[0];
        trendData.push({ date: key, count: counts[key] || 0 });
      }
      setTrend(trendData);
    } catch (err) {
      toast({ title: err.message, status: 'error' });
    }
  };

  const handleRefresh = async () => {
    setLoading(true);
    try {
      await Promise.all([fetchDeviceStats(), fetchActivitySummary(), fetchTrend()]);
      toast({
        title: "Data Refreshed",
        status: "success",
        duration: 2000,
        isClosable: true,
        position: "top-right"
      });
    } catch (err) {
      toast({ 
        title: "Refresh Failed", 
        description: err.message, 
        status: "error",
        position: "top-right"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleInitialScan = () => {
    setIsScanning(true);
    let progress = 0;
    const interval = setInterval(() => {
      const step = Math.floor(Math.random() * (SCAN_STEP_MAX - SCAN_STEP_MIN + 1)) + SCAN_STEP_MIN;
      progress = Math.min(progress + step, 100);
      setScanProgress(progress);
      if (progress >= 100) {
        clearInterval(interval);
        localStorage.setItem('initialScanDone', 'true');
        setInitialScanDone(true);
        setIsScanning(false);
        // After initial scan, load dashboard data
        fetchDeviceStats();
        fetchActivitySummary();
        fetchTrend();
      }
    }, SCAN_INTERVAL);
  };

  useEffect(() => {
    if (initialScanDone) {
      fetchTrend();
    }
  }, [startDate, endDate, initialScanDone]);

  // Show welcome animation on login
  if (showWelcome) {
    return <WelcomeAnimation onComplete={handleWelcomeComplete} />;
  }

  return (
    <Box p={6} maxW="8xl" mx="auto">
      {/* Enhanced Header */}
      <Flex justify="space-between" align="center" mb={8}>
        <Heading 
          size="xl" 
          fontWeight="800" 
          letterSpacing="-0.5px"
          bgGradient="linear(to-r, blue.500, purple.500)"
          bgClip="text"
        >
          Device Dashboard
        </Heading>
        <Button
          colorScheme="primary"
          rightIcon={<Icon as={FiRefreshCw} />}
          borderRadius="full"
          boxShadow="md"
          _hover={{
            transform: "translateY(-2px)",
            boxShadow: "lg"
          }}
          isLoading={loading}
          onClick={handleRefresh}
        >
          Refresh Data
        </Button>
      </Flex>

      {/* Stats Cards with visual upgrade */}
      <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6} mb={8}>
        {/* Activities Card */}
        <Stat 
          p={6}
          borderRadius="xl"
          bg="whiteAlpha.50"
          border="1px solid"
          borderColor="whiteAlpha.200"
          boxShadow="0 4px 24px rgba(0, 0, 0, 0.1)"
          _hover={{
            transform: 'translateY(-2px)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.15)'
          }}
          transition="all 0.3s ease"
        >
          <Flex align="center" mb={2}>
            <Icon as={FiActivity} boxSize={6} color={iconSecondary} mr={2} />
            <StatLabel>Activities</StatLabel>
          </Flex>
          <StatNumber fontSize="3xl">{activitySummary.total}</StatNumber>
          <StatHelpText>
            Actions: {activitySummary.actions}
          </StatHelpText>
        </Stat>

        {/* Devices Online Card */}
        <Stat
          p={6}
          borderRadius="xl"
          bg="whiteAlpha.50"
          border="1px solid"
          borderColor="whiteAlpha.200"
          boxShadow="0 4px 24px rgba(0, 0, 0, 0.1)"
          _hover={{
            transform: 'translateY(-2px)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.15)'
          }}
          transition="all 0.3s ease"
        >
          <Flex align="center" mb={2}>
            <Icon as={FiServer} boxSize={6} color={iconPrimary} mr={2} />
            <StatLabel>Devices Online</StatLabel>
          </Flex>
          <StatNumber fontSize="3xl">{deviceStats.online}</StatNumber>
          <StatHelpText>
            Offline: {deviceStats.offline}
          </StatHelpText>
        </Stat>

        {/* Security Alerts Card */}
        <Stat
          p={6}
          borderRadius="xl"
          bg="whiteAlpha.50"
          border="1px solid"
          borderColor="whiteAlpha.200"
          boxShadow="0 4px 24px rgba(0, 0, 0, 0.1)"
          _hover={{
            transform: 'translateY(-2px)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.15)'
          }}
          transition="all 0.3s ease"
        >
          <Flex align="center" mb={2}>
            <Icon as={FiAlertCircle} boxSize={6} color={iconSecondary} mr={2} />
            <StatLabel>Security Alerts</StatLabel>
          </Flex>
          <StatNumber fontSize="3xl">0</StatNumber>
          <StatHelpText>
            All systems normal
          </StatHelpText>
        </Stat>
      </SimpleGrid>

      {/* Activity Trend Chart with Date Picker */}
      <Box mb={4}>
        <Flex mb={2} align="center">
          <Text mr={2} fontWeight="medium">From:</Text>
          <Input type="date"
                 value={startDate}
                 min="2025-04-07"
                 size="sm"
                 mr={4}
                 onChange={e => {
                   const val = e.target.value;
                   setStartDate(val);
                   if (new Date(val) > new Date(endDate)) {
                     setEndDate(val);
                   }
                 }} />
          <Text mr={2} fontWeight="medium">To:</Text>
          <Input type="date"
                 value={endDate}
                 min={startDate}
                 max={new Date().toISOString().split('T')[0]}
                 size="sm"
                 onChange={e => {
                   const val = e.target.value;
                   setEndDate(val);
                   if (new Date(val) < new Date(startDate)) {
                     setStartDate(val);
                   }
                 }} />
        </Flex>
      </Box>

      <Box 
        mt={8}
        p={6}
        borderRadius="xl"
        bg="whiteAlpha.50"
        border="1px solid"
        borderColor="whiteAlpha.200"
        boxShadow="0 4px 24px rgba(0, 0, 0, 0.1)"
      >
        <Heading size="lg" mb={6} color="whiteAlpha.900">
          Performance Metrics
        </Heading>
        <Box height="400px">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trend}>
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3182CE" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#3182CE" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" opacity={0.5} />
              <XAxis dataKey="date" stroke="currentColor" />
              <YAxis stroke="currentColor" />
              <Tooltip 
                contentStyle={{
                  borderRadius: "lg",
                  boxShadow: "xl",
                  border: "none",
                  background: cardBg
                }}
              />
              <Line 
                type="monotone" 
                dataKey="count" 
                stroke="#3182ce" 
                strokeWidth={3}
                dot={{ r: 4 }}
                activeDot={{ r: 6, strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      </Box>
    </Box>
  );
}
