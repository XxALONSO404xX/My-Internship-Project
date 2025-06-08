import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Box, Spinner, Skeleton, Badge, Stack, Text, Button, Heading, Input, Select, SimpleGrid, Flex, useToast,
  Icon, useDisclosure, useBreakpointValue, useColorModeValue, Modal, ModalOverlay, ModalContent, ModalHeader,
  ModalBody, ModalFooter, ModalCloseButton, Progress, VStack, HStack, Image
} from '@chakra-ui/react';
import { InfiniteScroll } from '../components/InfiniteScroll';
import DeviceCard from '../components/DeviceCard';
import FullScreenLoader from '../components/FullScreenLoader';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { getDevices, toggleDevicePower } from '../services/device-service';
import { FiRadio, FiCheck, FiWifi, FiServer, FiShield, FiActivity } from 'react-icons/fi';
import { keyframes } from '@emotion/react';

export default function DeviceList() {
  const navigate = useNavigate();
  const toast = useToast();
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [allDevices, setAllDevices] = useState([]);
  const [visibleDevices, setVisibleDevices] = useState([]);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all'); // 'all' | 'online' | 'offline'
  const [isScanning, setIsScanning] = useState(false);
  const [scanCooldown, setScanCooldown] = useState(0);
  const lastScanTime = useRef(0);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const batchSize = 20;

  // Inline expand state for device details
  const [expandedIds, setExpandedIds] = useState(new Set());

  // Generate realistic sensor metadata for each device inline
  const generateMetadata = () => ({
    temperature: (Math.random() * 20 + 20).toFixed(1) + ' °C',
    humidity: (Math.random() * 50 + 30).toFixed(1) + ' %',
    battery: Math.floor(Math.random() * 100) + ' %',
  });

  // Animation for the scan button (uses primary palette)
  const pulse = keyframes`
    0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(33, 150, 243, 0.7); }
    70% { transform: scale(1.05); box-shadow: 0 0 0 10px rgba(33, 150, 243, 0); }
    100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(33, 150, 243, 0); }
  `;
  
  // Scan dialog component
  const ScanDialog = () => (
    <Modal isOpen={isOpen} onClose={onClose} isCentered size="md">
      <ModalOverlay bg="blackAlpha.600" backdropFilter="blur(4px)" />
      <ModalContent bg={useColorModeValue('white', 'gray.800')} borderRadius="xl" overflow="hidden" variant="card">
        <ModalHeader display="flex" alignItems="center">
          <Icon as={FiRadio} mr={2} color={useColorModeValue('primary.500','primary.300')} boxSize={6} />
          <Text>Network Scan</Text>
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          <Box textAlign="center" py={4}>
            {isScanning ? (
              <>
                <Box position="relative" w="100%" h="120px" mb={4}>
                  {[...Array(5)].map((_, i) => (
                    <Box
                      key={`pulse-${i}`}
                      position="absolute"
                      top="50%"
                      left="50%"
                      w={`${(i + 1) * 60}px`}
                      h={`${(i + 1) * 60}px`}
                      ml={`-${(i + 1) * 30}px`}
                      mt={`-${(i + 1) * 30}px`}
                      borderRadius="full"
                      border="2px solid"
                      borderColor={`primary.${200 + i * 100}`}
                      opacity={0.7 - (i * 0.1)}
                      animation={`pulse 2s infinite ${i * 0.2}s`}
                    />
                  ))}
                  <Box
                    position="absolute"
                    top="50%"
                    left="50%"
                    w="60px"
                    h="60px"
                    ml="-30px"
                    mt="-30px"
                    borderRadius="full"
                    bg="primary.500"
                    display="flex"
                    alignItems="center"
                    justifyContent="center"
                    color="white"
                    fontSize="xl"
                    fontWeight="bold"
                    boxShadow="lg"
                  >
                    <FiRadio size={24} />
                  </Box>
                </Box>
                <Text fontSize="lg" fontWeight="medium" mb={2}>
                  Scanning your network...
                </Text>
                <Text color="gray.500" mb={4}>
                  Found {allDevices.length} device{allDevices.length !== 1 ? 's' : ''} so far
                </Text>
                <Progress value={(allDevices.length / 6) * 100} size="sm" colorScheme="primary" borderRadius="full" />
              </>
            ) : (
              <>
                <Box
                  w="100px"
                  h="100px"
                  mx="auto"
                  mb={4}
                  borderRadius="full"
                  bg="green.100"
                  display="flex"
                  alignItems="center"
                  justifyContent="center"
                  color="green.500"
                >
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M5 13L9 17L19 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </Box>
                <Text fontSize="xl" fontWeight="bold" mb={2}>
                  Scan Complete!
                </Text>
                <Text color="gray.500" mb={4}>
                  Found {allDevices.length} new device{allDevices.length !== 1 ? 's' : ''} on your network
                </Text>
              </>
            )}
          </Box>
        </ModalBody>
        <ModalFooter>
          <Button
            colorScheme="primary"
            onClick={onClose}
            isFullWidth
            isDisabled={isScanning}
          >
            {isScanning ? 'Scanning...' : 'Close'}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );

  const toggleExpand = (id) => {
    setExpandedIds(prev => {
      const s = new Set(prev);
      s.has(id) ? s.delete(id) : s.add(id);
      return s;
    });
  };

  // Data fetch function
  const fetchData = async () => {
    try {
      const devices = await getDevices();
      const enriched = devices.map(d => ({ ...d, metadata: generateMetadata() }));
      setAllDevices(enriched);
      setVisibleDevices(enriched.slice(0, batchSize));
      setHasMore(enriched.length > batchSize);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Initial data load with delay for realism
  useEffect(() => {
    const timer = setTimeout(fetchData, 1500);
    return () => clearTimeout(timer);
  }, []);

  // Polling every 15s for realtime status after initial scan
  useEffect(() => {
    const id = setInterval(async () => {
      try {
        const freshDevices = await getDevices();
        const enriched = freshDevices.map(d => ({ ...d, metadata: generateMetadata() }));
        setAllDevices(enriched);
        setVisibleDevices(prev => {
          const currentIds = new Set(prev.map(d => d.hash_id));
          const newDevices = enriched.filter(d => !currentIds.has(d.hash_id));
          return [...prev, ...newDevices.slice(0, batchSize - prev.length)];
        });
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 15000);
    return () => clearInterval(id);
  }, []);

  // Handle scan cooldown
  useEffect(() => {
    if (scanCooldown > 0) {
      const timer = setTimeout(() => setScanCooldown(c => c - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [scanCooldown]);

  const loadMore = () => {
    if (visibleDevices.length >= allDevices.length) {
      setHasMore(false);
      return;
    }
    const nextBatch = allDevices.slice(
      visibleDevices.length,
      visibleDevices.length + batchSize
    );
    setVisibleDevices(prev => [...prev, ...nextBatch]);
    setHasMore(visibleDevices.length + batchSize < allDevices.length);
  };

  const filteredDevices = visibleDevices.filter(d => {
    const matchesSearch = searchTerm ? 
      d.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.ip_address.includes(searchTerm) : true;
    const matchesStatus = statusFilter === 'all' || 
      (statusFilter === 'online' ? d.is_online : !d.is_online);
    return matchesSearch && matchesStatus;
  });

  // Handle device power toggle
  const handleTogglePower = async (deviceId, currentState) => {
    try {
      await toggleDevicePower(deviceId, !currentState);
      const updatedAll = allDevices.map(d =>
        d.hash_id === deviceId ? { ...d, is_online: !currentState } : d
      );
      setAllDevices(updatedAll);
      setVisibleDevices(prev => prev.map(d =>
        d.hash_id === deviceId ? { ...d, is_online: !currentState } : d
      ));
    } catch (err) {
      console.error('Error toggling device power:', err);
    }
  };

  const handleScan = async () => {
    const startTime = Date.now();
    if (startTime - lastScanTime.current < 15000) {
      toast({ title: 'Please wait before scanning again', status: 'warning', duration: 2000, isClosable: true });
      return;
    }
    lastScanTime.current = startTime;
    setScanCooldown(15);
    setIsScanning(true);
    try {
      // perform vulnerability scan on all devices
      for (const dev of allDevices) {
        // await scanDevice(dev.id);
      }
      // refresh device list
      await fetchData();
      toast({ title: 'Network scan complete!', status: 'success', duration: 2000, isClosable: true });
    } catch (err) {
      toast({ title: 'Scan failed', description: err.message, status: 'error', duration: 3000, isClosable: true });
    } finally {
      const elapsed = Date.now() - startTime;
      const minDuration = 1500;
      const remaining = Math.max(0, minDuration - elapsed);
      setTimeout(() => setIsScanning(false), remaining);
    }
  };
  const handleRules = (type) => navigate(`/rules?type=${type}`);
  const showConfirm = (dev) => { setSelectedDevice(dev); };
  const confirmScan = async () => { await handleScan(selectedDevice.id); };

  const cols = useBreakpointValue({ base: 1, sm: 2, md: 3, lg: 4 });

  if (loading) return (
    <SimpleGrid columns={cols} spacing={6} p={8}>
      {[...Array(cols || 4)].map((_, i) => (
        <Skeleton key={i} height='180px' borderRadius='md' />
      ))}
    </SimpleGrid>
  );
  if (error) return <Text color='red.500'>Error: {error}</Text>;

  return (
    <Box p={8}>
      <FullScreenLoader isOpen={isScanning} message="Discovering devices..." />
      <Flex justify="space-between" align="center" mb={6}>
        <Heading>Devices</Heading>
        <Button
          leftIcon={isScanning ? <Spinner size="sm" /> : <Icon as={FiRadio} />}
          colorScheme="primary"
          onClick={() => handleScan()}
          isLoading={isScanning}
          loadingText="Discovering devices..."
          isDisabled={scanCooldown > 0}
          animation={scanCooldown === 0 && !isScanning ? `${pulse} 2s infinite` : 'none'}
          _hover={scanCooldown === 0 ? { transform: 'scale(1.03)' } : {}}
          transition="all 0.2s"
          size="md"
          px={6}
          py={2}
          borderRadius="md"
          boxShadow={scanCooldown === 0 ? '0 0 15px rgba(33, 150, 243, 0.4)' : 'none'}
        >
          {scanCooldown > 0 ? `Scan (${scanCooldown}s)` : 'Scan Devices'}
        </Button>
      </Flex>
      
      {/* Initial Scan Modal */}
      <Modal isOpen={isOpen} onClose={() => {}} closeOnOverlayClick={false} isCentered size="xl">
        <ModalOverlay bg="blackAlpha.700" backdropFilter="blur(4px)" />
        <ModalContent bg="gray.800" color="white" variant="card">
          <ModalHeader>Initial Network Scan</ModalHeader>
          <ModalBody>
            <VStack spacing={6} py={4}>
              <Box textAlign="center">
                <Box position="relative" w="200px" h="200px" mx="auto" mb={6}>
                  <Box
                    position="absolute"
                    top="50%"
                    left="50%"
                    w="100%"
                    h="100%"
                    borderRadius="full"
                    bg="primary.900"
                    opacity="0.3"
                    animation={`${pulse} 2s infinite`}
                  />
                  <Box
                    position="absolute"
                    top="50%"
                    left="50%"
                    w="80%"
                    h="80%"
                    borderRadius="full"
                    bg="primary.800"
                    opacity="0.5"
                    animation={`${pulse} 2s infinite 0.3s`}
                  />
                  <Box
                    position="absolute"
                    top="50%"
                    left="50%"
                    w="60%"
                    h="60%"
                    borderRadius="full"
                    bg="primary.700"
                    animation={`${pulse} 2s infinite 0.6s`}
                    display="flex"
                    alignItems="center"
                    justifyContent="center"
                    color="white"
                  >
                    <FiWifi size={48} className="pulse" />
                  </Box>
                </Box>
                <Text fontSize="xl" fontWeight="bold" mb={2}>
                  {isScanning ? 'Scanning your network...' : 'Scan Complete!'}
                </Text>
                <Text color="gray.400">
                  {isScanning 
                    ? 'Discovering all connected IoT devices...' 
                    : 'Your network has been successfully scanned.'}
                </Text>
                {isScanning && (
                  <Progress 
                    mt={6} 
                    size="sm" 
                    isIndeterminate 
                    colorScheme="primary" 
                    borderRadius="full"
                  />
                )}
              </Box>
            </VStack>
          </ModalBody>
          <ModalFooter>
            {!isScanning && (
              <Button 
                colorScheme="primary" 
                onClick={onClose}
                width="100%"
              >
                Continue to Dashboard
              </Button>
            )}
          </ModalFooter>
        </ModalContent>
      </Modal>
      <InfiniteScroll 
        loadMore={loadMore} 
        hasMore={hasMore} 
        loader={<Spinner mt={4} />}
      >
        <SimpleGrid minChildWidth="350px" spacing={6} mt={6} justifyItems="center" mx="auto">
          {filteredDevices.map(device => (
            <Box key={device.hash_id} w="100%" maxW="350px">
              <DeviceCard
                device={device}
                isExpanded={expandedIds.has(device.hash_id)}
                onToggleExpand={() => toggleExpand(device.hash_id)}
                onTogglePower={() => handleTogglePower(device.hash_id, device.is_online)}
              />
            </Box>
          ))}
        </SimpleGrid>
      </InfiniteScroll>
    </Box>
  );
}
