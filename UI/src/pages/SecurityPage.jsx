import React, { useState, useEffect } from 'react';
import { getDevices } from '../services/device-service.js';
import {
  startVulnerabilityScan,
  getVulnerabilityScanResults,
  remediateVulnerability,
  bulkRemediateVulnerabilities
} from '../services/security-service.js';
import { getCompatibleFirmware, startFirmwareUpdate, getUpdateStatus } from '../services/firmware-service.js';
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
  useToken,
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
  Fade,
  CircularProgress,
  Icon,
  Input,
  Select,
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
import { InfoOutlineIcon, TriangleUpIcon, TriangleDownIcon } from '@chakra-ui/icons';
import DeviceSelector from '../components/DeviceSelector';
import FullScreenLoader from '../components/FullScreenLoader';
// removed unused ant icons causing build error
import ScanPlaceholder from '../components/ScanPlaceholder';
import RemediationAnimation from '../components/RemediationAnimation';

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
  const [showRemediationAnim, setShowRemediationAnim] = useState(false);
  const { isOpen: isDrawerOpen, onOpen: openDrawer, onClose: closeDrawer } = useDisclosure();

  // UI state: filtering & sorting
  const [filterSeverity, setFilterSeverity] = useState('all'); // all | critical | high | medium | low | fixable
  const [searchText, setSearchText] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'severity', direction: 'desc' });

  // Helper to toggle sorting
  const toggleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  // Theme-driven styling
  const cardBg = useColorModeValue('white', 'gray.800');
  const accentColor = useColorModeValue('blue.500', 'blue.300');
  const [accentColorHex] = useToken('colors', [accentColor]);

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
    // Include ALL vulnerabilities for remediation, including those requiring firmware updates
    const ids = scanResult.vulnerabilities.map(v => v.id);
    if (ids.length === 0) {
      toast('No vulnerabilities to remediate', { icon: 'ℹ️' });
      return;
    }
    setShowRemediationAnim(true);
    const animStart = Date.now();
    const loadingId = toast.loading('Performing bulk remediation...');
    try {
      const map = { [selectedDeviceId]: ids };
      const res = await bulkRemediateVulnerabilities(map);
      const finish = () => {
        toast.success(res.message || 'Bulk remediation completed', { id: loadingId });
        setShowRemediationAnim(false);
      };
      const elapsed = Date.now() - animStart;
      const remain = 8000 - elapsed; // 8s min
      if (remain > 0) {
        setTimeout(finish, remain);
      } else {
        finish();
      }
      // Refresh scan results
      const refreshed = await getVulnerabilityScanResults(scanResult.id);
      if (refreshed.status === 'success') {
        setScanResult(refreshed.scan);
      }
    } catch (err) {
      toast.error(err.message || 'Bulk remediation failed', { id: loadingId });
      const elapsed = Date.now() - animStart;
      const remain = 8000 - elapsed; // 8s min
      if (remain > 0) {
        setTimeout(()=>setShowRemediationAnim(false), remain);
      } else {
        setShowRemediationAnim(false);
      }
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
    const toastId = toast.loading('Starting firmware update...');
    try {
      setUpdatingFw(true);
      const res = await startFirmwareUpdate(selectedDeviceId, version);
      if (!res.update_id) throw new Error('Failed to start update');
      toast.success('Firmware update queued', { id: toastId });

      // Poll status
      let status;
      do {
        await new Promise(r => setTimeout(r, 2000));
        status = await getUpdateStatus(res.update_id);
      } while (status.status === 'started' || status.status === 'in_progress');

      toast.success(`Firmware update ${status.status}`, { duration: 4000 });

      // Refresh compatible firmware list and scan results
      const list = await getCompatibleFirmware(selectedDeviceId);
      setCompatibleFw(list);
      if (scanResult?.id) {
        const refreshed = await getVulnerabilityScanResults(scanResult.id);
        if (refreshed.status === 'success') setScanResult(refreshed.scan);
      }
      setShowFirmwareModal(false);
    } catch (e) {
      toast.error(e.message || 'Update failed', { id: toastId });
    } finally {
      setUpdatingFw(false);
    }
  };

  // Compute severity distribution
  // Normalise severity keys to lowercase to avoid mismatches (e.g. "HIGH" vs "high")
  const severityCounts = scanResult?.vulnerabilities.reduce((acc, v) => {
    const sev = (v.severity || '').toLowerCase();
    acc[sev] = (acc[sev] || 0) + 1;
    return acc;
  }, {}) || {};
  const totalVulns = scanResult?.vulnerabilities.length || 0;

  // Compute and style risk gauge
  const riskScore = scanResult?.result?.risk_score || 0;
  const gaugeColorToken = riskScore > 7 ? 'red.400' : riskScore > 4 ? 'orange.400' : 'green.400';
  const [gaugeColorHex] = useToken('colors', [gaugeColorToken]);

  // Apply filtering & sorting to vulnerability list
  const displayedVulns = React.useMemo(() => {
    if (!scanResult) return [];
    let list = [...scanResult.vulnerabilities];
    if (searchText.trim()) {
      const q = searchText.toLowerCase();
      list = list.filter(v => v.title.toLowerCase().includes(q) || String(v.id).toLowerCase().includes(q));
    }

    if (filterSeverity === 'fixable') {
      list = list.filter(v => v.fix_available && v.fix_available !== '');
    } else if (filterSeverity !== 'all') {
      list = list.filter(v => v.severity.toLowerCase() === filterSeverity);
    }
    // Sorting
    const { key, direction } = sortConfig;
    list.sort((a,b) => {
      let valA = a[key];
      let valB = b[key];
      if (key === 'severity') {
        const order = { critical:4, high:3, medium:2, low:1 };
        valA = order[valA.toLowerCase()] || 0;
        valB = order[valB.toLowerCase()] || 0;
      }
      if (valA < valB) return direction==='asc'? -1: 1;
      if (valA > valB) return direction==='asc'? 1: -1;
      return 0;
    });
    return list;
  }, [scanResult, filterSeverity, sortConfig, searchText]);

  return (
    <Box p={8}>
      <FullScreenLoader isOpen={scanning} message="Scanning vulnerabilities..." />
      {showRemediationAnim && <RemediationAnimation />}
      <Box bgGradient="linear(to-r, gray.800 0%, gray.700 40%, gray.800 100%)" p="1px" borderRadius="xl" mb={8} boxShadow="inner">
        <Box bg={cardBg} borderRadius="xl" p={6}>
          <Heading size="lg" mb={4} bgGradient="linear(to-r, purple.600, blue.500)" bgClip="text">
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
      </Box>

      {/* Vulnerability summary and chart */}
      {scanResult && (
        <Fade in>
          {/* Risk gauge */}
          <HStack justify="center" spacing={8} mb={6}>
            <Box bg={cardBg} p={6} borderRadius="lg" shadow="md" textAlign="center">
              <Text mb={2}>Risk Score</Text>
              <CircularProgress value={riskScore*10} size="120px" thickness="10px" color={gaugeColorToken} trackColor={useColorModeValue('gray.700','gray.600')} />
              <Text mt={2} fontWeight="bold">{riskScore.toFixed(1)}/10</Text>
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
                <Bar dataKey="count" fill={accentColorHex}>
                  {Object.entries(severityCounts).map(([sev],i) => {
                    const token = `${severityColorScheme(sev)}.400`;
                    const [hex] = useToken('colors', [token]);
                    return <Cell key={sev} fill={hex} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Box>
        </Fade>
      )}

      {/* Placeholder when no scan results */}
      {!scanResult && (
        <ScanPlaceholder variant={!selectedDeviceId ? 'no-device' : 'ready'} />
      )}
      {scanResult && (
        <VStack align="stretch" spacing={4}>
          <Heading size="md">
            Scan Results for {devices.find((d) => d.hash_id === selectedDeviceId)?.name}
          </Heading>

          <HStack justifyContent="space-between" flexWrap="wrap" gap={4}>
            <Text fontSize="sm" color="gray.500">
              Showing {displayedVulns.length} / {scanResult.vulnerabilities.length} vulnerabilities
            </Text>
            <HStack spacing={3}>
              <Input
                size="sm"
                placeholder="Search title or ID"
                value={searchText}
                onChange={(e)=>setSearchText(e.target.value)}
                maxW="200px"
                bg={useColorModeValue('white','gray.700')}
              />
              <Select
                size="sm"
                value={filterSeverity}
                onChange={(e)=>setFilterSeverity(e.target.value)}
                maxW="160px"
                bg={useColorModeValue('white','gray.700')}
              >
                <option value="all">All severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
                <option value="fixable">Fixable</option>
              </Select>
              <Button
                size="sm"
                colorScheme="green"
                isDisabled={scanResult.vulnerabilities.length === 0}
                onClick={handleBulkRemediate}
              >
                Remediate All
              </Button>
            </HStack>
          </HStack>

          <Box bg={cardBg} p={4} borderRadius="md" boxShadow="lg" overflowX="auto">
            <Table size="sm">
              <Thead position="sticky" top={0} zIndex={1} bg={cardBg} backdropFilter="blur(6px)">
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
                {displayedVulns.length === 0 && (
                  <Tr>
                    <Td colSpan={6} textAlign="center">No vulnerabilities found</Td>
                  </Tr>
                )}
                {displayedVulns.map((v) => (
                  <Tr key={v.id} _hover={{ bg: useColorModeValue('gray.50', 'gray.700') }} borderLeftWidth={4} borderLeftColor={`${severityColorScheme(v.severity)}.400`}>
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
