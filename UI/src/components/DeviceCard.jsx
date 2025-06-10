import React, { useState, useEffect } from 'react';
import {
  Box, Flex, Text, Badge, Button, Progress, Icon, HStack, VStack, Heading,
  useColorModeValue, Collapse, Tooltip, useDisclosure
} from '@chakra-ui/react';
import { 
  FiPower, FiActivity, FiWifi, FiShield, FiRefreshCw,
  FiChevronDown, FiChevronUp, FiAlertCircle, FiInfo,
  FiThermometer, FiDroplet, FiBattery, FiZap, FiLock
} from 'react-icons/fi';
import { motion } from 'framer-motion';
import { scanDevice, getLatestReadings, simulateDeviceMetrics, getVulnerabilityScanResults } from '../services/device-service';
import { useToast } from '@chakra-ui/react';
import { Link as RouterLink } from 'react-router-dom';

export default function DeviceCard({ 
  device, 
  isExpanded, 
  onToggleExpand,
  onTogglePower
}) {
  const bgColor = useColorModeValue('rgba(255, 255, 255, 0.8)', 'rgba(26, 32, 44, 0.8)');
  const borderColor = useColorModeValue('rgba(0, 0, 0, 0.1)', 'rgba(255, 255, 255, 0.1)');
  const statusColor = device.is_online ? 'green' : 'red';
  
  const cardAnimation = {
    hover: { 
      scale: 1.03,
      boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.2)'
    },
    tap: { scale: 0.98 }
  };

  const toast = useToast();
  const [scanning, setScanning] = useState(false);
  const [sensorReadings, setSensorReadings] = useState(null);
  const [fetchingReadings, setFetchingReadings] = useState(false);
  const [vulnerabilities, setVulnerabilities] = useState(null);
  const [lastScan, setLastScan] = useState(device.last_scan);
  // Removed automatic vulnerability loading; vulnerabilities fetched only after manual scan

  // Fetch initial metrics for header summary
  useEffect(() => {
    const fetchSummaryMetrics = async () => {
      try {
        let data = await getLatestReadings(device.hash_id);
        // Auto-generate metrics if none exist
        if (!data || Object.entries(data).filter(([t]) => t !== 'status').length === 0) {
          await simulateDeviceMetrics(device.hash_id);
          data = await getLatestReadings(device.hash_id);
        }
        setSensorReadings(data);
      } catch (err) {
        console.error('Error fetching initial metrics:', err);
      }
    };
    fetchSummaryMetrics();
  }, [device.hash_id]);

  // Icon and label mappings for dynamic sensor metrics
  const metricsIcons = {
    temperature: FiThermometer,
    humidity: FiDroplet,
    battery_level: FiBattery,
    power_usage: FiZap,
    motion: FiActivity,
    light_level: FiActivity,
    lock_state: FiLock
  };
  const metricLabels = {
    temperature: 'Temp',
    humidity: 'Humidity',
    battery_level: 'Battery',
    power_usage: 'Power',
    motion: 'Motion',
    light_level: 'Light',
    lock_state: 'Lock'
  };
  metricsIcons.status = FiInfo;
  metricLabels.status = 'Status';
  const getMetricColor = (type) => {
    switch(type) {
      case 'temperature': return 'red.400';
      case 'humidity': return 'blue.400';
      case 'battery_level': return 'green.400';
      case 'power_usage': return 'yellow.400';
      case 'motion': return 'purple.400';
      case 'light_level': return 'orange.400';
      case 'lock_state': return 'teal.400';
      default: return 'gray.400';
    }
  };

  useEffect(() => {
    let intervalId;
    const fetchMetrics = async () => {
      setFetchingReadings(true);
      try {
        const data = await getLatestReadings(device.hash_id);
        setSensorReadings(data);
      } catch (err) {
        console.error('Error fetching sensor readings:', err);
        toast({
          title: 'Error loading metrics',
          description: err.message,
          status: 'error',
          duration: 3000,
          isClosable: true
        });
      } finally {
        setFetchingReadings(false);
      }
    };
    if (isExpanded) {
      fetchMetrics();
      intervalId = setInterval(fetchMetrics, 60000);
    }
    return () => clearInterval(intervalId);
  }, [isExpanded]);

  // Sleep helper for polling
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  const handleScan = async (e) => {
    e.stopPropagation();
    setScanning(true);
    setVulnerabilities(null);
    try {
      const result = await scanDevice(device.hash_id);
      const scanId = result.scan_id;
      toast({ title: 'Scan initiated', status: 'info', duration: 3000, isClosable: true });
      let pollRes;
      do {
        await sleep(2000);
        pollRes = await getVulnerabilityScanResults(scanId);
      } while (pollRes.status === 'in_progress');
      if (pollRes.status === 'error') {
        toast({ title: 'Scan failed', description: pollRes.error || 'Unknown error', status: 'error', duration: 3000, isClosable: true });
        setVulnerabilities([]);
      } else {
        setVulnerabilities(pollRes.vulnerabilities || []);
        const nowStr = new Date().toLocaleString();
        setLastScan(nowStr);
        toast({ title: 'Scan completed', status: 'success', description: `Scan completed at ${nowStr}`, duration: 3000, isClosable: true });
      }
    } catch (err) {
      console.error('Error scanning device:', err);
      toast({ title: 'Scan error', description: err.message, status: 'error', duration: 3000, isClosable: true });
    } finally {
      setScanning(false);
    }
  };

  const handleGenerateMetrics = async (e) => {
    e.stopPropagation();
    setFetchingReadings(true);
    try {
      await simulateDeviceMetrics(device.hash_id);
      const data = await getLatestReadings(device.hash_id);
      setSensorReadings(data);
    } catch (err) {
      console.error('Error simulating metrics:', err);
      toast({
        title: 'Simulation error',
        description: err.message,
        status: 'error',
        duration: 3000,
        isClosable: true
      });
    } finally {
      setFetchingReadings(false);
    }
  };

  // Reset vulnerabilities on collapse
  useEffect(() => {
    if (!isExpanded) {
      setVulnerabilities(null);
    }
  }, [isExpanded]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover="hover"
      whileTap="tap"
      variants={cardAnimation}
      transition={{ duration: 0.3 }}
    >
      <Box
        p={5}
        bg={bgColor}
        borderWidth="1px"
        borderColor={device.is_online ? 'green.300' : 'red.300'}
        borderRadius="lg"
        boxShadow="sm"
        _hover={{ boxShadow: 'md', transform: 'translateY(-4px)' }}
        transition="all 0.3s"
        position="relative"
        overflow="hidden"
      >
        <Flex justify="space-between" align="center" mb={3} zIndex={1}>
          <VStack align="start" spacing={1}>
            <HStack align="center" spacing={2}>
              <Heading size="md" fontWeight="semibold" color={useColorModeValue('blue.600','blue.300')}>
                {device.name}
              </Heading>
              <Badge colorScheme="teal" variant="subtle">
                {device.type}
              </Badge>
            </HStack>
            {/* Device metadata */}
            {(device.manufacturer || device.model) && (
              <Text fontSize="sm" color={useColorModeValue('gray.600', 'gray.400')}>
                {device.manufacturer}{device.model ? ` ${device.model}` : ''}
              </Text>
            )}
            {device.firmware_version && (
              <Text fontSize="sm" color={useColorModeValue('gray.600', 'gray.400')}>
                {`v${device.firmware_version}`}
              </Text>
            )}
            {sensorReadings && Object.entries(sensorReadings).filter(([t]) => t !== 'status').length > 0 && (
              <HStack spacing={4} mt={1}>
                {Object.entries(sensorReadings)
                  .filter(([t]) => t !== 'status')
                  .map(([type, reading]) => {
                    const IconComp = metricsIcons[type] || FiInfo;
                    return (
                      <HStack key={type} spacing={1}>
                        <Icon as={IconComp} color={getMetricColor(type)} boxSize={4} />
                        <Text fontSize="sm" color={useColorModeValue('gray.600', 'gray.400')}>
                          {`${reading.value}${reading.unit}`}
                        </Text>
                      </HStack>
                    );
                  })}
              </HStack>
            )}
          </VStack>
          
          <HStack spacing={3}>
            <Tooltip label={`Device is ${device.is_online ? 'online' : 'offline'}`}>
              <Box 
                w={4} 
                h={4} 
                borderRadius="full" 
                bg={`${statusColor}.400`}
                border="2px solid white"
                boxShadow={`0 0 12px ${statusColor}.400`}
                zIndex={1}
              />
            </Tooltip>
            
            <Button 
              size="sm" 
              variant="ghost"
              onClick={onToggleExpand}
              _hover={{ bg: 'rgba(0, 0, 0, 0.05)' }}
            >
              <Icon as={isExpanded ? FiChevronUp : FiChevronDown} />
            </Button>
          </HStack>
        </Flex>

        <Collapse in={isExpanded} animateOpacity>
          <VStack align="stretch" spacing={4} mt={4}>
            {/* Status Bar */}
            <Box 
              h={1} 
              w="full" 
              bg={`${statusColor}.100`} 
              borderRadius="full" 
              overflow="hidden"
            >
              <Box 
                h="full" 
                w={device.is_online ? '100%' : '0%'} 
                bg={`${statusColor}.400`}
                transition="all 0.5s ease"
              />
            </Box>
            
            {/* Device Details */}
            <HStack justify="space-between">
              <HStack>
                <Icon as={FiWifi} color={device.is_online ? 'green.400' : 'gray.400'} />
                <Text fontSize="sm">{device.ip_address}</Text>
              </HStack>
              
              <Badge colorScheme="blue" variant="subtle">
                {lastScan || 'Never scanned'}
              </Badge>
            </HStack>
            
            {/* Show vulnerabilities only after scan completes; otherwise health */}
            {vulnerabilities !== null && vulnerabilities.length > 0 ? (
              <Box>
                <HStack mb={2} spacing={2}>
                  <Icon as={FiAlertCircle} color="red.400" />
                  <Text fontSize="sm" color="red.500">
                    {vulnerabilities.length} Vulnerabilities
                  </Text>
                </HStack>
              </Box>
            ) : (
              <Box>
                <HStack mb={2}>
                  <Icon as={FiActivity} color="blue.400" />
                  <Text fontSize="sm">Operational: {device.health_score || 95}%</Text>
                </HStack>
                <Progress 
                  value={device.health_score || 95} 
                  size="sm"
                  borderRadius="full"
                  colorScheme={device.health_score > 85 ? 'green' : device.health_score > 60 ? 'orange' : 'red'}
                  sx={{ '> div': { transition: 'all 0.5s ease' } }}
                />
              </Box>
            )}
            
            {/* Sensor Metrics */}
            {fetchingReadings ? (
              <Text fontSize="sm">Loading metrics...</Text>
            ) : sensorReadings ? (
              <Box>
                <HStack mb={2} spacing={4}>
                  {(() => {
                    const entries = Object.entries(sensorReadings);
                    const filtered = entries.filter(([t]) => t !== 'status' || entries.length === 1);
                    return filtered.map(([type, reading]) => {
                      const IconComp = metricsIcons[type] || FiInfo;
                      if (type === 'status') {
                        return (
                          <HStack key={type} spacing={1}>
                            <Icon as={IconComp} color={reading.value === 1 ? 'green.400' : 'red.400'} />
                            <Text fontSize="sm">{`Status: ${reading.value === 1 ? 'OK' : 'Error'}`}</Text>
                          </HStack>
                        );
                      }
                      const label = metricLabels[type] || type.replace(/_/g, ' ');
                      return (
                        <HStack key={type} spacing={1}>
                          <Icon as={IconComp} color={getMetricColor(type)} />
                          <Text fontSize="sm">{`${label}: ${reading.value}${reading.unit}`}</Text>
                        </HStack>
                      );
                    });
                  })()}
                </HStack>
              </Box>
            ) : (
              <Button size="sm" variant="outline" onClick={handleGenerateMetrics} mt={2}>
                Generate Metrics
              </Button>
            )}

            {/* Action Buttons */}
            <HStack spacing={3} mt={2}>
              <Button 
                size="sm" 
                leftIcon={<Icon as={FiPower} />}
                colorScheme={device.is_online ? 'green' : 'gray'}
                variant="outline"
                onClick={onTogglePower}
                flex={1}
              >
                {device.is_online ? 'Power On' : 'Power Off'}
              </Button>
              
              <Button 
                size="sm" 
                leftIcon={<Icon as={FiShield} />}
                colorScheme="blue"
                variant="outline"
                onClick={handleScan}
                flex={1}
                isLoading={scanning}
              >
                Scan Vulnerabilities
              </Button>
            </HStack>
          </VStack>
        </Collapse>
      </Box>
    </motion.div>
  );
}
