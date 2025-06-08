import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box,
  Heading,
  SimpleGrid,
  Card,
  CardHeader,
  CardBody,
  CardFooter,
  Badge,
  Flex,
  Spacer,
  Skeleton,
  useColorModeValue,
  Text,
  IconButton,
  Switch,
  Button,
  useDisclosure,
  useToast,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  FormControl,
  FormLabel,
  Input,
  Stack,
  Table,
  Thead,
  Tr,
  Th,
  Tbody,
  Td,
  CheckboxGroup,
  Checkbox
} from '@chakra-ui/react';
import { FiPlus, FiTrash, FiRefreshCw, FiPlay, FiEye, FiX, FiZap } from 'react-icons/fi';

import {
  listRules,
  createRule,
  updateRule,
  enableRule,
  disableRule,
  deleteRule,
  applyAllRules,
  applyRulesToDevice,
  getActiveExecutions,
  cancelAllExecutions,
  cancelExecution
} from '../services/rule-service.js';
import { getDevices } from '../services/device-service.js';

import toast from 'react-hot-toast';
import RuleBuilder from '../components/RuleBuilder';

export default function RulesPage() {
  const [rules, setRules] = useState([]);
  const [filterText, setFilterText] = useState('');
  const [detailModal, setDetailModal] = useState(false);
  const [selectedRule, setSelectedRule] = useState(null);
  const [ruleToEdit, setRuleToEdit] = useState(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [execModal, setExecModal] = useState(false);
  const [executions, setExecutions] = useState([]);
  const toastChakra = useToast();
  const cardBg = useColorModeValue('white', 'gray.700');

  // Devices for selection
  const [deviceOptions, setDeviceOptions] = useState([]);
  const [selectedDeviceIds, setSelectedDeviceIds] = useState([]);
  const [isEditingDevices, setIsEditingDevices] = useState(false);
  // Map id to name
  const devicesMap = useMemo(() => Object.fromEntries(deviceOptions.map(dev => [dev.id, dev.name])), [deviceOptions]);

  const fetchRules = async () => {
    try {
      const res = await listRules();
      if (res.status === 'success') {
        setRules(Array.isArray(res.data) ? res.data : []);
      } else {
        toast.error(res.message || 'Failed to load rules');
      }
    } catch (e) {
      toast.error('Error loading rules');
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  // Load devices for editing
  useEffect(() => {
    const loadDevices = async () => {
      try {
        const devs = await getDevices();
        setDeviceOptions(devs);
      } catch (e) {
        toastChakra.error('Failed to load devices');
      }
    };
    loadDevices();
  }, []);

  const handleEnableToggle = async (rule) => {
    const id = toast.loading('Updating rule...');
    try {
      let res;
      if (rule.is_enabled) {
        res = await disableRule(rule.id);
      } else {
        res = await enableRule(rule.id);
      }
      toast.success('Updated', { id });
      // Refresh list
      fetchRules();
    } catch (e) {
      toast.error('Failed', { id });
    }
  };

  const handleDelete = async (ruleId) => {
    const ok = window.confirm('Delete this rule?');
    if (!ok) return;
    const id = toast.loading('Deleting rule...');
    try {
      await deleteRule(ruleId);
      toast.success('Deleted', { id });
      // refresh rules list and close detail modal
      await fetchRules();
      closeDetailModal();
    } catch (e) {
      toast.error('Delete failed', { id });
    }
  };

  const handleCreateRule = async (ruleData) => {
    const id = toast.loading('Creating rule...');
    try {
      const res = await createRule(ruleData);
      if (res.status === 'success') {
        toast.success('Rule created', { id });
        fetchRules();
        onClose();
      } else {
        toast.error(res.message || 'Failed', { id });
      }
    } catch (e) {
      toast.error('Error creating rule', { id });
    }
  };

  const handleUpdateRule = async (data) => {
    const id = toast.loading('Updating rule...');
    try {
      const res = await updateRule(ruleToEdit.id, data);
      if (res.status === 'success') {
        toast.success('Rule updated', { id });
        fetchRules();
        setSelectedRule(res.data);
        setRuleToEdit(null);
        onClose();
      } else {
        toast.error(res.message || 'Failed to update rule', { id });
      }
    } catch (e) {
      toast.error('Error updating rule', { id });
    }
  };

  const runAllRules = async () => {
    const id = toast.loading('Applying all rules...');
    try {
      const res = await applyAllRules();
      if (res.status === 'success') {
        toast.success('Rules applied', { id });
      } else {
        toast.error(res.message || 'Failed', { id });
      }
    } catch (e) {
      toast.error('Error', { id });
    }
  };

  const openExecutions = async () => {
    setExecModal(true);
    try {
      const res = await getActiveExecutions();
      if (res.status === 'success') {
        // convert executions object to list
        let execList = [];
        if (Array.isArray(res.data)) {
          execList = res.data;
        } else if (res.data && res.data.executions) {
          execList = Object.entries(res.data.executions).map(([execution_id, execData]) => ({ execution_id, ...execData }));
        }
        setExecutions(execList);
      } else {
        toast.error(res.message || 'Failed to get executions');
      }
    } catch (e) {
      toast.error('Error fetching executions');
    }
  };

  const handleCancelExec = async (execId) => {
    const id = toast.loading('Cancelling...');
    try {
      const res = await cancelExecution(execId);
      toast.success('Cancelled', { id });
      setExecutions(executions.filter((e) => e.execution_id !== execId));
    } catch (e) {
      toast.error('Failed', { id });
    }
  };

  const handleCancelAllExec = async () => {
    const id = toast.loading('Cancelling all...');
    try {
      await cancelAllExecutions();
      toast.success('Cancelled', { id });
      setExecutions([]);
    } catch (e) {
      toast.error('Failed', { id });
    }
  };

  const filteredRules = useMemo(
    () => rules.filter(r =>
      r.name.toLowerCase().includes(filterText.toLowerCase()) ||
      r.rule_type.toLowerCase().includes(filterText.toLowerCase())
    ),
    [rules, filterText]
  );

  const openDetailModal = useCallback(rule => {
    setSelectedRule(rule);
    setSelectedDeviceIds(rule.target_device_ids || []);
    setIsEditingDevices(false);
    setDetailModal(true);
  }, []);
  const closeDetailModal = useCallback(() => { setSelectedRule(null); setDetailModal(false); }, []);

  const openEditModal = () => {
    setRuleToEdit(selectedRule);
    onOpen();
  };

  // Save updated devices
  const saveDevices = async () => {
    const id = toastChakra.loading('Updating devices...');
    try {
      const res = await updateRule(selectedRule.id, { target_device_ids: selectedDeviceIds });
      if (res.status === 'success') {
        toastChakra.success('Devices updated', { id });
        fetchRules();
        setSelectedRule(prev => ({ ...prev, target_device_ids: selectedDeviceIds }));
        setIsEditingDevices(false);
      } else {
        toastChakra.error(res.message || 'Failed to update devices', { id });
      }
    } catch (e) {
      toastChakra.error('Error updating devices', { id });
    }
  };

  return (
    <Box p={8}>
      <Heading mb={4}>Automation Rules</Heading>
      <Input
        placeholder="Search rules..."
        mb={4}
        value={filterText}
        onChange={e => setFilterText(e.target.value)}
      />
      <Stack direction="row" mb={4} spacing={3}>
        <Button leftIcon={<FiPlus />} colorScheme='blue' onClick={onOpen}>
          Add Rule
        </Button>
        <IconButton icon={<FiRefreshCw />} onClick={fetchRules} aria-label='Refresh' />
        <IconButton icon={<FiPlay />} onClick={runAllRules} aria-label='Run All' />
        <IconButton icon={<FiEye />} onClick={openExecutions} aria-label='Executions' />
      </Stack>

      <SimpleGrid minChildWidth="400px" spacing={10} justifyItems="center" mx="auto">
        {filteredRules.map(rule => (
          <Card
            key={rule.id}
            maxW="400px"
            w="100%"
            bg={cardBg}
            borderWidth="1px"
            borderColor={rule.is_enabled ? 'green.300' : 'red.300'}
            borderRadius="lg"
            boxShadow="sm"
            _hover={{ boxShadow: 'md', transform: 'translateY(-4px)' }}
            transition="all 0.3s"
            p={8}
          >
            <Flex align="center">
              <Box>
                <Heading size="lg" fontWeight="semibold">{rule.name}</Heading>
                <Stack direction="row" spacing={2} mt={2}>
                  <Badge colorScheme={rule.is_enabled ? 'green' : 'red'}>
                    {rule.is_enabled ? 'Enabled' : 'Disabled'}
                  </Badge>
                  <Badge colorScheme={rule.rule_type === 'schedule' ? 'purple' : 'blue'} variant="subtle">
                    {rule.rule_type.charAt(0).toUpperCase() + rule.rule_type.slice(1)}
                  </Badge>
                  {rule.rule_type === 'schedule' && rule.schedule && (() => {
                    const [dateStr, timeStr] = rule.schedule.split('T');
                    const [year, month, day] = dateStr.split('-').map(Number);
                    const [hour, minute] = timeStr.split(':').map(Number);
                    const schedDate = new Date(year, month - 1, day, hour, minute);
                    const nowDate = new Date();
                    const executed = rule.last_triggered !== null;
                    const label = nowDate >= schedDate
                      ? (executed ? 'Done' : 'Expired')
                      : 'Pending';
                    const color = nowDate >= schedDate
                      ? (executed ? 'green' : 'red')
                      : 'purple';
                    return <Badge colorScheme={color}>{label}</Badge>;
                  })()}
                </Stack>
              </Box>
              <Spacer />
              <IconButton icon={<FiEye />} onClick={() => openDetailModal(rule)} aria-label="View Details" variant="ghost" />
            </Flex>
            <Box mt={4}>
              <Text noOfLines={3}>{rule.description || 'No description provided.'}</Text>
            </Box>
            <CardFooter p={0} mt={4}>
              <Stack direction="row" spacing={2}>
                <IconButton icon={<FiPlay />} onClick={() => applyRulesToDevice(rule.id)} aria-label="Run Rule" />
                <IconButton icon={<FiTrash />} onClick={() => handleDelete(rule.id)} aria-label="Delete Rule" colorScheme="red" />
                <Switch isChecked={rule.is_enabled} onChange={() => handleEnableToggle(rule)} />
              </Stack>
            </CardFooter>
          </Card>
        ))}
      </SimpleGrid>

      {/* Executions Modal */}
      <Modal isOpen={execModal} onClose={() => setExecModal(false)} size='lg'>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Active Rule Executions</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {executions.length === 0 ? (
              <Box textAlign='center' color='gray.500'>No active executions.</Box>
            ) : (
              <Table size='sm'>
                <Thead>
                  <Tr>
                    <Th>ID</Th>
                    <Th>Rule ID</Th>
                    <Th>Status</Th>
                    <Th></Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {executions.map((ex) => (
                    <Tr key={ex.execution_id}>
                      <Td>{ex.execution_id}</Td>
                      <Td>{ex.rule_id}</Td>
                      <Td>{ex.status || 'running'}</Td>
                      <Td>
                        <IconButton size='xs' icon={<FiX />} aria-label='Cancel' onClick={() => handleCancelExec(ex.execution_id)} />
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            )}
          </ModalBody>
          <ModalFooter>
            <Button leftIcon={<FiZap />} variant='outline' mr={3} onClick={handleCancelAllExec} disabled={executions.length === 0}>Cancel All</Button>
            <Button onClick={() => setExecModal(false)}>Close</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Rule Detail Modal */}
      <Modal isOpen={detailModal} onClose={closeDetailModal} size='md'>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Rule Details</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {selectedRule && (
              <Stack spacing={4}>
                <Heading size="sm">General</Heading>
                <Text><strong>Name:</strong> {selectedRule.name}</Text>
                <Text><strong>Description:</strong> {selectedRule.description || '—'}</Text>
                <Text><strong>Type:</strong> <Badge colorScheme="blue">{selectedRule.rule_type}</Badge></Text>
                <Text><strong>Status:</strong> <Badge colorScheme={selectedRule.is_enabled ? 'green' : 'red'}>{selectedRule.is_enabled ? 'Enabled' : 'Disabled'}</Badge></Text>
                <Text><strong>Schedule:</strong> {selectedRule.schedule || '—'}</Text>
                <Text><strong>Priority:</strong> {selectedRule.priority}</Text>
                <Text><strong>Devices:</strong> {selectedRule.target_device_ids?.length
                  ? selectedRule.target_device_ids.map(id => devicesMap[id] || id).join(', ')
                  : 'All'}</Text>
                {selectedRule.conditions ? (
                  <>
                    <Heading size="sm" mt={4}>Conditions</Heading>
                    <Text><strong>Operator:</strong> {selectedRule.conditions.operator}</Text>
                    <Stack pl={4} spacing={2}>
                      {selectedRule.conditions.conditions.map((cond, i) => (
                        <Box key={i} border="1px" borderColor="gray.200" borderRadius="md" p={2}>
                          <Text fontWeight="bold">Condition {i + 1}</Text>
                          <Text>Type: {cond.type}</Text>
                          {cond.device_id && <Text>Device ID: {cond.device_id}</Text>}
                          {cond.sensor_type && <Text>Sensor: {cond.sensor_type}</Text>}
                          {cond.property && <Text>Property: {cond.property}</Text>}
                          <Text>Operator: {cond.operator}</Text>
                          <Text>Value: {String(cond.value)}</Text>
                        </Box>
                      ))}
                    </Stack>
                  </>
                ) : (
                  <Text>No conditions defined for this rule.</Text>
                )}

                <Heading size="sm" mt={4}>Actions</Heading>
                <Stack pl={4} spacing={2}>
                  {selectedRule.actions.map((act, i) => (
                    <Box key={i} border="1px" borderColor="gray.200" borderRadius="md" p={2}>
                      <Text fontWeight="bold">Action {i + 1}</Text>
                      <Text>Type: {act.type}</Text>
                      {act.parameters.action && <Text>Action: {act.parameters.action}</Text>}
                      {act.parameters.message && <Text>Message: {act.parameters.message}</Text>}
                      {act.parameters.recipients && <Text>Recipients: {act.parameters.recipients.join(', ')}</Text>}
                      {act.parameters.channels && <Text>Channels: {act.parameters.channels.join(', ')}</Text>}
                    </Box>
                  ))}
                </Stack>
              </Stack>
            )}
          </ModalBody>
          <ModalFooter>
            <Button colorScheme='blue' mr={3} onClick={openEditModal}>Edit Rule</Button>
            <Button colorScheme='red' mr={3} onClick={() => handleDelete(selectedRule.id)}>
              Delete Rule
            </Button>
            <Button onClick={closeDetailModal}>Close</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      <RuleBuilder
        isOpen={isOpen}
        onClose={() => { onClose(); setRuleToEdit(null); }}
        onCreate={handleCreateRule}
        initialData={ruleToEdit}
        onUpdate={handleUpdateRule}
      />
    </Box>
  );
}
