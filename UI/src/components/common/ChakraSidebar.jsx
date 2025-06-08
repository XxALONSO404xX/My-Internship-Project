import React, { useState } from 'react';
import {
  Box, VStack, Button, Icon, useColorModeValue,
  Flex, Avatar, IconButton, Menu, MenuButton, MenuList, MenuItem, Text, Divider
} from '@chakra-ui/react';
import {
  FiHome, FiGlobe, FiLayers, FiShield, FiDownload, FiUsers, FiList, FiLogOut,
  FiChevronLeft, FiChevronRight
} from 'react-icons/fi';

const ChakraSidebar = ({ activeTab, onTabChange, onLogout }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  // Background for sidebar and button states
  const bg = useColorModeValue('gray.50', 'gray.900');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const activeBg = useColorModeValue('brand.100', 'brand.700');
  const hoverBg = useColorModeValue('gray.100', 'gray.800');
  const tabs = [
    { id: 'home', label: 'Home', icon: FiHome },
    { id: 'network', label: 'Network', icon: FiGlobe },
    { id: 'devices', label: 'Devices', icon: FiLayers },
    { id: 'security', label: 'Security', icon: FiShield },
    { id: 'firmware', label: 'Firmware', icon: FiDownload },
    { id: 'groups', label: 'Groups', icon: FiUsers },
    // Clients tab removed
    { id: 'rules', label: 'Rules', icon: FiList },
  ];

  return (
    <Box
      w={isCollapsed ? '20' : '60'}
      bg={bg}
      borderRightWidth='1px'
      borderColor={borderColor}
      pt='12'
      transition='width 0.2s ease'
    >
      {/* User menu & collapse */}
      <Box px='4' pb='4'>
        <Flex align='center' justify='space-between'>
          <Menu>
            <MenuButton as={Button} variant='ghost' w='full' justifyContent={isCollapsed ? 'center' : 'flex-start'} leftIcon={<Avatar size='sm' name='User Name' />}>
              {!isCollapsed && <Text ml='2'>User Name</Text>}
            </MenuButton>
            <MenuList>
              <MenuItem>Profile</MenuItem>
              <MenuItem>Settings</MenuItem>
              <MenuItem icon={<Icon as={FiLogOut} />} onClick={onLogout}>Logout</MenuItem>
            </MenuList>
          </Menu>
          <IconButton aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'} icon={isCollapsed ? <FiChevronRight /> : <FiChevronLeft />} onClick={() => setIsCollapsed(!isCollapsed)} size='sm' variant='ghost' />
        </Flex>
      </Box>
      <Divider />
      <VStack spacing='3' align='stretch'>
        {tabs.map(tab => {
          const isActive = activeTab === tab.id;
          return (
            <Button
              key={tab.id}
              w='full'
              px={isCollapsed ? 0 : 4}
              py='3'
              variant='ghost'
              bg={isActive ? activeBg : 'transparent'}
              color={isActive ? 'brand.500' : useColorModeValue('gray.600','gray.300')}
              _hover={{ bg: hoverBg }}
              justifyContent={isCollapsed ? 'center' : 'flex-start'}
              alignItems='center'
              onClick={() => onTabChange(tab.id)}
              transition='background 0.2s, color 0.2s'
              borderRadius='md'
            >
              <Icon as={tab.icon} boxSize='5' />
              {!isCollapsed && <Text ml='3'>{tab.label}</Text>}
            </Button>
          );
        })}
      </VStack>
    </Box>
  );
};

export default ChakraSidebar;
