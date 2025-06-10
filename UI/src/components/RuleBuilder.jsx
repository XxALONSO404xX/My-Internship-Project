import React, { useState, useEffect } from 'react';
import { useForm, Controller, useFieldArray } from 'react-hook-form';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  Button,
  FormControl,
  FormLabel,
  Input,
  Select,
  Switch,
  IconButton,
  Box,
  Checkbox,
  CheckboxGroup,
  HStack,
  VStack,
  RadioGroup,
  Radio,
  FormErrorMessage,
  useColorModeValue,
  Heading,
  Divider,
  Text,
  SimpleGrid,
  useToast,
} from '@chakra-ui/react';
import { FiPlus, FiTrash } from 'react-icons/fi';
import { getDevices } from '../services/device-service.js';

// Helper component to create styled sections in the form
const FormSection = ({ title, children }) => (
  <VStack spacing={4} align="stretch" w="full">
    <Heading size="sm" color={useColorModeValue('gray.600', 'gray.300')}>{title}</Heading>
    <Box pl={4} borderLeftWidth="2px" borderColor={useColorModeValue('gray.200', 'gray.700')}>
      <VStack spacing={4} align="stretch">
        {children}
      </VStack>
    </Box>
  </VStack>
);

export default function RuleBuilder({ isOpen, onClose, onSubmit, existingRule, devices }) {
  const toast = useToast();
  const isEditing = !!existingRule;

  // Normalize device IDs as strings, prefer hash_id when present (older API)
  const deviceList = devices.map(d => ({ id: String(d.hash_id ?? d.id), name: d.name }));

  const defaultValues = {
    name: '',
    description: '',
    rule_type: 'condition',
    is_enabled: true,
    priority: 1,
    scheduleType: 'once',
    onceDatetime: '',
    intervalValue: 1,
    intervalUnit: 'minutes',
    time: '',
    weekdays: [],
    target_device_ids: [],
    conditions: [],
    actions: [],
  };

  const { register, handleSubmit, watch, setValue, setError, reset, control, formState: { errors, isValid } } = useForm({ 
    defaultValues,
    mode: 'onChange', 
    shouldFocusError: false
  });

  useEffect(() => {
    if (isEditing && existingRule) {
      const scheduleParts = existingRule.schedule ? existingRule.schedule.split(' ') : [];
      let parsedSchedule = {};

      if (existingRule.schedule && existingRule.schedule.includes('*/')) { // Interval
        parsedSchedule = { scheduleType: 'interval', intervalValue: parseInt(scheduleParts[0].replace('*/', '')), intervalUnit: scheduleParts[1] };
      } else if (existingRule.schedule) { // Time-based
        const time = scheduleParts[0];
        const weekdays = scheduleParts[4];
        if (weekdays && weekdays !== '*') { // Weekly
          parsedSchedule = { scheduleType: 'weekly', time, weekdays: weekdays.split(',') };
        } else if (time.includes(':')) { // Daily
          parsedSchedule = { scheduleType: 'daily', time };
        } else { // Once
          parsedSchedule = { scheduleType: 'once', onceDatetime: existingRule.schedule };
        }
      }
      const initialDeviceIds = (existingRule.target_devices || []).map(d => String(d.id));
      reset({ ...defaultValues, ...existingRule, ...parsedSchedule, target_device_ids: initialDeviceIds });
    } else {
      reset(defaultValues);
    }
  }, [isEditing, existingRule, reset]);

  const { fields: condFields, append: addCondition, remove: removeCondition } = useFieldArray({ control, name: 'conditions' });
  const { fields: actFields, append: addAction, remove: removeAction } = useFieldArray({ control, name: 'actions' });

  const [filterText, setFilterText] = useState('');
  const filteredDeviceList = deviceList.filter(d => d.name.toLowerCase().includes(filterText.toLowerCase()));
  const [showAllDevices, setShowAllDevices] = useState(false);
  const SHOW_COUNT = 5;
  const visibleDevices = showAllDevices ? filteredDeviceList : filteredDeviceList.slice(0, SHOW_COUNT);

  const inputBg = useColorModeValue('white', 'gray.700');
  const borderColor = useColorModeValue('gray.300', 'gray.600');

  // Get current local time in YYYY-MM-DDTHH:mm format for the datetime-local input
  const now = new Date();
  const offset = now.getTimezoneOffset();
  const minDatetimeLocal = new Date(now.getTime() - (offset*60*1000)).toISOString().slice(0, 16);

  const handleFormSubmit = async (data) => {
    if (!data.target_device_ids || data.target_device_ids.length === 0) {
      setError('target_device_ids', { type: 'manual', message: 'Select at least one device' });
      return;
    }

    if (data.rule_type === 'schedule') {
      switch(data.scheduleType) {
        case 'once': data.schedule = data.onceDatetime; break;
        case 'interval': data.schedule = `*/${data.intervalValue} ${data.intervalUnit}`; break;
        case 'daily': data.schedule = `${data.time} * * *`; break;
        case 'weekly': data.schedule = `${data.time} * * ${data.weekdays.join(',')}`; break;
        default: data.schedule = '';
      }
    }

    if (data.conditions && data.conditions.length > 0) {
      data.conditions = { operator: 'AND', conditions: data.conditions };
    } else {
      delete data.conditions;
    }

    data.actions = data.actions.map(a => {
      if (a.type === 'control_device') {
        const cmd = a.parameters.command || a.parameters.action;
        return { ...a, parameters: { action: cmd } };
      }
      if (a.type === 'notification') {
        return { ...a, parameters: { message: a.parameters.message, recipients: data.target_device_ids, channels: ['in_app', 'email'] } };
      }
      return a;
    });

    try {
      await onSubmit(data);
      toast({ title: 'Notifications sent', status: 'success', duration: 3000 });
    } catch (err) {
      toast({ title: 'Error creating rule', description: err.message, status: 'error', duration: 5000 });
    } finally {
      onClose();
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="3xl" motionPreset="slideInBottom">
      <ModalOverlay bg="blackAlpha.500" />
      <ModalContent bg={useColorModeValue('gray.50', 'gray.800')} borderRadius="xl">
        <ModalHeader borderBottomWidth="1px" borderColor={useColorModeValue('gray.200', 'gray.700')}>
          {isEditing ? 'Edit Rule' : 'Create New Rule'}
        </ModalHeader>
        <ModalCloseButton />
        <form onSubmit={handleSubmit(handleFormSubmit)} noValidate>
          <ModalBody p={6}>
            <VStack spacing={6} align="stretch">
              <FormSection title="Rule Details">
                <SimpleGrid columns={2} spacing={4}>
                  <FormControl isRequired isInvalid={errors.name}>
                    <FormLabel>Name</FormLabel>
                    <Input {...register('name', { required: 'Name is required' })} bg={inputBg} borderColor={borderColor} />
                    <FormErrorMessage>{errors.name?.message}</FormErrorMessage>
                  </FormControl>
                  <FormControl>
                    <FormLabel>Description</FormLabel>
                    <Input {...register('description')} bg={inputBg} borderColor={borderColor} />
                  </FormControl>
                  <FormControl>
                    <FormLabel>Type</FormLabel>
                    <Select {...register('rule_type')} bg={inputBg} borderColor={borderColor}>
                      <option value="condition">Condition-based</option>
                      <option value="schedule">Scheduled</option>
                    </Select>
                  </FormControl>
                  <FormControl>
                    <FormLabel>Priority</FormLabel>
                    <Input type="number" {...register('priority')} bg={inputBg} borderColor={borderColor} />
                  </FormControl>
                </SimpleGrid>
                <FormControl display="flex" alignItems="center">
                  <FormLabel htmlFor="is_enabled" mb="0">Enabled</FormLabel>
                  <Switch id="is_enabled" {...register('is_enabled')} />
                </FormControl>
              </FormSection>

              {watch('rule_type') === 'schedule' && (
                <FormSection title="Schedule Configuration">
                  <FormControl as="fieldset">
                    <FormLabel as="legend">Schedule Type</FormLabel>
                    <RadioGroup onChange={(val) => setValue('scheduleType', val)} value={watch('scheduleType')}>
                      <HStack spacing={5}>
                        <Radio value="once">One-time</Radio>
                        <Radio value="interval">Interval</Radio>
                        <Radio value="daily">Daily</Radio>
                        <Radio value="weekly">Weekly</Radio>
                      </HStack>
                    </RadioGroup>
                  </FormControl>

                  {watch('scheduleType') === 'once' && (
                    <FormControl isInvalid={errors.onceDatetime} isRequired>
                      <FormLabel>Date and Time</FormLabel>
                      <Input
                        type="datetime-local"
                        {...register('onceDatetime', {
                          validate: v => {
                            const rt = watch('rule_type');
                            const st = watch('scheduleType');
                            if (rt !== 'schedule' || st !== 'once') return true;
                            if (!v) return 'Date is required';
                            return new Date(v) > new Date() || 'Select a future date';
                          }
                        })}
                        min={minDatetimeLocal}
                        bg={inputBg}
                        borderColor={borderColor}
                      />
                      <FormErrorMessage>{errors.onceDatetime?.message}</FormErrorMessage>
                    </FormControl>
                  )}

                  {watch('scheduleType') === 'interval' && (
                    <HStack spacing={2} align="end">
                      <FormControl isRequired>
                        <FormLabel>Every</FormLabel>
                        <Input
                          type="number"
                          placeholder="e.g., 15"
                          {...register('intervalValue', { required: true, valueAsNumber: true, min: 1 })}
                          bg={inputBg}
                          borderColor={borderColor}
                        />
                      </FormControl>
                      <FormControl isRequired>
                        <FormLabel>Unit</FormLabel>
                        <Select {...register('intervalUnit')} bg={inputBg} borderColor={borderColor}>
                          <option value="minutes">Minutes</option>
                          <option value="hours">Hours</option>
                          <option value="days">Days</option>
                        </Select>
                      </FormControl>
                    </HStack>
                  )}

                  {watch('scheduleType') === 'daily' && (
                    <FormControl isRequired>
                      <FormLabel>Time of Day</FormLabel>
                      <Input type="time" {...register('time', { required: true })} bg={inputBg} borderColor={borderColor} />
                    </FormControl>
                  )}

                  {watch('scheduleType') === 'weekly' && (
                    <VStack spacing={4} align="stretch">
                      <FormControl isRequired>
                        <FormLabel>Time of Day</FormLabel>
                        <Input type="time" {...register('time', { required: true })} bg={inputBg} borderColor={borderColor} />
                      </FormControl>
                      <FormControl isRequired>
                        <FormLabel>On these days</FormLabel>
                        <CheckboxGroup onChange={(val) => setValue('weekdays', val)} value={watch('weekdays') || []}>
                          <SimpleGrid columns={{base: 2, md: 4, lg: 7}} spacing={2}>
                            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day, i) => (
                              <Checkbox key={day} value={i.toString()}>{day}</Checkbox>
                            ))}
                          </SimpleGrid>
                        </CheckboxGroup>
                      </FormControl>
                    </VStack>
                  )}
                </FormSection>
              )}

              <FormSection title="Target Devices">
                <Input 
                  placeholder="Search devices..." 
                  value={filterText} 
                  onChange={e => setFilterText(e.target.value)} 
                  mb={2} 
                  bg={inputBg}
                  borderColor={borderColor}
                />
                <Controller
                  name="target_device_ids"
                  control={control}
                  defaultValue={[]}
                  rules={{ validate: (val) => (val && val.length > 0) || 'Select at least one device' }}
                  render={({ field }) => (
                    <FormControl isInvalid={!!errors.target_device_ids}>
                      <FormLabel>Target Devices</FormLabel>
                      <Text fontSize="sm" mb={2}>{(field.value || []).length} selected</Text>
                      <CheckboxGroup value={field.value || []} onChange={(val) => field.onChange(Array.isArray(val) ? val : [val])}>
                        <Box maxH="200px" overflowY="auto" border="1px solid" borderColor={borderColor} borderRadius="md" p={2}>
                          {visibleDevices.map(dev => (
                            <Checkbox key={dev.id} value={dev.id} borderColor={borderColor}>
                              {dev.name}
                            </Checkbox>
                          ))}
                        </Box>
                      </CheckboxGroup>
                      {filteredDeviceList.length > SHOW_COUNT && (
                        <Button size="sm" variant="link" mt={2} onClick={() => setShowAllDevices(prev => !prev)}>
                          {showAllDevices ? 'Show Less' : `Show ${filteredDeviceList.length - SHOW_COUNT} more`}
                        </Button>
                      )}
                      <FormErrorMessage>{errors.target_device_ids?.message}</FormErrorMessage>
                    </FormControl>
                  )}
                />
              </FormSection>

              <FormSection title="Conditions">
                <VStack spacing={3} align="stretch">
                  {condFields.map((item, index) => (
                    <HStack key={item.id} spacing={2}>
                      <Select {...register(`conditions.${index}.type`)} bg={inputBg} borderColor={borderColor} flex={1.5}>
                        <option value="device_property">Device Property</option>
                        <option value="sensor">Sensor Reading</option>
                      </Select>
                      <Input placeholder="Property/Sensor ID" {...register(`conditions.${index}.property`)} bg={inputBg} borderColor={borderColor} flex={1.5} />
                      <Select {...register(`conditions.${index}.operator`)} bg={inputBg} borderColor={borderColor} flex={1}>
                        <option value="equals">==</option>
                        <option value="gt">&gt;</option>
                        <option value="lt">&lt;</option>
                      </Select>
                      <Input placeholder="Value" {...register(`conditions.${index}.value`)} bg={inputBg} borderColor={borderColor} flex={1} />
                      <IconButton icon={<FiTrash />} aria-label="Remove Condition" onClick={() => removeCondition(index)} />
                    </HStack>
                  ))}
                </VStack>
                <Button leftIcon={<FiPlus />} size="sm" mt={2} onClick={() => addCondition({ type: 'device_property', property: '', operator: 'equals', value: '' })}>
                  Add Condition
                </Button>
              </FormSection>

              <FormSection title="Actions">
                <VStack spacing={3} align="stretch">
                  {actFields.map((item, index) => (
                    <HStack key={item.id} spacing={2}>
                      <Select {...register(`actions.${index}.type`)} bg={inputBg} borderColor={borderColor} flex={1.5}>
                        <option value="control_device">Control Device</option>
                        <option value="notification">Send Notification</option>
                      </Select>
                      {watch(`actions.${index}.type`) === 'control_device' ? (
                        <Select {...register(`actions.${index}.parameters.action`)} bg={inputBg} borderColor={borderColor} flex={2}>
                          <option value="turn_on">Turn On</option>
                          <option value="turn_off">Turn Off</option>
                        </Select>
                      ) : (
                        <Input placeholder="Message" {...register(`actions.${index}.parameters.message`)} bg={inputBg} borderColor={borderColor} flex={2} />
                      )}
                      <IconButton icon={<FiTrash />} aria-label="Remove Action" onClick={() => removeAction(index)} />
                    </HStack>
                  ))}
                </VStack>
                <Button leftIcon={<FiPlus />} size="sm" mt={2} onClick={() => addAction({ type: 'control_device', parameters: { action: 'turn_on' } })}>
                  Add Action
                </Button>
              </FormSection>
            </VStack>
          </ModalBody>
          <ModalFooter borderTopWidth="1px" borderColor={useColorModeValue('gray.200', 'gray.700')}>
            <Button variant="ghost" onClick={onClose}>Cancel</Button>
            <Button colorScheme="blue" ml={3} type="submit">
              {isEditing ? 'Save Changes' : 'Create Rule'}
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  );
}
