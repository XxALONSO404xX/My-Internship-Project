import React, { useState, useEffect } from 'react';
import { getDevices } from '../services/device-service.js';
import {
  startVulnerabilityScan,
  getVulnerabilityScanResults,
  getDeviceVulnerabilityHistory,
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
  Drawer,
  DrawerOverlay,
  DrawerContent,
  DrawerHeader,
  DrawerBody,
  DrawerFooter,
  useDisclosure,
  IconButton
} from '@chakra-ui/react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
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
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [selectedVulnerability, setSelectedVulnerability] = useState(null);
  const { isOpen: isDrawerOpen, onOpen: openDrawer, onClose: closeDrawer } = useDisclosure();

  // Card background adapts to color mode
  const cardBg = useColorModeValue('white', 'gray.800');

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

  // Fetch vulnerability history when device changes
  useEffect(() => {
    if (!selectedDeviceId) return;
    async function loadHistory() {
      setLoadingHistory(true);
      try {
        const res = await getDeviceVulnerabilityHistory(selectedDeviceId);
        if (res.status !== 'success') throw new Error(res.error || 'History fetch failed');
        setScanResult({ ...res, vulnerabilities: res.history || [] });
      } catch (err) {
        setError(err.message);
      } finally {
        setLoadingHistory(false);
      }
    }
    loadHistory();
  }, [selectedDeviceId]);

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
        <Box mb={6}>
          {/* Severity counts */}
          <SimpleGrid columns={{ base: 2, md: 5 }} spacing={4} mb={4}>
            {['critical','high','medium','low'].map((level) => (
              <Stat key={level} bg={cardBg} p={4} borderRadius="md" boxShadow="sm">
                <StatLabel>{level.charAt(0).toUpperCase() + level.slice(1)}</StatLabel>
                <StatNumber>{scanResult.vulnerabilities.filter(v => v.severity.toLowerCase() === level).length}</StatNumber>
              </Stat>
            ))}
            <Stat key="riskScore" bg={cardBg} p={4} borderRadius="md" boxShadow="sm">
              <StatLabel>Risk Score</StatLabel>
              <StatNumber>{scanResult.result?.risk_score ?? '-'}</StatNumber>
            </Stat>
          </SimpleGrid>
          <Text color="gray.500" mb={4}>{scanResult.result?.scan_summary}</Text>
          {/* Severity distribution pie chart */}
          <Box bg={cardBg} p={4} borderRadius="md" boxShadow="sm" height="300px">
            <Text mb={2}>Severity Distribution</Text>
            <ResponsiveContainer width="100%" height="90%">
              <PieChart>
                <Pie
                  data={[
                    { name: 'Critical', value: scanResult.vulnerabilities.filter(v => v.severity.toLowerCase() === 'critical').length },
                    { name: 'High', value: scanResult.vulnerabilities.filter(v => v.severity.toLowerCase() === 'high').length },
                    { name: 'Medium', value: scanResult.vulnerabilities.filter(v => v.severity.toLowerCase() === 'medium').length },
                    { name: 'Low', value: scanResult.vulnerabilities.filter(v => v.severity.toLowerCase() === 'low').length }
                  ]}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label
                >
                  {['#e53e3e','#dd6b20','#d69e2e','#38a169'].map((color, i) => (
                    <Cell key={i} fill={color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend verticalAlign="bottom" height={36} />
              </PieChart>
            </ResponsiveContainer>
          </Box>
        </Box>
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
