import React, { useState, useEffect, useMemo } from 'react';
import {
  Box, Flex, Text, Button, Icon, HStack, VStack, Heading, useColorModeValue, Collapse, Tooltip, IconButton, Skeleton, useToast, Divider
} from '@chakra-ui/react';
import {
  FiPower, FiChevronDown, FiChevronUp, FiShield, FiWifi, FiInfo, FiThermometer, 
  FiDroplet, FiBattery, FiZap, FiActivity, FiSun, FiLock
} from 'react-icons/fi';
import { motion } from 'framer-motion';
import { getLatestReadings, scanDevice, getVulnerabilityScanResults } from '../services/device-service';

const metricDetails = {
  temperature: { icon: FiThermometer, label: 'Temperature', color: 'red.400' },
  humidity: { icon: FiDroplet, label: 'Humidity', color: 'blue.400' },
  battery_level: { icon: FiBattery, label: 'Battery', color: 'green.400' },
  power_usage: { icon: FiZap, label: 'Power', color: 'yellow.400' },
  motion: { icon: FiActivity, label: 'Motion', color: 'purple.400' },
  light_level: { icon: FiSun, label: 'Light', color: 'orange.400' },
  lock_state: { icon: FiLock, label: 'Lock', color: 'teal.400' },
};

const MetricDisplay = ({ icon, label, value, color, isLoading }) => (
  <Tooltip label={label} placement="top">
    <VStack spacing={1} w="80px" h="80px" justifyContent="center">
      <Skeleton isLoaded={!isLoading} circle>
        <Icon as={icon || FiInfo} boxSize={6} color={color} mb={1} />
      </Skeleton>
      <Skeleton isLoaded={!isLoading} w="full" textAlign="center">
        <Text fontSize="md" fontWeight="bold">{value}</Text>
      </Skeleton>
    </VStack>
  </Tooltip>
);

export default function DeviceCard({ device, isExpanded, onToggleExpand, onTogglePower }) {
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const statusColor = device.is_online ? 'green.400' : 'red.400';
  const subtleTextColor = useColorModeValue('gray.500', 'gray.400');

  const toast = useToast();
  const [sensorReadings, setSensorReadings] = useState(null);
  const [fetchingReadings, setFetchingReadings] = useState(false);
  const [vulnerabilities, setVulnerabilities] = useState(null);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    if (isExpanded && !sensorReadings) {
      const fetchReadings = async () => {
        setFetchingReadings(true);
        try {
          const data = await getLatestReadings(device.hash_id);
          setSensorReadings(data);
        } catch (error) {
          // Silently fail for now
        } finally {
          setFetchingReadings(false);
        }
      };
      fetchReadings();
    }
  }, [isExpanded, device.hash_id, sensorReadings]);

  const handleScan = async (e) => {
    e.stopPropagation();
    setScanning(true);
    toast({ title: 'Vulnerability scan started...', status: 'info', duration: 3000, isClosable: true });
    try {
      const result = await scanDevice(device.hash_id);
      setVulnerabilities(result);
      toast({ title: 'Scan Complete', status: 'success', duration: 3000, isClosable: true });
    } catch (error) {
      toast({ title: 'Scan Failed', status: 'error', duration: 3000, isClosable: true });
    }
    setScanning(false);
  };

  const handlePowerClick = (e) => {
    e.stopPropagation();
    onTogglePower();
  };

  const vulnerabilityCount = vulnerabilities?.vulnerabilities?.length || 0;
  const securityStatus = vulnerabilityCount > 0 ? `${vulnerabilityCount} issues` : 'Secure';
  const securityColor = vulnerabilityCount > 0 ? 'orange.400' : 'green.400';

  const glow = useMemo(() => {
    if (vulnerabilityCount > 0) return '0 0 12px rgba(255,165,0,0.6)';
    return device.is_online ? '0 0 12px rgba(72,187,120,0.6)' : 'none';
  }, [vulnerabilityCount, device.is_online]);

  const renderMetrics = () => {
    if (fetchingReadings) {
      return (
        <HStack justify="center" spacing={4} wrap="wrap">
          <MetricDisplay isLoading={true} />
          <MetricDisplay isLoading={true} />
          <MetricDisplay isLoading={true} />
        </HStack>
      );
    }

    if (sensorReadings && Object.keys(sensorReadings).length > 0) {
      return (
        <HStack justify="center" spacing={4} wrap="wrap">
          {Object.entries(sensorReadings).map(([type, reading]) => {
            const details = metricDetails[type] || { icon: FiInfo, label: type.replace(/_/g, ' '), color: 'gray.400' };
            let displayValue;
            if (typeof reading.value === 'boolean') {
              displayValue = reading.value ? 'Active' : 'Inactive';
            } else if (reading.value === null || reading.value === undefined) {
              displayValue = '-';
            } else {
              displayValue = `${reading.value}${reading.unit || ''}`;
            }

            return (
              <MetricDisplay 
                key={type}
                icon={details.icon}
                label={details.label}
                value={displayValue}
                color={details.color}
                isLoading={false}
              />
            );
          })}
        </HStack>
      );
    }

    return (
      <Text fontSize="sm" color={subtleTextColor} w="full" textAlign="center">
        No live metrics available for this device.
      </Text>
    );
  };

  return (
    <motion.div layout whileHover={{ y: -4, rotateX: 2, rotateY: -2 }} transition={{ type: 'spring', stiffness: 200, damping: 15 }}>
      <Box bgGradient="linear(to-br, gray.600 0%, gray.900 100%)" p="1px" borderRadius="2xl" boxShadow={glow} onClick={onToggleExpand} cursor="pointer">
        <Box
          bg={cardBg}
          borderRadius="2xl"
          p={5}
          w="100%"
          maxW="400px"
          boxShadow={isExpanded ? 'dark-lg' : 'md'}
          transition="all 0.2s ease-in-out"
        >
          <VStack spacing={4} align="stretch">
            <Flex justify="space-between" align="center">
              <HStack spacing={3}>
                <Box w={3} h={3} borderRadius="full" bg={statusColor} />
                <Heading size="md" noOfLines={1}>{device.name}</Heading>
              </HStack>
              <IconButton 
                icon={isExpanded ? <FiChevronUp /> : <FiChevronDown />}
                variant="ghost"
                size="sm"
                aria-label="Toggle Details"
              />
            </Flex>

            <HStack justify="space-between" color={subtleTextColor} fontSize="sm">
              <HStack><Icon as={FiWifi} mr={1} /><Text>{device.ip_address}</Text></HStack>
              <HStack><Icon as={FiInfo} mr={1} /><Text>FW: {device.firmware_version}</Text></HStack>
              <HStack><Icon as={FiShield} color={securityColor} mr={1} /><Text color={securityColor}>{securityStatus}</Text></HStack>
            </HStack>

            <Collapse in={isExpanded} animateOpacity>
              <Divider my={4} />
              <VStack spacing={5} align="stretch">
                <Box>
                  <Heading size="sm" mb={4} textAlign="center">Live Metrics</Heading>
                  {renderMetrics()}
                </Box>
                <HStack justify="space-between">
                  <Button size="sm" variant="outline" isLoading={scanning} onClick={handleScan}>Scan Vulnerabilities</Button>
                  <Button size="sm" colorScheme={device.is_online ? 'red' : 'green'} onClick={handlePowerClick}>{device.is_online ? 'Power Off' : 'Power On'}</Button>
                </HStack>
              </VStack>
            </Collapse>
          </VStack>
        </Box>
      </Box>
    </motion.div>
  );
}
