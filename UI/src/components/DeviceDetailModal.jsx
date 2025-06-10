import React, { useState, useEffect } from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalFooter, ModalBody, ModalCloseButton, Button, Box, VStack, HStack, Text, Heading, useColorModeValue, useToast, Flex, Icon, Skeleton, Progress, Tooltip
} from '@chakra-ui/react';
import { FiCpu, FiServer, FiHardDrive, FiShield, FiActivity } from 'react-icons/fi';
import { getLatestReadings, scanDevice, getVulnerabilityScanResults } from '../services/device-service';

const Metric = ({ icon, label, value, color, ...props }) => (
  <VStack spacing={1} align="center" bg={useColorModeValue('gray.50', 'gray.700')} p={4} borderRadius="lg" w="100px" {...props}>
    <Icon as={icon} boxSize={6} color={color} />
    <Text fontSize="lg" fontWeight="bold">{value}</Text>
    <Text fontSize="xs" color="gray.500">{label}</Text>
  </VStack>
);

export default function DeviceDetailModal({ isOpen, onClose, device }) {
  const toast = useToast();
  const [sensorReadings, setSensorReadings] = useState(null);
  const [fetchingReadings, setFetchingReadings] = useState(false);
  const [vulnerabilities, setVulnerabilities] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [lastScan, setLastScan] = useState(device?.last_scan);

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const statusColor = device?.is_online ? 'green.400' : 'red.400';

  const vulnerabilitySeverity = {
    'Critical': 'red.500',
    'High': 'orange.500',
    'Medium': 'yellow.500',
    'Low': 'blue.500',
    'None': 'green.500',
  };

  useEffect(() => {
    if (isOpen && device) {
      // Fetch initial data when modal opens
      const fetchAllData = async () => {
        setFetchingReadings(true);
        try {
          const [readingsData, vulnerabilitiesData] = await Promise.all([
            getLatestReadings(device.hash_id),
            getVulnerabilityScanResults(device.hash_id).catch(e => null) // Allow this to fail silently
          ]);
          setSensorReadings(readingsData);
          setVulnerabilities(vulnerabilitiesData);
        } catch (error) {
          toast({ title: 'Error fetching device details', status: 'error', duration: 3000, isClosable: true });
        }
        setFetchingReadings(false);
      };
      fetchAllData();
    } else {
      // Reset state when modal closes
      setSensorReadings(null);
      setVulnerabilities(null);
    }
  }, [isOpen, device, toast]);

  const handleScan = async () => {
    if (!device) return;
    setScanning(true);
    toast({ title: 'Vulnerability scan started...', status: 'info', duration: 3000, isClosable: true });
    try {
      const result = await scanDevice(device.hash_id);
      setVulnerabilities(result);
      setLastScan(new Date().toISOString());
      toast({ title: 'Scan Complete', description: `Found ${result?.vulnerabilities?.length || 0} vulnerabilities.`, status: 'success', duration: 3000, isClosable: true });
    } catch (error) {
      toast({ title: 'Scan Failed', description: error.message, status: 'error', duration: 3000, isClosable: true });
    }
    setScanning(false);
  };

  if (!device) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl" isCentered>
      <ModalOverlay bg="blackAlpha.600" backdropFilter="blur(4px)" />
      <ModalContent bg={cardBg} borderRadius="xl">
        <ModalHeader borderBottomWidth="1px" borderColor={borderColor}>
          <HStack>
            <Box w={3} h={3} borderRadius="full" bg={statusColor} />
            <Heading size="md">{device.name}</Heading>
          </HStack>
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody py={6}>
          <VStack spacing={6} align="stretch">
            {/* Basic Info */}
            <HStack justify="space-around" color="gray.500" fontSize="sm">
              <Text><strong>IP:</strong> {device.ip_address}</Text>
              <Text><strong>MAC:</strong> {device.mac_address}</Text>
              <Text><strong>Firmware:</strong> {device.firmware_version}</Text>
            </HStack>

            {/* Health Metrics */}
            <Box>
              <Heading size="sm" mb={4}>Health Metrics</Heading>
              {fetchingReadings ? (
                <HStack justify="space-around">
                  <Skeleton height="80px" width="100px" />
                  <Skeleton height="80px" width="100px" />
                  <Skeleton height="80px" width="100px" />
                </HStack>
              ) : sensorReadings ? (
                <HStack justify="space-around">
                  <Metric icon={FiCpu} label="CPU Usage" value={`${sensorReadings.cpu_usage}%`} color="blue.400" />
                  <Metric icon={FiServer} label="Memory" value={`${sensorReadings.memory_usage}%`} color="purple.400" />
                  <Metric icon={FiHardDrive} label="Disk" value={`${sensorReadings.disk_usage}%`} color="green.400" />
                </HStack>
              ) : (
                <Text fontSize="sm" color="gray.500" textAlign="center">No sensor data available.</Text>
              )}
            </Box>

            {/* Security */}
            <Box>
              <Heading size="sm" mb={3}>Security</Heading>
              <Flex justify="space-between" align="center" bg={useColorModeValue('gray.50', 'gray.700')} p={4} borderRadius="lg">
                <VStack align="start" spacing={1}>
                  <Text fontWeight="bold" fontSize="lg" color={vulnerabilitySeverity[vulnerabilities?.severity || 'None']}>
                    {vulnerabilities?.severity || 'Secure'}
                  </Text>
                  <Text fontSize="xs" color="gray.500">Last scan: {lastScan ? new Date(lastScan).toLocaleString() : 'Never'}</Text>
                </VStack>
                <Button size="sm" colorScheme="blue" isLoading={scanning} onClick={handleScan}>Scan Now</Button>
              </Flex>
            </Box>
          </VStack>
        </ModalBody>
        <ModalFooter borderTopWidth="1px" borderColor={borderColor}>
          <Button onClick={onClose}>Close</Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
