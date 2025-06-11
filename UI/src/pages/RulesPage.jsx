import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
  Box,
  Heading,
  SimpleGrid,
  Badge,
  Flex,
  useColorModeValue,
  Text,
  IconButton,
  Switch,
  Button,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Input,
  Stack,
  Table,
  Thead,
  Tr,
  Th,
  Tbody,
  Td,
  CheckboxGroup,
  Checkbox,
  VStack,
  HStack,
  Icon,
  ButtonGroup,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  Skeleton,
  Divider,
  Card,
  CardHeader,
  CardBody,
  CardFooter,
  Select,
} from '@chakra-ui/react';
import { FiPlus, FiTrash, FiPlay, FiEye, FiZap, FiClock, FiRefreshCw, FiX } from 'react-icons/fi';

import {
  listRules,
  createRule,
  updateRule,
  enableRule,
  disableRule,
  deleteRule,
  applyRulesToDevice,
  getActiveExecutions,
  cancelExecution,
} from '../services/rule-service.js';
import { getDevices } from '../services/device-service.js';
import toast from 'react-hot-toast';
import RuleBuilder from '../components/RuleBuilder';

import { FiInbox } from 'react-icons/fi';
import { motion } from 'framer-motion';

// Badge for schedule status
const ScheduleBadge = ({ schedule, lastTriggered }) => {
  if (!schedule) return null;
  const [dateStr, timeStr] = schedule.split('T');
  const [year, month, day] = dateStr.split('-').map(Number);
  const [hour, minute] = timeStr.split(':').map(Number);
  const schedDate = new Date(year, month - 1, day, hour, minute);
  const nowDate = new Date();
  const executed = lastTriggered !== null;

  let label = 'Pending';
  let color = 'purple';

  if (nowDate >= schedDate) {
    label = executed ? 'Done' : 'Expired';
    color = executed ? 'green' : 'red';
  }

  return <Badge colorScheme={color} variant="solid">{label}</Badge>;
};

// Helper for detail items in modal
const DetailItem = ({ label, children }) => (
  <VStack align="start" w="full" spacing={1}>
    <Text fontSize="sm" fontWeight="bold" color={useColorModeValue('gray.500', 'gray.400')}>
      {label}
    </Text>
    <Box w="full">{children}</Box>
  </VStack>
);

// Empty state component
const EmptyRulesState = ({ onAddRule }) => {
  const bgColor = useColorModeValue('gray.100', 'gray.700');
  const textColor = useColorModeValue('gray.500', 'gray.300');

  return (
    <Flex
      direction="column"
      align="center"
      justify="center"
      p={10}
      bg={bgColor}
      borderRadius="xl"
      textAlign="center"
      w="100%"
      gridColumn="1 / -1"
    >
      <Icon as={FiInbox} boxSize={12} color={textColor} mb={4} />
      <Heading size="md" mb={2}>No Rules Found</Heading>
      <Text color={textColor} mb={6}>
        Get started by creating a new rule.
      </Text>
      <Button
        leftIcon={<FiPlus />}
        colorScheme="blue"
        onClick={onAddRule}
      >
        Add Rule
      </Button>
    </Flex>
  );
};

// Reusable Rule Card Component
const RuleCard = ({ rule, devicesMap, onView, onRun, onDelete, onToggle }) => {
  const cardBg = useColorModeValue('white', 'gray.700');
  const textColor = useColorModeValue('gray.600', 'gray.300');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  
  // Dynamic colors based on rule type and status
  const accentColor = useColorModeValue(
    rule.rule_type === 'schedule' ? 'purple.500' : 'cyan.500',
    rule.rule_type === 'schedule' ? 'purple.300' : 'cyan.300'
  );
  const statusColor = rule.is_enabled ? 'green.400' : 'gray.400';
  const headerBg = useColorModeValue('gray.50', 'gray.700');

  const glow = useMemo(() => (rule.is_enabled ? '0 0 10px rgba(72,187,120,0.6)' : 'none'), [rule.is_enabled]);

  // Determine target device IDs from various possible fields
  const targetIds = rule.target_device_ids?.length ? rule.target_device_ids : (
    rule.device_ids?.length ? rule.device_ids : (rule.target_devices?.map(d => d.id) || [])
  );
  const deviceNames = targetIds.map(id => devicesMap[id]).filter(Boolean);
  const deviceCount = targetIds.length;
  const deviceLabel = deviceNames.length === 0
    ? `${deviceCount} devices`
    : (deviceNames.length > 3 ? `${deviceNames.length} devices` : deviceNames.join(', '));

  return (
    <Box bgGradient="linear(to-br, gray.600 0%, gray.900 100%)" p="1px" borderRadius="2xl" boxShadow={glow} _hover={{ transform: 'translateY(-4px)', boxShadow: 'xl' }} transition="all 0.2s ease-in-out" cursor="pointer" onClick={onView}>
      <Card
        bg={cardBg}
        borderRadius="2xl"
        h="100%"
        display="flex"
        flexDirection="column"
        borderWidth="1px"
        borderColor={borderColor}
        overflow="hidden"
      >
        <CardHeader 
          borderBottomWidth="1px" 
          borderColor={borderColor} 
          bg={headerBg}
          py={3}
          px={4}
        >
          <Flex justify="space-between" align="center">
            <HStack spacing={3} overflow="hidden">
              <Icon as={rule.rule_type === 'schedule' ? FiClock : FiZap} w={6} h={6} color={accentColor} />
              <Heading size="md" noOfLines={1} title={rule.name}>{rule.name}</Heading>
            </HStack>
            <Switch isChecked={rule.is_enabled} onChange={onToggle} colorScheme="green" />
          </Flex>
        </CardHeader>
        <CardBody flex="1" py={4} px={4}>
          <Text color={textColor} noOfLines={2} minH="40px">{rule.description || 'No description provided.'}</Text>
        </CardBody>
        <CardFooter 
          display="flex" 
          flexDirection="column" 
          mt="auto" 
          pt={3} 
          pb={3} 
          px={4}
          borderTopWidth="1px"
          borderColor={borderColor}
        >
          <HStack spacing={2} mb={3} wrap="wrap">
            <Badge colorScheme={rule.rule_type === 'schedule' ? 'purple' : 'cyan'} variant="subtle">
              {rule.rule_type.charAt(0).toUpperCase() + rule.rule_type.slice(1)}
            </Badge>
            {rule.rule_type === 'schedule' && (
              <ScheduleBadge schedule={rule.schedule} lastTriggered={rule.last_triggered} />
            )}
            <Badge colorScheme="blue" variant="subtle" title={deviceNames.length ? deviceNames.join(', ') : 'All devices'}>
              {deviceLabel}
            </Badge>
          </HStack>
          <ButtonGroup variant="ghost" spacing="1" w="full">
            <Button leftIcon={<FiEye />} size="sm" onClick={onView} flex="1">Details</Button>
            <IconButton 
              icon={<FiPlay />} 
              onClick={onRun} 
              aria-label="Run Rule" 
              isDisabled={!rule.is_enabled}
              _hover={{ color: useColorModeValue('green.500', 'green.300') }}
            />
            <IconButton 
              icon={<FiTrash />} 
              onClick={onDelete} 
              aria-label="Delete Rule" 
              _hover={{ color: useColorModeValue('red.500', 'red.300') }}
            />
          </ButtonGroup>
        </CardFooter>
      </Card>
    </Box>
  );
};

export default function RulesPage() {
  const [rules, setRules] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterText, setFilterText] = useState('');
  const [detailModal, setDetailModal] = useState(false);
  const [selectedRule, setSelectedRule] = useState(null);
  const [ruleToEdit, setRuleToEdit] = useState(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [execModal, setExecModal] = useState(false);
  const [executions, setExecutions] = useState([]);
  const [deviceOptions, setDeviceOptions] = useState([]);
  const [selectedDeviceIds, setSelectedDeviceIds] = useState([]);
  const [isEditingDevices, setIsEditingDevices] = useState(false);
  // Map device id and hash_id to device name for quick lookup
  const devicesMap = useMemo(() => {
    const pairs = [];
    deviceOptions.forEach(dev => {
      if (dev.id !== undefined) pairs.push([String(dev.id), dev.name]);
      if (dev.hash_id !== undefined) pairs.push([String(dev.hash_id), dev.name]);
    });
    return Object.fromEntries(pairs);
  }, [deviceOptions]);

  const [ruleToDelete, setRuleToDelete] = useState(null);
  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure();
  const cancelRef = useRef();

  const [statusFilter, setStatusFilter] = useState('all'); // all | enabled | disabled
  const [typeFilter, setTypeFilter] = useState('all'); // all | schedule | trigger
  const [sortOption, setSortOption] = useState('nameAZ'); // nameAZ | nameZA

  const fetchRules = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await listRules();
      setRules(Array.isArray(res.data) ? res.data : []);
    } catch (e) {
      toast.error('Error loading rules');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRules();
    const loadDevices = async () => {
      try {
        setDeviceOptions(await getDevices());
      } catch (e) {
        toast.error('Failed to load devices');
      }
    };
    loadDevices();
  }, [fetchRules]);

  const handleEnableToggle = async (rule) => {
    const id = toast.loading('Updating rule...');
    try {
      await (rule.is_enabled ? disableRule(rule.id) : enableRule(rule.id));
      toast.success('Rule updated', { id });
      fetchRules();
    } catch (e) {
      toast.error('Failed to update rule', { id });
    }
  };

  const handleDeleteClick = (ruleId) => {
    setRuleToDelete(ruleId);
    onDeleteOpen();
  };

  const confirmDelete = async () => {
    if (!ruleToDelete) return;
    const id = toast.loading('Deleting rule...');
    try {
      await deleteRule(ruleToDelete);
      toast.success('Rule deleted', { id });
      fetchRules();
      if (selectedRule && selectedRule.id === ruleToDelete) {
        closeDetailModal();
      }
    } catch (e) {
      toast.error('Failed to delete rule', { id });
    } finally {
      onDeleteClose();
      setRuleToDelete(null);
    }
  };

  const handleRuleSubmit = (data) => {
    const isEditing = !!ruleToEdit;
    const promise = isEditing ? updateRule(ruleToEdit.id, data) : createRule(data);

    toast.promise(promise, {
      loading: isEditing ? 'Updating rule...' : 'Creating rule...',
      success: () => {
        fetchRules();
        return `Rule ${isEditing ? 'updated' : 'created'} successfully!`;
      },
      error: `Failed to ${isEditing ? 'update' : 'create'} rule.`,
    });
  };

  const openExecutions = async () => {
    setExecModal(true);
    try {
      const res = await getActiveExecutions();
      let execList = [];
      if (Array.isArray(res.data)) {
        execList = res.data;
      } else if (res.data && res.data.executions) {
        execList = Object.entries(res.data.executions).map(([execution_id, execData]) => ({ execution_id, ...execData }));
      }
      setExecutions(execList);
    } catch (e) {
      toast.error('Error getting executions');
    }
  };

  const stopExecution = async (execId) => {
    const id = toast.loading('Stopping execution...');
    try {
      await cancelExecution(execId);
      toast.success('Execution stopped', { id });
      openExecutions(); // Refresh list
    } catch (e) {
      toast.error('Failed to stop execution', { id });
    }
  };

  const openDetailModal = (rule) => {
    setSelectedRule(rule);
    setDetailModal(true);
  };

  const closeDetailModal = () => {
    setDetailModal(false);
    setSelectedRule(null);
    setIsEditingDevices(false);
  };
  
  const handleDeviceUpdate = async () => {
    // Placeholder for device update logic
    toast.success('Device list updated!');
    setIsEditingDevices(false);
  }

  const displayRules = useMemo(() => {
    let list = rules.filter(rule => rule.name.toLowerCase().includes(filterText.toLowerCase()));

    // Status filter
    if (statusFilter === 'enabled') list = list.filter(r => r.is_enabled);
    else if (statusFilter === 'disabled') list = list.filter(r => !r.is_enabled);

    // Type filter
    if (typeFilter === 'schedule') list = list.filter(r => r.rule_type === 'schedule');
    else if (typeFilter === 'trigger') list = list.filter(r => r.rule_type !== 'schedule');

    // Sorting
    if (sortOption === 'nameAZ') list = list.sort((a, b) => a.name.localeCompare(b.name));
    else if (sortOption === 'nameZA') list = list.sort((a, b) => b.name.localeCompare(a.name));

    return list;
  }, [rules, filterText, statusFilter, typeFilter, sortOption]);
  
  const cardBg = useColorModeValue('white', 'gray.700');

  return (
    <Box p={{ base: 4, md: 8 }} bg={useColorModeValue('gray.50', 'gray.900')} minH="100vh">
      <Flex justify="space-between" align={{ base: 'start', md: 'center' }} mb={8} direction={{ base: 'column', md: 'row' }} gap={4}>
        <VStack align="start" mb={{ base: 4, md: 0 }}>
          <Heading as="h1" size="xl" bgGradient="linear(to-r, blue.500, purple.500)" bgClip="text">
            Rules Engine
          </Heading>
          <Text color={useColorModeValue('gray.600', 'gray.400')}>
            Automate actions based on triggers or schedules.
          </Text>
        </VStack>
        <HStack spacing={3}>
          <IconButton icon={<FiRefreshCw />} onClick={fetchRules} aria-label="Refresh Rules" variant="ghost" colorScheme="gray" />
          <Button leftIcon={<FiZap />} onClick={openExecutions} variant="outline">
            Executions
          </Button>
          <Button 
            leftIcon={<FiPlus />} 
            colorScheme="blue" 
            onClick={() => { setRuleToEdit(null); onOpen(); }} 
            boxShadow="md"
            _hover={{ boxShadow: 'lg' }}
          >
            Add Rule
          </Button>
        </HStack>
      </Flex>

      <Input
        placeholder="Filter rules by name..."
        value={filterText}
        onChange={(e) => setFilterText(e.target.value)}
        mb={8}
        bg={useColorModeValue('white', 'gray.700')}
        focusBorderColor="blue.500"
      />

      {/* Additional Filters */}
      <HStack spacing={4} mb={8} flexWrap="wrap">
        <Select w="160px" value={statusFilter} onChange={(e)=>setStatusFilter(e.target.value)} bg={useColorModeValue('white','gray.700')}>
          <option value="all">All status</option>
          <option value="enabled">Enabled</option>
          <option value="disabled">Disabled</option>
        </Select>
        <Select w="160px" value={typeFilter} onChange={(e)=>setTypeFilter(e.target.value)} bg={useColorModeValue('white','gray.700')}>
          <option value="all">All types</option>
          <option value="schedule">Schedule</option>
          <option value="trigger">Trigger</option>
        </Select>
        <Select w="180px" value={sortOption} onChange={(e)=>setSortOption(e.target.value)} bg={useColorModeValue('white','gray.700')}>
          <option value="nameAZ">Sort: Name A-Z</option>
          <option value="nameZA">Sort: Name Z-A</option>
        </Select>
      </HStack>

      <motion.div
        initial="hidden"
        animate="visible"
        variants={{
          visible: {
            transition: {
              staggerChildren: 0.05,
            },
          },
        }}
      >
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3, xl: 4 }} spacing={6}>
          {isLoading
            ? Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} height="320px" borderRadius="xl" />)
            : displayRules.length > 0 ? displayRules.map((rule) => (
                <motion.div
                  key={rule.id}
                  variants={{
                    hidden: { y: 20, opacity: 0 },
                    visible: { y: 0, opacity: 1 },
                  }}
                  transition={{ duration: 0.3 }}
                >
                  <RuleCard
                    rule={rule}
                    devicesMap={devicesMap}
                    onView={() => openDetailModal(rule)}
                    onRun={() => applyRulesToDevice(rule.id)}
                    onDelete={() => handleDeleteClick(rule.id)}
                    onToggle={() => handleEnableToggle(rule)}
                  />
                </motion.div>
              ))
            : <EmptyRulesState onAddRule={() => { setRuleToEdit(null); onOpen(); }} />
          }
        </SimpleGrid>
      </motion.div>

      <AlertDialog isOpen={isDeleteOpen} leastDestructiveRef={cancelRef} onClose={onDeleteClose} isCentered motionPreset="slideInBottom">
        <AlertDialogOverlay bg="blackAlpha.600" />
        <AlertDialogContent bg={useColorModeValue('white', 'gray.800')} borderRadius="xl">
          <AlertDialogHeader 
            fontSize="lg" 
            fontWeight="bold" 
            borderBottomWidth="1px" 
            borderColor={useColorModeValue('gray.200', 'gray.700')}
          >
            <HStack>
              <Icon as={FiTrash} color="red.500" w={5} h={5} />
              <Text>Confirm Deletion</Text>
            </HStack>
          </AlertDialogHeader>
          <AlertDialogBody py={6}>
            Are you sure you want to delete this rule? This action cannot be undone.
          </AlertDialogBody>
          <AlertDialogFooter borderTopWidth="1px" borderColor={useColorModeValue('gray.200', 'gray.700')}>
            <Button ref={cancelRef} onClick={onDeleteClose} variant="ghost">
              Cancel
            </Button>
            <Button colorScheme="red" onClick={confirmDelete} ml={3}>
              Delete Rule
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Executions Modal */}
      <Modal isOpen={execModal} onClose={() => setExecModal(false)} size='2xl' isCentered motionPreset="slideInBottom">
        <ModalOverlay bg="blackAlpha.500" />
        <ModalContent bg={useColorModeValue('gray.50', 'gray.800')} borderRadius="xl">
          <ModalHeader borderBottomWidth="1px" borderColor={useColorModeValue('gray.200', 'gray.700')}>Active Rule Executions</ModalHeader>
          <ModalCloseButton />
          <ModalBody p={6}>
            {executions.length > 0 ? (
              <Table variant='simple'>
                <Thead>
                  <Tr>
                    <Th>Execution ID</Th>
                    <Th>Rule Name</Th>
                    <Th>Device Name</Th>
                    <Th>Status</Th>
                    <Th>Action</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {executions.map(exec => (
                    <Tr key={exec.execution_id} _hover={{ bg: useColorModeValue('gray.100', 'gray.700') }}>
                      <Td fontFamily="monospace">{exec.execution_id.slice(0, 8)}</Td>
                      <Td>{rules.find(r => r.id === exec.rule_id)?.name || 'N/A'}</Td>
                      <Td>{devicesMap[exec.device_id] || 'N/A'}</Td>
                      <Td><Badge colorScheme="blue" variant="solid">Running</Badge></Td>
                      <Td>
                        <IconButton
                          icon={<FiX />}
                          onClick={() => stopExecution(exec.execution_id)}
                          aria-label="Stop Execution"
                          colorScheme='red'
                          variant="ghost"
                          size="sm"
                        />
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            ) : (
              <Flex direction="column" align="center" justify="center" p={8} bg={useColorModeValue('gray.100', 'gray.700')} borderRadius="lg">
                <Icon as={FiInbox} boxSize={10} color={useColorModeValue('gray.400', 'gray.500')} mb={4} />
                <Heading size="sm">No Active Executions</Heading>
                <Text color={useColorModeValue('gray.500', 'gray.400')} mt={2}>All automated tasks are currently idle.</Text>
              </Flex>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>

      {/* Rule Details Modal */}
      {selectedRule && (
        <Modal isOpen={detailModal} onClose={closeDetailModal} size="xl" isCentered motionPreset="slideInBottom">
          <ModalOverlay bg="blackAlpha.500" />
          <ModalContent bg={useColorModeValue('gray.50', 'gray.800')} borderRadius="xl">
            <ModalHeader borderBottomWidth="1px" borderColor={useColorModeValue('gray.200', 'gray.700')}>{selectedRule.name}</ModalHeader>
            <ModalCloseButton />
            <ModalBody p={6}>
              {isEditingDevices ? (
                <VStack spacing={4} align="stretch">
                  <Heading size="sm">Edit Attached Devices</Heading>
                  <Box p={4} bg={useColorModeValue('gray.100', 'gray.700')} borderRadius="lg" maxH="200px" overflowY="auto">
                    <CheckboxGroup
                      value={selectedDeviceIds}
                      onChange={setSelectedDeviceIds}
                    >
                      <VStack align="start" spacing={2}>
                        {deviceOptions.map(dev => (
                          <Checkbox key={dev.id} value={dev.id}>{dev.name}</Checkbox>
                        ))}
                      </VStack>
                    </CheckboxGroup>
                  </Box>
                  <HStack justify="flex-end">
                    <Button onClick={() => setIsEditingDevices(false)} variant="ghost">Cancel</Button>
                    <Button onClick={handleDeviceUpdate} colorScheme="blue">Save Devices</Button>
                  </HStack>
                </VStack>
              ) : (
                <VStack spacing={5} align="stretch">
                  <DetailItem label="Description">
                    <Text color={useColorModeValue('gray.600', 'gray.300')}>{selectedRule.description || 'No description provided.'}</Text>
                  </DetailItem>
                  <Divider />
                  <HStack spacing={4} align="start">
                    <DetailItem label="Rule Type">
                      <Badge colorScheme={selectedRule.rule_type === 'schedule' ? 'purple' : 'cyan'} variant="solid">
                        {selectedRule.rule_type}
                      </Badge>
                    </DetailItem>
                    {selectedRule.rule_type === 'schedule' && (
                      <DetailItem label="Schedule">
                        <Text color={useColorModeValue('gray.700', 'gray.200')}>{new Date(selectedRule.schedule).toLocaleString()}</Text>
                      </DetailItem>
                    )}
                  </HStack>
                  <DetailItem label="Attached Devices">
                    <Text color={useColorModeValue('gray.700', 'gray.200')}>
                      {(() => {
                        const ids = selectedRule.target_device_ids?.length ? selectedRule.target_device_ids : (selectedRule.device_ids?.length ? selectedRule.device_ids : (selectedRule.target_devices?.map(d=>d.id) || []));
                        if (ids.length === 0) return 'All devices';
                        const names = ids.map(id => devicesMap[id]).filter(Boolean);
                        return names.length > 0 ? names.join(', ') : `${ids.length} devices`;
                      })()}
                    </Text>
                  </DetailItem>
                </VStack>
              )}
            </ModalBody>
            <ModalFooter borderTopWidth="1px" borderColor={useColorModeValue('gray.200', 'gray.700')}>
              {!isEditingDevices && (
                <Button onClick={() => {
                  setSelectedDeviceIds(selectedRule.device_ids || []);
                  setIsEditingDevices(true);
                }}>Edit Devices</Button>
              )}
              <HStack ml="auto">
                <Button variant="ghost" onClick={closeDetailModal}>Close</Button>
                <Button colorScheme="blue" onClick={() => { closeDetailModal(); setRuleToEdit(selectedRule); onOpen(); }}>Edit Rule</Button>
              </HStack>
            </ModalFooter>
          </ModalContent>
        </Modal>
      )}

      {/* Create/Edit Rule Modal */}
      <RuleBuilder
        isOpen={isOpen}
        onClose={() => { setRuleToEdit(null); onClose(); }}
        onSubmit={handleRuleSubmit}
        existingRule={ruleToEdit}
        devices={deviceOptions}
      />
    </Box>
  );
}
