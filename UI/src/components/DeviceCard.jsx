import React, { useState } from 'react';
import {
  Box, Flex, Text, Badge, Button, Progress, Icon, HStack, VStack, Heading,
  useColorModeValue, Collapse, Tooltip, useDisclosure
} from '@chakra-ui/react';
import { 
  FiPower, FiActivity, FiWifi, FiShield, FiRefreshCw, 
  FiChevronDown, FiChevronUp, FiAlertCircle, FiInfo
} from 'react-icons/fi';
import { motion } from 'framer-motion';
import { scanDevice } from '../services/device-service';
import { useToast } from '@chakra-ui/react';
import { Link as RouterLink } from 'react-router-dom';

export default function DeviceCard({ 
  device, 
  isExpanded, 
  onToggleExpand,
  onTogglePower
}) {
  const bgColor = useColorModeValue('rgba(255, 255, 255, 0.8)', 'rgba(26, 32, 44, 0.8)');
  const borderColor = useColorModeValue('rgba(0, 0, 0, 0.1)', 'rgba(255, 255, 255, 0.1)');
  const statusColor = device.is_online ? 'green' : 'red';
  
  const cardAnimation = {
    hover: { 
      scale: 1.03,
      boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.2)'
    },
    tap: { scale: 0.98 }
  };

  const toast = useToast();
  const [scanning, setScanning] = useState(false);

  const handleScan = async (e) => {
    e.stopPropagation();
    setScanning(true);
    try {
      const result = await scanDevice(device.hash_id);
      {
        const success = result.status === 'started' || result.status === 'success';
        toast({
          title: success ? 'Scan initiated' : 'Scan failed',
          description: success ? '' : (result.error || result.message || ''),
          status: success ? 'success' : 'error',
          duration: 3000,
          isClosable: true
        });
      }
    } catch (err) {
      console.error('Error scanning device:', err);
      toast({
        title: 'Scan error',
        description: err.message,
        status: 'error',
        duration: 3000,
        isClosable: true
      });
    } finally {
      setScanning(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover="hover"
      whileTap="tap"
      variants={cardAnimation}
      transition={{ duration: 0.3 }}
    >
      <Box
        p={5}
        bg={bgColor}
        borderWidth="1px"
        borderColor={device.is_online ? 'green.300' : 'red.300'}
        borderRadius="lg"
        boxShadow="sm"
        _hover={{ boxShadow: 'md', transform: 'translateY(-4px)' }}
        transition="all 0.3s"
        position="relative"
        overflow="hidden"
      >
        <Flex justify="space-between" align="center" mb={3} zIndex={1}>
          <VStack align="start" spacing={1}>
            <HStack align="center" spacing={2}>
              <Heading size="md" fontWeight="semibold" color={useColorModeValue('blue.600','blue.300')}>
                {device.name}
              </Heading>
              <Badge colorScheme="teal" variant="subtle">
                {device.type}
              </Badge>
            </HStack>
          </VStack>
          
          <HStack spacing={3}>
            <Tooltip label={`Device is ${device.is_online ? 'online' : 'offline'}`}>
              <Box 
                w={4} 
                h={4} 
                borderRadius="full" 
                bg={`${statusColor}.400`}
                border="2px solid white"
                boxShadow={`0 0 12px ${statusColor}.400`}
                zIndex={1}
              />
            </Tooltip>
            
            <Button 
              size="sm" 
              variant="ghost"
              onClick={onToggleExpand}
              _hover={{ bg: 'rgba(0, 0, 0, 0.05)' }}
            >
              <Icon as={isExpanded ? FiChevronUp : FiChevronDown} />
            </Button>
          </HStack>
        </Flex>

        <Collapse in={isExpanded} animateOpacity>
          <VStack align="stretch" spacing={4} mt={4}>
            {/* Status Bar */}
            <Box 
              h={1} 
              w="full" 
              bg={`${statusColor}.100`} 
              borderRadius="full" 
              overflow="hidden"
            >
              <Box 
                h="full" 
                w={device.is_online ? '100%' : '0%'} 
                bg={`${statusColor}.400`}
                transition="all 0.5s ease"
              />
            </Box>
            
            {/* Device Details */}
            <HStack justify="space-between">
              <HStack>
                <Icon as={FiWifi} color={device.is_online ? 'green.400' : 'gray.400'} />
                <Text fontSize="sm">{device.ip_address}</Text>
              </HStack>
              
              <Badge colorScheme="blue" variant="subtle">
                {device.last_scan || 'Never scanned'}
              </Badge>
            </HStack>
            
            {/* Health Metrics */}
            <Box>
              <HStack mb={2}>
                <Icon as={FiActivity} color="blue.400" />
                <Text fontSize="sm">Operational: {device.health_score || 95}%</Text>
              </HStack>
              <Progress 
                value={device.health_score || 95} 
                size="sm" 
                borderRadius="full"
                colorScheme={device.health_score > 85 ? 'green' : device.health_score > 60 ? 'orange' : 'red'}
                sx={{
                  '> div': {
                    transition: 'all 0.5s ease'
                  }
                }}
              />
            </Box>
            
            {/* Action Buttons */}
            <HStack spacing={3} mt={2}>
              <Button 
                size="sm" 
                leftIcon={<Icon as={FiPower} />}
                colorScheme={device.is_online ? 'green' : 'gray'}
                variant="outline"
                onClick={onTogglePower}
                flex={1}
              >
                {device.is_online ? 'Power On' : 'Power Off'}
              </Button>
              
              <Button 
                size="sm" 
                leftIcon={<Icon as={FiShield} />}
                colorScheme="blue"
                variant="outline"
                onClick={handleScan}
                flex={1}
                isLoading={scanning}
              >
                Scan
              </Button>
            </HStack>
          </VStack>
        </Collapse>
      </Box>
    </motion.div>
  );
}
