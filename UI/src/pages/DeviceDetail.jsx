import React, { useEffect, useState, useMemo } from 'react';
import { getDevice, toggleDevicePower } from '../services/device-service';
import { getDeviceReadings } from '../services/sensor-service';
import { getCompatibleFirmware, startFirmwareUpdate, getUpdateStatus } from '../services/firmware-service';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Box, 
  Heading, 
  Text, 
  Button, 
  Spinner, 
  Stack, 
  Badge, 
  useToast, 
  Table, 
  Thead, 
  Tbody, 
  Tr, 
  Th, 
  Td, 
  IconButton,
  Collapse
} from '@chakra-ui/react';
import { FiRefreshCw } from 'react-icons/fi';
import FirmwareProgress from '../components/FirmwareProgress';

export default function DeviceDetail() {
  const { id: deviceId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [device, setDevice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [readings, setReadings] = useState([]);
  const [readingsLoading, setReadingsLoading] = useState(true);
  const [compatibleFirmware, setCompatibleFirmware] = useState([]);
  const [firmwareLoading, setFirmwareLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [updateStatus, setUpdateStatus] = useState(null);

  const availableUpdates = useMemo(
    () => compatibleFirmware.filter(fw => fw.version !== device?.firmware_version),
    [compatibleFirmware, device?.firmware_version]
  );

  // Fetch device details, readings, and firmware
  const fetchDetail = async () => {
    setLoading(true);
    try {
      const data = await getDevice(deviceId);
      setDevice(data);
    } catch (err) {
      toast({ title: err.message, status: 'error' });
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  const fetchReadings = async () => {
    setReadingsLoading(true);
    try {
      const data = await getDeviceReadings(deviceId, { limit: 20 });
      setReadings(data);
    } catch (err) {
      console.error(err);
      toast({ title: err.message, status: 'error' });
    } finally {
      setReadingsLoading(false);
    }
  };
  const fetchFirmware = async () => {
    setFirmwareLoading(true);
    try {
      const data = await getCompatibleFirmware(deviceId);
      setCompatibleFirmware(data);
    } catch (err) {
      toast({ title: err.message, status: 'error' });
    } finally {
      setFirmwareLoading(false);
    }
  };
  useEffect(() => {
    fetchDetail();
    fetchReadings();
    fetchFirmware();
  }, [deviceId]);

  const handleToggle = async () => {
    if (!device) return;
    setBusy(true);
    try {
      await toggleDevicePower(deviceId, !device.is_online);
      const fresh = await getDevice(deviceId);
      setDevice(fresh);
      toast({ title: 'Power toggled', status: 'success' });
    } catch (err) {
      toast({ title: err.message, status: 'error' });
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <Spinner size='xl' />;
  if (error) return <Text color='red.500'>{error}</Text>;

  return (
    <Box p='8'>
      <Heading mb='4'>Device Details: {device.name}</Heading>
      <Stack spacing='2'>
        <Text><strong>ID:</strong> {device.hash_id}</Text>
        <Text><strong>IP:</strong> {device.ip_address}</Text>
        <Text>
          <strong>Status:</strong>{' '}
          <Badge colorScheme={device.is_online ? 'green' : 'red'}>
            {device.is_online ? 'Online' : 'Offline'}
          </Badge>
        </Text>
      </Stack>
      {/* Metadata Section */}
      <Box mt='6'>
        <Heading size='md' mb='2'>Metadata</Heading>
        {device.metadata && Object.keys(device.metadata).length > 0 ? (
          <Stack spacing='1'>
            {Object.entries(device.metadata).map(([key, value]) => (
              <Text key={key}><strong>{key}:</strong> {String(value)}</Text>
            ))}
          </Stack>
        ) : (
          <Text color='gray.500'>No metadata available.</Text>
        )}
      </Box>
      {/* Firmware Section */}
      <Box mt='6'>
        <Heading size='md' mb='2'>Firmware</Heading>
        {firmwareLoading ? (
          <Spinner />
        ) : availableUpdates.length === 0 ? (
          <Text color='green.500'>Device firmware is up to date.</Text>
        ) : (
          <Stack spacing='2'>
            <Text>Current Version: <strong>{device.firmware_version || 'Unknown'}</strong></Text>
            <Table size='sm' variant='striped'>
              <Thead>
                <Tr><Th>Version</Th><Th>Critical</Th><Th>Action</Th></Tr>
              </Thead>
              <Tbody>
                {availableUpdates.map(fw => (
                  <Tr key={fw.id}>
                    <Td>{fw.version}</Td>
                    <Td>{fw.is_critical ? 'Yes' : 'No'}</Td>
                    <Td>
                      <Button size='sm' colorScheme='blue'
                        isLoading={updating && updateStatus?.version === fw.version}
                        onClick={async () => {
                          setUpdating(true);
                          const res = await startFirmwareUpdate(deviceId, fw.version);
                          if (res.update_id) {
                            toast({ title: `Update ${res.update_id} started`, status: 'info' });
                            let status;
                            do {
                              await new Promise(r => setTimeout(r, 2000));
                              status = await getUpdateStatus(res.update_id);
                              setUpdateStatus({ ...status, version: fw.version });
                            } while (status.status === 'started' || status.status === 'in_progress');
                            toast({ title: `Update ${status.status}`, status: status.status === 'completed' ? 'success' : 'error' });
                            fetchDetail();
                          }
                          setUpdating(false);
                        }}
                      >
                        Update
                      </Button>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
            {updateStatus && (
              (updateStatus.status === 'started' || updateStatus.status === 'in_progress') ? (
                <Collapse in={true} animateOpacity>
                  <FirmwareProgress key={updateStatus.version} progress={updateStatus.job_progress?.progress ?? undefined} />
                </Collapse>
              ) : (
                <Text mt='2'>Status: {updateStatus.status}</Text>
              )
            )}
          </Stack>
        )}
      </Box>
      <Stack direction='row' spacing='4' mt='6'>
        <Button
          colorScheme={device.is_online ? 'red' : 'green'}
          onClick={handleToggle}
          isLoading={busy}
        >
          {device.is_online ? 'Turn Off' : 'Turn On'}
        </Button>
        <Button onClick={() => navigate('/devices')} variant='outline'>
          Back to Devices
        </Button>
      </Stack>

      {/* Sensor readings */}
      <Box mt='8'>
        <Heading size='md' mb='4'>Recent Sensor Readings</Heading>
        <IconButton size='sm' icon={<FiRefreshCw />} aria-label='Refresh' onClick={fetchReadings} isLoading={readingsLoading} mb='2' />
        {readingsLoading ? (
          <Spinner />
        ) : readings.length === 0 ? (
          <Text color='gray.500'>No readings available.</Text>
        ) : (
          <Table size='sm' variant='striped'>
            <Thead>
              <Tr>
                <Th>Timestamp</Th>
                <Th>Sensor</Th>
                <Th>Value</Th>
                <Th>Status</Th>
              </Tr>
            </Thead>
            <Tbody>
              {readings.map((r) => (
                <Tr key={`${r.timestamp}-${r.sensor_type}`}>
                  <Td>{new Date(r.timestamp).toLocaleString()}</Td>
                  <Td>{r.sensor_type}</Td>
                  <Td>{r.value} {r.unit || ''}</Td>
                  <Td>
                    <Badge colorScheme={r.status === 'alert' ? 'red' : r.status === 'warning' ? 'yellow' : 'green'}>
                      {r.status}
                    </Badge>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </Box>
    </Box>
  );
}
