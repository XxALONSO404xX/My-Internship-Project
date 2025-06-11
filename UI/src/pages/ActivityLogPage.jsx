import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import {
  Box, Flex, Heading, Button, Input, HStack, VStack,
  TableContainer, Table, Thead, Tbody, Tr, Th, Td,
  Spinner, Text, useColorModeValue, Badge, Tooltip,
  useBreakpointValue, Icon, ButtonGroup, SlideFade, Tag, TagLabel, Code
} from '@chakra-ui/react';
import { useLocation, useParams } from 'react-router-dom';
import { FiDownload, FiCalendar, FiList, FiActivity } from 'react-icons/fi';
import { AiOutlineAlert, AiOutlineInfoCircle, AiOutlineCheckCircle } from 'react-icons/ai';
import { getActivitiesInRange, searchActivities } from '../services/activity-service';

export default function ActivityLogPage() {
  const location = useLocation();
  const params = useParams();
  const showAlerts = location.pathname.endsWith('/alerts');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activities, setActivities] = useState([]);
  const [startDate, setStartDate] = useState(new Date(Date.now() - 7*24*60*60*1000).toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [viewMode, setViewMode] = useState('table'); // 'table' | 'timeline'

  const bg = useColorModeValue('white', 'gray.800');
  const cardBg = useColorModeValue('white', 'gray.700');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const headerBg = useColorModeValue('primary.50', 'primary.900');
  const hoverBg = useColorModeValue('gray.50', 'gray.600');
  const isMobile = useBreakpointValue({ base: true, md: false });

  const paramsQs = new URLSearchParams(location.search);
  const pathType = params.targetType;
  const pathId = params.targetId;
  const targetType = pathType ?? paramsQs.get('targetType');
  const targetId = pathId ?? paramsQs.get('targetId');

  const load = async () => {
    setLoading(true);
    try {
      const from = `${startDate}T00:00:00Z`;
      const to = `${endDate}T23:59:59Z`;
      let data;
      if (targetType && targetId) {
        data = await searchActivities({ start_time: from, end_time: to, target_type: targetType, target_id: parseInt(targetId, 10), limit: 1000 });
      } else {
        data = await getActivitiesInRange(from, to);
      }
      setActivities(data);
    } catch (err) {
      toast.error(err.message);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [startDate, endDate, location.search, params.targetType, params.targetId]);

  // filter based on route
  const displayedActivities = showAlerts
    ? activities.filter(a => a.activity_type === 'alert')
    : activities.filter(a => a.activity_type !== 'alert');

  const exportCSV = () => {
    if (activities.length === 0) {
      toast('No data to export');
      return;
    }
    const header = Object.keys(activities[0]).join(',');
    const rows = activities.map((a) =>
      Object.values(a)
        .map((v) => `"${String(v).replace(/"/g, '""')}"`)
        .join(',')
    );
    const csv = [header, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `activities_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Exported CSV');
  };

  const getActivityBadge = (type) => {
    const colors = {
      alert: 'red',
      warning: 'orange',
      info: 'primary',
      success: 'green',
    };
    return colors[type.toLowerCase()] || 'gray';
  };

  return (
    <Box p={8}>
      <Box variant="card">
        {/* Header */}
        <Flex 
          justify="space-between" 
          align="center" 
          p={5}
          borderBottomWidth="1px"
          borderColor={useColorModeValue('gray.100', 'gray.700')}
          bg={useColorModeValue('gray.50', 'gray.900')}
        >
          <VStack align="flex-start" spacing={1}>
            <Heading size="lg" bgGradient="linear(to-r, purple.600, blue.500)" bgClip="text" mb={4}>{showAlerts ? 'Activity Alerts' : 'Activity Log'}</Heading>
            {targetType && targetId && (
              <Text fontSize="sm" color={useColorModeValue('gray.600', 'gray.400')}>
                Showing activities for {targetType} {targetId}
              </Text>
            )}
            <HStack spacing={3}>
              <HStack spacing={2} alignItems="center">
                <Icon as={FiCalendar} boxSize={5} />
                <Input 
                  type="date" 
                  value={startDate} 
                  max={endDate} 
                  onChange={e => setStartDate(e.target.value)}
                  size="md"
                  w="160px"
                />
                <Text>to</Text>
                <Input 
                  type="date" 
                  value={endDate} 
                  min={startDate} 
                  onChange={e => setEndDate(e.target.value)}
                  size="md"
                  w="160px"
                />
              </HStack>
            </HStack>
          </VStack>
          <HStack spacing={3}>
            <ButtonGroup isAttached variant="outline" size="sm">
              <Button leftIcon={<FiList />} isActive={viewMode==='table'} onClick={()=>setViewMode('table')}>
                Table
              </Button>
              <Button leftIcon={<FiActivity />} isActive={viewMode==='timeline'} onClick={()=>setViewMode('timeline')}>
                Timeline
              </Button>
            </ButtonGroup>

            <Button 
              leftIcon={<FiDownload />} 
              size="md"
              onClick={exportCSV}
              px={6}
            >
              Export CSV
            </Button>
          </HStack>
        </Flex>

        {/* Loading State */}
        {loading && (
          <Flex justify="center" p={8}>
            <Spinner size="lg" />
          </Flex>
        )}

        {/* Error State */}
        {error && (
          <Text color="red.500" p={4} textAlign="center">
            {error}
          </Text>
        )}

        {/* Empty State */}
        {!loading && displayedActivities.length === 0 && (
          <Text p={6} textAlign="center" color={useColorModeValue('gray.500', 'gray.400')}>
            No activities found for the selected period
          </Text>
        )}

        {/* Activity Content */}
        {displayedActivities.length > 0 && viewMode==='table' && (
          <TableContainer p={2}>
            <Table variant="simple" size="lg">
              <Thead>
                <Tr 
                  bg={useColorModeValue('gray.50', 'gray.700')}
                  sx={{
                    '& th': {
                      fontSize: 'md',
                      py: 4,
                      px: 4,
                      fontWeight: 'semibold',
                      color: useColorModeValue('gray.700', 'gray.200')
                    }
                  }}
                >
                  <Th>Timestamp</Th>
                  <Th>Event Type</Th>
                  <Th>Device</Th>
                  <Th>Action</Th>
                </Tr>
              </Thead>
              <Tbody>
                {displayedActivities.map((activity) => (
                  <Tr 
                    key={activity.id} 
                    _hover={{ bg: useColorModeValue('gray.50', 'gray.700') }}
                    transition="background 0.2s"
                    sx={{
                      '& td': {
                        py: 3,
                        px: 4,
                        fontSize: 'md',
                        verticalAlign: 'top'
                      }
                    }}
                  >
                    <Td whiteSpace="nowrap">
                      <Box>
                        <Text fontSize="md" fontWeight="medium">
                          {new Date(activity.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        </Text>
                        <Text fontSize="sm" color={useColorModeValue('gray.500', 'gray.400')}>
                          {new Date(activity.timestamp).toLocaleDateString([], {month: 'short', day: 'numeric'})}
                        </Text>
                      </Box>
                    </Td>
                    <Td>
                      <Badge 
                        variant="subtle"
                        colorScheme={{
                          alert: 'red',
                          warning: 'orange',
                          info: 'primary',
                          success: 'green',
                          user_action: 'purple',
                          system_event: 'primary',
                          state_change: 'teal'
                        }[activity.activity_type] || 'gray'}
                        px={3}
                        py={1}
                        borderRadius="md"
                        fontSize="sm"
                      >
                        {activity.activity_type?.replace('_', ' ') || 'unknown'}
                      </Badge>
                    </Td>
                    <Td>
                      <Box>
                        <Text fontWeight="medium">
                          {activity.target_name || `Untitled ${activity.target_type || 'item'}`}
                        </Text>
                        {activity.target_type && (
                          <Text fontSize="xs" color={useColorModeValue('gray.500', 'gray.400')}>
                            {activity.target_type} • ID: {activity.target_id || 'N/A'}
                          </Text>
                        )}
                        {activity.description && (
                          <Text fontSize="sm" color={useColorModeValue('gray.600', 'gray.300')} mt={1} noOfLines={2}>
                            {activity.description}
                          </Text>
                        )}
                      </Box>
                    </Td>
                    <Td>
                      <Text 
                        color={{
                          create: 'green.500',
                          update: 'primary.500',
                          delete: 'red.500',
                          error: 'red.500',
                          warning: 'orange.500',
                          success: 'green.500',
                          default: 'inherit'
                        }[activity.action?.toLowerCase()] || 'inherit'}
                        fontWeight="500"
                        textTransform="capitalize"
                      >
                        {activity.action?.replace(/_/g, ' ').toLowerCase()}
                      </Text>
                    </Td>
                    {/* Description is included in CSV export but not shown in the table */}
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </TableContainer>
        )}

        {/* Timeline view */}
        {displayedActivities.length > 0 && viewMode==='timeline' && (
          <Box maxH="70vh" overflowY="auto" px={6} py={4}>
            <VStack align="stretch" spacing={6} position="relative">
              {displayedActivities.map((activity, idx) => {
                const colorMap = {
                  alert: 'red',
                  warning: 'orange',
                  info: 'primary',
                  success: 'green',
                  user_action: 'purple',
                  system_event: 'primary',
                  state_change: 'teal'
                };
                const iconMap = {
                  alert: AiOutlineAlert,
                  warning: AiOutlineAlert,
                  info: AiOutlineInfoCircle,
                  success: AiOutlineCheckCircle
                };
                const color = colorMap[activity.activity_type] || 'gray';
                const IconCmp = iconMap[activity.activity_type] || AiOutlineInfoCircle;

                const isLast = idx === displayedActivities.length - 1;
                return (
                  <HStack key={activity.id} align="flex-start" spacing={4} position="relative">
                    {/* vertical line */}
                    {!isLast && (
                      <Box position="absolute" top={6} left={3} w="2px" h="calc(100% - 6px)" bg={useColorModeValue('gray.200','gray.600')} />
                    )}
                    <Icon as={IconCmp} color={`${color}.400`} boxSize={5} mt={1} />
                    <SlideFade in={true} offsetY={4} style={{ width:'100%' }}>
                      <Box bg={cardBg} p={4} borderRadius="md" shadow="sm" _hover={{ shadow:'md' }}>
                        <HStack justify="space-between">
                          <Text fontWeight="medium">{activity.action?.replace(/_/g,' ')}</Text>
                          <Text fontSize="sm" color={useColorModeValue('gray.500','gray.400')} whiteSpace="nowrap">
                            {new Date(activity.timestamp).toLocaleString()}
                          </Text>
                        </HStack>
                        <Text fontSize="sm" color={useColorModeValue('gray.600','gray.300')} mt={1}>
                          {activity.description || 'No description'}
                        </Text>
                        {activity.target_name && (
                          <Text fontSize="xs" color={useColorModeValue('gray.500','gray.400')} mt={1}>
                            {activity.target_name} ({activity.target_type})
                          </Text>
                        )}
                      </Box>
                    </SlideFade>
                  </HStack>
                );
              })}
            </VStack>
          </Box>
        )}
      </Box>
    </Box>
  );
}
