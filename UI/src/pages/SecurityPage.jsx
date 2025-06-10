import React, { useState, useEffect } from 'react';
import { getDevices } from '../services/device-service.js';
import {
  startVulnerabilityScan,
  getVulnerabilityScanResults,
  remediateVulnerability,
  bulkRemediateVulnerabilities
} from '../services/security-service.js';
import { getCompatibleFirmware, startFirmwareUpdate } from '../services/firmware-service.js';
import toast from 'react-hot-toast';
import {
  Box,
  Heading,
  Text,
  Button,
  HStack,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  VStack,
  useColorModeValue,
  Spinner,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Drawer,
  DrawerOverlay,
  DrawerContent,
  DrawerHeader,
  DrawerBody,
  DrawerFooter,
  useDisclosure,
  IconButton,
  Flex,
  Fade
} from '@chakra-ui/react';
import { 
  PieChart, 
  Pie, 
  Cell, 
  ResponsiveContainer, 
  Tooltip, 
  Legend, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis,
  RadialBarChart,
  RadialBar
} from 'recharts';
import { InfoOutlineIcon } from '@chakra-ui/icons';
import DeviceSelector from '../components/DeviceSelector';
import FullScreenLoader from '../components/FullScreenLoader';

// Map severity -> Chakra color scheme for Badge
const severityColorScheme = (severity) => {
  switch (severity.toLowerCase()) {
    case 'critical':
      return 'red';
    case 'high':
      return 'orange';
    case 'medium':
      return 'yellow';
    case 'low':
    default:
      return 'green';
  }
};

export default function SecurityPage() {
  const [devices, setDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState('');
  const [scanResult, setScanResult] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState(null);
  const [showFirmwareModal, setShowFirmwareModal] = useState(false);
  const [compatibleFw, setCompatibleFw] = useState([]);
  const [updatingFw, setUpdatingFw] = useState(false);
  const [selectedVulnerability, setSelectedVulnerability] = useState(null);
  const { isOpen: isDrawerOpen, onOpen: openDrawer, onClose: closeDrawer } = useDisclosure();

  // Theme-driven styling
  const cardBg = useColorModeValue('white', 'gray.800');
  const accentColor = useColorModeValue('blue.500', 'blue.300');

  useEffect(() => {
    async function fetchAllDevices() {
      try {
        const devs = await getDevices();
        setDevices(devs);
      } catch (err) {
        setError(err.message);
      }
    }
    fetchAllDevices();
  }, []);

  const handleScan = async () => {
    if (!selectedDeviceId) {
      toast.error('Please select a device to scan');
      return;
    }
    const id = toast.loading('Starting vulnerability scan...');
    setScanning(true);
    try {
      const { scan_id } = await startVulnerabilityScan(selectedDeviceId);
      let result;
      do {
        await new Promise(res => setTimeout(res, 2000));
        result = await getVulnerabilityScanResults(scan_id);
      } while (
        result.status === 'success' &&
        (result.scan.status === 'pending' || result.scan.status === 'in_progress')
      );
      if (result.status !== 'success') {
        throw new Error(result.error || 'Scan failed');
      }
      setScanResult(result.scan);
      toast.success('Scan completed', { id });
    } catch (err) {
      toast.error(err.message, { id });
      setError(err.message);
    } finally {
      setScanning(false);
    }
  };

  const handleRemediate = async (vulnId) => {
    const id = toast.loading('Remediating vulnerability...');
    try {
      const res = await remediateVulnerability(selectedDeviceId, vulnId);
      // Choose toast style based on remediation outcome
      if (res.outcome === 'complete_fix' || res.status === 'success') {
        toast.success(res.message || 'Remediated', { id });
      } else if (res.outcome === 'partial_fix') {
        toast(res.message || 'Partially remediated', { id, icon: '⚠️' });
      } else if (res.outcome === 'temporary_fix') {
        toast(res.message || 'Temporary fix applied', { id, icon: '⏳' });
      } else {
        toast(res.message || 'Remediation result', { id });
      }
      if (scanResult?.id) {
        const refreshed = await getVulnerabilityScanResults(scanResult.id);
        if (refreshed.status === 'success') {
          setScanResult(refreshed.scan);
        }
      }
    } catch (err) {
      toast.error(err.message, { id });
    }
  };

  // Perform bulk remediation of non-firmware vulnerabilities
  const handleBulkRemediate = async () => {
    if (!selectedDeviceId) return;
    // Only include vulnerabilities that can be remediated via API
    const ids = scanResult.vulnerabilities
      .filter(v => v.fix_available !== 'firmware_update')
      .map(v => v.id);
    if (ids.length === 0) {
      toast('No vulnerabilities to remediate', { icon: 'ℹ️' });
      return;
    }
    const loadingId = toast.loading('Performing bulk remediation...');
    try {
      const map = { [selectedDeviceId]: ids };
      const res = await bulkRemediateVulnerabilities(map);
      toast.success(res.message || 'Bulk remediation completed', { id: loadingId });
      // Refresh scan results
      const refreshed = await getVulnerabilityScanResults(scanResult.id);
      if (refreshed.status === 'success') {
        setScanResult(refreshed.scan);
      }
    } catch (err) {
      toast.error(err.message || 'Bulk remediation failed', { id: loadingId });
    }
  };

  const openFirmwareModal = async () => {
    try {
      setShowFirmwareModal(true);
      const list = await getCompatibleFirmware(selectedDeviceId);
      setCompatibleFw(list);
    } catch (e) {
      toast.error('Failed to fetch firmware list');
    }
  };

  const handleFirmwareUpdate = async (version) => {
    const id = toast.loading('Starting firmware update...');
    try {
      setUpdatingFw(true);
      const res = await startFirmwareUpdate(selectedDeviceId, version);
      toast.success('Firmware update started', { id });
      setShowFirmwareModal(false);
    } catch (e) {
      toast.error(e.message || 'Update failed', { id });
    } finally {
      setUpdatingFw(false);
    }
  };

  // Compute severity distribution
  const severityCounts = scanResult?.vulnerabilities.reduce((acc,v) => { acc[v.severity] = (acc[v.severity]||0)+1; return acc; }, {}) || {};
  const totalVulns = scanResult?.vulnerabilities.length || 0;

  // Compute and style risk gauge
  const riskScore = scanResult?.result?.risk_score || 0;
  const gaugeValue = Math.min(Math.max(riskScore * 10, 0), 100);
  const gaugeColor = riskScore > 7 ? useColorModeValue('red.500','red.300')
                    : riskScore > 4 ? useColorModeValue('orange.500','orange.300')
                    : useColorModeValue('green.500','green.300');

  return (
    <Box p={8}>
      <FullScreenLoader isOpen={scanning} message="Scanning vulnerabilities..." />
      <Box bg={cardBg} p={6} borderRadius="md" boxShadow="sm" mb={6}>
        <Heading size="lg" mb={4}>
          Security / Vulnerabilities
        </Heading>

        {error && (
          <Text color="red.500" mb={4}>
            Error: {error}
          </Text>
        )}

        <HStack justify="space-between" align="center" mb={6}>
          <DeviceSelector
            devices={devices}
            selectedDeviceId={selectedDeviceId}
            onSelect={setSelectedDeviceId}
          />
          <Button
            onClick={handleScan}
            isDisabled={scanning || !selectedDeviceId}
            colorScheme="primary"
            leftIcon={scanning && <Spinner size="xs" />}
          >
            {scanning ? 'Scanning vulnerabilities...' : 'Run Vulnerability Scan'}
          </Button>
          <Button
            onClick={openFirmwareModal}
            isDisabled={!selectedDeviceId || updatingFw}
            colorScheme="purple"
            leftIcon={updatingFw && <Spinner size="xs" />}
          >
            {updatingFw ? 'Updating...' : 'Update Firmware'}
          </Button>
        </HStack>
      </Box>

      {/* Vulnerability summary and chart */}
      {scanResult && (
        <Fade in>
          {/* Risk gauge */}
          <HStack justify="center" spacing={8} mb={6}>
            <Box bg={cardBg} p={4} borderRadius="md" shadow="md" width="150px">
              <Text textAlign="center" mb={2}>Risk Score</Text>
              <RadialBarChart width={120} height={120} cx="50%" cy="50%" innerRadius="80%" outerRadius="100%" barSize={10} data={[{ name:'', value: gaugeValue }]} startAngle={180} endAngle={0}>
                <RadialBar background minAngle={15} clockWise dataKey="value" fill={gaugeColor} />
              </RadialBarChart>
              <Text textAlign="center" mt={2} fontWeight="bold">{riskScore.toFixed(1)}/10</Text>
            </Box>
          </HStack>
          <SimpleGrid columns={{ base:1, md:4 }} spacing={6} mb={6}>
            {['critical','high','medium','low'].map(sev => (
              <Stat key={sev} bg={cardBg} borderLeftWidth={4} borderLeftColor={`${severityColorScheme(sev)}.500`} p={4} borderRadius="md" shadow="md">
                <StatLabel textTransform="capitalize">{sev}</StatLabel>
                <StatNumber>{severityCounts[sev] || 0}</StatNumber>
                <StatHelpText>{totalVulns ? `${((severityCounts[sev]||0)/totalVulns*100).toFixed(0)}%` : '0%'}</StatHelpText>
              </Stat>
            ))}
          </SimpleGrid>
          <Box bg={cardBg} p={4} borderRadius="md" shadow="md" mb={6} height="200px">
            <Text mb={2}>Severity Distribution</Text>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={Object.entries(severityCounts).map(([sev,count])=>({ sev, count }))}>
                <XAxis dataKey="sev" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill={accentColor}>
                  {Object.entries(severityCounts).map(([sev],i) => (
                    <Cell key={sev} fill={useColorModeValue(`${severityColorScheme(sev)}.500`, `${severityColorScheme(sev)}.300`)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Box>
        </Fade>
      )}

      {/* Placeholder when no scan results */}
      {!scanResult && (
        <Box mt={8} textAlign="center">
          {!selectedDeviceId ? (
            <Text color={useColorModeValue('gray.600','gray.400')}>
              Select a device and click "Run Scan" to view vulnerabilities.
            </Text>
          ) : (
            <Text color={useColorModeValue('gray.600','gray.400')}>
              No scan results. Click "Run Scan" to start vulnerability scanning.
            </Text>
          )}
        </Box>
      )}

      {scanResult && (
        <VStack align="stretch" spacing={4}>
          <Heading size="md">
            Scan Results for {devices.find((d) => d.hash_id === selectedDeviceId)?.name}
          </Heading>

          <HStack justifyContent="space-between">
            <Text fontSize="sm" color="gray.500">
              Showing {scanResult.vulnerabilities.length} vulnerabilities
            </Text>
            <Button
              size="sm"
              colorScheme="green"
              isDisabled={scanResult.vulnerabilities.filter(v => v.fix_available!=='firmware_update').length === 0}
              onClick={handleBulkRemediate}
            >
              Remediate All
            </Button>
          </HStack>

          <Box bg={cardBg} p={4} borderRadius="md" boxShadow="sm">
            <Table size="sm">
              <Thead>
                <Tr>
                  <Th>Details</Th>
                  <Th>Vuln ID</Th>
                  <Th>Title</Th>
                  <Th>Severity</Th>
                  <Th>Fix Available</Th>
                  <Th textAlign="center">Action</Th>
                </Tr>
              </Thead>
              <Tbody>
                {scanResult.vulnerabilities.length === 0 && (
                  <Tr>
                    <Td colSpan={6} textAlign="center">No vulnerabilities found</Td>
                  </Tr>
                )}
                {scanResult.vulnerabilities.map((v) => (
                  <Tr key={v.id} _hover={{ bg: useColorModeValue('gray.50', 'gray.700') }}>
                    <Td>
                      <IconButton
                        icon={<InfoOutlineIcon />}
                        size="xs"
                        variant="ghost"
                        aria-label="View Details"
                        onClick={() => { setSelectedVulnerability(v); openDrawer(); }}
                      />
                    </Td>
                    <Td fontFamily="mono" fontSize="xs">
                      {v.id}
                    </Td>
                    <Td>{v.title}</Td>
                    <Td>
                      <Badge colorScheme={severityColorScheme(v.severity)}>
                        {v.severity}
                      </Badge>
                    </Td>
                    <Td>
                      <Badge colorScheme={v.fix_available === 'firmware_update' ? 'purple' : 'gray'}>
                        {v.fix_available || '-'}
                      </Badge>
                    </Td>
                    <Td textAlign="center">
                      {v.fix_available === 'firmware_update' ? (
                        <Button
                          size="xs"
                          colorScheme="purple"
                          onClick={openFirmwareModal}
                          isLoading={updatingFw}
                        >
                          Update FW
                        </Button>
                      ) : (
                        <Button
                          size="xs"
                          colorScheme="green"
                          onClick={() => handleRemediate(v.id)}
                        >
                          Remediate
                        </Button>
                      )}
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        </VStack>
      )}
      {showFirmwareModal && (
        <Modal isOpen onClose={() => setShowFirmwareModal(false)}>
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>Select Firmware Version</ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              <VStack align="stretch" spacing={2}>
                {!compatibleFw.length ? (
                  <Text color={useColorModeValue('gray.600','gray.400')} textAlign="center">
                    No compatible firmware versions found.
                  </Text>
                ) : (
                  compatibleFw.map((fw) => (
                    <Button
                      key={fw.id}
                      size="sm"
                      isLoading={updatingFw}
                      onClick={() => handleFirmwareUpdate(fw.version)}
                    >
                      {fw.version} {fw.is_critical && ' (critical)'}
                    </Button>
                  ))
                )}
              </VStack>
            </ModalBody>
          </ModalContent>
        </Modal>
      )}
      {/* Vulnerability details drawer */}
      {selectedVulnerability && (
        <Drawer isOpen={isDrawerOpen} placement="right" onClose={closeDrawer} size="md">
          <DrawerOverlay />
          <DrawerContent>
            <DrawerHeader>Vulnerability Details</DrawerHeader>
            <DrawerCloseButton />
            <DrawerBody>
              <VStack align="start" spacing={4}>
                <Text fontWeight="bold" fontSize="lg">{selectedVulnerability.title}</Text>
                <Badge colorScheme={severityColorScheme(selectedVulnerability.severity)}>
                  {selectedVulnerability.severity}
                </Badge>
                <Text>{selectedVulnerability.description}</Text>
                <Text><strong>CVSS Score:</strong> {selectedVulnerability.cvss_score}</Text>
                <Text><strong>Affected Component:</strong> {selectedVulnerability.affected_component}</Text>
                <Text><strong>Fix Available:</strong> {selectedVulnerability.fix_available}</Text>
                <Text><strong>Remediation:</strong> {selectedVulnerability.remediation}</Text>
              </VStack>
            </DrawerBody>
            <DrawerFooter>
              {selectedVulnerability.fix_available === 'firmware_update' ? (
                <Button colorScheme="purple" onClick={() => { openFirmwareModal(); closeDrawer(); }}>
                  Update Firmware
                </Button>
              ) : (
                <Button colorScheme="green" onClick={() => { handleRemediate(selectedVulnerability.id); closeDrawer(); }}>
                  Remediate
                </Button>
              )}
            </DrawerFooter>
          </DrawerContent>
        </Drawer>
      )}
    </Box>
  );
}
