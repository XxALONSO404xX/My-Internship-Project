import React, { useState, useEffect } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { useToast } from '@chakra-ui/react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  Button,
  Stack,
  FormControl,
  FormLabel,
  Input,
  Select,
  Switch,
  IconButton,
  Box,
  CheckboxGroup,
  Checkbox,
  HStack,
  RadioGroup,
  Radio,
  FormErrorMessage
} from '@chakra-ui/react';
import { FiPlus, FiTrash } from 'react-icons/fi';
import { getDevices } from '../services/device-service.js';

export default function RuleBuilder({ isOpen, onClose, onCreate, initialData, onUpdate }) {
  // default form values
  const defaultValues = initialData ? {
    name: initialData.name, description: initialData.description, rule_type: initialData.rule_type, is_enabled: initialData.is_enabled,
    priority: initialData.priority, scheduleType: initialData.scheduleType, onceDatetime: initialData.onceDatetime, intervalValue: initialData.intervalValue, intervalUnit: initialData.intervalUnit,
    time: initialData.time, weekdays: initialData.weekdays, target_device_ids: initialData.target_device_ids, conditions: initialData.conditions, actions: initialData.actions,
  } : {
    name: '', description: '', rule_type: 'condition', is_enabled: true,
    priority: 1, scheduleType: 'once', onceDatetime: '', intervalValue: 1, intervalUnit: 'minutes',
    time: '', weekdays: [], target_device_ids: [], conditions: [], actions: [],
  };
  const { register, control, handleSubmit, watch, setValue, reset, formState: { errors, isValid } } = useForm({ defaultValues, mode: 'onChange' });
  // reset form on open
  useEffect(() => { if (isOpen) reset(defaultValues); }, [isOpen, initialData]);
  const toast = useToast();
  // min datetime for one-time schedules
  const now = new Date();
  const minDatetimeLocal = now.toISOString().slice(0,16);

  const { fields: condFields, append: addCondition, remove: removeCondition } = useFieldArray({ control, name: 'conditions' });
  const { fields: actFields, append: addAction, remove: removeAction } = useFieldArray({ control, name: 'actions' });

  const onSubmit = (data) => {
    switch(data.scheduleType) {
      case 'once': data.schedule = data.onceDatetime; break;
      case 'interval': data.schedule = `*/${data.intervalValue} ${data.intervalUnit}`; break;
      case 'daily': data.schedule = `${data.time} * * *`; break;
      case 'weekly': data.schedule = `${data.time} * * ${data.weekdays.join(',')}`; break;
      default: data.schedule = '';
    }
    data.target_device_ids = data.target_device_ids || [];
    // only include conditions if any defined
    if (data.conditions && data.conditions.length > 0) {
      data.conditions = { operator: 'AND', conditions: data.conditions };
    } else {
      delete data.conditions;
    }
    // normalize actions: map command to action and add recipients/channels for notifications
    data.actions = data.actions.map(a => {
      if (a.type === 'control_device') {
        const cmd = a.parameters.command || a.parameters.action;
        return { ...a, parameters: { action: cmd } };
      }
      if (a.type === 'notification') {
        return { ...a, parameters: { message: a.parameters.message, recipients: data.target_device_ids, channels: ['in_app'] } };
      }
      return a;
    });
    if (initialData && onUpdate) onUpdate(data);
    else onCreate(data);
    onClose();
  };

  const [devices, setDevices] = useState([]);
  useEffect(() => { getDevices().then(res => setDevices(res)); }, []);

  const [filterText, setFilterText] = useState('');
  const selectedIds = watch('target_device_ids') || [];
  const filteredDevices = devices.filter(d => d.name.toLowerCase().includes(filterText.toLowerCase()));

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{initialData ? 'Edit Rule' : 'Create New Rule'}</ModalHeader>
        <ModalCloseButton />
        <form onSubmit={handleSubmit(onSubmit)}>
          <ModalBody>
            <Stack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Name</FormLabel>
                <Input {...register('name', { required: true })} />
              </FormControl>
              <FormControl>
                <FormLabel>Description</FormLabel>
                <Input {...register('description')} />
              </FormControl>
              <FormControl>
                <FormLabel>Type</FormLabel>
                <Select {...register('rule_type')}>
                  <option value="condition">Condition</option>
                  <option value="schedule">Schedule</option>
                </Select>
              </FormControl>
              <FormControl display="flex" alignItems="center">
                <FormLabel mb="0">Enabled</FormLabel>
                <Switch {...register('is_enabled')} />
              </FormControl>
              <FormControl>
                <FormLabel>Priority</FormLabel>
                <Input type="number" {...register('priority')} />
              </FormControl>
              <FormControl>
                <FormLabel>Schedule</FormLabel>
                <RadioGroup {...register('scheduleType')}>
                  <HStack spacing={4} mt={2}>
                    <Radio value="once">One-time</Radio>
                    <Radio value="interval">Interval</Radio>
                    <Radio value="daily">Daily</Radio>
                    <Radio value="weekly">Weekly</Radio>
                  </HStack>
                </RadioGroup>
                {watch('scheduleType') === 'once' && (
                  <>
                    <Input
                      type="datetime-local"
                      {...register('onceDatetime', { validate: v => v && new Date(v) > new Date() || 'Select future date' })}
                      mt={2}
                      min={minDatetimeLocal}
                    />
                    {errors.onceDatetime && <FormErrorMessage>{errors.onceDatetime.message}</FormErrorMessage>}
                  </>
                )}
                {watch('scheduleType') === 'interval' && (
                  <HStack mt={2} spacing={2}>
                    <Input
                      type="number"
                      placeholder="Every"
                      {...register('intervalValue', { valueAsNumber: true, min: 1 })}
                    />
                    <Select {...register('intervalUnit')}>
                      <option value="minutes">Minutes</option>
                      <option value="hours">Hours</option>
                      <option value="days">Days</option>
                    </Select>
                  </HStack>
                )}
                {watch('scheduleType') === 'daily' && (
                  <Input type="time" {...register('time')} mt={2}/>
                )}
                {watch('scheduleType') === 'weekly' && (
                  <Stack mt={2} spacing={2}>
                    <Input type="time" {...register('time')} />
                    <CheckboxGroup {...register('weekdays')}>
                      {['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].map((day,i) => (
                        <Checkbox key={day} value={i.toString()}>{day}</Checkbox>
                      ))}
                    </CheckboxGroup>
                  </Stack>
                )}
              </FormControl>
              <FormControl>
                <FormLabel>Target Devices</FormLabel>
                <Input placeholder="Search devices..." value={filterText} onChange={e => setFilterText(e.target.value)} mb={2} />
                <Checkbox
                  isChecked={selectedIds.length === devices.length}
                  isIndeterminate={selectedIds.length > 0 && selectedIds.length < devices.length}
                  onChange={() => setValue('target_device_ids', selectedIds.length === devices.length ? [] : devices.map(d => d.hash_id))}
                  mb={2}
                >
                  Select All
                </Checkbox>
                <CheckboxGroup
                  value={selectedIds}
                  onChange={vals => setValue('target_device_ids', vals)}
                >
                  <Box maxH="200px" overflowY="auto" border="1px solid" borderColor="gray.200" borderRadius="md" p={2}>
                    {filteredDevices.map(dev => (
                      <Checkbox key={dev.hash_id} value={dev.hash_id} mb={1}>
                        {dev.name}
                      </Checkbox>
                    ))}
                  </Box>
                </CheckboxGroup>
              </FormControl>
              <Box>
                <FormLabel>Conditions</FormLabel>
                {condFields.map((item, index) => (
                  <Stack direction="row" key={item.id} spacing={2} align="center">
                    <Select {...register(`conditions.${index}.type`)}>
                      <option value="device_property">Device Property</option>
                      <option value="sensor">Sensor</option>
                    </Select>
                    <Input placeholder="Property or Sensor" {...register(`conditions.${index}.property`)} />
                    <Select {...register(`conditions.${index}.operator`)}>
                      <option value="equals">Equals</option>
                      <option value="gt">Greater Than</option>
                      <option value="lt">Less Than</option>
                    </Select>
                    <Input placeholder="Value" {...register(`conditions.${index}.value`)} />
                    <IconButton icon={<FiTrash />} size="sm" onClick={() => removeCondition(index)} />
                  </Stack>
                ))}
                <Button leftIcon={<FiPlus />} size="sm" mt={2} onClick={() => addCondition({ type: 'device_property', property: '', operator: 'equals', value: '' })}>
                  Add Condition
                </Button>
              </Box>
              <Box>
                <FormLabel>Actions</FormLabel>
                {actFields.map((item, index) => {
                  const actionType = watch(`actions.${index}.type`);
                  return (
                    <Stack direction="row" key={item.id} spacing={2} align="center">
                      <Select {...register(`actions.${index}.type`)}>
                        <option value="control_device">Control Device</option>
                        <option value="set_status">Set Status</option>
                        <option value="notification">Notification</option>
                      </Select>
                      {actionType === 'control_device' && (
                        <Select {...register(`actions.${index}.parameters.action`)}>
                          <option value="turn_on">Turn On</option>
                          <option value="turn_off">Turn Off</option>
                          <option value="reboot">Reboot</option>
                        </Select>
                      )}
                      {actionType === 'set_status' && (
                        <Select {...register(`actions.${index}.parameters.status`)}>
                          <option value="active">Active</option>
                          <option value="inactive">Inactive</option>
                          <option value="maintenance">Maintenance</option>
                        </Select>
                      )}
                      {actionType === 'notification' && (
                        <Input placeholder="Notification message" {...register(`actions.${index}.parameters.message`)} />
                      )}
                      <IconButton icon={<FiTrash />} size="sm" onClick={() => removeAction(index)} />
                    </Stack>
                  );
                })}
                <Button leftIcon={<FiPlus />} size="sm" mt={2} onClick={() => addAction({ type: 'control_device', parameters: { action: 'turn_on' } })}>
                  Add Action
                </Button>
              </Box>
            </Stack>
          </ModalBody>
          <ModalFooter>
            <Button colorScheme="blue" mr={3} type="submit" disabled={!isValid}>
              {initialData ? 'Save Changes' : 'Create Rule'}
            </Button>
            <Button variant="ghost" onClick={onClose} type="button">Cancel</Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  );
}
